#!/usr/bin/python3
import subprocess
import time
import sys
import os
import psutil

width = 640
height = 360
framerate = 30
line_count = 0

try:
    p = subprocess.Popen("node ./server/script6.js",stdout=subprocess.PIPE,bufsize=1,universal_newlines=True,shell=True)
    for line in p.stdout:
        output = line.rstrip()
        print(output)
        line_count = line_count + 1
        if(line_count == 2):
            break
    print("node udp server running")
    time.sleep(5)

    if(sys.argv[1] == "raw"):
        cmd='./python_gst.py {} {} {}'.format(width,height,framerate)
        os.system(cmd)
    elif(sys.argv[1] == "infer"):
        cmd= './app_edgeai.py ../configs/image_classification.yaml'
        os.system(cmd)
    else:
        print("invalid command")
except:
    process_name="node"
    for proc in psutil.process_iter():
        if process_name in proc.name():
            #print("killing node process")
            pid = proc.pid
            count = 1
            os.kill(pid,1)



