"""Deterministic, database-free timetable planning. No writes occur here."""
from collections import defaultdict
from datetime import timedelta
from math import ceil


class PlanningError(ValueError):
    pass


def signature(row):
    return tuple(str(row.get(k) or '') for k in (
        'student_group', 'course', 'instructor', 'room', 'schedule_date',
        'from_time', 'to_time', 'custom_period'))


def overlaps(a, b):
    return a['from_time'] < b['to_time'] and a['to_time'] > b['from_time']


def plan_timetable(courses, slots, start, end, existing, holidays=(), unavailable=(),
                   max_group_daily=0, max_teacher_daily=0, preferred_rows=()):
    """Weekly quotas prorate over actual eligible dates; no dates before start.

    slots maps weekday -> sorted teaching periods, each with name/from/to.
    A greedy allocation prefers the previous week's pattern and spreads a
    course across days. It does not claim that every feasible problem is solved.
    """
    by_date = defaultdict(list)
    for row in existing:
        by_date[row['schedule_date']].append(row)
    weeks = defaultdict(list)
    current = start
    while current <= end:
        if slots.get(current.weekday()) and current not in holidays:
            weeks[current - timedelta(days=current.weekday())].append(current)
        current += timedelta(days=1)
    if not weeks:
        raise PlanningError('There are no teaching dates in the selected range.')
    bundles = defaultdict(list)
    for row in courses:
        key = ('option', row.get('student_batch'), row['option_block']) if row.get('option_block') and row.get('student_batch') else ('course', row['student_group'], row['course'])
        bundles[key].append(row)
    bundles = sorted(bundles.items(), key=lambda pair: (-int(pair[1][0]['periods_per_week']), str(pair[0])))
    for key, rows in bundles:
        for field in ('instructor', 'room', 'student_group'):
            values = [r[field] for r in rows if r.get(field)]
            if len(values) != len(set(values)):
                raise PlanningError(f'{key[-1]} uses the same {field.replace("_", " ")} in simultaneous option classes.')
    planned, errors, quotas = [], [], []
    preferred = defaultdict(set)
    for key, bundle in bundles:
        for old in preferred_rows:
            if any(old.get('student_group') == row['student_group'] and old.get('course') == row['course'] for row in bundle):
                preferred[key].add((old['schedule_date'].weekday(), old.get('custom_period')))
    teaching_days = len([day for day in slots if slots[day]])

    def blocked(row, day, period):
        daily = by_date[day]
        for other in daily:
            if overlaps(period, other):
                if any(row.get(k) and row.get(k) == other.get(k) for k in ('student_group', 'instructor', 'room')):
                    return True
                # Separate option groups in the same batch cannot overlap other blocks.
                if (row.get('student_batch') and row.get('student_batch') == other.get('student_batch')
                        and row.get('option_block') and other.get('option_block')
                        and row['option_block'] != other['option_block']):
                    return True
        for rule in unavailable:
            if not rule['from_date'] <= day <= rule['to_date']:
                continue
            scopes = [k for k in ('instructor', 'room', 'student_group') if rule.get(k)]
            if scopes and not all(row.get(k) == rule[k] for k in scopes):
                continue
            if not rule.get('from_time') or overlaps(period, rule):
                return True
        for field, cap in (('student_group', max_group_daily), ('instructor', max_teacher_daily)):
            occupied = {(r['from_time'], r['to_time']) for r in daily if r.get('course') and r.get(field) == row[field]}
            if cap and len(occupied) >= cap:
                return True
        course_cap = int(row.get('max_per_day') or 1)
        if sum(r.get('student_group') == row['student_group'] and r.get('course') == row['course'] for r in daily) >= course_cap:
            return True
        return False

    for monday, days in sorted(weeks.items()):
        for key, rows in bundles:
            required = ceil(int(rows[0]['periods_per_week']) * len(days) / teaching_days)
            quotas.append({'week': str(monday), 'group': rows[0]['student_group'], 'course': rows[0]['course'], 'required': required, 'teaching_days': len(days)})
            row_slots = []
            for row in rows:
                row_slots.append({(day, r['from_time'], r['to_time']) for day in days for r in by_date[day]
                    if all(r.get(k) == row.get(k) for k in ('student_group', 'course', 'instructor', 'room'))})
            common = set.intersection(*row_slots)
            placed = len(common)
            candidates = [(day, period) for day in days for period in slots[day.weekday()]]
            while placed < required:
                def rank(candidate):
                    day, period = candidate
                    same_course = sum(r.get('student_group') == rows[0]['student_group'] and r.get('course') == rows[0]['course'] for r in by_date[day])
                    return (same_course, (day.weekday(), period['name']) not in preferred[key], len(by_date[day]), day, period['from_time'])
                candidates.sort(key=rank)
                chosen = next(((day, p) for day, p in candidates if not any(blocked(row, day, p) for row in rows)), None)
                if not chosen:
                    errors.append(f'Week of {monday}: {key[-1]} ({placed} of {required} lessons placed). Check available periods, daily limits, teacher/room availability and conflicts.')
                    break
                day, period = chosen
                candidates.remove(chosen)
                for row in rows:
                    item = {k: row.get(k) for k in ('student_group', 'course', 'instructor', 'room', 'student_batch', 'option_block')}
                    item.update(schedule_date=day, from_time=period['from_time'], to_time=period['to_time'], custom_period=period['name'])
                    planned.append(item)
                    by_date[day].append(item)
                preferred[key].add((day.weekday(), period['name']))
                placed += 1
    if errors:
        raise PlanningError('Nothing was changed.\n' + '\n'.join(errors[:50]))
    if len(planned) > 5000:
        raise PlanningError('This operation would create more than 5,000 lessons. Split the generator into smaller groups or use a shorter date range.')
    return planned, quotas
