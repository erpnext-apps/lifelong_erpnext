from . import __version__ as app_version

app_name = "lifelong_erpnext"
app_title = "Lifelong ERPNext"
app_publisher = "Frappe"
app_description = "Lifelong ERPNext"
app_icon = "octicon octicon-file-directory"
app_color = "grey"
app_email = "contact@erpnext.com"
app_license = "MIT"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/lifelong_erpnext/css/lifelong_erpnext.css"
app_include_js = "/assets/lifelong_erpnext/js/serial_no_batch_selector.js"

# include js, css files in header of web template
# web_include_css = "/assets/lifelong_erpnext/css/lifelong_erpnext.css"
# web_include_js = "/assets/lifelong_erpnext/js/lifelong_erpnext.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "lifelong_erpnext/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "lifelong_erpnext.utils.jinja_methods",
# 	"filters": "lifelong_erpnext.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "lifelong_erpnext.install.before_install"
# after_install = "lifelong_erpnext.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "lifelong_erpnext.uninstall.before_uninstall"
# after_uninstall = "lifelong_erpnext.uninstall.after_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "lifelong_erpnext.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

override_doctype_class = {
	"Putaway Rule": "lifelong_erpnext.lifelong_erpnext.custom_server_scripts.custom_putaway_rule.CustomPutawayRule",
    "Purchase Receipt": "lifelong_erpnext.lifelong_erpnext.custom_server_scripts.custom_stock_controller.CustomStockController",
	"Stock Entry": "lifelong_erpnext.lifelong_erpnext.custom_server_scripts.custom_stock_controller.CustomStockEntry",
	"Pick List": "lifelong_erpnext.lifelong_erpnext.custom_server_scripts.custom_pick_list.CustomPickList",
	"Stock Reconciliation": "lifelong_erpnext.lifelong_erpnext.custom_server_scripts.custom_stock_reconciliation.CustomStockReconciliation"
}

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Stock Ledger Entry": {
		"validate": "lifelong_erpnext.lifelong_erpnext.custom_server_scripts.custom_stock_ledger_entry.update_shelf_data",
	},
	"Purchase Receipt": {
		"before_submit": "lifelong_erpnext.lifelong_erpnext.custom_server_scripts.custom_utils.create_batch",
	},
	"Stock Entry": {
		"before_submit": "lifelong_erpnext.lifelong_erpnext.custom_server_scripts.custom_utils.create_batch",
	}
}

doctype_js = {
	"Delivery Note" : "lifelong_erpnext/custom_client_scripts/custom_delivery_note.js",
	"Purchase Receipt" : "lifelong_erpnext/custom_client_scripts/custom_purchase_receipt.js",
	"Stock Entry" : "lifelong_erpnext/custom_client_scripts/custom_stock_entry.js"
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"lifelong_erpnext.tasks.all"
# 	],
# 	"daily": [
# 		"lifelong_erpnext.tasks.daily"
# 	],
# 	"hourly": [
# 		"lifelong_erpnext.tasks.hourly"
# 	],
# 	"weekly": [
# 		"lifelong_erpnext.tasks.weekly"
# 	],
# 	"monthly": [
# 		"lifelong_erpnext.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "lifelong_erpnext.install.before_tests"

# Overriding Methods
# ------------------------------
#
override_whitelisted_methods = {
	"erpnext.stock.doctype.putaway_rule.putaway_rule.apply_putaway_rule": "lifelong_erpnext.lifelong_erpnext.custom_server_scripts.custom_putaway_rule.apply_putaway_rule"
}
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "lifelong_erpnext.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]


# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"lifelong_erpnext.auth.validate"
# ]

