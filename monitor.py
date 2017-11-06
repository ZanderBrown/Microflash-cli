#! /usr/bin/env python3

from gi.repository import GLib, Gio
from os.path import getsize

try:
	file = Gio.File.new_for_path ("{}/Downloads".format(GLib.get_home_dir ()));
	monitor = file.monitor (Gio.FileMonitorFlags.NONE, None);
	print ("Monitoring: {}".format(file.get_path ()));

	def cb (obj, src, dest, event):
		if event == Gio.FileMonitorEvent.CREATED and src.get_path().endswith(".hex"):
			# Ideally we check if the hex is valid somehow
			if getsize(src.get_path ()) < 1:
				return
			print ("Found: {}".format(src.get_path ()));
			drives = Gio.VolumeMonitor.get()
			for drive in drives.get_volumes():
				if drive.get_name() == "MICROBIT":
					location = drive.get_mount().get_default_location()
					try:
						dest = Gio.File.new_for_path("{}/firmware.hex".format(location.get_path()))
						def done (src, res, user_data):
							src.copy_finish (res)
							print("Flashed: {}".format(user_data))
						src.copy_async(dest, Gio.FileCopyFlags.OVERWRITE, GLib.PRIORITY_DEFAULT, None, None, None, done, location.get_path())
					except:
						print("Failed to copy to {}".format(location.get_path()))

	monitor.connect ("changed", cb);

	GLib.MainLoop().run() 
except KeyboardInterrupt: 
	GLib.MainLoop().quit() 
