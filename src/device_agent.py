'''
Fast API endpoints for Agent on EVM
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
from definitions import response_code,response_detail,server_details

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
cwd = os.getcwd()

# Define request-body using pydantic
class Session(BaseModel):
    id: str
    http_port: int = Field(default=server_details.HTTP_PORT.value)
    http_url: str = Field(default="/stream")
    http_status: str 
    http_pid: int
    ws_port: int = Field(default=server_details.WS_PORT.value)
    ws_url: str = Field(default=server_details.WS_URL.value)
    ws_status: str = Field(default="down")
    ws_pid: int = Field(default=0)
    udp_server_port: int = Field(default=server_details.UDP_SERVER_PORT.value)
    udp_client_port: int = Field(default=server_details.UDP_CLIENT_PORT.value)
    udp_status: str
    udp_pid: int
    tcp_server_port: int = Field(default=server_details.TCP_SERVER_PORT.value)
    tcp_client_port: int = Field(default=server_details.TCP_CLIENT_PORT.value)
    tcp_status: str = Field(default=server_details.TCP_STATUS.value)
    tcp_pid: int = Field(default=server_details.TCP_PID.value)
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
    id: str = Field(default="null")
    name: str = Field(default="null") 
    sensor: str = Field(default="null")
    task_type: str = Field(default="null")
    model: str = Field(default="null")
    target_device: str = Field(default="null")
    model_file: str = Field(default="null")
    model_file_checksum: str = Field(default="null")

class Model(BaseModel):
    session: Session
    sensor: Sensor
    project: Optional[Project]
    inference: Optional[bool]

# PUT call endpoint for starting sensor session by running pipeline
@app.put('/sensor-session/{id}',status_code=response_code.ACCEPTED.value)
def start_sensor_session(id,x: Model):
    global ss_id
    global rawvideo_process
    global inference_process
    global sensor_session
    global cwd
    process_name="node"
    count = 0
    for proc in psutil.process_iter():
        if process_name in proc.name():
            pid = proc.pid
            count = 1
            break
    if(count == 0):
        raise HTTPException(
            status_code=response_code.NOT_FOUND.value, detail=response_detail.NOT_FOUND.value)
    if(id != ss_id):
         raise HTTPException(status_code=response_code.BAD_REQUEST.value, detail=response_detail.INVALID_ID.value)
    if(x.inference == False):
        if rawvideo_process is None or not rawvideo_process.is_alive():
            rawvideo_process = RawvideoProcess()
            rawvideo_process.start()
            process_name="python_gst.py"
            for proc in psutil.process_iter():
                if process_name in proc.name():
                    pid = proc.pid
                    print(pid)
            x.session.data_pipeline_pid=pid
            x.session.data_pipeline_status="up"
            sensor_session = x.dict()
            return x
        else:
            raise HTTPException(
                status_code=response_code.CONFLICT.value, detail=response_detail.SESSION_CONFLICT.value)
    else:
        count = 0
        for path in glob.iglob('{}/../../projects/**'.format(cwd),recursive=True):
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
                status_code=response_code.NOT_FOUND.value, detail=response_detail.NOT_FOUND.value)
        else:
            if inference_process is None or not inference_process.is_alive():
                inference_process = InferenceProcess()
                inference_process.start()
                return {"status": f"Inference pipeline has been initiated"}
            else:
                raise HTTPException(
                     status_code=response_code.CONFLICT.value, detail=response_detail.SESSION_CONFLICT.value)

# POST call endpoint for initiating sensor session by starting server
@app.post('/sensor-session',status_code=response_code.ACCEPTED.value)
def initiate_sensor_session(x: Sensor):
    global ss_id
    global sensor_session
    global cwd
    count = 0
    line_count = 0
    i=0
    process_name="node"
    pid=None
    id = subprocess.check_output("./get_videono.sh")
    if(len(id) == 0):
        raise HTTPException(
            status_code=response_code.METHOD_NOT_ALLOWED.value, detail=response_detail.INVALID_INPUT.value)
    else:
        for line in id.split(b'\n'):
            i=i+1
            if i==2:
                id=line.decode()
        id="dev/video" + (id[len(id)-1])
        if(id != x.device[0].id):
            raise HTTPException(
                status_code=response_code.METHOD_NOT_FOUND.value, detail=response_detail.NOT_FOUND.value)
    for proc in psutil.process_iter():
        if process_name in proc.name():
            pid = proc.pid
            count = 1
            break

    if(count != 1):
   
        p = subprocess.Popen("node ../server/script6.js",stdout=subprocess.PIPE,bufsize=1,universal_newlines=True,shell=True)
        for line in p.stdout:
            output = line.rstrip()
            print(output)
            line_count = line_count + 1
            if(line_count == 2):
                break
        for proc in psutil.process_iter():
            if process_name in proc.name():
                pid = proc.pid
        ss_id = str(uuid.uuid4())
        session = Model(session = { "id":ss_id, "http_status":"started", "http_pid":p.pid + 1, "udp_status":"started", "udp_pid":p.pid + 1, "data_pipeline_status":"down","data_pipeline_pid":0},sensor = { "name":x.name, "id":x.id, "type":x.type, "device": [{"id":x.device[0].id, "type":x.device[0].type, "description":x.device[0].type, "status":x.device[0].status}]})
        sensor_session = session.dict()
        return session
    return sensor_session

#GET endpoint for getting sensor session details
@app.get('/sensor-session',status_code=response_code.OK.value)
def get_sensor_session():
    global ss_id
    global sensor_session
    if(sensor_session==None):
         raise HTTPException(
            status_code=response_code.NOT_FOUND.value, detail=response_detail.NOT_FOUND.value)
    else:
        return sensor_session

#GET endpoint for getting sensor session details using id
@app.get('/sensor-session/{id}',status_code=response_code.OK.value)
def get_sensor_session_id(id):
    global ss_id
    global sensor_session
    if(sensor_session==None):
         raise HTTPException(
            status_code=response_code.NOT_FOUND.value, detail=response_detail.NOT_FOUND.value)
    print(sensor_session["session"]["id"])
    if(id != sensor_session["session"]["id"]):
        raise HTTPException(
            status_code=response_code.BAD_REQUEST.value, detail=response_detail.INVALID_ID.value)
    else:
        return sensor_session

#DELETE sensor session 
@app.delete('/sensor-session/{id}',status_code=response_code.ACCEPTED.value)
def delete_sensor_session(id):
    global ss_id
    global sensor_session
    pid=None
    count = 0
    if(id != ss_id):
        raise HTTPException(
            status_code=response_code.BAD_REQUEST.value, detail=response_detail.INVALID_ID.value)
    process_name="node"
    for proc in psutil.process_iter():
        if process_name in proc.name():
            pid = proc.pid
            count = 1
            os.kill(pid,2)
            sensor_session=None
            return(response_detail.ACCEPTED.value)
    if(count == 0):
        raise HTTPException(
            status_code=response_code.NOT_FOUND.value, detail=response_detail.NOT_FOUND.value)

#DELETE datapipeline of particular session    
@app.delete('/sensor-session/{id}/dpipe',status_code=response_code.ACCEPTED.value)
def delete_data_pipeline(id):
    global rawvideo_process
    global inference_process
    global ss_id
    pid=None
    if(id != ss_id):
        raise HTTPException(
            status_code=response_code.BAD_REQUEST.value, detail=response_detail.INVALID_ID.value)
    if rawvideo_process is not None and rawvideo_process.is_alive():
        process_name="python_gst.py"
        for proc in psutil.process_iter():
            if process_name in proc.name():
                pid = proc.pid
                os.kill(pid,2)
                sensor_session["session"]["data_pipeline_status"]="down"
                sensor_session["session"]["data_pipeline_pid"]=0
        return(response_detail.ACCEPTED.value)
    else:
        raise HTTPException(
            status_code=response_code.NOT_FOUND.value, detail=response_detail.NOT_FOUND.value)
    
    if inference_process is not None and inference_process.is_alive():
        process_name="app_edgeai.py"
        for proc in psutil.process_iter():
            if process_name in proc.name():
                pid = proc.pid
                os.kill(pid,2)
        return 
    else:
        raise HTTPException(
            status_code=response_code.NOT_FOUND.value, detail=response_detail.NOT_FOUND.value)
    
#GET call endpoint to get sensor details
@app.get('/sensor',status_code=response_code.OK.value) # get sensor details
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

        sensor = [Sensor(name = name,id = Id, type = "Webcam", device = [DeviceItem(id = id,type = type, description = description, status = status)])]
        return sensor
    else:
        raise HTTPException(
            status_code=response_code.NOT_FOUND.value, detail=response_detail.NOT_FOUND.value)

#GET call endpoint to get sensor details using id
@app.get('/sensor/{id}',status_code=response_code.OK.value) # get sensor details by id
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
            status_code=response_code.NOT_FOUND.value, detail=response_detail.NOT_FOUND.value)

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

    sensor = [Sensor(name = name,id = Id, type = "Webcam", device = [DeviceItem(id = id,type = type, description = description, status = status)])]
    return sensor

#POST call endpoint to create project
@app.post('/project',status_code=response_code.CREATED.value)
def post_project(x: Project):
    global cwd
    project = x.dict()
    if(os.path.exists('{}/../../projects/{}_{}'.format(cwd,x.id,x.name))):
        raise HTTPException(status_code=response_code.CONFLICT.value, detail=response_detail.PROJECT_CONFLICT.value)
    os.system('mkdir {}/../../projects/{}_{}'.format(cwd,x.id,x.name))
    with open("{}/../../projects/{}_{}/project.config".format(cwd,x.id,x.name), "w") as outfile:
        json.dump(project, outfile)
        return(response_detail.CREATED.value)

#POST call endpoint to upload model
@app.post('/project/{id}/model',status_code=response_code.CREATED.value)
async def upload_file(id,file: UploadFile = File(...)):
    count = 0
    global cwd
    for path in glob.iglob('{}/../../projects/**'.format(cwd),recursive=True):
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
                            cmd = 'tar -xvf {} -C {}/../../projects/{}_{}/'.format(file.filename,cwd,project['id'],project['name'])
                            print(cmd)
                            os.system(cmd)
                            model_file = subprocess.Popen(['ls', '{}/../../projects/{}_{}/model/'.format(cwd,project['id'],project['name'])],
                                stdout=subprocess.PIPE,
                                bufsize=1,
                                universal_newlines=True).communicate()[0]
                            print(model_file)
                            path = '{}/../../projects/{}_{}/model/{}'.format(cwd,project['id'],project['name'],model_file.strip())
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
            status_code=response_code.NOT_FOUND.value, detail=response_detail.NOT_FOUND.value)
    else:
        return(response_detail.CREATED.value)

#GET call endpoint to get project details
@app.get('/project/{id}',status_code=response_code.OK.value)
def get_project_id(id):
    count = 0
    global cwd
    for path in glob.iglob('{}/../../projects/**'.format(cwd),recursive=True):
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
            status_code=response_code.NOT_FOUND.value, detail=response_detail.NOT_FOUND.value)
    else:
        return(project)

#DELETE call endpoint to delete project
@app.delete('/project/{id}',status_code=response_code.OK.value)
def delete_project(id):
    count = 0
    global cwd
    for path in glob.iglob('{}/../../projects/**'.format(cwd),recursive=True):
        if os.path.isfile(path): # filter dirs
            print(path)
            try:
                with open(path,'r+') as config:
                    project = json.load(config)
                    print(project)
                    print(type(project['id']))
                    if(int(project['id']) == int(id)):
                        os.system('rm -r {}/../../projects/{}_{}'.format(cwd,project['id'],project['name']))
                        count = count + 1
                        break
            except:
                continue

    if(count == 0):
        raise HTTPException(
            status_code=response_code.NOT_FOUND.value, detail=response_detail.NOT_FOUND.value)
    else:
        return(response_detail.SUCCESS.value)

if __name__ == "__main__":
    uvicorn.run("device_agent:app",
                host="0.0.0.0", port=8000, reload=True)

'''
To see api list in swagger, go to "ip-address:/8000/docs" and there you can test
Or can make HTTP call from any place
'''
