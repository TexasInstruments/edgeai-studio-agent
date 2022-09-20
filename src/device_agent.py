'''
Fast API endpoints for Agent on EVM
Dependency:
$ pip3 install fastapi uvicorn
'''

import time
import uvicorn
from typing import Optional
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import os
import subprocess
from main_2 import InferenceProcess,RawvideoProcess
import re
import psutil
import json
from typing import List
from fastapi.responses import FileResponse
import uuid
import glob
import hashlib

app = FastAPI()
app = FastAPI()

origins = [
"http://localhost",
"http://localhost:3000",
]
app.add_middleware(
CORSMiddleware,
allow_origins=origins,
allow_credentials=True,
allow_methods=["*"],
allow_headers=["*"],
)
inference_process=None
rawvideo_process=None
ss_id=0
sensor_session=None

# Define request-body using pydantic
class Session(BaseModel):
    id: str
    http_port: int
    http_url: str
    http_status: str
    http_pid: int
    ws_port: int
    ws_url: str
    ws_status: str
    ws_pid: int
    udp_server_port: int
    udp_client_port: int
    udp_status: str
    udp_pid: int
    tcp_server_port: int
    tcp_client_port: int
    tcp_status: str
    tcp_pid: int
    data_pipeline_status: str
    data_pipeline_pid: int


class DeviceItem(BaseModel):
    id: str
    type: str
    description: str
    status: str


class Sensor(BaseModel):
    name: str
    id: str
    type: str
    device: List[DeviceItem]


class Project(BaseModel):
    id: str
    name: str
    sensor: str
    task_type: str
    model: str
    target_device: str
    model_file: str
    model_file_checksum: str

class Model1(BaseModel):
    session: Session
    sensor: Sensor

class Model2(BaseModel):
    session: Session
    sensor: Sensor
    project: Project
    inference: bool

# PUT call endpoint for starting sensor session by running pipeline
@app.put('/sensor-session/{id}',status_code=202)
def start_sensor_session(id,x: Model2):
    global ss_id
    global rawvideo_process
    global inference_process
    global sensor_session
    process_name="node"
    count = 0
    for proc in psutil.process_iter():
        if process_name in proc.name():
            pid = proc.pid
            count = 1
            break
    if(count == 0):
        raise HTTPException(
            status_code=404, detail="sensor session not found!!")
    if(id != ss_id):
         raise HTTPException(status_code=400, detail="Invalid ID supplied")
    if(x.inference == False):
        if rawvideo_process is None or not rawvideo_process.is_alive():
            rawvideo_process = RawvideoProcess()
            rawvideo_process.start()
            process_name="python_gst.py"
            for proc in psutil.process_iter():
                if process_name in proc.name():
                    pid = proc.pid
            x.session.data_pipeline_pid=pid
            x.session.data_pipeline_status="up"
            sensor_session = x.dict()
            return x
        else:
            raise HTTPException(
                status_code=409, detail="Other raw video streaming in progress..!")
    else:
        count = 0
        for path in glob.iglob('/opt/edge_ai_apps/apps_python/projects/**',recursive=True):
            if os.path.isfile(path):
                try:
                    with open(path,'r+') as config:
                        project = json.load(config)
                        if(project['id'] == int(x.project.id)):
                            count = count + 1
                            break
                except:
                    continue

        if(count == 0):
            raise HTTPException(
                status_code=404, detail="project doesnt exist")
        else:
            if inference_process is None or not inference_process.is_alive():
                inference_process = InferenceProcess()
                inference_process.start()
                return {"status": f"Inference pipeline has been initiated"}
            else:
                raise HTTPException(
                     status_code=409, detail="Other inference in progress..!")

