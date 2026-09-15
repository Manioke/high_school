"""Preview/apply and printable data for the School Timetable Generator."""
from collections import defaultdict
from datetime import timedelta
from hashlib import sha256
from html import escape
import json

import frappe
from frappe import _
from frappe.utils import cint, getdate, now_datetime
from frappe.model.delete_doc import check_if_doc_is_linked, check_if_doc_is_dynamically_linked

from high_school.high_school.course_scheduling import normalise_time
from high_school.high_school.timetable_planning import plan_timetable, signature, PlanningError

DAYS = ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')
ROLES = ('Academics User', 'Education Manager', 'System Manager')


def require_access(doc):
    frappe.only_for(ROLES)
    doc.check_permission('write')


def configuration(doc):
    term = frappe.get_doc('School Term', doc.school_term)
    if term.academic_year != doc.academic_year:
        frappe.throw(_('The School Term must belong to the selected Academic Year.'))
    if not doc.effective_from:
        frappe.throw(_('Choose Schedule From: tomorrow or a later date.'))
    start = getdate(doc.effective_from)
    end = getdate(doc.schedule_until or term.end_date)
    if start <= getdate():
        frappe.throw(_('Schedule From must be tomorrow or later. Past and current-day lessons are protected.'))
    if start < getdate(term.start_date) or end > getdate(term.end_date) or end < start:
        frappe.throw(_('The scheduling range must be within the School Term, with From on or before Until.'))
    labels = [s.strip() for s in (doc.teaching_days or '').split(',') if s.strip()]
    if not labels or any(s not in DAYS for s in labels) or len(labels) != len(set(labels)):
        frappe.throw(_('Enter unique full weekday names, separated by commas.'))
    days = sorted(DAYS.index(s) for s in labels)
    for field in ('max_periods_per_day', 'max_teacher_periods_per_day'):
        if cint(doc.get(field)) < 0:
            frappe.throw(_('Daily limits cannot be negative.'))
    periods = frappe.get_all('School Period', fields=['name', 'period_name', 'from_time', 'to_time'], order_by='from_time asc', limit_page_length=0)
    lookup = {p.name: p for p in periods}
    entries = list(doc.get('periods') or []) or [frappe._dict(school_period=p.name, day='Every teaching day', is_break=0) for p in periods]
    slots, display = defaultdict(list), defaultdict(list)
    for entry in entries:
        p = lookup.get(entry.school_period)
        if not p or p.from_time is None or p.to_time is None:
            frappe.throw(_('Every selected School Period needs valid From and To times.'))
        item = dict(name=p.name, label=p.period_name or p.name, from_time=normalise_time(p.from_time), to_time=normalise_time(p.to_time), is_break=cint(entry.is_break))
        if item['from_time'] >= item['to_time']:
            frappe.throw(_('School Period From Time must be before To Time.'))
        if entry.day not in ('Every teaching day', *DAYS):
            frappe.throw(_('Choose a valid day for each period.'))
        targets = days if entry.day == 'Every teaching day' else [DAYS.index(entry.day)]
        if any(day not in days for day in targets):
            frappe.throw(_('A period is assigned to a day outside Teaching Days.'))
        for day in targets:
            display[day].append(dict(item))
            if not item['is_break']:
                slots[day].append(dict(item))
    for day in days:
        display[day].sort(key=lambda p: p['from_time'])
        for first, second in zip(display[day], display[day][1:]):
            if first['to_time'] > second['from_time']:
                frappe.throw(_('Overlapping or duplicate periods on {0}: {1} and {2}.').format(DAYS[day], first['label'], second['label']))
        slots[day].sort(key=lambda p: p['from_time'])
        if not slots[day]:
            frappe.throw(_('Select at least one teaching period for {0}.').format(DAYS[day]))
    holidays = []
    if doc.holiday_list:
        holidays = [getdate(d) for d in frappe.get_all('Holiday', filters={'parent': doc.holiday_list, 'parenttype': 'Holiday List', 'holiday_date': ['between', [start, end]]}, pluck='holiday_date', limit_page_length=0)]
    unavailable = []
    for row in doc.get('unavailability') or []:
        if not row.from_date or not row.to_date or getdate(row.from_date) > getdate(row.to_date):
            frappe.throw(_('Each unavailability row needs a valid date range.'))
        item = {k: row.get(k) for k in ('instructor', 'room', 'student_group')}
        item.update(from_date=getdate(row.from_date), to_date=getdate(row.to_date))
        if bool(row.from_time) != bool(row.to_time):
            frappe.throw(_('Enter both unavailable times or leave both blank for all day.'))
        if row.from_time and row.to_time:
            item.update(from_time=normalise_time(row.from_time), to_time=normalise_time(row.to_time))
            if item['from_time'] >= item['to_time']:
                frappe.throw(_('Unavailability From Time must be before To Time.'))
        # School-wide full-day closures reduce partial-week quotas too.
        if not any(item.get(k) for k in ('instructor', 'room', 'student_group')) and not item.get('from_time'):
            date = max(start, item['from_date'])
            while date <= min(end, item['to_date']):
                holidays.append(date)
                date += timedelta(days=1)
        unavailable.append(item)
    return dict(start=start, end=end, slots=dict(slots), display=dict(display), holidays=sorted(set(holidays)), unavailable=unavailable)


