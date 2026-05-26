import gi

gi.require_version('Gio', '2.0')

from gi.repository import Gio, GLib  # type: ignore

from ipv6_roamer.core.models import StaticIPv6Address, WlanProfile

NM_DBUS_NAME = "org.freedesktop.NetworkManager"
NM_DBUS_PATH_SETTINGS = "/org/freedesktop/NetworkManager/Settings"
NM_DBUS_INTERFACE_SETTINGS = "org.freedesktop.NetworkManager.Settings"
NM_DBUS_INTERFACE_SETTINGS_CONNECTION = "org.freedesktop.NetworkManager.Settings.Connection"

class NMDBusClient:
    def __init__(self):
        self.bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)

    def fetch_wlan_profiles(self) -> list[WlanProfile]:
        profiles = []
        try:
            # Get list of connections
            result = self.bus.call_sync(
                NM_DBUS_NAME,
                NM_DBUS_PATH_SETTINGS,
                NM_DBUS_INTERFACE_SETTINGS,
                "ListConnections",
                None,
                GLib.VariantType.new("(ao)"),
                Gio.DBusCallFlags.NONE,
                -1,
                None
            )
            paths = result.unpack()[0]
            
            for path in paths:
                # Fetch settings for each connection
                settings_result = self.bus.call_sync(
                    NM_DBUS_NAME,
                    path,
                    NM_DBUS_INTERFACE_SETTINGS_CONNECTION,
                    "GetSettings",
                    None,
                    GLib.VariantType.new("(a{sa{sv}})"),
                    Gio.DBusCallFlags.NONE,
                    -1,
                    None
                )
                settings = settings_result.unpack()[0]
                
                con_setting = settings.get("connection", {})
                con_type = con_setting.get("type")
                if con_type != "802-11-wireless":
                    continue
                    
                name = con_setting.get("id", "Unknown")
                uuid = con_setting.get("uuid", "")
                
                ipv6_setting = settings.get("ipv6", {})
                addresses = []
                
                # Check modern address-data array
                address_data = ipv6_setting.get("address-data", [])
                for addr_dict in address_data:
                    address = addr_dict.get("address", "")
                    prefix = addr_dict.get("prefix", 64)
                    if address:
                        addresses.append(StaticIPv6Address(address=address, prefix=prefix))
                        
                profiles.append(WlanProfile(name=name, uuid=uuid, static_ipv6_addresses=addresses))
        except GLib.Error as e:
            print(f"Error fetching connections: {e}")
        
        return profiles

    def update_ipv6_addresses(self, uuid: str, new_addresses: list[StaticIPv6Address]) -> str | None:
        # 1. Find connection path by UUID
        try:
            result = self.bus.call_sync(
                NM_DBUS_NAME,
                NM_DBUS_PATH_SETTINGS,
                NM_DBUS_INTERFACE_SETTINGS,
                "GetConnectionByUuid",
                GLib.Variant("(s)", (uuid,)),
                GLib.VariantType.new("(o)"),
                Gio.DBusCallFlags.NONE,
                -1,
                None
            )
            path = result.unpack()[0]
            
            # 2. Get current settings (using child value to keep proper variants)
            settings_result = self.bus.call_sync(
                NM_DBUS_NAME,
                path,
                NM_DBUS_INTERFACE_SETTINGS_CONNECTION,
                "GetSettings",
                None,
                GLib.VariantType.new("(a{sa{sv}})"),
                Gio.DBusCallFlags.NONE,
                -1,
                None
            )
            settings_gvar = settings_result.get_child_value(0)
            
            # 3. Update ipv6 setting
            address_data_list = []
            for addr in new_addresses:
                address_data_list.append({
                    "address": GLib.Variant('s', addr.address),
                    "prefix": GLib.Variant('u', addr.prefix)
                })
            new_addr_data_var = GLib.Variant("aa{sv}", address_data_list)
            
            outer_builder = GLib.VariantBuilder(GLib.VariantType("a{sa{sv}}"))
            ipv6_found = False
            
            for i in range(settings_gvar.n_children()):
                section_entry = settings_gvar.get_child_value(i)
                section_name = section_entry.get_child_value(0).get_string()
                section_props = section_entry.get_child_value(1)
                
                if section_name == "ipv6":
                    ipv6_found = True
                    inner_builder = GLib.VariantBuilder(GLib.VariantType("a{sv}"))
                    for j in range(section_props.n_children()):
                        prop_entry = section_props.get_child_value(j)
                        prop_name = prop_entry.get_child_value(0).get_string()
                        
                        if prop_name not in ("address-data", "addresses", "method"):
                            inner_builder.add_value(prop_entry)
                    
                    inner_builder.add_value(GLib.Variant.new_dict_entry(
                        GLib.Variant('s', 'address-data'), 
                        GLib.Variant('v', new_addr_data_var)
                    ))
                    # Ensure method is auto/manual so static entries are actually used
                    inner_builder.add_value(GLib.Variant.new_dict_entry(
                        GLib.Variant('s', 'method'),
                        GLib.Variant('v', GLib.Variant('s', 'manual' if new_addresses else 'auto'))
                    ))
                    
                    outer_builder.add_value(GLib.Variant.new_dict_entry(
                        GLib.Variant('s', 'ipv6'), 
                        inner_builder.end()
                    ))
                else:
                    outer_builder.add_value(section_entry)
            
            if not ipv6_found:
                inner_builder = GLib.VariantBuilder(GLib.VariantType("a{sv}"))
                inner_builder.add_value(GLib.Variant.new_dict_entry(
                    GLib.Variant('s', 'address-data'), 
                    GLib.Variant('v', new_addr_data_var)
                ))
                inner_builder.add_value(GLib.Variant.new_dict_entry(
                    GLib.Variant('s', 'method'),
                    GLib.Variant('v', GLib.Variant('s', 'manual' if new_addresses else 'auto'))
                ))
                outer_builder.add_value(GLib.Variant.new_dict_entry(
                    GLib.Variant('s', 'ipv6'), 
                    inner_builder.end()
                ))
                
            final_settings = outer_builder.end()
            
            # 4. Update the connection
            self.bus.call_sync(
                NM_DBUS_NAME,
                path,
                NM_DBUS_INTERFACE_SETTINGS_CONNECTION,
                "Update",
                GLib.Variant.new_tuple(final_settings),
                None,
                Gio.DBusCallFlags.ALLOW_INTERACTIVE_AUTHORIZATION,
                -1,
                None
            )
            
            # 5. Save the connection (Update usually saves, but Save is explicit if needed)
            self.bus.call_sync(
                NM_DBUS_NAME,
                path,
                NM_DBUS_INTERFACE_SETTINGS_CONNECTION,
                "Save",
                None,
                None,
                Gio.DBusCallFlags.ALLOW_INTERACTIVE_AUTHORIZATION,
                -1,
                None
            )
            return None
            
        except GLib.Error as e:
            err_msg = str(e)
            print(f"Error updating connection {uuid}: {err_msg}")
            if "PermissionDenied" in err_msg or "AccessDenied" in err_msg:
                return "Insufficient privileges. Please run via pkexec (e.g. 'pkexec uv run ipv6-roamer') to modify this NetworkManager profile."
            return f"Failed to save profile: {err_msg}"
