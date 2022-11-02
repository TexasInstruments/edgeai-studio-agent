from multiprocessing import Process
from websocket import create_connection
import time
import os
import psutil
import cv2
import subprocess

def run_loop(model_config,name=''):
    if name=='INFERENCE':
        print(model_config)
        ws = create_connection("ws://localhost:8000/ws/1")
        time.sleep(1)
        process = subprocess.Popen('../../app_edgeai.py ../../../configs/{}.yaml'.format(model_config),
                            stdout=subprocess.PIPE,
                            bufsize=1,
                            universal_newlines=True,shell=True)
        for line in process.stdout:
            line = line.rstrip()
            #print(line)
            time.sleep(0.1)
            ws.send(line)
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
