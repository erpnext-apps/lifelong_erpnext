frappe.ui.form.on('Pick List', {
    setup(frm) {

        frm.set_query('shelf', 'locations', function(doc, cdt, cdn) {
            var row  = locals[cdt][cdn];

            let warehouse = row.warehouse || row.s_warehouse || row.t_warehouse;
            let shelf_type = ['Sellable', 'Unsellable'];
            if (in_list(['Pick List', 'Delivery Note', 'Sales Invoice'], frm.doc.doctype)) {
                shelf_type = ['Sellable', "Dock"];
            }

            if (warehouse) {
                return {
                    filters: {
                        'warehouse': warehouse,
                        'type': ['in', shelf_type]
                    }
                }
            }
        });

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

frappe.ui.form.on("Pick List Item", {
    shelf(frm, cdt, cdn) {
        let child = locals[cdt][cdn];

        if (child.shelf && frm.doc.select_manually && child.item_code && child.warehouse) {
            frappe.call({
                method: "lifelong_erpnext.lifelong_erpnext.custom_server_scripts.custom_utils.get_available_batches",
                args: {
                    item_code: child.item_code,
                    warehouse: child.warehouse,
                    company: frm.doc.company,
                    qty: 0,
                    batch_no: '',
                    shelf: child.shelf
                },
                callback: function(r) {
                    if (r.message) {
                        let batch_wise_balance = {}
                        let locations = frm.doc.locations;
                        r.message.forEach(batch_data => {
                            if (batch_data.bal_qty > 0) {
                                batch_wise_balance[batch_data.batch_no] = batch_data.bal_qty;
                            }
                        });

                        locations.forEach(location => {
                            if (location.batch_no && (location.batch_no in batch_wise_balance)) {
                                delete batch_wise_balance[location.batch_no];
                            }
                        });

                        if (batch_wise_balance && Object.keys(batch_wise_balance).length) {
                            for (let key in batch_wise_balance) {
                                if (batch_wise_balance[key] >= child.qty) {
                                    frappe.model.set_value(child.doctype, child.name, {
                                        "batch_no": key,
                                        "stock_qty": batch_wise_balance[key]
                                    });
                                }
                            }
                        }
                    }
                }
            });
        }
    }
})