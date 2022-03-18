import frappe
from frappe import _, bold
from lifelong_erpnext.lifelong_erpnext.custom_server_scripts.custom_utils import get_available_batches

def update_shelf_data(doc, method):
	doctype_mapper = {
		'Purchase Receipt': 'Purchase Receipt Item',
		'Purchase Invoice': 'Purchase Invoice Item',
		'Stock Entry': 'Stock Entry Detail',
		'Delivery Note': 'Delivery Note Item',
		'Sales Invoice': 'Sales Invoice Item',
	}

	if doctype_mapper.get(doc.voucher_type) and doc.voucher_detail_no:
		doc.shelf = frappe.db.get_value(doctype_mapper.get(doc.voucher_type), doc.voucher_detail_no, 'shelf')

	if (doc.voucher_type in ['Stock Entry', 'Purchase Receipt', 'Purchase Invoice', 'Sales Invoice'] and doc.warehouse
		and not doc.shelf and frappe.get_cached_value('Warehouse', doc.warehouse, 'has_shelf')):
		frappe.throw(f"The shelf is required for the warehouse {doc.warehouse}")

	if not doc.batch_no:
		return

	data = get_available_batches(doc.item_code, doc.warehouse, doc.company,
		batch_no=doc.batch_no, shelf=doc.shelf)

	for row in data:
		if (row.qty + doc.actual_qty) < 0:
			msg = (f'''The stock becomes negative as {(row.qty + doc.actual_qty)} for the item
				{bold(doc.item_code)} in the warehouse {bold(doc.warehouse)} for the shelf {bold(doc.shelf)}
				after this entry. <br><br>
				Either you need to increase the stock in the respective shelf and warehouse to complete
				this entry or select the different batch and shelf which has the sufficient stock.''')

			frappe.throw(_(msg), title= _('Insufficient Stock Error'))