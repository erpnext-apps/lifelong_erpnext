// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.queries");
$.extend(erpnext.queries, {
	company_address_query: function(doc) {
		let filters = {
			is_your_company_address: 1,
			link_doctype:
			'Company', link_name: doc.company || ''
		};

		if (doc.branch) {
			filters['branch'] = doc.branch;
		}

		return {
			query: 'lifelong_erpnext.lifelong_erpnext.custom_server_scripts.custom_stock_controller.address_query',
			filters: filters
		};
	},
});