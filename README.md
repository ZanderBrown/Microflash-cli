# Microflash-cli
Automatically copy hex to micro:bit

Microflash is currently a single python3 script, you can launch it from a terminal with `./monitor.py`

Currently, it's hardcoded to watch `USERDIR/Downloads` and should work on any platform.
MF is developed on Fedora 27 but aims to be fully compatible with Raspbian

## Requirements

The only requirements are python3 and PyGObject, I expect many versions are compatible but GLib 2.48 is roughly the minimum
