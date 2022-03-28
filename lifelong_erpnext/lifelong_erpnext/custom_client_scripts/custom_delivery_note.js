
frappe.ui.form.on('Delivery Note', {
	setup(frm) {
		erpnext.queries.setup_shelf_query(frm);
	}
})


frappe.ui.form.on('Delivery Note Item', {
	edit_batch(frm, cdt, cdn) {
		let row = locals[cdt][cdn];

		frappe.db.get_value("Item", row.item_code, ["has_batch_no", "has_serial_no"])
			.then((r) => {
				if (r.message && (r.message.has_batch_no || r.message.has_serial_no)) {
					row.has_batch_no = r.message.has_batch_no;
					row.has_serial_no = r.message.has_serial_no;

					erpnext.show_serial_batch_selector(frm, row, (item) => {
						frm.script_manager.trigger('qty', item.doctype, item.name);
					}, undefined, true);
				}
			});
	}
})