#! /usr/bin/env python3

from gi.repository import GLib, Gio

try:
    wdir = "{}/Downloads".format(GLib.get_home_dir())
    gfile = Gio.File.new_for_path(wdir)

    polyfil = "copy_async" not in dir(gfile)
    if polyfil:
        import threading

    monitor = gfile.monitor(Gio.FileMonitorFlags.NONE, None)
    print("Monitoring: {}".format(gfile.get_path()))

    def cb(obj, src, dest, event):
        if (event == Gio.FileMonitorEvent.CREATED and
                src.get_path().endswith(".hex")):
            # Ideally we check if the hex is valid somehow
            print("Found: {}".format(src.get_path()))
            drives = Gio.VolumeMonitor.get()
            for drive in drives.get_volumes():
                if drive.get_name() == "MICROBIT":
                    location = drive.get_mount().get_default_location()
                    try:
                        mb = location.get_path()

                        path = "{}/firmware.hex".format(mb)
                        dest = Gio.File.new_for_path(path)

                        flags = Gio.FileCopyFlags.OVERWRITE
                        priority = GLib.PRIORITY_DEFAULT

                        def done(src, res, user_data):
                            src.copy_finish(res)
                            print("Flashed: {}".format(user_data))

                        if polyfil:
                            def wrap():
                                src.copy(dest, flags)
                                print("Flashed: {}".format(mb))

                            threading.Thread(target=wrap).start()
                        else:
                            src.copy_async(dest, flags, priority,
                                           None, None, None, done, mb)

                    except:
                        print("Failed to copy to {}".format(mb))

    monitor.connect("changed", cb)

    GLib.MainLoop().run()
except KeyboardInterrupt:
    GLib.MainLoop().quit()
