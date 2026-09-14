"""Workspace navigation maintained by the High School app."""

import frappe


def ensure_instructor_workspace_access():
	"""Expose both Education and High School without narrowing an open workspace."""
	for workspace_name in ("Education", "High School"):
		if not frappe.db.exists("Workspace", workspace_name):
			continue
		workspace = frappe.get_doc("Workspace", workspace_name)
		# Education v16 ships with no role restriction, which already includes
		# Instructor. Adding one row there would accidentally exclude every
		# other role, so only extend it when a site has already scoped its roles.
		if workspace_name == "Education" and not workspace.roles:
			continue
		if any(row.role == "Instructor" for row in workspace.roles):
			continue
		workspace.append("roles", {"role": "Instructor"})
		workspace.save(ignore_permissions=True)
