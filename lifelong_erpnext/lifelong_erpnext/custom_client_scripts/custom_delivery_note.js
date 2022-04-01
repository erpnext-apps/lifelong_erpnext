
frappe.ui.form.on('Delivery Note', {
	setup(frm) {
		erpnext.queries.setup_shelf_query(frm);
		frm.trigger('is_internal_customer_shelf_query');
	},

	is_internal_customer(frm) {
		frm.trigger('is_internal_customer_shelf_query');
	},

	is_internal_customer_shelf_query(frm) {
		if (frm.doc.is_internal_customer) {
			erpnext.queries.setup_child_target_shelf_query(frm);
			erpnext.queries.setup_parent_taget_shelf_query(frm);
		}
	},

	target_shelf(frm) {
		if (frm.doc.target_shelf) {
			frm.doc.items.forEach(row => {
				frappe.model.set_value(row.doctype, row.name, 'target_shelf', frm.doc.target_shelf);
			});
		}
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