# POST call endpoint for initiating sensor session by starting server
@app.post('/sensor-session',status_code=202)
def initiate_sensor_session(x: Sensor):
    global ss_id
    global sensor_session
    count = 0
    i=0
    process_name="node"
    pid=None
    global p
    id = subprocess.check_output("./get_videono.sh")
    if(len(id) == 0):
        raise HTTPException(
            status_code=405, detail="invalid input ")
    else:
        for line in id.split(b'\n'):
            i=i+1
            if i==2:
                id=line.decode()
        id="dev/video" + (id[len(id)-1])
        if(id != x.device[0].id):
            raise HTTPException(
                status_code=405, detail="invalid input ")
    for proc in psutil.process_iter():
        if process_name in proc.name():
            pid = proc.pid
            count = 1
            break
    
    if(count != 1):
        #raise HTTPException(
         #   status_code=409, detail="sensor session already running..!!")
        print("hello")
        p = subprocess.Popen("node ../server/script6.js", shell=True)
        time.sleep(2)
        ss_id = str(uuid.uuid4())
        y=Model1(session={
            "id": ss_id,
            "http_port": 8080,
            "http_url": "/stream",
            "http_status": "started",
            "http_pid": p.pid + 1,
            "ws_port": 0,
            "ws_url": "",
            "ws_status": "down",
            "ws_pid": 0,
            "udp_server_port": 8081,
            "udp_client_port": 0,
            "udp_status": "started",
            "udp_pid": p.pid +1,
            "tcp_server_port": 0,
            "tcp_client_port": 0,
            "tcp_status": "down",
            "tcp_pid": 0,
            "data_pipeline_status": "down",
            "data_pipeline_pid": 0
            },
            sensor={
            "name": x.name,
            "id": x.id,
            "type": x.type,
            "device": [
                {
                "id": x.device[0].id,
                "type": x.device[0].type,
                "description": x.device[0].description,
                "status": x.device[0].status
                }
            ]
            })
        sensor_session = y.dict()
        return y
    return sensor_session

#GET endpoint for getting sensor session details
@app.get('/sensor-session')
def get_sensor_session():
    global ss_id
    global sensor_session
    if(sensor_session==None):
         raise HTTPException(
            status_code=404, detail="Sensor session not found")
    else:
        return sensor_session

#GET endpoint for getting sensor session details using id
@app.get('/sensor-session/{id}')
def get_sensor_session_id(id):
    global ss_id
    global sensor_session
    if(sensor_session==None):
         raise HTTPException(
            status_code=404, detail="Sensor session not found")
    print(sensor_session["session"]["id"])
    if(id != sensor_session["session"]["id"]):
        raise HTTPException(
            status_code=400, detail="Invalid id")
    else:
        return sensor_session

#DELETE sensor session 
@app.delete('/sensor-session/{id}',status_code=202)
def delete_sensor_session(id):
    global ss_id
    global sensor_session
    pid=None
    count = 0
    if(id != ss_id):
        raise HTTPException(
            status_code=400, detail="Invalid id")
    process_name="node"
    for proc in psutil.process_iter():
        if process_name in proc.name():
            pid = proc.pid
            count = 1
            os.kill(pid,2)
            sensor_session=None
            return("session deleted")
    if(count == 0):
        raise HTTPException(
            status_code=404, detail="sensor session not found!!")

#DELETE datapipeline of particular session    
@app.delete('/sensor-session/{id}/dpipe',status_code=202)
def delete_data_pipeline(id):
    global rawvideo_process
    global inference_process
    global ss_id
    pid=None
    if(id != ss_id):
        raise HTTPException(
            status_code=400, detail="Invalid id")
    if rawvideo_process is not None and rawvideo_process.is_alive():
        process_name="python_gst.py"
        for proc in psutil.process_iter():
            if process_name in proc.name():
                pid = proc.pid
                os.kill(pid,2)
                sensor_session["session"]["data_pipeline_status"]="down"
                sensor_session["session"]["data_pipeline_pid"]=0
        return("data pipleine stopped")
    else:
        raise HTTPException(
            status_code=404, detail="No session found")
    
    if inference_process is not None and inference_process.is_alive():
        process_name="app_edgeai.py"
        for proc in psutil.process_iter():
            if process_name in proc.name():
                pid = proc.pid
                os.kill(pid,2)
        return 
    else:
        raise HTTPException(
            status_code=404, detail="No running inference instance found..!!")
    
#GET call endpoint to get sensor details
@app.get('/sensor') # get sensor details
def get_sensor():   
    i=0
    j=0
    print("get sensor details called")
    id = subprocess.check_output("./get_videono.sh")
    if(len(id) != 0):
        for line in id.split(b'\n'):
            i=i+1
            if i==2:
                id=line.decode()
        id="dev/video" + (id[len(id)-1])
        type="V4L2"
        description="device available for capture"
        status="available"
        device_re = re.compile(b"Bus\s+(?P<bus>\d+)\s+Device\s+(?P<device>\d+).+ID\s(?P<id>\w+:\w+)\s(?P<tag>.+)$", re.I)
        df = subprocess.check_output("lsusb")
        devices = []
        for k in df.split(b'\n'):
            if k:
                info = device_re.match(k)
                if info:
                    dinfo = info.groupdict()
                    dinfo['device'] = '/dev/bus/usb/%s/%s' % (dinfo.pop('bus'), dinfo.pop('device'))
                    devices.append(dinfo)
                    j=j+1
        j=j-1
        while j>0:
            x = re.search("Webcam", (devices[j]['tag']).decode())
            if(x):
                name=(devices[j]['tag']).decode()
                Id=(devices[j]['id']).decode()
            j=j-1

        sensor= [{
        "name": name,
        "id": Id,
        "type": type,
        "device": [
        {
            "id": id,
            "type": type,
            "description": description,
            "status": status
        }
        ]
        }]
        return sensor
    else:
        raise HTTPException(
            status_code=404, detail="No sensor found")

