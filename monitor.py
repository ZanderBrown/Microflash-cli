#! /usr/bin/env python3

from gi.repository import GLib, Gio, GObject
from os.path import getsize

# 'copy_async' is unavailable in some releases of the Gio bindings
# so we import Thread so that we may emulate 'copy_async' if needed
from threading import Thread

class Microflash(GObject.Object):
    def __init__(self, path):
        super().__init__()
        # Setup a GFile for the directory we are interested in
        gfile = Gio.File.new_for_path(path)

        # Fetch a GFileMonitor for the interesting directory
        self.monitor = gfile.monitor(Gio.FileMonitorFlags.NONE, None)

        self.operations = {}
        # We should attempt to override existing
        self.flags = Gio.FileCopyFlags.OVERWRITE
        # The operation is of standard priority
        self.priority = GLib.PRIORITY_DEFAULT

        # If the gfile instance of GFile doesn't have a member called
        # 'copy_async' we should emulate it
        self.polyfil = "copy_async" not in dir(gfile)
        
        # Connect the callback to the changed signal
        self.monitor.connect("changed", self.cb)

        # State where we are monitoring
        print("Monitoring: {}".format(gfile.get_path()))

    @GObject.Signal(arg_types=(str, str))
    def flashed (self, what, where):
        print("Flashed: {}".format(where))
        self.operations[where] = None

    # Callback for copy_async so we can
    # communicate the fact it's finished
    def copy_async(self, src, res, mb):
        try:
            # Ensure the write is compleate
            src.copy_finish(res)
            # Say where we copied to
            print("Flashed: {}".format(mb))
            self.emit("flashed", src.get_basename(), mb)
            self.operations[mb] = None
        except Exception as e:
            self.operations[mb] = None
            print("Failed to copy to {}\nError: {}".format(mb, str(e)))

    # A wrapper around 'copy' so we can use it
    # as the target of a threading.Thread
    def copy(self, src, dest, mb):
        # Copy the file 'src' to the destination
        # 'dest' with flags
        try:
            src.copy(dest, self.flags, self.operations[mb])
            # Copy is blocking so this will be run
            # when it has successfully compleated
            # Show that we managed to flash the hex
            self.emit("flashed", src.get_basename(), mb)
        except Exception as e:
            self.operations[mb] = None
            print("Failed to copy to {}\nError: {}".format(mb, str(e)))

    # This function is run whenever 'monitor' notices a change
    def cb(self, obj, src, dest, event):
        # If it was a create event and the file extension is hex
        if (event == Gio.FileMonitorEvent.CREATED and
                src.get_path().endswith(".hex")):
            # Ideally we check if the hex is valid somehow as
            # all this does it check it isn't an empty file
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
                    mount = drive.get_mount()
                    if not mount:
                        if not mount.can_mount():
                            print("Unable to mount micro:bit")
                            continue
                        # todo: mount
                        print('Bad')
                        continue
                    location = mount.get_default_location()
                    # copy / copy_async may fail so here we catch
                    # exceptions with the hope it may succeed on
                    # another connected micro:bit
                    try:
                        # get the mount location as a string
                        mb = location.get_path()

                        if mb in self.operations and self.operations[mb]:
                            print("Cancelling current operation")
                            self.operations[mb].cancel()

                        self.operations[mb] = Gio.Cancellable()

                        # we must copy to a file dispite the micro:bits
                        # virtual fs system
                        path = "{}/firmware.hex".format(mb)
                        # a GFile for the destination path
                        dest = Gio.File.new_for_path(path)

                        # If copy_async is unavailable we have to copy
                        # the hex differently to emulate it
                        if self.polyfil:
                            # Run 'wrap' in a thread so that we may
                            # flash multiple bits simultaneously
                            Thread(target=self.copy,
                                args=(src, dest, mb)).start()
                        else:
                            # Copy 'src' to 'dest' asynchronous with
                            # the givien flags and priority. We also
                            # pass three None because we are not
                            # providing a GCancellable or a progress
                            # callback (at least presently) then we
                            # provide the 'done' callback and some
                            # data to pass to it so it know who called
                            # back so it can communicate compleation
                            src.copy_async(dest, self.flags,
                                           self.priority,
                                           self.operations[mb], None,
                                           None, self.copy_async, mb)

                    except Exception as e:
                        # Something broke, say we couldn't copy to
                        # this micro:bit
                        print("Failed to copy to {}\nError: {}".format(mb, str(e)))

# If the __name__ is main this script was run directly so start the
# watcher otherwise leave it for the script including us to do
if __name__ == '__main__':
	# Directory to monitor,
	# by default we use the current users downloads
	wdir = "{}/Downloads".format(GLib.get_home_dir())
	mf = Microflash(wdir)

	# This try is used to catch events such as Ctrl-C
	# so we can exit gracefully
	try:
		# Start the mainloop so that GFileMonitor can looks for changes
		# and the script doesn't complete instantly
		GLib.MainLoop().run()
	except KeyboardInterrupt:
		# Quit the main loop on Ctrl-C and friends
		GLib.MainLoop().quit()
