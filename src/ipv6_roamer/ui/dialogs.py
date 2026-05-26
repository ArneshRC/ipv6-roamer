import ipaddress
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Adw, Gtk  # type: ignore

from ipv6_roamer.core.models import StaticIPv6Address, WlanProfile
from ipv6_roamer.core.nm_dbus import NMDBusClient


class EditProfileDialog(Adw.PreferencesWindow):
    def __init__(self, parent, profile: WlanProfile, dbus_client: NMDBusClient, **kwargs):
        super().__init__(transient_for=parent, default_width=500, default_height=400, **kwargs)
        self.set_title(f"Edit {profile.name}")
        self.profile = profile
        self.dbus_client = dbus_client
        
        self.page = Adw.PreferencesPage()
        self.add(self.page)
        
        self.addresses_group = Adw.PreferencesGroup()
        self.addresses_group.set_title("Static IPv6 Addresses")
        self.page.add(self.addresses_group)
        
        # New address entry row
        self.add_row = Adw.ActionRow()
        self.add_row.set_title("New Address")
        
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        box.set_valign(Gtk.Align.CENTER)
        
        self.add_entry = Gtk.Entry()
        self.add_entry.set_placeholder_text("e.g. 2001:db8::1/64")
        self.add_entry.set_width_chars(20)
        box.append(self.add_entry)
        
        add_btn = Gtk.Button(label="Add")
        add_btn.add_css_class("suggested-action")
        add_btn.connect("clicked", self.on_add_clicked)
        box.append(add_btn)
        
        self.add_row.add_suffix(box)
        
        self.addresses_group.add(self.add_row)
        self._address_rows = []
        
        self.render_addresses()

    def render_addresses(self):
        # Clear existing address rows
        for row in self._address_rows:
            self.addresses_group.remove(row)
        self._address_rows.clear()
            
        for ip in self.profile.static_ipv6_addresses:
            row = Adw.ActionRow()
            row.set_title(ip.address)
            row.set_subtitle(f"Prefix: /{ip.prefix}")
            
            btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            btn_box.set_valign(Gtk.Align.CENTER)
            
            copy_btn = Gtk.Button(label="Copy")
            copy_btn.set_valign(Gtk.Align.CENTER)
            copy_btn.connect("clicked", self.on_copy_clicked, ip)
            btn_box.append(copy_btn)

            del_btn = Gtk.Button(label="Delete")
            del_btn.set_valign(Gtk.Align.CENTER)
            del_btn.add_css_class("destructive-action")
            del_btn.connect("clicked", self.on_delete_clicked, ip)
            btn_box.append(del_btn)
            
            row.add_suffix(btn_box)
            
            self.addresses_group.add(row)
            self._address_rows.append(row)

    def on_copy_clicked(self, button, ip: StaticIPv6Address):
        clipboard = self.get_clipboard()
        clipboard.set(ip.address)

    def on_add_clicked(self, button):
        text = self.add_entry.get_text().strip()
        if not text:
            return
            
        # Basic validation/parsing for IP/Prefix
        parts = text.split('/')
        address = parts[0]
        prefix = 64
        if len(parts) > 1:
            try:
                prefix = int(parts[1])
            except ValueError:
                print("Invalid prefix, defaulting to /64")
        
        try:
            ipaddress.IPv6Address(address)
        except ipaddress.AddressValueError:
            print(f"Invalid IPv6 address: {address}")
            return
        
        new_ip = StaticIPv6Address(address=address, prefix=prefix)
        self.profile.static_ipv6_addresses.append(new_ip)
        
        # Commit to NetworkManager
        success = self.dbus_client.update_ipv6_addresses(
            self.profile.uuid, 
            self.profile.static_ipv6_addresses
        )
        
        if success:
            self.add_entry.set_text("")
            self.render_addresses()
        else:
            self.profile.static_ipv6_addresses.remove(new_ip)
            print(f"Error: Failed to update IPv6 addresses for profile {self.profile.name}")

    def on_delete_clicked(self, button, ip: StaticIPv6Address):
        self.profile.static_ipv6_addresses.remove(ip)
        
        success = self.dbus_client.update_ipv6_addresses(
            self.profile.uuid, 
            self.profile.static_ipv6_addresses
        )
        
        if success:
            self.render_addresses()
        else:
            self.profile.static_ipv6_addresses.append(ip)
            print(f"Error: Failed to delete IPv6 address from profile {self.profile.name}")

