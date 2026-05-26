import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Adw, Gio  # type: ignore

from ipv6_roamer.ui.window import IPv6RoamerWindow


class IPv6RoamerApp(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(
            application_id='com.example.IPv6Roamer',
            flags=Gio.ApplicationFlags.FLAGS_NONE,
            **kwargs
        )
        self.win = None

    def do_activate(self):
        if not self.win:
            self.win = IPv6RoamerWindow(application=self)
        self.win.present()
