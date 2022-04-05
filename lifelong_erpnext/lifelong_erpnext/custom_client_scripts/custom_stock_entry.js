frappe.ui.form.on('Stock Entry', {
	setup(frm) {
		erpnext.queries.setup_shelf_query(frm);
		frm.trigger('is_internal_transfer_shelf_query');
	},

	refresh(frm) {
		frm.trigger('hide_batch_selector');
	},

	stock_entry_type(frm) {
		frm.trigger('hide_batch_selector');
		frm.trigger('is_internal_transfer_shelf_query');
	},

	is_internal_transfer_shelf_query(frm) {
		if (frm.doc.purpose === 'Material Transfer') {
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
	},

	hide_batch_selector(frm) {
		frappe.flags.hide_serial_batch_dialog = true;
	}
})

frappe.ui.form.on('Stock Entry Detail', {
	item_code(frm, cdt, cdn) {
		let row = locals[cdt][cdn];

		frappe.flags.hide_serial_batch_dialog = true;
		if (row.item_code && row.s_warehouse) {
			frappe.call({
				method: 'lifelong_erpnext.lifelong_erpnext.custom_server_scripts.custom_utils.has_batch_no',
				args: {
					item_code: row.item_code
				},
				callback: function(r) {
					if (r.message) {
						row.has_batch_no = r.message.has_batch_no;
						row.has_serial_no = r.message.has_serial_no;

						frappe.require("/assets/lifelong_erpnext/js/serial_no_batch_selector.js", function() {
							erpnext.stock.select_batch_and_serial_no(frm, row);
						});
					}
				}
			});
		}
	},

	edit_batch(frm, cdt, cdn) {
		let row = locals[cdt][cdn];

		frappe.flags.hide_serial_batch_dialog = true;
		if (row.item_code && row.s_warehouse) {
			frappe.call({
				method: 'lifelong_erpnext.lifelong_erpnext.custom_server_scripts.custom_utils.has_batch_no',
				args: {
					item_code: row.item_code
				},
				callback: function(r) {
					if (r.message) {
						row.has_batch_no = r.message.has_batch_no;
						row.has_serial_no = r.message.has_serial_no;

						frappe.require("/assets/lifelong_erpnext/js/serial_no_batch_selector.js", function() {
							erpnext.stock.select_batch_and_serial_no(frm, row);
						});
					}
				}
			});
		} else {
			frappe.msgprint(__('Select Item Code and Source Warehouse'));
		}
	}
})