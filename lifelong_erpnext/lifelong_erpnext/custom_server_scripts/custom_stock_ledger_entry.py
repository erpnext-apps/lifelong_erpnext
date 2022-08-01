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

	if doctype_mapper.get(doc.voucher_type) and doc.voucher_detail_no and doc.is_cancelled == 0:
		is_internal_transfer = False
		if (doc.voucher_type in ["Delivery Note", "Sales Invoice"] and
			frappe.db.get_value(doc.voucher_type, doc.voucher_no, 'is_internal_customer')):
			is_internal_transfer = True

		if (doc.voucher_type == 'Stock Entry' and
			frappe.db.get_value(doc.voucher_type, doc.voucher_no, 'purpose') in
			["Material Transfer", "Manufacture", "Repack"]):
			is_internal_transfer = True

		if is_internal_transfer and doc.actual_qty > 0:
			doc.shelf = frappe.db.get_value(doctype_mapper.get(doc.voucher_type),
				doc.voucher_detail_no, 'target_shelf')
		elif doc.voucher_type != 'Purchase Receipt' or doc.actual_qty > 0:
			doc.shelf = frappe.db.get_value(doctype_mapper.get(doc.voucher_type),
				doc.voucher_detail_no, 'shelf')

		if (doc.voucher_type == 'Purchase Receipt' and doc.actual_qty < 0):
			voucher_data = frappe.db.get_value(doc.voucher_type,
				doc.voucher_no, ["is_internal_supplier", "is_return"], as_dict=1)

			if voucher_data.is_internal_supplier:
				doc.shelf = frappe.db.get_value(doctype_mapper.get(doc.voucher_type),
					doc.voucher_detail_no, 'from_shelf')
			elif voucher_data.is_return:
				doc.shelf = frappe.db.get_value(doctype_mapper.get(doc.voucher_type),
					doc.voucher_detail_no, 'shelf')

		if (doc.voucher_type in ["Delivery Note", "Sales Invoice"]
			and doc.is_return and is_internal_transfer):
			if doc.actual_qty > 0:
				doc.shelf = frappe.db.get_value(doctype_mapper.get(doc.voucher_type),
					doc.voucher_detail_no, 'shelf')
			else:
				doc.shelf = frappe.db.get_value(doctype_mapper.get(doc.voucher_type),
					doc.voucher_detail_no, 'target_shelf')

	if not doc.shelf and doc.is_cancelled == 0:
		has_shelf_ledgers = frappe.get_all('Stock Ledger Entry', fields=['name'],
			filters = {'item_code': doc.item_code, 'is_cancelled': 0, 'shelf': ['is', 'set'], 'warehouse': doc.warehouse}, limit=1)

		if has_shelf_ledgers and frappe.session.user != "harsha.vardhana@lifelongonline.com":
			frappe.throw(_(f'Shelf required for the item {bold(doc.item_code)} and warehouse {bold(doc.warehouse)}'))

	if not doc.batch_no or doc.voucher_type == 'Stock Reconciliation':
		return

	if doc.shelf and doc.is_cancelled == 0:
		validate_shelf_data(doc)

def validate_shelf_data(doc):
	shelf_warehouse = frappe.db.get_value('Shelf', doc.shelf, 'warehouse')
	if (doc.shelf and doc.warehouse and shelf_warehouse != doc.warehouse):
		frappe.throw(_(f'''The shelf {bold(doc.shelf)} does belong to the warehouse {shelf_warehouse}
			and does not belong to the warehouse {bold(doc.warehouse)}'''))

	if doc.shelf and not frappe.db.exists('Shelf', doc.shelf):
		frappe.throw(_(f"Shelf {doc.shelf} doesn't exists"), title= _('Shelf Not Exists'))

	if doc.actual_qty > 0:
		return

	data = get_available_batches(doc.item_code, doc.warehouse, doc.company,
		batch_no=doc.batch_no, shelf=doc.shelf)

	if not data:
		msg = (f'''The stock not exists for the item {bold(doc.item_code)} and batch {bold(doc.batch_no)}
			in the shelf {bold(doc.shelf)} for the warehouse {bold(doc.warehouse)}. <br><br>
			Either you need to increase the stock in the respective shelf and warehouse to complete
			this entry or select the different batch and shelf which has the sufficient stock.''')

		frappe.throw(_(msg), title= _('Insufficient Stock Error'))

	for row in data:
		if (row.qty + doc.actual_qty) < 0:
			msg = (f'''The stock becomes negative as {(row.qty + doc.actual_qty)} for the item
				{bold(doc.item_code)} in the warehouse {bold(doc.warehouse)} for the shelf {bold(doc.shelf)}
				after this entry. <br><br>
				Either you need to increase the stock in the respective shelf and warehouse to complete
				this entry or select the different batch and shelf which has the sufficient stock.''')

			frappe.throw(_(msg), title= _('Insufficient Stock Error'))
