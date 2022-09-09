#!/usr/bin/python3
import gi
import signal
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GObject, GLib
import json


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
    print("before play")
    p = Gst.parse_launch(" v4l2src device=/dev/video2 ! videoconvert ! clockoverlay ! video/x-raw, width=640, height=360, framerate=10/1 ! x264enc tune=zerolatency speed-preset=superfast bitrate=128 ! video/x-h264,profile=high ! mp4mux fragment-duration=1 ! udpsink host=127.0.0.1 port=8081")
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
        pass

    p.set_state(Gst.State.NULL)
