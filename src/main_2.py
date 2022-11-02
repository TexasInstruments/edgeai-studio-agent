from multiprocessing import Process
from websocket import create_connection
import time
import os
import psutil
import cv2
import subprocess
import re
import json
import sys

def run_loop(model_config,name=''):
    if name=='INFERENCE':
        line_count = 0
        print(model_config)
        ws1 = create_connection("ws://localhost:8000/ws/1/log")
        ws2= create_connection("ws://localhost:8000/ws/1/inference")
        time.sleep(1)
        process = subprocess.Popen('../../app_edgeai.py ../../../configs/{}.yaml'.format(model_config),
                            stdout=subprocess.PIPE,
                            bufsize=1,
                            universal_newlines=True,shell=True)
        time.sleep(0.5)
        process_name="app_edgeai.py"
        for proc in psutil.process_iter():
            if process_name in proc.name():
                pid = proc.pid
                #print(pid)
        for line in process.stdout:
            line = line.rstrip()
            #print(line)
            totaltime = r"total time.*?\s+?(?P<inference_time>\d{1,5}\.\d{1,})\s+?m?s.*?from\s+(?P<sampples>\d+?)\s+?samples"
            m = re.search(totaltime, line)
            if m is not None:
                process2 = subprocess.Popen('ps -p {} -o %mem'.format(pid),
                            stdout=subprocess.PIPE,
                            bufsize=1,
                            universal_newlines=True,shell=True)
                for line in process2.stdout:
                    #output = line.rstrip()
                    #print(output)
                    line_count = line_count + 1
                    if(line_count == 2): 
                        avg_mem = line.rstrip()
                        line_count = 0
                        #sys.stdout.write('\x1b[1A')
                        #sys.stdout.write('\x1b[2K')

                        break
                #infer_param = {"inference_time":m.group("inference_time"),"average_memory":avg_mem}
                infer_param = {
                         "inference_time": {
                            "unit": "s",
                            "value": m.group("inference_time"),
                            "dtype": "float"
                            },
                        "average_memory_use": {
                            "unit": "%",
                            "value": avg_mem,
                            "dtype": "float"
                        }
                }
                time.sleep(0.1)
                #ws2.send(json.dumps(infer_param))
                ws2.send(str(infer_param))
                time.sleep(0.1)
            time.sleep(0.1)
            ws1.send(line)
            time.sleep(0.1)
    elif name=='RAWVIDEO':
        cap = cv2.VideoCapture(2)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        cmd='./python_gst.py {} {}'.format(width,height)

        os.system(cmd)
    else:
        print("invalid")

class InferenceProcess(Process):
    def __init__(self,model_config):
        self.model_config = model_config
        print(self.model_config)
        super(InferenceProcess, self).__init__()
    def run(self):
        print("Inference thread started....")
        run_loop(self.model_config,'INFERENCE')
        print("Inference thread completed...!!!")

class RawvideoProcess(Process):
    def __init__(self):
        super(RawvideoProcess, self).__init__()
    def run(self):
        print("raw video stream thread started....")
        run_loop(None,'RAWVIDEO')
        print("raw video stream thread completed...!!!")
