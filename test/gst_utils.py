try:
    import gi

    gi.require_version("Gst", "1.0")
    from gi.repository import Gst, GObject, GLib

    Gst.init()

    def on_message(bus, message, loop):
        mtype = message.type
        if mtype == Gst.MessageType.EOS:
            loop.quit()

        elif mtype == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            print(err, debug)
            print()
            loop.quit()

        elif mtype == Gst.MessageType.WARNING:
            err, debug = message.parse_warning()
            print()
            print(err, debug)

        return True

    def convert_multipart_data_to_jpeg(path):
        pipeline_str = (
            "filesrc location=%s ! multipartdemux ! image/jpeg ! \
                        jpegparse ! multifilesink location=%s.jpg"
            % (path, path)
        )
        pipeline = Gst.parse_launch(pipeline_str)

        bus = pipeline.get_bus()
        bus.add_signal_watch()

        pipeline.set_state(Gst.State.PLAYING)
        loop = GLib.MainLoop()
        bus.connect("message", on_message, loop)
        try:
            loop.run()
        except KeyboardInterrupt:
            loop.quit()
        pipeline.set_state(Gst.State.NULL)

        return 0

except ImportError:
    print("\n[WARNING] GStreamer python bindings not found\n")

    def convert_multipart_data_to_jpeg(path):
        return -1