def _schedule_rows(start, end):
    fields = ['name', 'modified', 'docstatus', 'student_group', 'course', 'instructor', 'room', 'schedule_date', 'from_time', 'to_time', 'custom_period', 'custom_school_term', 'custom_timetable_generator']
    rows = frappe.get_all('Course Schedule', filters={'schedule_date': ['between', [start, end]], 'docstatus': ['<', 2]}, fields=fields, order_by='name asc', limit_page_length=0)
    for row in rows:
        row.schedule_date = getdate(row.schedule_date)
        row.from_time, row.to_time = normalise_time(row.from_time), normalise_time(row.to_time)
    return rows


def _protect_removals(rows):
    for row in rows:
        doc = frappe.get_doc('Course Schedule', row['name'])
        doc.check_permission('delete')
        if cint(doc.docstatus) != 0:
            frappe.throw(_('Schedule {0} is submitted and cannot be replaced. Choose a later date or resolve it manually.').format(doc.name))
        # Ordinary static and dynamic link checks include attendance. Never force-delete.
        check_if_doc_is_linked(doc)
        check_if_doc_is_dynamically_linked(doc)


def build_preview(doc):
    require_access(doc)
    doc.validate()
    if not doc.courses:
        frappe.throw(_('Load or add course requirements first.'))
    cfg = configuration(doc)
    all_existing = _schedule_rows(cfg['start'], cfg['end'])
    replace = doc.schedule_mode == 'Replace future lessons'
    if doc.schedule_mode not in ('Add missing lessons', 'Replace future lessons'):
        frappe.throw(_('Select a valid scheduling mode.'))
    owned = [row for row in all_existing if replace and row.custom_timetable_generator == doc.name and row.custom_school_term == doc.school_term]
    owned_names = {r.name for r in owned}
    unaffected = [dict(r) for r in all_existing if r.name not in owned_names]
    courses = [dict(row.as_dict()) for row in doc.courses]
    group_names = sorted({r['student_group'] for r in courses + unaffected})
    group_fields = {f.fieldname for f in frappe.get_meta('Student Group').fields}
    batch_field = next((f for f in ('student_batch_name', 'student_batch', 'batch') if f in group_fields), None)
    groups = frappe.get_all('Student Group', filters={'name': ['in', group_names]}, fields=['name', 'academic_year', 'program', 'course'] + ([f'{batch_field} as student_batch'] if batch_field else []), limit_page_length=0)
    groups.sort(key=lambda g: g.name)
    group_lookup = {g.name: g for g in groups}
    # Derive option metadata from trusted Student Group data, not read-only client fields.
    from high_school.high_school.doctype.school_timetable_generator.school_timetable_generator import _option_block
    for row in courses + unaffected:
        group = group_lookup.get(row['student_group'])
        if not group:
            frappe.throw(_('Student Group no longer exists: {0}').format(row['student_group']))
        row['student_batch'] = group.get('student_batch')
        row['option_block'] = _option_block(group.name)
    room_required = cint(frappe.db.get_single_value('School MIS Settings', 'require_rooms_for_timetable'))
    for row in courses:
        group = group_lookup[row['student_group']]
        if group.academic_year != doc.academic_year or group.program != doc.program or (doc.student_batch and group.get('student_batch') != doc.student_batch):
            frappe.throw(_('Course rows must belong to the selected year, program and batch. Reload the courses after changing these filters.'))
        if group.course and group.course != row['course']:
            frappe.throw(_('Course {0} does not match course-based Student Group {1}.').format(row['course'], row['student_group']))
        if not row.get('instructor') or (room_required and not row.get('room')):
            frappe.throw(_('Every course needs an Instructor and, when required by MIS Settings, a Room.'))
        if cint(row.get('max_per_day')) < 0:
            frappe.throw(_('Maximum Lessons per Day cannot be negative.'))
    frequencies = defaultdict(set)
    for row in courses:
        if row.get('option_block') and row.get('student_batch'):
            frequencies[(row['student_batch'], row['option_block'])].add(cint(row['periods_per_week']))
    if any(len(v) != 1 for v in frequencies.values()):
        frappe.throw(_('Simultaneous option classes must have the same weekly load.'))
    # Assessment Plans occupy group, room and supervising teacher slots too.
    exam_fields = {f.fieldname for f in frappe.get_meta('Assessment Plan').fields}
    exam_names = [f for f in ('name', 'modified', 'student_group', 'room', 'supervisor', 'schedule_date', 'from_time', 'to_time') if f in exam_fields or f in ('name', 'modified')]
    exams = frappe.get_all('Assessment Plan', filters={'schedule_date': ['between', [cfg['start'], cfg['end']]], 'docstatus': ['<', 2]}, fields=exam_names, order_by='name asc', limit_page_length=0)
    blockers = []
    for exam in exams:
        if exam.get('from_time') is not None and exam.get('to_time') is not None:
            blockers.append(dict(student_group=exam.get('student_group'), room=exam.get('room'), instructor=exam.get('supervisor'), schedule_date=getdate(exam.schedule_date), from_time=normalise_time(exam.from_time), to_time=normalise_time(exam.to_time)))
    try:
        planned, quotas = plan_timetable(courses, cfg['slots'], cfg['start'], cfg['end'], unaffected + blockers, cfg['holidays'], cfg['unavailable'], cint(doc.max_periods_per_day), cint(doc.max_teacher_periods_per_day), preferred_rows=owned)
    except PlanningError as exc:
        frappe.throw(escape(str(exc)).replace('\n', '<br>'), title=_('Timetable needs changes'))
    by_signature = defaultdict(list)
    for row in owned:
        by_signature[signature(row)].append(row)
    additions, retained = [], []
    for row in planned:
        matches = by_signature[signature(row)]
        if matches:
            retained.append(matches.pop()['name'])
        else:
            additions.append(row)
    removals = [row for matches in by_signature.values() for row in matches]
    removals.sort(key=lambda r: r['name'])
    if len(removals) > 5000:
        frappe.throw(_('This replacement exceeds 5,000 removed lessons. Use a shorter date range.'))
    _protect_removals(removals)
    # Hash server-built data, including all collision inputs and the saved generator.
    snapshot = dict(generator=doc.as_dict(), configuration=cfg, existing=all_existing, exams=exams, groups=groups, room_required=room_required, additions=additions, removals=removals)
    digest = sha256(json.dumps(snapshot, sort_keys=True, default=str).encode()).hexdigest()
    final_rows = unaffected + additions + [dict(r) for r in owned if r.name in set(retained)]
    teacher_days = defaultdict(lambda: defaultdict(int))
    selected_teachers = {r['instructor'] for r in courses}
    for row in final_rows:
        if row.get('instructor') in selected_teachers:
            teacher_days[row['instructor']][str(row['schedule_date'])] += 1
    workloads = [dict(instructor=teacher, total_lessons=sum(counts.values()), busiest_day=max(counts.values(), default=0), days_over_limit=sum(count > cint(doc.max_teacher_periods_per_day) for count in counts.values()) if cint(doc.max_teacher_periods_per_day) else 0) for teacher, counts in sorted(teacher_days.items())]
    return dict(token=digest, start=str(cfg['start']), end=str(cfg['end']), mode=doc.schedule_mode,
        additions=additions, removals=[dict(r) for r in removals], retained=retained,
        unaffected=len(unaffected), workloads=workloads, quotas=quotas, weeks=len({q['week'] for q in quotas}),
        warning='Partial weeks use rounded-up proportional weekly loads. Unchanged matching records keep their names. Only this generator’s records in this date range can be replaced.')


