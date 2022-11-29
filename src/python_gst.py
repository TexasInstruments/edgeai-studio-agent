#!/usr/bin/python3
import gi
import signal
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GObject, GLib
import json
import sys

def on_message(bus: Gst.Bus, message: Gst.Message, loop: GLib.MainLoop):
    mtype = message.type
    """
        Gstreamer Message Types and how to parse
        https://lazka.github.io/pgi-docs/Gst-1.0/flags.html#Gst.MessageType
    """
    if mtype == Gst.MessageType.EOS:
        print("End of stream")
        loop.quit()

    elif mtype == Gst.MessageType.ERROR:
        err, debug = message.parse_error()
        print(err, debug)
        loop.quit()

    elif mtype == Gst.MessageType.WARNING:
        err, debug = message.parse_warning()
        print(err, debug)

    return True

if __name__ == '__main__':
    Gst.init()
    print("before playing")
    p = Gst.parse_launch(" v4l2src device={} ! videoconvert ! video/x-raw, width={}, height={}, framerate=30/1, format=NV12 ! v4l2h264enc gop-size=30 ! h264parse ! matroskamux ! udpsink host=127.0.0.1  port=8081".format(sys.argv[1],sys.argv[2],sys.argv[3]))
    bus = p.get_bus()
    # allow bus to emit messages to main thread
    bus.add_signal_watch()
    p.set_state(Gst.State.PLAYING)
    print("playing")
    loop = GLib.MainLoop()
    bus.connect("message", on_message, loop)
    try:
        loop.run()
    except KeyboardInterrupt:
        loop.quit()

    p.set_state(Gst.State.NULL)
