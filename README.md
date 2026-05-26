# IPv6 Roamer

IPv6 Roamer is a Python-based GTK4/Libadwaita application designed to manage static IPv6 addresses across saved NetworkManager Wi-Fi profiles. It interfaces directly with NetworkManager over the system D-Bus.

This tool is built for users who host servers or services on portable Linux devices (like laptops) and rely on IPv6 to bypass Carrier-Grade NAT (CGNAT). It solves the problem of tracking and updating static inbound IPv6 addresses across multiple delegated ISP prefixes as the device roams between different networks.

## Features

* **Centralized Management:** View all known `802-11-wireless` NetworkManager profiles in a single list.
* **Static IPv6 Configuration:** Add, edit, and delete static IPv6 addresses and their prefix lengths (e.g., `2001:db8::1/64`) for any saved Wi-Fi network.
* **Smart Filtering:** By default, the application only lists networks that currently have a static IPv6 address configured. Users can toggle a view to see all known networks.
* **Native UI:** Built with GTK4 and Libadwaita for seamless integration with modern Linux desktop environments.
* **Direct D-Bus Integration:** Modifies NetworkManager configurations directly via the `org.freedesktop.NetworkManager.Settings` interface without relying on shell wrappers.

---

## Requirements

To run this application, your system must have the following dependencies installed:

* **Python 3.10+**
* **NetworkManager** (Running and managing your system network connections)
* **GTK4 & Libadwaita** (System libraries)
* **PyGObject** (Python bindings for standard GNOME libraries)
* **Pydantic** (For data validation and parsing)

On Debian/Ubuntu-based systems, install the system dependencies using:

```bash
sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 libgirepository1.0-dev

```

---

## Installation and Usage

It is recommended to run this project using a modern Python package manager like `uv`.

1. **Clone the repository:**
```bash
git clone https://github.com/ArneshRC/ipv6-roamer
cd ipv6-roamer

```


2. **Install dependencies and run the application:**
If using `uv`:
```bash
uv run python -m ipv6_roamer

```


If using a standard virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate
pip install pydantic pygobject
python -m ipv6_roamer

```

### Permissions

> [!IMPORTANT]
> Modifying system-wide NetworkManager profiles requires root privileges or appropriate Polkit authorization. If you encounter permission errors when attempting to save a new IPv6 address, you must run the application with elevated privileges.

For example, using `pkexec`:

```bash
pkexec uv run python -m ipv6_roamer

```

Alternatively, ensure your user is part of the `netdev` group or configure a custom Polkit rule to allow NetworkManager profile modification without a password prompt.