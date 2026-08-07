import frappe


def redirect_after_login(login_manager):
    user = frappe.session.user

    if user == "Guest":
        return

    roles = frappe.get_roles(user)

    # Desk users stay in Desk
    if "System Manager" in roles or "Teacher" in roles or "Staff" in roles:
        return

    # Portal-only users
    if "Guardian" in roles or "Student" in roles:
        frappe.local.response["home_page"] = "/edu-portal"