def preview(name):
    doc = frappe.get_doc('School Timetable Generator', name)
    result = build_preview(doc)
    frappe.cache.set_value(f'timetable-preview:{frappe.session.user}:{name}', result['token'], expires_in_sec=900)
    return result


def apply(name, token):
    frappe.only_for(ROLES)
    # Transaction-held row lock serializes all generator applies on this site,
    # across generator documents. It is released by the request commit/rollback.
    frappe.db.sql('SELECT name FROM `tabDocType` WHERE name=%s FOR UPDATE', ('School Timetable Generator',))
    doc = frappe.get_doc('School Timetable Generator', name)
    require_access(doc)
    key = f'timetable-preview:{frappe.session.user}:{name}'
    if not token or frappe.cache.get_value(key) != token:
        frappe.throw(_('Preview this timetable again; the preview has expired or was already applied.'))
    result = build_preview(doc)
    if result['token'] != token:
        frappe.throw(_('Schedules or settings changed since the preview. Preview again before applying.'))
    frappe.db.savepoint('timetable_apply')
    try:
        for row in result['removals']:
            frappe.delete_doc('Course Schedule', row['name'])
        created = []
        for row in result['additions']:
            payload = {k: row.get(k) for k in ('student_group', 'course', 'instructor', 'room', 'schedule_date', 'from_time', 'to_time', 'custom_period')}
            payload.update(program=doc.program, doctype='Course Schedule', custom_school_term=doc.school_term, custom_timetable_generator=doc.name)
            schedule = frappe.get_doc(payload)
            schedule.insert()
            created.append(schedule.name)
        doc.generated_schedule_count = len(created)
        doc.last_generated_on = now_datetime()
        doc.save()
        audit = dict(from_date=result['start'], until=result['end'], mode=result['mode'], removed=result['removals'], added=[dict(row, name=name) for row, name in zip(result['additions'], created)], retained=result['retained'])
        doc.add_comment('Comment', '<b>Timetable applied</b><pre>' + escape(json.dumps(audit, indent=2, default=str)) + '</pre>')
    except Exception:
        frappe.db.rollback(save_point='timetable_apply')
        raise
    frappe.cache.delete_value(key)
    return dict(created=created, removed=[r['name'] for r in result['removals']], retained=len(result['retained']), weeks=result['weeks'])
