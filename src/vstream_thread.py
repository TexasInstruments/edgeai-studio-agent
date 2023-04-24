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

from multiprocessing import Process
from websocket import create_connection
from definitions import Dir_Path
import time
import os
import psutil
import subprocess
import re
import json


def run_loop(dev_num, config, stream_type, name=""):
    """ "
    Function call for threading
    Args:
        dev_num: video device file name
        config: config yaml file for starting inference
        stream_type: video/image stream
        name: Defines which type of streaming(inference/raw)
    """
    if name == "INFERENCE":
        line_count = 0
        model_config = config
        ws1 = create_connection("ws://localhost:8000/ws/1/log")
        ws2 = create_connection("ws://localhost:8000/ws/1/inference")
        ws3 = create_connection("ws://localhost:8000/ws/1/usbcam_status")
        time.sleep(0.5)
        # start inference using optiflow script
        process1 = subprocess.Popen(
            "{}/optiflow.sh ../config/{}.yaml".format(
                Dir_Path.INFER_DIR.value,
                model_config,
            ),
            stdout=subprocess.PIPE,
            bufsize=1,
            universal_newlines=True,
            shell=True,
        )
        time.sleep(5)
        process_name = "gst-launch"
        for proc in psutil.process_iter():
            if process_name in proc.name():
                pid = proc.pid
        for line in process1.stdout:
            line = line.rstrip()
            ws1.send(line)

            # get memory consumption data using psutil module
            process2 = psutil.Process(pid)
            mem_percent = process2.memory_percent()
            avg_mem = "{:.1f}".format(mem_percent)

            # parse inference time from log
            inference = r"inferer.*?\s+?(?P<inference_time>\d{1,5}\.\d{1,})\s+?"
            m = re.search(inference, line)
            if m is not None:
                infer_param = {
                    "inference_time": {
                        "unit": "ms",
                        "value": m.group("inference_time"),
                        "dtype": "float",
                    },
                    "average_memory_use": {
                        "unit": "%",
                        "value": avg_mem,
                        "dtype": "float",
                    },
                }
                ws2.send(json.dumps(infer_param))

            # check usb cam's availability during streaming by checking if video device file is present or not
            path = "/sys/class/video4linux/"
            if os.path.exists(os.path.join(path, dev_num)):
                status = "AVAILABLE"
                ws3.send(status)
                time.sleep(0.1)
            else:
                status = "USB_CAM NOT FOUND"
                ws3.send(status)
                time.sleep(0.1)
            time.sleep(0.1)

    elif name == "RAWVIDEO":
        width = 640
        height = 360
        ws3 = create_connection("ws://localhost:8000/ws/1/usbcam_status")
        # start raw stream by invoking python_gst script
        cmd = "./python_gst.py {} {} {} {}".format(dev_num, width, height, stream_type)
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, bufsize=1, universal_newlines=True, shell=True
        )

        while True:
            # check usb cam's availability during streaming by checking if video device file is present or not
            path = "/sys/class/video4linux/"
            if os.path.exists(os.path.join(path, dev_num)):
                status = "AVAILABLE"
                ws3.send(status)
                time.sleep(0.1)
            else:
                status = "USB_CAM NOT FOUND"
                ws3.send(status)
                time.sleep(0.1)
    else:
        print("invalid")


class InferenceProcess(Process):
    """
    Class for starting inference thread
    """

    def __init__(self, model_config, dev_num):
        """
        Constructor for InferenceProcess class
        Args:
            model_config: name of config yaml file in config folder
            dev_num: video device file name
        """
        self.model_config = model_config
        self.dev_num = dev_num
        print(self.model_config)
        super(InferenceProcess, self).__init__()

    def run(self):
        print("Inference thread started....")
        run_loop(self.dev_num, self.model_config, None, "INFERENCE")
        print("Inference thread completed...!!!")


class RawvideoProcess(Process):
    """
    Class for starting raw stream thread
    """

    def __init__(self, dev_num, stream_type):
        """
        Constructor for RawVideoProcess class
        Args:
            dev_num: video device file name
            stream_type: video/image stream
        """
        self.dev_num = dev_num
        self.stream_type = stream_type
        super(RawvideoProcess, self).__init__()

    def run(self):
        print("raw video stream thread started....")
        run_loop(self.dev_num, None, self.stream_type, "RAWVIDEO")
        print("raw video stream thread completed...!!!")
