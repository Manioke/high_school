"""Escaped standalone weekly print grid from actual saved Course Schedules."""
from collections import defaultdict
from datetime import timedelta
from html import escape

import frappe
from frappe import _
from frappe.utils import getdate
from high_school.high_school.course_scheduling import normalise_time


def render_grid(title, subtitle, monday, slots, rows, notes='', closures=()):
    e = lambda value: escape(str(value or ''))
    cells = defaultdict(list)
    for row in rows:
        cells[(row['from_time'], row['to_time'], getdate(row['schedule_date']).weekday())].append(row)
    parts = ['<!doctype html><html><head><meta charset="utf-8"><title>' + e(title) + '</title><style>' + CSS + '</style></head><body>',
        '<div class="toolbar"><button onclick="window.print()">Print / Save PDF</button><span>Choose landscape orientation; enable background graphics for colour.</span></div>',
        '<header><div class="eyebrow">WEEKLY SCHOOL TIMETABLE</div><h1>' + e(title) + '</h1><p>' + e(subtitle) + '</p></header>',
        '<table><thead><tr><th class="time">Period / Time</th>']
    for day in range(7):
        date = monday + timedelta(days=day)
        parts.append('<th>' + e(date.strftime('%A')) + '<small>' + e(date.strftime('%d %b')) + '</small></th>')
    parts.append('</tr></thead><tbody>')
    for slot in slots:
        start, end = slot['from_time'], slot['to_time']
        parts.append('<tr><th class="time">' + e(slot.get('label')) + '<small>' + e(start[:5]) + '–' + e(end[:5]) + '</small></th>')
        # Break is shown only where configured, and never conceals a saved lesson.
        breaks = set(slot.get('break_days', []))
        if breaks == set(range(7)) and not any(cells[(start, end, d)] for d in range(7)):
            parts.append('<td colspan="7" class="break">' + e(slot.get('label') or 'Break') + '</td>')
        else:
            for day in range(7):
                values = cells[(start, end, day)]
                if values:
                    content = ''.join('<div class="lesson"><b>' + e(r['course']) + '</b><span>' + e(r['student_group']) + '</span><span>' + e(r.get('instructor_name') or r.get('instructor')) + '</span><span>' + e(r.get('room')) + '</span></div>' for r in values)
                    parts.append('<td>' + content + '</td>')
                elif day in breaks:
                    parts.append('<td class="break">' + e(slot.get('label') or 'Break') + '</td>')
                else:
                    parts.append('<td class="' + ('weekend' if day >= 5 else '') + '">' + ('<span class="closed">No teaching — holiday</span>' if monday + timedelta(days=day) in closures else '') + '</td>')
        parts.append('</tr>')
    parts.append('</tbody></table><footer><b>Notes</b><div>' + e(notes).replace('\n', '<br>') + '</div></footer><p class="legend">Blank cells have no saved lesson in this scope. Times are taken from saved schedules; breaks use the generator’s current configuration.</p></body></html>')
    return ''.join(parts)


