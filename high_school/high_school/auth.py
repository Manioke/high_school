import frappe


def redirect_after_login(login_manager):
    user = frappe.session.user

    if user == "Guest":
        return

    roles = frappe.get_roles(user)

    # Desk users stay in Desk
    if set(roles).intersection({"System Manager", "Education Manager", "Academics User", "Teacher", "Staff", "Instructor", "Employee"}):
        return

    # Portal-only users
    if "Guardian" in roles or "Student" in roles:
        frappe.local.response["home_page"] = "/edu-portal"


def restrict_guardian_to_portal():
    """Keep Guardian-only accounts out of Desk even when an old User is System type."""
    user = frappe.session.user
    if not user or user == "Guest":
        return
    path = getattr(getattr(frappe.local, "request", None), "path", "") or ""
    if not (path == "/desk" or path.startswith("/desk/") or path == "/app" or path.startswith("/app/")):
        return
    roles = set(frappe.get_roles(user))
    privileged = {"Administrator", "System Manager", "Education Manager", "Academics User", "Teacher", "Staff", "Instructor", "Employee"}
    if "Guardian" in roles and not roles.intersection(privileged):
        frappe.local.flags.redirect_location = "/edu-portal"
        raise frappe.Redirect
