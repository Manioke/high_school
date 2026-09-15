"""Evidence-based academic explanations, without attributing unproven causes."""
from collections import Counter, defaultdict
from datetime import date, datetime
from html import unescape
from html.parser import HTMLParser
import math

CLOSED = {"Closed - Successful", "Closed - Not Required"}
PLAN_FIELDS = [
    "name", "student", "student_name", "intervention_type", "school_term", "course",
    "student_group", "instructor", "status", "assigned_to", "root_cause",
    "diagnosis_notes", "opened_on", "monitoring_started_on", "review_date",
]
ACTION_FIELDS = ["name", "parent", "action_type", "assigned_to", "due_date", "status", "completion_notes"]


class _Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
    def handle_data(self, data):
        self.parts.append(data)


def has_evidence(value):
    parser = _Text()
    parser.feed(str(value or ""))
    return bool(unescape("".join(parser.parts)).replace("\xa0", " ").strip())


def _date(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def number(value):
    if value is None or value == "":
        return None
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (ValueError, TypeError):
        return None


def follow_up(plan, actions, as_of, window_days=21):
    """Report missing records, never infer effort from status or a timestamp."""
    as_of = _date(as_of)
    active = [a for a in actions if a.get("status") != "Cancelled"]
    started = any(a.get("status") == "In Progress" or
                  (a.get("status") == "Completed" and has_evidence(a.get("completion_notes")))
                  for a in active)
    diagnosed = bool(plan.get("root_cause") and has_evidence(plan.get("diagnosis_notes")))
    gaps = []
    overdue = [a for a in active if a.get("status") != "Completed"
               and _date(a.get("due_date")) and _date(a["due_date"]) < as_of]
    opened = _date(plan.get("opened_on"))
    age = max((as_of - opened).days, 0) if opened else None
    late_start = bool(not started and age is not None and age > window_days)
    if plan.get("status") not in CLOSED:
        if not diagnosed:
            gaps.append("Diagnosis or supporting notes missing")
        if not active:
            gaps.append("No active action recorded")
        elif not started:
            gaps.append("No action marked In Progress or completed with evidence")
        if late_start:
            gaps.append(f"No recorded start after {age} days (follow-up window: {window_days})")
        if overdue:
            gaps.append(f"{len(overdue)} action(s) past their recorded due date")
        if any(a.get("status") == "Completed" and not has_evidence(a.get("completion_notes")) for a in active):
            gaps.append("Completed action lacks completion evidence")
        if any(not a.get("assigned_to") for a in active):
            gaps.append("Action owner missing")
        if any(not a.get("due_date") for a in active):
            gaps.append("Action due date missing")
        if not plan.get("assigned_to"):
            gaps.append("Plan owner missing")
    return {
        "diagnosed": diagnosed, "started": started, "days_open": age,
        "late_start": late_start and plan.get("status") not in CLOSED,
        "overdue_actions": len(overdue) if plan.get("status") not in CLOSED else 0,
        "overdue_owners": sorted({a.get("assigned_to") or "Unassigned" for a in overdue}),
        "next_due_date": min((str(a["due_date"])[:10] for a in active
                              if a.get("due_date") and a.get("status") != "Completed"), default=None),
        "gaps": gaps,
    }


def explain_scope(label, average, summaries, plans, actions, target, as_of,
                  window_days=21, blocked=False, provisional=False):
    counts = Counter(r.get("student") for r in summaries if r.get("student"))
    ambiguous = {student for student, count in counts.items() if count > 1}
    eligible = [r for r in summaries if r.get("status") == "Complete"
                and r.get("student") and r.get("student") not in ambiguous
                and number(r.get("overall_percentage")) is not None]
    low = {r["student"] for r in eligible if number(r["overall_percentage"]) < target}
    scope_plans = [p for p in plans if p.get("student") in low and p.get("intervention_type") == "Academic"]
    by_plan = defaultdict(list)
    for action in actions:
        by_plan[action.get("parent")].append(action)
    causes = defaultdict(set)
    diagnosed_students, covered = set(), set()
    attention, unstarted, overdue, late_starts = [], 0, 0, 0
    for plan in scope_plans:
        covered.add(plan["student"])
        state = follow_up(plan, by_plan[plan["name"]], as_of, window_days)
        if state["diagnosed"]:
            causes[plan["root_cause"]].add(plan["student"])
            diagnosed_students.add(plan["student"])
        if plan.get("status") not in CLOSED:
            unstarted += int(not state["started"])
            overdue += state["overdue_actions"]
            late_starts += int(state["late_start"])
            if state["gaps"]:
                attention.append({
                    "plan": plan["name"], "student": plan.get("student"),
                    "course": plan.get("course"), "assigned_to": plan.get("assigned_to"),
                    "status": plan.get("status"), **state,
                })
    cause_rows = [{"cause": cause, "students": len(students)} for cause, students in causes.items()]
    cause_rows.sort(key=lambda r: (-r["students"], r["cause"]))
    attention.sort(key=lambda r: (-r["overdue_actions"], -int(r["late_start"]), -(r["days_open"] or 0), r["plan"]))
    average = number(average)
    invalid_complete = any(r.get("status") == "Complete" and
                           (not r.get("student") or number(r.get("overall_percentage")) is None
                            or not 0 <= number(r.get("overall_percentage")) <= 100) for r in summaries)
    blocked = blocked or bool(ambiguous) or invalid_complete
    if blocked:
        answer = "A reliable comparison is unavailable because performance records are duplicated, invalid or ambiguous. Correct the records before drawing conclusions."
    elif average is None:
        answer = "No usable academic average is available. Complete and review the performance summaries before diagnosing a target gap."
    elif average >= target:
        answer = f"{label} is at or above the {target:g}% target ({average:g}%). {len(low)} assessed student(s) are still below target."
    else:
        answer = f"{label} averages {average:g}%, {target-average:.1f} percentage points below the {target:g}% target. {len(low)} of {len(eligible)} students with usable complete summaries are below target."
    if not blocked and low:
        if cause_rows:
            recorded = "; ".join(f"{r['cause']} ({r['students']} student(s))" for r in cause_rows[:3])
            answer += f" Staff-recorded explanations include {recorded}. These are recorded diagnoses, not verified causal findings."
        else:
            answer += " There are no supported recorded diagnoses for these students; the records do not yet explain why."
        answer += f" {len(low-diagnosed_students)} below-target student(s) have no diagnosis supported by notes; {len(low-covered)} have no academic intervention plan in this term."
        if unstarted or overdue:
            answer += f" Follow-up gaps: {unstarted} open plan(s) have no recorded action start; {overdue} action(s) are overdue. These show missing or late recorded follow-up, not proof that a teacher caused the results."
    coverage = f"{len(eligible)} usable complete summaries; {sum(r.get('status') != 'Complete' for r in summaries)} incomplete/other summaries; {sum(int(r.get('docstatus') or 0) == 0 for r in summaries)} draft summaries."
    if provisional:
        coverage += " Performance-period coverage is incomplete; this is not a fully covered school result."
    next_steps = []
    if blocked or average is None:
        next_steps.append("Resolve missing, invalid or duplicate performance data before attributing the result to a student or staff member.")
    else:
        if low - diagnosed_students:
            next_steps.append(f"Request a supported diagnosis for {len(low-diagnosed_students)} below-target student(s); review the linked plans with their owners.")
        if low - covered:
            next_steps.append(f"Review {len(low-covered)} student(s) without a plan against the automation threshold and submitted-summary requirements; create an intervention where justified.")
        if overdue or late_starts:
            next_steps.append("Ask the named owners for a progress update and completion evidence or an agreed revised due date; refer unresolved delays to the Head of Department.")
        suggestions = {
            "High Absence": "For recorded High Absence, review attendance evidence and agree a catch-up/attendance action with the student and guardian.",
            "Conceptual / Knowledge Gap": "For recorded knowledge gaps, identify the weak concept, assign focused practice and record a reassessment date.",
            "Incomplete Work": "For recorded incomplete work, agree which tasks will be completed, by when, and how the teacher will check them.",
            "Teacher / Course Delivery Review": "For recorded delivery concerns, ask the Head of Department to review lesson, assessment and support evidence before deciding responsibility.",
            "Financial Barrier": "For recorded financial barriers, arrange a confidential review with the appropriate finance/support staff; do not assume unpaid fees caused the result.",
            "Data Error / Not a Valid Concern": "Review the recorded data concern and correct the source result through the normal approval process before regenerating summaries.",
        }
        for row in cause_rows[:3]:
            if row["cause"] in suggestions:
                next_steps.append(suggestions[row["cause"]])
    return {
        "next_steps": next_steps,
        "scope": label, "average": average, "target": target,
        "gap": round(target-average, 1) if average is not None and not blocked else None,
        "below_target": average is not None and average < target and not blocked,
        "blocked": blocked, "answer": answer, "coverage": coverage,
        "assessed_students": len(eligible), "below_target_students": len(low),
        "diagnosed_students": len(diagnosed_students), "without_plan": len(low-covered),
        "missing_diagnosis": len(low-diagnosed_students), "unstarted_plans": unstarted,
        "late_start_plans": late_starts, "overdue_actions": overdue,
        "causes": cause_rows, "attention_count": len(attention), "attention": attention[:50],
        "plan_owners": dict(Counter(r.get("assigned_to") or "Unassigned" for r in attention)),
    }


def get_academic_explanations(school_term, performance, settings):
    import frappe
    from frappe.utils import nowdate
    frappe.only_for(("Academics User", "Education Manager", "System Manager"))
    target = number(settings.get("academic_performance_target"))
    target = 60 if target is None else target
    raw_window = settings.get("intervention_follow_up_days")
    window = 21 if raw_window is None else max(int(raw_window), 0)
    as_of = nowdate()
    groups = performance.get("groups") or []
    periods = [g["performance_period"] for g in groups]
    summaries = frappe.get_all("Student Performance Summary", filters={
        "performance_period": ["in", periods], "docstatus": ["<", 2],
    }, fields=["name", "student", "performance_period", "main_student_group", "status", "overall_percentage", "docstatus"],
        limit_page_length=0) if periods else []
    students = list({r.student for r in summaries if r.student})
    plans = frappe.get_all("Student Intervention Plan", filters={
        "school_term": school_term, "intervention_type": "Academic", "student": ["in", students],
    }, fields=PLAN_FIELDS, limit_page_length=0) if students else []
    names = [p.name for p in plans]
    actions = frappe.get_all("Student Intervention Action", filters={
        "parent": ["in", names], "parenttype": "Student Intervention Plan", "parentfield": "actions",
    }, fields=ACTION_FIELDS, limit_page_length=0) if names else []
    duplicate_groups = {r["student_group"] for r in performance.get("duplicate_group_periods") or []}
    school = explain_scope("School", performance.get("school_average"), summaries, plans, actions, target, as_of, window,
                           blocked=bool(performance.get("duplicate_students") or duplicate_groups),
                           provisional=not (performance.get("setup") or {}).get("complete"))
    results = []
    occurrences = Counter(r.student for r in summaries if r.student)
    ambiguous_students = {student for student, count in occurrences.items() if count > 1}
    for group in groups:
        rows = [r for r in summaries if r.performance_period == group["performance_period"]]
        item = explain_scope(group["student_group"], group.get("average"), rows, plans, actions, target, as_of, window,
                             blocked=group["student_group"] in duplicate_groups or any(r.student in ambiguous_students for r in rows))
        item["performance_period"] = group["performance_period"]
        results.append(item)
    return {
        "as_of": as_of, "school": school, "groups": results,
        "note": "Diagnoses are staff-recorded and can overlap across courses; cause counts must not be added together. Missing records are not proof of inactivity or causation. Full diagnosis notes stay in the permission-controlled plan.",
        "trigger_note": f"Academic target: {target:g}%. Automatic intervention threshold: {settings.get('academic_intervention_threshold', 50)}%. Automation also requires a submitted complete summary and its course-level trigger; being below the target alone need not create a plan.",
    }


def render_explanations_html(data, include_people=False, expand_groups=False):
    """Shared, escaped rendering for dashboard and board snapshots."""
    from html import escape
    from urllib.parse import quote
    if not data:
        return ""
    sections = []
    scopes = [data.get("school") or {}] + (data.get("groups") or [])
    for index, scope in enumerate(scopes):
        if index:
            avg = scope.get("average")
            badge = "comparison unavailable" if scope.get("blocked") or avg is None else f"{avg:g}% / target {scope['target']:g}%"
            sections.append("<details" + (" open" if expand_groups else "") + "><summary><b>" + escape(str(scope.get("scope") or "Group")) + "</b> — " + escape(badge) + "</summary>")
        causes = "; ".join(f"{r['cause']}: {r['students']} student(s)" for r in scope.get("causes") or [])
        sections.append(f"<h4>{escape(str(scope.get('scope') or 'School'))}</h4><p>{escape(scope.get('answer') or '')}</p><p class='text-muted'>{escape(scope.get('coverage') or '')}</p>")
        if causes and not scope.get("blocked"):
            sections.append(f"<p><b>Recorded diagnoses:</b> {escape(causes)}</p>")
        if scope.get("next_steps"):
            sections.append("<p><b>Suggested next steps:</b></p><ul>" + ''.join("<li>" + escape(step) + "</li>" for step in scope["next_steps"]) + "</ul>")
        if index:
            if include_people and not scope.get("blocked") and scope.get("plan_owners"):
                owners = "; ".join(f"{owner}: {count} plan(s) with recording/follow-up gaps" for owner, count in sorted(scope["plan_owners"].items()))
                sections.append("<p><b>Plan owners to follow up:</b> " + escape(owners) + "</p>")
                links = []
                for item in scope.get("attention", [])[:10]:
                    url = '/app/student-intervention-plan/' + quote(item['plan'], safe='')
                    links.append(f"<a href='{escape(url, quote=True)}'>{escape(item['plan'])}</a>")
                sections.append("<p>Plan evidence (up to 10): " + ", ".join(links) + "</p>")
            sections.append("</details>")
    school = data.get("school") or {}
    if include_people and not school.get("blocked") and school.get("attention"):
        rows = []
        for item in school["attention"]:
            url = '/app/student-intervention-plan/' + quote(item['plan'], safe='')
            rows.append(f"<tr><td><a href='{escape(url, quote=True)}'>{escape(item['plan'])}</a></td><td>{escape(item.get('course') or '')}</td><td>{escape(item.get('assigned_to') or 'Unassigned')}</td><td>{escape(', '.join(item.get('overdue_owners') or []) or '—')}</td><td>{escape('; '.join(item['gaps']))}</td></tr>")
        sections.append("<h4>Follow-up requiring attention</h4><p>Plan owner and overdue action owners can differ. Check the linked plan before assigning responsibility.</p><div style='overflow-x:auto'><table class='table table-bordered'><thead><tr><th>Plan</th><th>Course</th><th>Plan owner</th><th>Overdue action owners</th><th>Recorded gap</th></tr></thead><tbody>" + ''.join(rows) + "</tbody></table></div>")
        sections.append(f"<p>Showing {len(rows)} of {school.get('attention_count', 0)} plans requiring attention among assessed students below target. Open Intervention Follow-up for the full permission-filtered queue.</p>")
    return "<section><h3>Why are results below target?</h3><p>Evidence as of " + escape(str(data.get('as_of') or '')) + "</p>" + ''.join(sections) + "<p>" + escape(data.get('note') or '') + "</p><p>" + escape(data.get('trigger_note') or '') + "</p></section>"