#GET call endpoint to get sensor details using id
@app.get('/sensor/{id}') # get sensor details by id
def get_sensor_byid(id):
    k=0
    j=0
    c=0
    print("get sensor details by id called")
    device_re = re.compile(b"Bus\s+(?P<bus>\d+)\s+Device\s+(?P<device>\d+).+ID\s(?P<id>\w+:\w+)\s(?P<tag>.+)$", re.I)
    df = subprocess.check_output("lsusb")
    devices = []
    for i in df.split(b'\n'):
        if i:
            info = device_re.match(i)
            if info:
                dinfo = info.groupdict()
                dinfo['device'] = '/dev/bus/usb/%s/%s' % (dinfo.pop('bus'), dinfo.pop('device'))
                devices.append(dinfo)
                j=j+1
    j=j-1
    while j > 0:
        if id==(devices[j]['id']).decode():
            name=(devices[j]['tag']).decode()
            Id=(devices[j]['id']).decode()
            c=1
        j=j-1  
    if c==0:
        raise HTTPException(
            status_code=404, detail="No sensor found")

    id = subprocess.check_output("./get_videono.sh")
    if(id):
        for line in id.split(b'\n'):
            k=k+1
            if k==2:
                id=line.decode()
        id="dev/video" + (id[len(id)-1])
        type="V4L2"
        description="device available for capture"
        status="available"

    sensor= [{
    "name": name,
    "id": Id,
    "type": type,
    "device": [
      {
        "id": id,
        "type": type,
        "description": description,
        "status": status
        }
    ]
    }]
    return sensor

# DUMMY POST call endpoint for triggering start_inference function
@app.post('/start_inference')
def start_inference(x: Project):
    print("Starting inference...!!!")
    global inference_process
    if inference_process is None or not inference_process.is_alive():
        inference_process = InferenceProcess()
        inference_process.start()
        inference_process.join()
        return {"status": f"Inference pipeline for project '{x.project}' has initiated"}
    else:
        raise HTTPException(
            status_code=404, detail="Other inference in progress..!")


# DUMMY POST call endpoint for triggering stop_inference function
@app.post('/stop_inference')
def stop_inference():
    print("Stopping inference...!!!")
    global inference_process
    if inference_process is not None and inference_process.is_alive():
        pid = None
        process_name="app_edgeai.py"
        for proc in psutil.process_iter():
            if process_name in proc.name():
                pid = proc.pid
                print(pid)
                os.kill(pid,2)
        return {"status": "Inference pipeline stopped"}
    else:
        raise HTTPException(
            status_code=404, detail="No running inference instance found..!!")

#DUMMY POST call endpoint to start raw video stream
@app.post('/start_raw_videostream')
def start_raw_videostream():
    print("starting raw video streamin")
    global rawvideo_process
    if rawvideo_process is None or not rawvideo_process.is_alive():
        rawvideo_process = RawvideoProcess()
        rawvideo_process.start()
        rawvideo_process.join()
        return {"status": "Raw video streaming has initiated"}
    else:
        raise HTTPException(
            status_code=404, detail="Other raw video streamin in progress..!")

#DUMMY POST call to switch pipeline
@app.post('/switch_pipeline')
def switch_pipeline():
    print("switching pipeline")
    global inference_process
    global rawvideo_process
    if inference_process is not None and inference_process.is_alive():
        pid = None
        process_name="app_edgeai.py"
        for proc in psutil.process_iter():
            if process_name in proc.name():
                pid = proc.pid
                print(pid)
                os.kill(pid,2)
                time.sleep(2)
                
                if rawvideo_process is None or not rawvideo_process.is_alive():
                    rawvideo_process = RawvideoProcess()
                    rawvideo_process.start()
                    rawvideo_process.join()
                    return {"status": "Raw video streaming has initiated"}
                else:
                    raise HTTPException(
                        status_code=404, detail="Other raw video streamin in progress..!")
        return {"status": "Inference pipeline switched"}
    else:
        raise HTTPException(
            status_code=404, detail="No running inference instance found..!!")

