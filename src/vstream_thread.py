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

def run_loop(config, stream_type, name=""):
    """ "
    Function call for threading
    Args:
        config: Either config yaml file or video device file
        name: Defines which type of streaming(inference/raw)
    """
    if name == "INFERENCE":
        line_count = 0
        model_config = config
        ws1 = create_connection("ws://localhost:8000/ws/1/log")
        ws2 = create_connection("ws://localhost:8000/ws/1/inference")
        ws3 = create_connection("ws://localhost:8000/ws/1/usbcam_status")
        time.sleep(0.5)
        process = subprocess.Popen(
            "{}/app_edgeai.py ../config/{}.yaml".format(
                Dir_Path.INFER_DIR.value,
                model_config,
            ),
            stdout=subprocess.PIPE,
            bufsize=1,
            universal_newlines=True,
            shell=True,
        )
        time.sleep(1)
        process_name = "app_edgeai.py"
        for proc in psutil.process_iter():
            if process_name in proc.name():
                pid = proc.pid
        for line in process.stdout:
            line = line.rstrip()
            #parse inference time from log
            inference = r"inference.*?\s+?(?P<inference_time>\d{1,5}\.\d{1,})\s+?m?s.*?from\s+(?P<sampples>\d+?)\s+?samples"
            m = re.search(inference, line)
            if m is not None:
                process2 = subprocess.Popen(
                    "ps -p {} -o %mem".format(pid),
                    stdout=subprocess.PIPE,
                    bufsize=1,
                    universal_newlines=True,
                    shell=True,
                )
                for line2 in process2.stdout:
                    line_count = line_count + 1
                    if line_count == 2:
                        avg_mem = line2.rstrip()
                        line_count = 0
                        break

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
            time.sleep(0.1)
            ws1.send(line)

            # Below subprocess is run to check usb cam's availability during streaming
            data = subprocess.Popen(
                "{}/setup_cameras.sh".format(Dir_Path.SCRIPTS_DIR.value),
                stdout=subprocess.PIPE,
                bufsize=1,
                universal_newlines=True,
                shell=True,
            )
            line3 = data.stdout.readline()
            if not line3:
                status = "USB_CAM NOT FOUND"
                ws3.send(status)
                time.sleep(0.1)
            else:
                status = "AVAILABLE"
                ws3.send(status)
                time.sleep(0.1)
            time.sleep(0.1)

    elif name == "RAWVIDEO":
        width = 640
        height = 360
        dev_num = config
        ws3 = create_connection("ws://localhost:8000/ws/1/usbcam_status")
        cmd = "./python_gst.py {} {} {} {}".format(dev_num, width, height, stream_type)
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, bufsize=1, universal_newlines=True, shell=True
        )

        while True:
            data = subprocess.Popen(
                "{}/setup_cameras.sh".format(Dir_Path.SCRIPTS_DIR.value),
                stdout=subprocess.PIPE,
                bufsize=1,
                universal_newlines=True,
                shell=True,
            )
            line = data.stdout.readline()
            if not line:
                status = "USB_CAM NOT FOUND"
                time.sleep(0.1)
                ws3.send(status)
                time.sleep(0.1)
            else:
                status = "AVAILABLE"
                time.sleep(0.1)
                ws3.send(status)
                time.sleep(0.1)
    else:
        print("invalid")


class InferenceProcess(Process):
    """
    Class for starting inference thread
    """

    def __init__(self, model_config):
        """
        Constructor for InferenceProcess class
        Args:
            model_config: name of config yaml file in config folder
        """
        self.model_config = model_config
        print(self.model_config)
        super(InferenceProcess, self).__init__()

    def run(self):
        print("Inference thread started....")
        run_loop(self.model_config, None, "INFERENCE")
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
        """
        self.dev_num = dev_num
        self.stream_type = stream_type
        super(RawvideoProcess, self).__init__()

    def run(self):
        print("raw video stream thread started....")
        run_loop(self.dev_num, self.stream_type, "RAWVIDEO")
        print("raw video stream thread completed...!!!")
