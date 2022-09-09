from multiprocessing import Process
import time
import os
import psutil

def run_loop(name=''):
    if name=='INFERENCE':
        cmd='../../app_edgeai.py ../../../configs/object_inputcam.yaml'
        os.system(cmd)
    elif name=='RAWVIDEO':
        cmd='../../python_gst.py'
        os.system(cmd)
    else:
        print("invalid")

class InferenceProcess(Process):
    def __init__(self):
        super(InferenceProcess, self).__init__()
    def run(self):
        print("Inference thread started....")
        run_loop('INFERENCE')
        print("Inference thread completed...!!!")

class RawvideoProcess(Process):
    def __init__(self):
        super(RawvideoProcess, self).__init__()
    def run(self):
        print("raw video stream thread started....")
        run_loop('RAWVIDEO')
        print("raw video stream thread completed...!!!")
