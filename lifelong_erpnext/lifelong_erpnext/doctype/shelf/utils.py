import frappe
from frappe import _

def validate_rack_zone_warehouse(self):
    if self.rack and self.zone:
        # Ensure the Rack belongs to the correct Zone
        rack_zone = frappe.db.get_value("Rack", self.rack, "zone")
        
        if rack_zone != self.zone:
            frappe.throw(_("Rack {0} belongs to Zone {1}, not {2}.")
                        .format(self.rack, rack_zone, self.zone))

    if self.zone and self.warehouse:
        # Ensure the Zone belongs to the correct Warehouse
        zone_wh = frappe.db.get_value("Zone", self.zone, "warehouse")
        
        if zone_wh != self.warehouse:
            frappe.throw(_("Zone {0} belongs to Warehouse {1}, not {2}.")
                        .format(self.zone, zone_wh, self.warehouse))