(() => {
    const existing_settings =
        frappe.listview_settings["Course Schedule"] || {};

    frappe.listview_settings["Course Schedule"] = {
        ...existing_settings,

        onload(listview) {
            if (existing_settings.onload) {
                existing_settings.onload(listview);
            }

            const route = frappe.get_route();

            if (
                route[0] === "List" &&
                route[1] === "Course Schedule" &&
                route[2] !== "Calendar"
            ) {
                frappe.set_route(
                    "List",
                    "Course Schedule",
                    "Calendar"
                );
            }
        },
    };
})();