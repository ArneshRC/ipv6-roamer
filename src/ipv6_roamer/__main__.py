import sys

import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from ipv6_roamer.app import IPv6RoamerApp


def main():
    app = IPv6RoamerApp()
    return app.run(sys.argv)

if __name__ == '__main__':
    sys.exit(main())
