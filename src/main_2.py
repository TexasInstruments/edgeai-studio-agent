from multiprocessing import Process
from websocket import create_connection
from definitions import dir_path
import time
import os
import psutil
import cv2
import subprocess
import re
import json
import sys

cwd = os.getcwd()

def run_loop(config,name=''):
    if name=='INFERENCE':
        line_count = 0
        model_config = config
        ws1 = create_connection("ws://localhost:8000/ws/1/log")
        ws2= create_connection("ws://localhost:8000/ws/1/inference")
        ws3= create_connection("ws://localhost:8000/ws/1/usbcam_status")
        time.sleep(0.5)
        process = subprocess.Popen('{}{}app_edgeai.py {}{}/{}.yaml'.format(cwd,dir_path.INFER_DIR.value,cwd,dir_path.CONFIG_DIR.value,model_config),
                            stdout=subprocess.PIPE,
                            bufsize=1,
                            universal_newlines=True,shell=True)
        time.sleep(1)
        process_name="app_edgeai.py"
        #file1 = open("log.txt", "w") 
        for proc in psutil.process_iter():
            if process_name in proc.name():
                pid = proc.pid
        for line in process.stdout:
            line = line.rstrip()
            #file1.write(line)
            #file1.write('\n')
            #inference = r"total time.*?\s+?(?P<inference_time>\d{1,5}\.\d{1,})\s+?m?s.*?from\s+(?P<sampples>\d+?)\s+?samples"
            inference = r"inference.*?\s+?(?P<inference_time>\d{1,5}\.\d{1,})\s+?m?s.*?from\s+(?P<sampples>\d+?)\s+?samples"
            m = re.search(inference, line)
            if m is not None:
                process2 = subprocess.Popen('ps -p {} -o %mem'.format(pid),
                            stdout=subprocess.PIPE,
                            bufsize=1,
                            universal_newlines=True,shell=True)
                for line2 in process2.stdout:
                    line_count = line_count + 1
                    if(line_count == 2): 
                        avg_mem = line2.rstrip()
                        line_count = 0
                        break
                
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
                ws2.send(json.dumps(infer_param))
            time.sleep(0.1)
            ws1.send(line)
            data = subprocess.Popen('{}{}/setup_cameras.sh'.format(cwd,dir_path.SCRIPTS_DIR.value),stdout=subprocess.PIPE,bufsize=1,universal_newlines=True,shell=True)
            line3 = data.stdout.readline()
            if not line3:
                status='USB_CAM NOT FOUND'
                ws3.send(status)
                time.sleep(0.1)
            else:
                status='AVAILABLE'
                ws3.send(status)
                time.sleep(0.1)
            time.sleep(0.1)
        #file1.close()
    elif name=='RAWVIDEO':
        width = 640
        height = 360
        dev_num = config
        ws3= create_connection("ws://localhost:8000/ws/1/usbcam_status")
        cmd='./python_gst.py {} {} {}'.format(dev_num,width,height)
        process = subprocess.Popen(cmd,stdout=subprocess.PIPE,bufsize=1,universal_newlines=True,shell=True)
        #os.system(cmd)
        while True: 
            data = subprocess.Popen('{}{}/setup_cameras.sh'.format(cwd,dir_path.SCRIPTS_DIR.value),stdout=subprocess.PIPE,bufsize=1,universal_newlines=True,shell=True)
            line = data.stdout.readline()
            if not line:
                status='USB_CAM NOT FOUND'
                time.sleep(0.1)
                ws3.send(status)
                time.sleep(0.1)
            else:
                status='AVAILABLE'
                time.sleep(0.1)
                ws3.send(status)
                time.sleep(0.1)
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
    def __init__(self,dev_num):
        self.dev_num = dev_num
        super(RawvideoProcess, self).__init__()
    def run(self):
        print("raw video stream thread started....")
        run_loop(self.dev_num,'RAWVIDEO')
        print("raw video stream thread completed...!!!")
