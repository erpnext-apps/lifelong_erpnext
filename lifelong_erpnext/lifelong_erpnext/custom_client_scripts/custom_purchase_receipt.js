frappe.ui.form.on('Purchase Receipt', {
	setup(frm) {
		erpnext.queries.setup_shelf_query(frm);
	}
})