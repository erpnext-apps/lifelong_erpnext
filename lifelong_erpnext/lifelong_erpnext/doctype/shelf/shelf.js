// Copyright (c) 2022, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Shelf', {
    onload: function(frm) {
        // Block force input on all link fields
        ['warehouse', 'zone', 'rack'].forEach(field => {
            frm.set_df_property(field, 'only_select', 1);
        });

        // Warehouse filter (Enabled only)
        frm.set_query('warehouse', () => {
            return { filters: { 'disabled': 0 } };
        });
    },

    warehouse: function(frm) {
        frm.set_value('zone', '');
        frm.set_value('rack', '');
    },

    zone: function(frm) {
        frm.set_value('rack', '');
    },

    refresh: function(frm) {
        // 1. Filter Zone by Warehouse
        frm.set_query('zone', () => {
            return {
                filters: { 'warehouse': frm.doc.warehouse || 'Select Warehouse' }
            };
        });

        // 2. Filter Rack by Warehouse AND Zone
        frm.set_query('rack', () => {
            return {
                filters: {
                    'warehouse': frm.doc.warehouse || 'Select Warehouse',
                    'zone': frm.doc.zone || 'Select Zone'
                }
            };
        });
    }
});