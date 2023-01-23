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

import time
import uvicorn
from typing import Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import os
import subprocess
from vstream_thread import InferenceProcess,RawvideoProcess
import re
import psutil
import json
from typing import List
from fastapi.responses import FileResponse
import uuid
import glob
import hashlib
from definitions import Response_Code,Response_Details,Server_Details,Dir_Path
import yaml
import math
import tarfile
import sys
import base64
import aiofiles

app = FastAPI()
active_connections: List[WebSocket] = []
#Set CORS setting
origins = [
"http://localhost",
"http://localhost:3000",
"http://localhost:2000",
"*"
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
sensor=[]
cwd = os.getcwd()
keyCount = 0
config_yaml_path = None
dev_num = None

#Below classes define request-body using pydantic
class Session(BaseModel):
    """
    Class to store sensor session parameters
    """
    id: str
    http_port: int = Field(default=Server_Details.HTTP_PORT.value)
    http_url: str = Field(default=Server_Details.HTTP_URL.value)
    http_status: str 
    http_pid: int
    ws_port: int = Field(default=Server_Details.WS_PORT.value)
    ws_url: str = Field(default=Server_Details.WS_URL.value)
    ws_status: str = Field(default="down")
    ws_pid: int = Field(default=0)
    udp_server_port: int = Field(default=Server_Details.UDP_SERVER_PORT.value)
    udp_client_port: int = Field(default=Server_Details.UDP_CLIENT_PORT.value)
    udp_status: str
    udp_pid: int
    tcp_server_port: int = Field(default=Server_Details.TCP_SERVER_PORT.value)
    tcp_client_port: int = Field(default=Server_Details.TCP_CLIENT_PORT.value)
    tcp_status: str = Field(default=Server_Details.TCP_STATUS.value)
    tcp_pid: int = Field(default=Server_Details.TCP_PID.value)
    data_pipeline_status: str
    data_pipeline_pid: int


class DeviceItem(BaseModel):
    """
    Class to store device details
    """
    id: str
    type: str
    description: str
    status: str


class Sensor(BaseModel):
    """
    Class to store sensor details
    """
    name: str
    id: str
    type: str
    device: List[DeviceItem]


class Project(BaseModel):
    """
    Class to store project details
    """
    id: str = Field(default="null")
    name: str = Field(default="null") 
    sensor: str = Field(default="null")
    task_type: str = Field(default="null")
    model: str = Field(default="null")
    target_device: str = Field(default="null")
    model_file: str = Field(default="null")
    model_file_checksum: str = Field(default="null")

class Model(BaseModel):
    """
    Class to store above classes
    """
    session: Session
    sensor: Sensor
    project: Optional[Project]
    inference: Optional[bool]

class ConnectionManager:
    """
    Class to manage websocket endpoints
    """
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast_log(self, a):
        for connection in self.active_connections:
            await connection.send_json(a)

    async def broadcast_inference(self, a):
        for connection in self.active_connections:
            await connection.send_json(a)

    async def broadcast_status(self, a):
        for connection in self.active_connections:
            await connection.send_json(a)


manager1 = ConnectionManager()
manager2 = ConnectionManager()
manager3 = ConnectionManager()


@app.websocket("/ws/{client_id}/log")
"""
Websocket endpoint to send inference log
"""
async def websocket_endpoint(websocket: WebSocket,client_id: int):
    await manager1.connect(websocket)
    try:
      while True:
        """
        Receives log from websocket endpoint in vstream_thread file
        and broadcast to GUI
        """
         data = await websocket.receive_text()
         text = re.sub(r'(\x9B|\x1B[\[\(\=])[0-?]*[ -\/]*([@-~]|$)', '', data)
         await manager1.broadcast_log(text)
    except Exception as e:
        manager1.disconnect(websocket)

@app.websocket("/ws/{client_id}/inference")
"""
Websocket endpoint to send inference parameters
"""
async def websocket_endpoint(websocket: WebSocket,client_id: int):
    await manager2.connect(websocket)
    try:
      while True:
         data = await websocket.receive_text()
         infer_data = json.loads(data)
         await manager2.broadcast_inference(infer_data)
    except Exception as e:
        manager2.disconnect(websocket)

@app.websocket("/ws/{client_id}/usbcam_status")
"""
Websocket endpoint to send usb camera status(connected or not)
"""
async def websocket_endpoint(websocket: WebSocket,client_id: int):
    await manager3.connect(websocket)
    try:
        while True: 
            data = await websocket.receive_text()
            await manager3.broadcast_status(data)
               
    except Exception as e:
        manager3.disconnect(websocket)

@app.put('/sensor-session/{id}',status_code=Response_Code.ACCEPTED.value)
"""
Start sensor session access by setting up all the required data access pipeline processes
"""
def start_sensor_session(id,x: Model):
    """
    Function to start sensor session 
    Args:
        id: Sensor session id parameter
        x: Object of class Model 
    """
    global ss_id
    global rawvideo_process
    global inference_process
    global sensor_session
    global cwd
    global keyCount
    global dev_num
    global config_yaml_path
    process_name="node"
    count = 0
    model_type=None
    for proc in psutil.process_iter():
        if process_name in proc.name():
            pid = proc.pid
            count = 1
            break
    if(count == 0):
        raise HTTPException(
            status_code=Response_Code.NOT_FOUND.value, detail=Response_Details.SESSION_NOT_FOUND.value)
    if(id != ss_id):
         raise HTTPException(status_code=Response_Code.BAD_REQUEST.value, detail=Response_Details.INVALID_ID.value)
    if(x.inference == False):
        
        if rawvideo_process is None or not rawvideo_process.is_alive():
            
            try:
                #Start raw video stream thread
                rawvideo_process = RawvideoProcess(dev_num)
                rawvideo_process.start()
                process_name="python_gst.py"
                time.sleep(1.5)
                for proc in psutil.process_iter():
                    if process_name in proc.name():
                        pid = proc.pid
                        print(pid)
                x.session.data_pipeline_pid=pid
                x.session.data_pipeline_status="up"
                x.session.ws_status="up"
                x.session.ws_pid=os.getpid()
                sensor_session = x.dict()
                return x
            except:
                print("Error starting raw stream ")
                x.session.data_pipeline_pid=0
                x.session.data_pipeline_status="down"
                sensor_session = x.dict()

        else:
            raise HTTPException(
                status_code=Response_Code.CONFLICT.value, detail=Response_Details.SESSION_CONFLICT.value)
            
    else:
        if inference_process is None or not inference_process.is_alive():
            print("inside inference")
            pcount = 0
            if os.path.isdir('{}{}/{}'.format(cwd,Dir_Path.PROJECT_DIR.value,x.project.id)):
                
                with open('{}{}/{}/project.config'.format(cwd,Dir_Path.PROJECT_DIR.value,x.project.id),'r+') as config:
                    project = json.load(config)
                    #Confirm project folder before starting inference
                    if(project['id'] == x.project.id):
                        pcount = pcount + 1
                        path = '{}{}/{}'.format(cwd,Dir_Path.PROJECT_DIR.value,project['id'])
                        '''with open('{}/dataset.yaml'.format(path),'r') as f:
                            categories = {w['id']:w['name'] for w in yaml.safe_load(f.read())["categories"]}
                            print(categories)
                        with open('{}{}classnames.py'.format(cwd,Dir_Path.INFER_DIR.value),'a') as fobj: 
                            fobj.writelines("modelmaker="+str(categories)) '''   
            
            if(pcount == 0):
                raise HTTPException(
                    status_code=Response_Code.NOT_FOUND.value, detail=Response_Details.PROJECT_NOT_FOUND.value)
            else:
                if x.project.task_type == "classification":
                    model_type="image_classification"
                    config_yaml_path = '{}{}/image_classification.yaml'.format(cwd,Dir_Path.CONFIG_DIR.value)
                if x.project.task_type == "detection":
                    model_type="object_detection"
                    config_yaml_path = '{}{}/object_detection.yaml'.format(cwd,Dir_Path.CONFIG_DIR.value)
                with open(config_yaml_path,'r+') as f:
                    y = json.dumps(yaml.load(f,Loader=yaml.FullLoader))
                    y=json.loads(y)
                    keyCount  = int(len(y["models"]))
                    #Parse threshold value from param.yaml file for detection models and update in config file
                    if model_type == "object_detection":
                        with open('{}/param.yaml'.format(path),'r') as fp:
                            z = json.dumps(yaml.load(fp,Loader=yaml.FullLoader))
                            z = json.loads(z)
                            threshold = z["postprocess"]["detection_threshold"]

                        model = {"model{}".format(keyCount):{"model_path":"{}".format(path),"viz_threshold":threshold}}
                    #If classification model, set topN as 1
                    if model_type == "image_classification":
                        model = {"model{}".format(keyCount):{"model_path":"{}".format(path),"topN":1}}
                    y["models"].update(model)
                    #y["flows"]["flow0"]["models"] = ['model{}'.format(keyCount)]
                    y["flows"]["flow0"][1] = 'model{}'.format(keyCount)
                    y["inputs"]["input0"]["source"] = dev_num
                    
                with open(config_yaml_path,'w') as fout:
                    yaml.safe_dump(y,fout,sort_keys=False)
                
                
                    try:
                        #Start inference thread
                        inference_process = InferenceProcess(model_type)
                        inference_process.start()
                        process_name="app_edgeai.py"
                        time.sleep(2)
                        for proc in psutil.process_iter():
                            if process_name in proc.name():
                                pid = proc.pid
                                print(pid)
                        x.session.data_pipeline_pid=pid
                        x.session.data_pipeline_status="up"
                        x.session.ws_status="up"
                        x.session.ws_pid=os.getpid()
                        sensor_session = x.dict()
                        return x
                    except:   
                        """
                        If exception occurred while starting inference do cleanup as in delete project folder 
                        and remove model path updated in config file
                        """
                        #os.system("sed -i '/modelmaker/d' {}{}classnames.py".format(cwd,Dir_Path.INFER_DIR.value)) 
                        dir_name = '{}{}'.format(cwd,Dir_Path.PROJECT_DIR.value)
                        for dir in os.listdir(dir_name):
                            path = os.path.join(dir_name, dir)
                            if len(path) != 0:
                                os.system('rm -r {}'.format(path))
                        x.session.data_pipeline_pid=0
                        x.session.data_pipeline_status="down"
                        x.session.ws_status="down"
                        x.session.ws_pid=0
                        sensor_session = x.dict()
                        with open(config_yaml_path, 'r') as fin:
                            y = json.dumps(yaml.load(fin,Loader=yaml.FullLoader))
                            y=json.loads(y) 
                            x = y["models"]
                            x.popitem()
                            y["models"] = x
                        with open(config_yaml_path,'w') as fout:
                            yaml.safe_dump(y,fout,sort_keys=False)
        else:
            raise HTTPException(
                status_code=Response_Code.CONFLICT.value, detail=Response_Details.SESSION_CONFLICT.value)
            
            
@app.post('/sensor-session',status_code=Response_Code.ACCEPTED.value)
"""
Initiate sensor session by starting udp node server
"""
def initiate_sensor_session(x: Sensor):
    """
    Function to initiate sensor session
    Args:
        x: Object of class Sensor
    """
    global ss_id
    global sensor_session
    global cwd
    global sensor
    global sensor_count
    count = 0
    line_count = 0
    j=0
    process_name="node"
    pid=None
    if x.device[0].id!=(sensor[0].device[0].id):
        raise HTTPException(
                status_code=Response_Code.METHOD_NOT_ALLOWED.value, detail=Response_Details.INVALID_INPUT.value)
    #Check if node process is running or not
    for proc in psutil.process_iter():
        if process_name in proc.name():
            pid = proc.pid
            count = 1
            break
    if count != 1:
        print("starting server")
        p = subprocess.Popen("node ../server/node_webserver.js",stdout=subprocess.PIPE,bufsize=1,universal_newlines=True,shell=True)
        for line in p.stdout:
            output = line.rstrip()
            print(output)
            line_count = line_count + 1
            if(line_count == 2):
                break
        for proc in psutil.process_iter():
            if process_name in proc.name():
                pid = proc.pid
                print("newly created node",pid)
        #Generate sensor session id
        ss_id = str(uuid.uuid4())
        session = Model(session = { "id":ss_id, "http_status":"started", "http_pid":p.pid, "udp_status":"started", "udp_pid":p.pid, "data_pipeline_status":"down","data_pipeline_pid":0},sensor = { "name":x.name, "id":x.id, "type":x.type, "device": [{"id":x.device[0].id, "type":x.device[0].type, "description":x.device[0].type, "status":x.device[0].status}]})
        sensor_session = session.dict()
        return session
    return sensor_session


@app.get('/sensor-session',status_code=Response_Code.OK.value)
"""
Returns all sensor sessions including initiated and started ones.
"""
def get_sensor_session():
    """
    Function to return sensor session details
    """
    global ss_id
    global sensor_session
    if(sensor_session==None):
         raise HTTPException(
            status_code=Response_Code.NOT_FOUND.value, detail=Response_Details.SESSION_NOT_FOUND.value)
    else:
        return sensor_session

@app.get('/sensor-session/{id}',status_code=Response_Code.OK.value)
"""
Returns all sensor session of specified sensor session id.
"""
def get_sensor_session_id(id):
    """
    Function to return single sensor session
    Args:
        id: Sensor session id parameter
    """
    global ss_id
    global sensor_session
    if(sensor_session==None):
         raise HTTPException(
            status_code=Response_Code.NOT_FOUND.value, detail=Response_Details.SESSION_NOT_FOUND.value)
    if(id != sensor_session["session"]["id"]):
        raise HTTPException(
            status_code=Response_Code.BAD_REQUEST.value, detail=Response_Details.INVALID_ID.value)
    else:
        return sensor_session

@app.delete('/sensor-session/{id}',status_code=Response_Code.ACCEPTED.value)
"""
Stop node udp server
"""
def delete_sensor_session(id):
    """
    Function to stop node udp server
    Args:
        id: Sensor session id
    """
    global ss_id
    global sensor_session
    pid=None
    count = 0
    if(id != ss_id):
        raise HTTPException(
            status_code=Response_Code.BAD_REQUEST.value, detail=Response_Details.INVALID_ID.value)
    process_name="node"
    for proc in psutil.process_iter():
        if process_name in proc.name():
            pid = proc.pid
            count = 1
            os.kill(pid,2)
            sensor_session=None
            return(Response_Details.ACCEPTED.value)
    if(count == 0):
        raise HTTPException(
            status_code=Response_Code.NOT_FOUND.value, detail=Response_Details.NOT_FOUND.value)

   
@app.delete('/sensor-session/{id}/dpipe',status_code=Response_Code.ACCEPTED.value)
"""
Terminate data pipeline process associated with started session
"""
def delete_data_pipeline(id):
    """
    Function to terminate data pipeline
    Args:
        id: Sensor session id parameter
    """
    global rawvideo_process
    global inference_process
    global sensor_session
    global ss_id
    global keyCount
    global config_yaml_path
    pid=None

    if(id != ss_id):
        raise HTTPException(
            status_code=Response_Code.BAD_REQUEST.value, detail=Response_Details.INVALID_ID.value)
    if sensor_session["inference"] == False:
        if rawvideo_process is not None and rawvideo_process.is_alive():
            process_name="python_gst.py"
            #Terminate/kill raw video stream pipeline using its process id
            for proc in psutil.process_iter():
                if process_name in proc.name():
                    pid = proc.pid
                    os.kill(pid,2)
                    rawvideo_process.terminate()
                    sensor_session["session"]["data_pipeline_status"]="down"
                    sensor_session["session"]["data_pipeline_pid"]=0
                
            return(Response_Details.ACCEPTED.value)
        else:
            raise HTTPException(
                status_code=Response_Code.NOT_FOUND.value, detail=Response_Details.SESSION_NOT_FOUND.value)
    else:
        if inference_process is not None and inference_process.is_alive():
            process_name="app_edgeai.py"
            #Terminate/kill inference stream pipeline using its process id
            for proc in psutil.process_iter():
                if process_name in proc.name():
                    pid = proc.pid
                    os.kill(pid,2)
                    inference_process.terminate()
                    sensor_session["session"]["data_pipeline_status"]="down"
                    sensor_session["session"]["data_pipeline_pid"]=0
                    sensor_session["session"]["ws_status"]="down"
                    sensor_session["session"]["ws_pid"]=0
                    #os.system("sed -i '/modelmaker/d' {}{}classnames.py".format(cwd,Dir_Path.INFER_DIR.value))
                    #Remove json object for model path in config file as part of cleanup
                    with open(config_yaml_path, 'r') as fin:
                        y = json.dumps(yaml.load(fin,Loader=yaml.FullLoader))
                        y=json.loads(y) 
                        x = y["models"]
                        x.popitem()
                        y["models"] = x
                    with open(config_yaml_path,'w') as fout:
                        yaml.safe_dump(y,fout,sort_keys=False)
                        
                    return(Response_Details.ACCEPTED.value) 
        else:

            #os.system("sed -i '/modelmaker/d' {}{}classnames.py".format(cwd,Dir_Path.INFER_DIR.value)) 
            raise HTTPException(
                status_code=Response_Code.NOT_FOUND.value, detail=Response_Details.SESSION_NOT_FOUND.value)

@app.get('/sensor',status_code=Response_Code.OK.value)
"""
Returns sensor details
""" 
def get_sensor(): 
    i = 0
    j=0
    global sensor
    global dev_num
    print("get sensor endpoint called")
    if len(sensor) != 0:
        sensor.clear()
    line_count = 0
    """
    Use setup_cameras.sh sdk script to check camera connection and
    if yes,extract video device file
    """
    data = subprocess.Popen('{}{}/setup_cameras.sh'.format(cwd,Dir_Path.SCRIPTS_DIR.value),stdout=subprocess.PIPE,bufsize=1,universal_newlines=True,shell=True)
    line = data.stdout.readline()
    if not line:
        print("sensor not found")
        raise HTTPException(
            status_code=Response_Code.NOT_FOUND.value, detail=Response_Details.SENSOR_NOT_FOUND.value)
    else: 
        for l in data.stdout:
            output = l.rstrip()
            line_count = line_count + 1
            if(line_count == 1):
                break
        parts = output.split(' ')
        #Extracted video device file name copied to dev_num variable
        dev_num = (parts[6])
        dev_no = dev_num.replace('/dev/','')
        #Extract sensor name
        usb_name = subprocess.Popen('cat /sys/class/video4linux/{}/name'.format(dev_no),stdout=subprocess.PIPE,bufsize=1,universal_newlines=True,shell=True)
        usb_name = usb_name.communicate()[0]
        if len(usb_name) == 0:
            name = "unknown device"
        else:
            name = usb_name.strip()               
        device_type="V4L2"
        sensor_type="Webcam"
        description="device available for capture"
        status="available"
        sensor.append(Sensor(name = name,id = "null", type = sensor_type, device = [DeviceItem(id = dev_num,type = device_type, description = description, status = status)]))
        return sensor

@app.post('/project',status_code=Response_Code.CREATED.value)
"""
Sets up a project entry with all the parameters supplied
"""
def post_project(x: Project):
    """
    Create project folder and add Project class object 
    sent as part of request body in project config file 
    Args:
        x: Project class object
    """
    global cwd
    project = x.dict()
    dir_name = '{}{}'.format(cwd,Dir_Path.PROJECT_DIR.value)
    for dir in os.listdir(dir_name):
        path = os.path.join(dir_name, dir)
        if len(path) != 0:
            os.system('rm -r {}'.format(path))
    os.system('mkdir {}{}/{}'.format(cwd,Dir_Path.PROJECT_DIR.value,x.id))    
    with open("{}{}/{}/project.config".format(cwd,Dir_Path.PROJECT_DIR.value,x.id), "w") as outfile:
        json.dump(project, outfile)
        return(Response_Details.CREATED.value)

@app.post('/project/{id}/model',status_code=Response_Code.CREATED.value)
"""
Uploads model and artifacts for inference to the project
"""
async def upload_model(id,file: UploadFile = File(...)):
    """
    Function to upload model
    Args:
        id: Project id parameter
        file: actual Python file that you can pass directly to other functions 
              or libraries that expect a "file-like" object
    """
    global cwd
    try:
        print("FILE:",file)
        print("filename :",file.filename)
        filecontent= await file.read()
        filesize = len(filecontent)
        print('filesize is',filesize)

        filepath = os.path.join('./', os.path.basename('outputFile.tar.gz'))
        #Use aiofiles package to write base 64 file
        async with aiofiles.open(filepath, 'wb') as f:
            await f.write(filecontent)
        count = 0
        
        if os.path.isdir('{}{}/{}'.format(cwd,Dir_Path.PROJECT_DIR.value,id)):
            
            with open('{}{}/{}/project.config'.format(cwd,Dir_Path.PROJECT_DIR.value,id),'r+') as config:
                project = json.load(config)
                if(project['id'] == id):
                    count = count + 1
                    name = project['name']
                    tar = tarfile.open('{}outputFile.tar.gz'.format(cwd))
                    tar.extractall('{}{}/{}'.format(cwd,Dir_Path.PROJECT_DIR.value,project['id']))
                    print('EXTRACTED') 
                    os.remove('{}outputFile.tar.gz'.format(cwd))

                    with open('{}{}/{}/param.yaml'.format(cwd,Dir_Path.PROJECT_DIR.value,project['id']),'r+') as f:
                        model_param = json.dumps(yaml.load(f,Loader=yaml.FullLoader))
                        y=json.loads(model_param)
                        model_path = y['session']['model_path']
                        
                    path = '{}{}/{}/{}'.format(cwd,Dir_Path.PROJECT_DIR.value,project['id'],model_path)
                    model_checksum = hashlib.md5(open(path,'rb').read()).hexdigest()
                    project['model_file_checksum']=model_checksum
                    project['model_file']=model_path
                    #Update project config file
                    config.seek(0)
                    json.dump(project,config)
                    config.truncate()
    except Exception as e:
        print("Error in uploading model to EVM whose exception is",e)
        raise HTTPException(
            status_code=Response_Code.METHOD_NOT_ALLOWED.value, detail=Response_Details.INVALID_INPUT.value)           
    if(count == 0):
        raise HTTPException(
            status_code=Response_Code.NOT_FOUND.value, detail=Response_Details.PROJECT_NOT_FOUND.value)
    else:
        return(Response_Details.CREATED.value,project['id'])

@app.get('/project',status_code=Response_Code.OK.value)
"""
Returns project details
"""
def get_projects():
    project_list = []
    count = 0
    for path in glob.iglob('{}{}/**'.format(cwd,Dir_Path.PROJECT_DIR.value),recursive=True):
        if os.path.isfile(path): 
            try:
                with open(path,'r+') as config:
                    project = json.load(config)
                    project_list.append(project)
                    count = count + 1
            except:
                continue
    if(count == 0):
        raise HTTPException(
            status_code=Response_Code.NOT_FOUND.value, detail=Response_Details.PROJECT_NOT_FOUND.value)
    else:
        return(project_list)

@app.get('/project/{id}',status_code=Response_Code.OK.value)
"""
Returns project details using the id.
"""
def get_project_id(id):
    """
    Function to return project details 
    Args:
        id: Project id parameter
    """
    count = 0
    global cwd
    
    if os.path.isdir('{}{}/{}'.format(cwd,Dir_Path.PROJECT_DIR.value,id)): # filter dirs
            with open('{}{}/{}/project.config'.format(cwd,Dir_Path.PROJECT_DIR.value,id),'r+') as config:
                project = json.load(config)
                if(project['id'] == id):
                    count = count + 1
    if(count == 0):
        raise HTTPException(
            status_code=Response_Code.NOT_FOUND.value, detail=Response_Details.PROJECT_NOT_FOUND.value)
    else:
        return(project)

@app.delete('/project/{id}',status_code=Response_Code.OK.value)
"""
All resources associated to the project will be cleared and freed
"""
def delete_project(id):
    """
    Function to delete project folder
    Args:
        id: Project ID parameter
    """
    count = 0
    global cwd
    
    if os.path.isdir('{}{}/{}'.format(cwd,Dir_Path.PROJECT_DIR.value,id)): # filter dirs
        with open('{}{}/{}/project.config'.format(cwd,Dir_Path.PROJECT_DIR.value,id),'r+') as config:
            project = json.load(config)
            if(project['id'] == id):
                os.system('rm -r {}{}/{}'.format(cwd,Dir_Path.PROJECT_DIR.value,project['id']))
                count = count + 1
    
    if(count == 0):
        raise HTTPException(
            status_code=Response_Code.NOT_FOUND.value, detail=Response_Details.PROJECT_NOT_FOUND.value)
    else:
        return(Response_Details.SUCCESS.value)

#MAIN FUNCTION
if __name__ == "__main__":
    """
    Main function which runs the uvicorn server
    Check if any node process running if yes, kill them
    Check if projects folder is created, if no create folder.
    """
    process_name = 'node'
    for proc in psutil.process_iter():                                                                           
        if process_name in proc.name():                                                                                                                
            pid = proc.pid  
            print(pid)                                                                                                                        
            os.system('kill -1 {}'.format(pid)) 
    os.system('killall node')
    if not os.path.isdir('{}{}'.format(cwd,Dir_Path.PROJECT_DIR.value)):
        os.system('mkdir {}{}'.format(cwd,Dir_Path.PROJECT_DIR.value)) 
    '''os.system("sed -i '/modelmaker/d' {}{}classnames.py".format(cwd,Dir_Path.INFER_DIR.value))
    config_yaml_path = ['{}{}/image_classification.yaml'.format(cwd,Dir_Path.CONFIG_DIR.value),'{}{}/object_detection.yaml'.format(cwd,Dir_Path.CONFIG_DIR.value)]
    for path in config_yaml_path:
        count = 0
        with open(path, 'r') as f:
            for index, line in enumerate(f):
                if 'udpsink' in line:
                    count = count + 1
        if count == 0:
            
            with open(path,'r+') as f:
                y = json.dumps(yaml.load(f,Loader=yaml.FullLoader))
                y=json.loads(y)
                keyCount  = int(len(y["outputs"]))
                
                sink = {"output{}".format(keyCount):{"sink":"udpsink host=127.0.0.1 port=8081","width":1280,"height":720}}
                y["outputs"].update(sink)
                y["flows"]["flow0"]["outputs"] = ['output{}'.format(keyCount)]
                input = {"input0":{"source":"/dev/video2","format":"jpeg","width":640,"height":360,"framerate":30}}
                y["inputs"].update(input)
                y["flows"]["flow0"]["input"] = "input0"
                y["flows"]["flow0"]["mosaic"]["mosaic0"]["width"] = 640
                y["flows"]["flow0"]["mosaic"]["mosaic0"]["height"] = 360
                
            with open(path,'w') as fout:
                yaml.safe_dump(y,fout,sort_keys=False)'''
            
    uvicorn.run("device_agent:app",
                host="0.0.0.0", port=8000, reload=True, ws_ping_interval=math.inf, ws_ping_timeout=math.inf)


