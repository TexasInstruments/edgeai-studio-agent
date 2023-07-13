#!/usr/bin/python3
#  Copyright (C) 2023 Texas Instruments Incorporated - http://www.ti.com/
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions
#  are met:
#
#    Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#
#    Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the
#    distribution.
#
#    Neither the name of Texas Instruments Incorporated nor the names of
#    its contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
#  "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
#  LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
#  A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
#  OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
#  SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
#  LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
#  DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
#  THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
#  OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import gi
import signal

gi.require_version("Gst", "1.0")
from gi.repository import Gst, GObject, GLib
import json
import sys


def on_message(bus: Gst.Bus, message: Gst.Message, loop: GLib.MainLoop):
    """
    Gstreamer Message Types and parsing
    """
    mtype = message.type
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


if __name__ == "__main__":
    """
    Function to run gstreamer pipeline for raw video stream
    """
    Gst.init()
    if (sys.argv[4] == 'video'):
        print("starting video stream")
        p = Gst.parse_launch(
            " v4l2src device={} ! image/jpeg, width={}, height={} ! jpegdec ! tiovxdlcolorconvert ! video/x-raw, format=NV12 ! v4l2h264enc extra-controls=\"controls,frame_level_rate_control_enable=1,video_bitrate=10000000,video_gop_size=30\" ! h264parse ! mp4mux fragment-duration=1 ! udpsink host=127.0.0.1  port=8081".format(
                sys.argv[1], sys.argv[2], sys.argv[3]
            )
        )
    elif (sys.argv[4] == 'image'):
        print("starting image stream")
        p = Gst.parse_launch(
            " v4l2src device={} ! image/jpeg, width={}, height={} ! multipartmux boundary=spionisto ! rndbuffersize max=65000 ! udpsink host=127.0.0.1  port=8081".format(
                sys.argv[1], sys.argv[2], sys.argv[3]
            )
        )
    else:
        print("invalid stream type")
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
