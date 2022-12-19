// Copyright (c) 2022, Frappe and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Shelf Wise Batch Balance Report"] = {
	"filters": [
		{
			"fieldname":"company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"reqd": 1
		},
		{
			"fieldname":"from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"width": "80",
			"default": frappe.sys_defaults.year_start_date,
			"reqd": 1
		},
		{
			"fieldname":"to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"width": "80",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		},
		{
			"fieldname":"item_code",
			"label": __("Item Code"),
			"fieldtype": "Link",
			"options": "Item",
			"get_query": function() {
				return {
					filters: {
						"has_batch_no": 1
					}
				};
			}
		},
		{
			"fieldname":"warehouse",
			"label": __("Warehouse"),
			"fieldtype": "MultiSelectList",
			"options": "Warehouse",
			get_data: function(txt) {
				return frappe.db.get_link_options('Warehouse', txt, {
					"company": frappe.query_report.get_filter_value("company")
				});
			},
			"get_query": function() {
				let company = frappe.query_report.get_filter_value('company');
				return {
					filters: {
						"company": company
					}
				};
			}
		},
		{
			"fieldname":"batch_no",
			"label": __("Batch No"),
			"fieldtype": "Link",
			"options": "Batch",
			"get_query": function() {
				let item_code = frappe.query_report.get_filter_value('item_code');
				if (item_code) {
					return {
						filters: {
							"item": item_code
						}
					};
				}
			}
		},
		{
			"fieldname":"shelf",
			"label": __("Shelf"),
			"fieldtype": "Link",
			"options": "Shelf",
			"get_query": function() {
				let item_code = frappe.query_report.get_filter_value('item_code');
				let warehouse = frappe.query_report.get_filter_value('warehouse');
				let company = frappe.query_report.get_filter_value('company');
				// if (item_code) {
				// 	return {
				// 		filters: {
				// 			"item": item_code
				// 		}
				// 	};
				// }
			}
		},
		{
			"fieldname":"doctype",
			"label": __("Doctype"),
			"fieldtype": "Link",
			"options": "DocType"
		},
		{
			"fieldname":"show_zero_and_negative_stock",
			"label": __("Show Zero and Negative Stock"),
			"fieldtype": "Check"
		},
	],
	"formatter": function (value, row, column, data, default_formatter) {
		if (column.fieldname == "Batch" && data && !!data["Batch"]) {
			value = data["Batch"];
			column.link_onclick = "frappe.query_reports['Batch-Wise Balance History'].set_batch_route_to_stock_ledger(" + JSON.stringify(data) + ")";
		}

		value = default_formatter(value, row, column, data);
		return value;
	},
	"set_batch_route_to_stock_ledger": function (data) {
		frappe.route_options = {
			"batch_no": data["Batch"]
		};

		frappe.set_route("query-report", "Stock Ledger");
	}
};