def printable(name, week_start, student_group=None, instructor=None):
    frappe.only_for(('Academics User', 'Education Manager', 'System Manager'))
    doc = frappe.get_doc('School Timetable Generator', name)
    doc.check_permission('read')
    if bool(student_group) == bool(instructor):
        frappe.throw(_('Choose one Student Group or one Instructor.'))
    if not week_start:
        frappe.throw(_('Choose a date in the week to print.'))
    anchor = getdate(week_start)
    monday = anchor - timedelta(days=anchor.weekday())
    sunday = monday + timedelta(days=6)
    term = frappe.get_doc('School Term', doc.school_term)
    if sunday < getdate(term.start_date) or monday > getdate(term.end_date):
        frappe.throw(_('Choose a week that overlaps this School Term.'))
    filters = {'schedule_date': ['between', [max(monday, getdate(term.start_date)), min(sunday, getdate(term.end_date))]], 'docstatus': ['<', 2]}
    if student_group:
        group = frappe.get_doc('Student Group', student_group)
        group.check_permission('read')
        if group.academic_year != doc.academic_year or group.program != doc.program:
            frappe.throw(_('Choose a Student Group in this generator’s year and program.'))
        filters['student_group'] = student_group
    else:
        frappe.get_doc('Instructor', instructor).check_permission('read')
        filters['instructor'] = instructor
    # A teacher print includes all their classes in the date range, across programs.
    rows = frappe.get_list('Course Schedule', filters=filters, fields=['name', 'schedule_date', 'from_time', 'to_time', 'course', 'student_group', 'instructor', 'instructor_name', 'room'], order_by='schedule_date asc, from_time asc', limit_page_length=0)
    periods = frappe.get_all('School Period', fields=['name', 'period_name', 'from_time', 'to_time'], limit_page_length=0)
    lookup = {p.name: p for p in periods}
    slots = {}
    from high_school.high_school.timetable_operations import DAYS
    days = [DAYS.index(d.strip()) for d in (doc.teaching_days or 'Monday, Tuesday, Wednesday, Thursday, Friday').split(',') if d.strip() in DAYS]
    entries = doc.get('periods') or [frappe._dict(school_period=p.name, day='Every teaching day', is_break=0) for p in periods]
    for entry in entries:
        period = lookup.get(entry.school_period)
        if not period or period.from_time is None or period.to_time is None:
            continue
        start, end = normalise_time(period.from_time), normalise_time(period.to_time)
        item = slots.setdefault((start, end), dict(label=period.period_name or period.name, from_time=start, to_time=end, break_days=[]))
        if entry.is_break:
            targets = days if entry.day == 'Every teaching day' else ([DAYS.index(entry.day)] if entry.day in DAYS else [])
            item['break_days'].extend(targets)
    for row in rows:
        row.from_time, row.to_time = normalise_time(row.from_time), normalise_time(row.to_time)
        slots.setdefault((row.from_time, row.to_time), dict(label='Lesson', from_time=row.from_time, to_time=row.to_time))
    closures = set()
    if doc.holiday_list:
        closures = {getdate(d) for d in frappe.get_all('Holiday', filters={'parent': doc.holiday_list, 'parenttype': 'Holiday List', 'holiday_date': ['between', [monday, sunday]]}, pluck='holiday_date', limit_page_length=0)}
    title = student_group or frappe.db.get_value('Instructor', instructor, 'instructor_name') or instructor
    subtitle = f'{doc.school_term} · Week of {monday:%d %B %Y}'
    return render_grid(title, subtitle, monday, [slots[k] for k in sorted(slots)], rows, doc.print_notes or '', closures)


CSS = '''
@page{size:A4 landscape;margin:10mm}*{box-sizing:border-box}body{font:12px Arial,sans-serif;color:#233744;margin:24px auto;max-width:1400px;padding:0 18px}header{border-top:5px solid #2996a4;padding:14px 0 10px}.eyebrow{font-size:10px;letter-spacing:2px;color:#337982}h1{font-size:26px;margin:5px 0}header p{margin:5px 0;color:#526775}table{width:100%;border-collapse:collapse;table-layout:fixed}thead th{background:#dda334;color:#172935;padding:9px 3px;text-align:center;font-size:11px}th small{display:block;font-weight:normal;margin-top:5px;font-size:10px}td,th{border:1px solid #acb9c0}tbody td{height:66px;vertical-align:top;padding:6px 4px}.time{width:90px;font-size:10px;text-align:center}tbody .time{background:#f4f7f8}td.break{background:#f6e6c5;text-align:center;vertical-align:middle;color:#665025;height:28px}.weekend{background:#f8fafb}.lesson{border-left:3px solid #43a6ae;padding-left:5px;margin-bottom:4px;overflow-wrap:anywhere}.lesson b{display:block;font-size:11px}.lesson span{display:block;font-size:9px;margin-top:3px}.closed{font-size:9px;color:#677c87}footer{border-bottom:2px solid #dda334;margin-top:14px;padding:10px 0;display:flex;gap:18px;min-height:44px}footer div{white-space:normal;overflow-wrap:anywhere}.legend{font-size:9px;color:#61717a}.toolbar{display:flex;gap:16px;align-items:center;margin-bottom:15px;font-size:11px}.toolbar button{background:#256a78;color:white;border:0;border-radius:5px;padding:10px 16px;cursor:pointer}tr{break-inside:avoid}thead{display:table-header-group}@media print{body{margin:0;padding:0;max-width:none;font-size:10px}.toolbar{display:none}*{-webkit-print-color-adjust:exact;print-color-adjust:exact}tbody td{height:48px}header{padding:8px 0}h1{font-size:22px}}
'''
