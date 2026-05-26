import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Adw, Gtk  # type: ignore

from ipv6_roamer.core.models import WlanProfile
from ipv6_roamer.core.nm_dbus import NMDBusClient
from ipv6_roamer.ui.dialogs import EditProfileDialog


class IPv6RoamerWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("IPv6 Roamer")
        self.set_default_size(600, 400)
        
        self.dbus_client = NMDBusClient()
        self.profiles = []
        
        self.display_limit = 5
        self.current_loaded_idx = 0
        self.show_more_row = None
        self.show_non_static = False
        
        self.setup_ui()
        self.load_profiles()

    def setup_ui(self):
        # Main layout
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(box)
        
        # Header bar
        header = Adw.HeaderBar()
        box.append(header)
        
        # Preferences Page
        self.page = Adw.PreferencesPage()
        
        # Global Settings Group
        settings_group = Adw.PreferencesGroup()
        settings_group.set_title("Settings")
        self.page.add(settings_group)
        
        # Show non-static networks checkbox
        show_non_static_row = Adw.ActionRow()
        show_non_static_row.set_title("Show non-static-assigned networks")
        
        self.show_non_static_check = Gtk.CheckButton()
        self.show_non_static_check.set_active(self.show_non_static)
        self.show_non_static_check.set_valign(Gtk.Align.CENTER)
        self.show_non_static_check.connect("toggled", self.on_show_non_static_toggled)
        show_non_static_row.add_suffix(self.show_non_static_check)
        settings_group.add(show_non_static_row)
        
        # Scrollable container
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_child(self.page)
        scroll.set_vexpand(True)
        box.append(scroll)
        
        self.group = Adw.PreferencesGroup()
        self.group.set_title("Wi-Fi Networks")
        self.page.add(self.group)

    def load_profiles(self):
        all_profiles = self.dbus_client.fetch_wlan_profiles()
        
        if not self.show_non_static:
            self.profiles = [p for p in all_profiles if p.static_ipv6_addresses]
        else:
            self.profiles = all_profiles
            
        self.profiles.sort(key=lambda p: len(p.static_ipv6_addresses), reverse=True)
        
        # Clear existing group children before rendering
        # (This is needed when reloading)
        if hasattr(self, 'profile_rows'):
            for row in self.profile_rows:
                self.group.remove(row)
        self.profile_rows = []
        if self.show_more_row:
            self.group.remove(self.show_more_row)
            self.show_more_row = None

        self.current_loaded_idx = 0
        self._render_batch()

    def on_show_non_static_toggled(self, check):
        self.show_non_static = check.get_active()
        self.load_profiles()

    def _render_batch(self):
        if self.show_more_row:
            self.group.remove(self.show_more_row)
            self.show_more_row = None

        next_limit = self.current_loaded_idx + self.display_limit
        batch = self.profiles[self.current_loaded_idx:next_limit]
        
        for profile in batch:
            row = Adw.ActionRow()
            row.set_title(profile.name)
            
            sub = "No static IPv6"
            if profile.static_ipv6_addresses:
                sub = f"{len(profile.static_ipv6_addresses)} static IPv6 address(es)"
            row.set_subtitle(sub)
            
            # Button to edit
            btn = Gtk.Button()
            btn.set_icon_name("document-edit-symbolic")
            btn.set_valign(Gtk.Align.CENTER)
            btn.connect("clicked", self.on_edit_clicked, profile)
            row.add_suffix(btn)
            
            self.group.add(row)
            if not hasattr(self, 'profile_rows'):
                self.profile_rows = []
            self.profile_rows.append(row)
            
        self.current_loaded_idx += len(batch)
        
        if self.current_loaded_idx < len(self.profiles):
            self._add_show_more_button()

    def _add_show_more_button(self):
        remaining = len(self.profiles) - self.current_loaded_idx
        
        self.show_more_row = Adw.ActionRow()
        self.show_more_row.set_title(f"Show {remaining} more...")
        self.show_more_row.set_subtitle("Load additional Wi-Fi profiles")
        
        self.show_more_row.set_activatable(True)
        self.show_more_row.connect("activated", lambda *args: self._render_batch())
        
        img = Gtk.Image.new_from_icon_name("list-add-symbolic")
        self.show_more_row.add_prefix(img)
        
        self.group.add(self.show_more_row)

    def on_edit_clicked(self, button, profile: WlanProfile):
        dialog = EditProfileDialog(parent=self, profile=profile, dbus_client=self.dbus_client)
        dialog.present()
