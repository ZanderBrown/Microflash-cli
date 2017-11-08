#! /usr/bin/env python3

from gi.repository import GLib, Gio
from os.path import getsize

# This try is used to catch events such as Ctrl-C
# so we can exit gracefully
try:
    # Directory to monitor,
    # by default we use the current users downloads
    wdir = "{}/Downloads".format(GLib.get_home_dir())
    # Setup a GFile for the directory we are interested in
    gfile = Gio.File.new_for_path(wdir)

    # If the gfile instance of GFile doesn't have a member called
    # 'copy_async' we should emulate it
    polyfil = "copy_async" not in dir(gfile)
    if polyfil:
        # We import threading here to avoid importing it multiple
        # times later when we are copying files, however it isn't
        # imported at the top of the script because we only need it
        # when 'copy_async' is unavailable
        import threading

    # Fetch a GFileMonitor for the interesting directory
    monitor = gfile.monitor(Gio.FileMonitorFlags.NONE, None)
    # State where we are monitoring
    print("Monitoring: {}".format(gfile.get_path()))

    # This function is run whenever 'monitor' notices a change
    def cb(obj, src, dest, event):
        # If it was a create event and the file extension is hex
        if (event == Gio.FileMonitorEvent.CREATED and
                src.get_path().endswith(".hex")):
            # Ideally we check if the hex is valid somehow as
            # all this does it check it isn't an empty file
            getsize(src.get_path())
            if getsize(src.get_path()) < 1:
                return
            # Say we found a hex
            print("Found: {}".format(src.get_path()))
            # Get a refrence to the default GVolumeMonitor that allows
            # us to inspect the connected Volumes
            drives = Gio.VolumeMonitor.get()
            # Intereate over all the current volumes
            for drive in drives.get_volumes():
                # If this volume is called MICROBIT we assume it's a
                # micro:bit rather than HDD ect
                if drive.get_name() == "MICROBIT":
                    # Find out where the micro:bit was mounted to
                    location = drive.get_mount().get_default_location()
                    # copy / copy_async may fail so here we catch
                    # exceptions with the hope it may succeed on
                    # another connected micro:bit
                    try:
                        # get the mount location as a string
                        mb = location.get_path()

                        # we must copy to a file dispite the micro:bits
                        # virtual fs system
                        path = "{}/firmware.hex".format(mb)
                        # a GFile for the destination path
                        dest = Gio.File.new_for_path(path)

                        # We should attempt to override existing
                        flags = Gio.FileCopyFlags.OVERWRITE
                        # The operation is of standard priority
                        priority = GLib.PRIORITY_DEFAULT

                        # If copy_async is unavailable we have to copy
                        # the hex differently to emulate it
                        if polyfil:
                            # A wrapper around 'copy' so we can use it
                            # as the target of a threading.Thread
                            def wrap():
                                # Copy the file 'src' to the destination
                                # 'dest' with flags
                                src.copy(dest, flags)
                                # Copy is blocking so this will be run
                                # when it has successfully compleated
                                # Show that we managed to flash the hex
                                print("Flashed: {}".format(mb))

                            # Run 'wrap' in a thread so that we may
                            # flash multiple bits simultaneously
                            threading.Thread(target=wrap).start()
                        else:
                            # Callback for copy_async so we can
                            # communicate the fact it's finished
                            def done(src, res, user_data):
                                # Ensure the write is compleate
                                src.copy_finish(res)
                                # Say where we copied to
                                print("Flashed: {}".format(user_data))

                            # Copy 'src' to 'dest' asynchronous with
                            # the givien flags and priority. We also
                            # pass three None because we are not
                            # providing a GCancellable or a progress
                            # callback (at least presently) then we
                            # provide the 'done' callback and some
                            # data to pass to it so it know who called
                            # back so it can communicate compleation
                            src.copy_async(dest, flags, priority,
                                           None, None, None, done, mb)

                    except:
                        # Something broke, say we couldn't copy to
                        # this micro:bit
                        print("Failed to copy to {}".format(mb))

    # Connect the callback to the changed signal
    monitor.connect("changed", cb)

    # Start the mainloop so that GFileMonitor can looks for changes
    # and the script doesn't complete instantly
    GLib.MainLoop().run()
except KeyboardInterrupt:
    # Quit the main loop on Ctrl-C and friends
    GLib.MainLoop().quit()
