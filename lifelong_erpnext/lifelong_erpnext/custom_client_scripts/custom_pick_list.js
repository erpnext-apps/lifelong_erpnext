frappe.ui.form.on('Pick List', {
    setup(frm) {
        frm.set_query("child_warehouse", () => {
            return {
                query:"lifelong_erpnext.lifelong_erpnext.custom_server_scripts.custom_pick_list.warehouse_query",
                filters: {'parent_warehouse': frm.doc.parent_warehouse, 'company': frm.doc.company}
            }
        })
    },

    child_warehouse(frm) {
        frm.events.set_item_locations(frm, false);
    }

})