#DUMMY POST call to stop raw video streaming
@app.post('/stop_raw_videostream')
def stop_raw_videostream():
    print("Stopping raw video streaming...!!!")
    global rawvideo_process
    if rawvideo_process is not None and rawvideo_process.is_alive():
        pid = None
        process_name="python_gst.py"
        for proc in psutil.process_iter():
            if process_name in proc.name():
                pid = proc.pid
                print(pid)
                os.kill(pid,2)
        return {"status": "raw video stream pipeline stopped"}
    else:
        raise HTTPException(
            status_code=404, detail="No running raw video streaming instance found..!!")


#POST call endpoint to create project
@app.post('/project')
def post_project(x: Project):
    project = x.dict()
    if(os.path.exists('../../projects/{}_{}'.format(x.id,x.name))):
        raise HTTPException(status_code=409, detail="Project already exists")
    os.system('mkdir ../../projects/{}_{}'.format(x.id,x.name))
    with open("../../projects/{}_{}/project.config".format(x.id,x.name), "w") as outfile:
        json.dump(project, outfile)
        return("Project successfully registered")

#POST call endpoint to upload model
@app.post('/project/{id}/model')
async def upload_file(id,file: UploadFile = File(...)):
    count = 0
    for path in glob.iglob('/opt/edge_ai_apps/apps_python/projects/**',recursive=True):
        if os.path.isfile(path): # filter dirs
            print(path)
            try:
                with open(path,'r+') as config:
                    project = json.load(config)
                    print(project)
                    print(type(project['id']))
                    if(int(project['id']) == int(id)):
                        count = count + 1
                        name = project['name']
                        print(name)
                        with open(file.filename, 'wb') as f:
                            content = await file.read()
                            f.write(content)
                            f.close()
                            print(file.filename)
                            cmd = 'tar -xvf {} -C /opt/edge_ai_apps/apps_python/projects/{}_{}/'.format(file.filename,project['id'],project['name'])
                            print(cmd)
                            os.system(cmd)
                            model_file = subprocess.Popen(['ls', '../../projects/{}_{}/model/'.format(project['id'],project['name'])],
                                stdout=subprocess.PIPE,
                                bufsize=1,
                                universal_newlines=True).communicate()[0]
                            print(model_file)
                            path = '../../projects/{}_{}/model/{}'.format(project['id'],project['name'],model_file.strip())
                            model_checksum = hashlib.md5(open(path,'rb').read()).hexdigest()
                            project['model_file_checksum']=model_checksum
                            project['model_file']=model_file.strip()
                            config.seek(0)
                            json.dump(project,config)
                            config.truncate()
                            break
            except:
                continue
                
    if(count == 0):
        raise HTTPException(
            status_code=404, detail="project doesnt exist/invalid id")
    else:
        return("model uploaded successfully")

#GET call endpoint to get project details
@app.get('/project/{id}')
def get_project_id(id):
    count = 0
    for path in glob.iglob('/opt/edge_ai_apps/apps_python/projects/**',recursive=True):
        if os.path.isfile(path): # filter dirs
            print(path)
            try:
                with open(path,'r+') as config:
                    project = json.load(config)
                    print(project)
                    if(int(project['id']) == int(id)):
                        count = count + 1
                        break
            except:
                continue

    if(count == 0):
        raise HTTPException(
            status_code=404, detail="project doesnt exist")
    else:
        return(project)

#DELETE call endpoint to delete project
@app.delete('/project/{id}')
def delete_project(id):
    count = 0
    for path in glob.iglob('/opt/edge_ai_apps/apps_python/projects/**',recursive=True):
        if os.path.isfile(path): # filter dirs
            print(path)
            try:
                with open(path,'r+') as config:
                    project = json.load(config)
                    print(project)
                    print(type(project['id']))
                    if(int(project['id']) == int(id)):
                        os.system('rm -r ../../projects/{}_{}'.format(project['id'],project['name']))
                        count = count + 1
                        break
            except:
                continue

    if(count == 0):
        raise HTTPException(
            status_code=404, detail="project doesnt exist")
    else:
        return("model deleted successfully")

if __name__ == "__main__":
    uvicorn.run("device_agent:app",
                host="0.0.0.0", port=8000, reload=True)

'''
To see api list in swagger, go to "ip-address:/8000/docs" and there you can test
Or can make HTTP call from any place
'''
