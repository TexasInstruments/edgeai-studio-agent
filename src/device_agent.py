'''
Fast API endpoints for Agent on EVM
'''

import time
import uvicorn
from typing import Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, WebSocket
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
import yaml
import math
import tarfile
import sys
import base64
import aiofiles
import click
app = FastAPI()

active_connections: List[WebSocket] = []
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
sensor_count=0
cwd = os.getcwd()
project_dir = '/../../../../projects'
keyCount = 0
#model_type = None
config_yaml_path = None
dev_num = None

""" class model:
    model_type = None
    def __init__(self, model_type):
        self.model_type = model_type """

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
    #project: Project = Field(default="null")
    inference: Optional[bool]

class ConnectionManager:
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

manager1 = ConnectionManager()
manager2 = ConnectionManager()

#websocket endpoint to send inference log
@app.websocket("/ws/{client_id}/log")
async def websocket_endpoint(websocket: WebSocket,client_id: int):
    await manager1.connect(websocket)
    try:
      while True:
         data = await websocket.receive_text()
         await manager1.broadcast_log(data)
    except Exception as e:
        manager1.disconnect(websocket)
        #await manager1.broadcast(f"websocket disconnected")

#websocket endpoint to send inference log
@app.websocket("/ws/{client_id}/inference")
async def websocket_endpoint(websocket: WebSocket,client_id: int):
    await manager2.connect(websocket)
    try:
      while True:
         data = await websocket.receive_text()
         infer_data = json.loads(data)
         await manager2.broadcast_inference(infer_data)
    except Exception as e:
        manager2.disconnect(websocket)
        #await manager2.broadcast(f"websocket disconnected")

# PUT call endpoint for starting sensor session by running pipeline
@app.put('/sensor-session/{id}',status_code=response_code.ACCEPTED.value)
def start_sensor_session(id,x: Model):
    global ss_id
    global rawvideo_process
    global inference_process
    global sensor_session
    global cwd
    global project_dir
    global keyCount
    global dev_num
    #global model_type
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
            status_code=response_code.NOT_FOUND.value, detail=response_detail.NOT_FOUND.value)
    if(id != ss_id):
         raise HTTPException(status_code=response_code.BAD_REQUEST.value, detail=response_detail.INVALID_ID.value)
    if(x.inference == False):
        if rawvideo_process is None or not rawvideo_process.is_alive():
            print(dev_num)
            rawvideo_process = RawvideoProcess(dev_num)
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
        print("inside inference")
        pcount = 0
        #for path in glob.iglob('{}/../../../../projects/**'.format(cwd),recursive=True):
        if os.path.isdir('{}{}/{}'.format(cwd,project_dir,x.project.id)):
               
            with open('{}{}/{}/project.config'.format(cwd,project_dir,x.project.id),'r+') as config:
                project = json.load(config)

                if(project['id'] == x.project.id):
                    print(x.project.id)
                    pcount = pcount + 1
                    print(pcount)
                    path = '{}{}/{}'.format(cwd,project_dir,project['id'])
                    with open('{}/dataset.yaml'.format(path),'r') as f:
                        print("open dataset ")
                        categories = {w['id']:w['name'] for w in yaml.safe_load(f.read())["categories"]}
                        print(categories)
                    with open('{}/../../classnames.py'.format(cwd),'a') as fobj:
                        fobj.writelines("\nmodelmaker="+str(categories))       
                        #fobj.write(f"modelmaker = {json.dumps(categories)}")
                        #json.dump(categories,f)

                
        if(pcount == 0):
            raise HTTPException(
                status_code=response_code.NOT_FOUND.value, detail=response_detail.NOT_FOUND.value)
        else:
            if x.project.task_type == "classification":
                model_type="image_classification"
                config_yaml_path = '{}/../../../configs/image_classification.yaml'.format(cwd)
            if x.project.task_type == "detection":
                model_type="object_detection"
                config_yaml_path = '{}/../../../configs/object_detection.yaml'.format(cwd)
            with open(config_yaml_path,'r+') as f:
                y = json.dumps(yaml.load(f,Loader=yaml.FullLoader))
                y=json.loads(y)
                #keyCount  = int(len(y)/2)
                keyCount  = int(len(y["models"]))
                print(keyCount)
                if model_type == "object_detection":
                    with open('{}/param.yaml'.format(path),'r') as fp:
                        print("open param file")
                        z = json.dumps(yaml.load(fp,Loader=yaml.FullLoader))
                        z = json.loads(z)
                        threshold = z["postprocess"]["detection_threshold"]
                        print(threshold)
                        print(type(threshold))
                    model = {"model{}".format(keyCount):{"model_path":"{}".format(path),"viz_threshold":threshold}}
                    #model = {"model{}".format(keyCount):{"model_path":"{}".format(path),"viz_threshold":0.6}}
                if model_type == "image_classification":
                    model = {"model{}".format(keyCount):{"model_path":"{}".format(path),"topN":1}}
                #print(y["models"])
                y["models"].update(model)
                #print(y)
                
                y["flows"]["flow0"]["models"] = ['model{}'.format(keyCount)]
                y["inputs"]["input0"]["source"] = dev_num
                #print(y)
            os.rename(config_yaml_path,'{}/../../../configs/copy.yaml'.format(cwd))
            with open('{}/../../../configs/copy.yaml'.format(cwd),'w') as fout:
                yaml.safe_dump(y,fout,sort_keys=False)
            os.rename('{}/../../../configs/copy.yaml'.format(cwd),config_yaml_path)
            if inference_process is None or not inference_process.is_alive():
                inference_process = InferenceProcess(model_type)
                inference_process.start()
                process_name="app_edgeai.py"
                print("point 1")
                for proc in psutil.process_iter():
                    if process_name in proc.name():
                        pid = proc.pid
                        print(pid)
                x.session.data_pipeline_pid=pid
                x.session.data_pipeline_status="up"
                x.session.ws_status="up"
                x.session.ws_pid=os.getpid()
                sensor_session = x.dict()
                print("point 2")
                if inference_process is None or not inference_process.is_alive():
                    os.system("sed -i '/modelmaker/d' {}/../../classnames.py".format(cwd)) 
                    dir_name = '{}/../../../../projects'.format(cwd)
                    for dir in os.listdir(dir_name):
                        path = os.path.join(dir_name, dir)
                        if len(path) != 0:
                            os.system('rm -r {}'.format(path))
                    x.session.data_pipeline_pid=0
                    x.session.data_pipeline_status="down"
                    x.session.ws_status="down"
                    x.session.ws_pid=0
                    sensor_session = x.dict()

                    raise HTTPException(
                     status_code=response_code.CONFLICT.value, detail=response_detail.SESSION_CONFLICT.value)

                else:
                    return x
            else:
                raise HTTPException(
                     status_code=response_code.CONFLICT.value, detail=response_detail.SESSION_CONFLICT.value)

# POST call endpoint for initiating sensor session by starting server
@app.post('/sensor-session',status_code=response_code.ACCEPTED.value)
def initiate_sensor_session(x: Sensor):
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
    ncount=0
    #while j < sensor_count:
    if x.device[0].id!=(sensor[0].device[0].id):
        #count = count + 1
        #break
        #j = j + 1
        #if(count==0):
        raise HTTPException(
                status_code=response_code.METHOD_NOT_ALLOWED.value, detail=response_detail.INVALID_INPUT.value)
    #count = 0
    if ncount != 0:
        for proc in psutil.process_iter():
            if process_name in proc.name():
                pid = proc.pid
                print(pid)
                count = 1
                ncount = 1
                break
    print('hi')
    if count != 1:
        print("before starting server")
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
                print("newly created node",pid)
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
    global sensor_session
    global ss_id
    global keyCount
    #global model_type
    global config_yaml_path
    #global sensor
    #global sensor_count
    pid=None
    if(id != ss_id):
        raise HTTPException(
            status_code=response_code.BAD_REQUEST.value, detail=response_detail.INVALID_ID.value)
    if sensor_session["inference"] == False:
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
    else:
        if inference_process is not None and inference_process.is_alive():
            process_name="app_edgeai.py"
            for proc in psutil.process_iter():
                if process_name in proc.name():
                    pid = proc.pid
                    os.kill(pid,2)
                    inference_process.terminate()
                    sensor_session["session"]["data_pipeline_status"]="down"
                    sensor_session["session"]["data_pipeline_pid"]=0
                    sensor_session["session"]["ws_status"]="down"
                    sensor_session["session"]["ws_pid"]=0
                    #sensor.clear()
                    #sensor_count = 0
                    #print("sensor after clearing is",sensor)
                    #os.system("sed -i '$d' {}/../../classnames.py".format(cwd)) 
                    os.system("sed -i '/modelmaker/d' {}/../../classnames.py".format(cwd))
                    #if model_type == "image_classification":
                    with open(config_yaml_path, 'r') as fin:
                        y = json.dumps(yaml.load(fin,Loader=yaml.FullLoader))
                        y=json.loads(y) 
                        x = y["models"]
                        x.popitem()
                        y["models"] = x
                    with open(config_yaml_path,'w') as fout:
                        yaml.safe_dump(y,fout,sort_keys=False)
                        
                    return(response_detail.ACCEPTED.value) 
        else:

            os.system("sed -i '/modelmaker/d' {}/../../classnames.py".format(cwd)) 
            raise HTTPException(
                status_code=response_code.NOT_FOUND.value, detail=response_detail.NOT_FOUND.value)

""" #GET call endpoint to get sensor details
@app.get('/sensor',status_code=response_code.OK.value) # get sensor details
def get_sensor():   
    i = 0
    j=0
    dev_no = []
    name = []
    Id = []
    global sensor
    global sensor_count 
    print("get sensor details called")
    if len(sensor) != 0:
        sensor.clear()
        sensor_count = 0
    data = subprocess.check_output("./get_videono.sh")
    if(len(data) != 0):
        for line in data.split(b'\n'):
            if(re.search('/sys/class/video4linux',line.decode())):
                dev_no.append("video" + line.decode()[len(line.decode())-1])
                sensor_count = sensor_count + 1
        print(dev_no)
        device_type="V4L2"
        sensor_type="Webcam"
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
                name.append((devices[j]['tag']).decode())
                Id.append((devices[j]['id']).decode())
            j=j-1
        print(name)
        print(Id)
        while i < sensor_count:
            sensor.append(Sensor(name = name[i],id = Id[i], type = sensor_type, device = [DeviceItem(id = dev_no[i],type = device_type, description = description, status = status)]))
            i = i + 1
        print(sensor)
        return sensor
    else:
        raise HTTPException(
            status_code=response_code.NOT_FOUND.value, detail=response_detail.NOT_FOUND.value)
 """
#GET call endpoint to get sensor details
@app.get('/sensor',status_code=response_code.OK.value) # get sensor details
def get_sensor():   
    i = 0
    j=0
    #dev_no = []
    #name = []
    #Id = []
    global sensor
    global sensor_count 
    global dev_num
    print("get sensor details called")
    if len(sensor) != 0:
        sensor.clear()
        sensor_count = 0
    line_count = 0
    data = subprocess.Popen('../../../scripts/setup_cameras.sh',stdout=subprocess.PIPE,bufsize=1,universal_newlines=True,shell=True)
    #line = data.stdout.readline()
    line = data.stdout.readline()
    #print(line)
    #out = data.communicate()[0]
    if not line:
    #if len(data) == 0:
        print("not found")
        raise HTTPException(
            status_code=response_code.NOT_FOUND.value, detail=response_detail.NOT_FOUND.value)
    else: 
        for l in data.stdout:
            output = l.rstrip()
            print(output)
            line_count = line_count + 1
            print(line_count)
            if(line_count == 1):
                break
        parts = output.split(' ')
        #print(output)
        #print(parts)
        dev_num = (parts[6])
        #print(dev_no)
        dev_no = dev_num.replace('/dev/','')
        usb_name = subprocess.Popen('cat /sys/class/video4linux/{}/name'.format(dev_no),stdout=subprocess.PIPE,bufsize=1,universal_newlines=True,shell=True)
        usb_name = usb_name.communicate()[0]
        #print(usb_name)
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
        
#GET call endpoint to get sensor details using id
@app.get('/sensor/{id}',status_code=response_code.OK.value) # get sensor details by id
def get_sensor_byid(id):
    global sensor
    global sensor_count
    count=0
    j=0
    while j < sensor_count:
        if id==(sensor[j].device[0].id):
            count = count + 1
            break
        j = j + 1
    if(count==0):
        raise HTTPException(
                status_code=response_code.NOT_FOUND.value, detail=response_detail.NOT_FOUND.value)
    else:
        return sensor[j]
    

'''#POST call endpoint to create project
@app.post('/project',status_code=response_code.CREATED.value)
def post_project(x: Project):
    global cwd
    project = x.dict()
    if(os.path.exists('{}/../../../../projects/{}'.format(cwd,x.id))):
        #raise HTTPException(status_code=response_code.CONFLICT.value, detail=response_detail.PROJECT_CONFLICT.value)
        print("project exists")
    else:
        os.system('mkdir {}/../../../../projects/{}'.format(cwd,x.id))    
    with open("{}/../../../../projects/{}/project.config".format(cwd,x.id), "w") as outfile:
        json.dump(project, outfile)
        return(response_detail.CREATED.value)'''

#POST call endpoint to create project
@app.post('/project',status_code=response_code.CREATED.value)
def post_project(x: Project):
    global cwd
    project = x.dict()
    dir_name = '{}/../../../../projects'.format(cwd)
    for dir in os.listdir(dir_name):
        path = os.path.join(dir_name, dir)
        if len(path) != 0:
            os.system('rm -r {}'.format(path))
    os.system('mkdir {}/../../../../projects/{}'.format(cwd,x.id))    
    with open("{}/../../../../projects/{}/project.config".format(cwd,x.id), "w") as outfile:
        json.dump(project, outfile)
        return(response_detail.CREATED.value)

#POST call endpoint to upload model
@app.post('/project/{id}/model',status_code=response_code.CREATED.value)
async def upload_model(id,file: UploadFile = File(...)):
    global cwd
    global project_dir

    print("FILE:",file)
    print("filename :",file.filename)
    filecontent= await file.read()
  
    filesize = len(filecontent)
    print('filesize',filesize)

    filepath = os.path.join('./', os.path.basename('outputFile.tar.gz'))
    print('inside filepath')
    async with aiofiles.open(filepath, 'wb') as f:
        print('inside async')
        await f.write(filecontent)
    count = 0
    
    if os.path.isdir('{}{}/{}'.format(cwd,project_dir,id)):
           
        with open('{}{}/{}/project.config'.format(cwd,project_dir,id),'r+') as config:
            project = json.load(config)
            print("project",project)
            print("project type",type(project['id']))
            if(project['id'] == id):
                count = count + 1
                name = project['name']
                print("name :",name)
                #with open(file.filename, 'wb') as f:
                    #content = await file.read()
                    #print("content type :",type(content))                            
                    #f.write(content)
                    #f.close()
                    #print("file.filename :",file.filename)    

                    #tar = tarfile.open('/opt/edge_ai_apps/apps_python/ti-edgeai-studio-evm-agent/src/yolox_s_lite_mmdet_20000101-010101_onnxrt_tda4vm.tar.gz')
                    #print(tar.getnames()) 
                    #tar.extractall('{}/../../../../projects/{}'.format(cwd,project['id']))
                    #print('EXTRACTED') 


                tar = tarfile.open('/opt/edge_ai_apps/apps_python/ti-edgeai-studio-evm-agent/src/outputFile.tar.gz')
                print(tar.getnames()) 
                tar.extractall('{}/../../../../projects/{}'.format(cwd,project['id']))
                print('EXTRACTED') 
                os.remove('/opt/edge_ai_apps/apps_python/ti-edgeai-studio-evm-agent/src/outputFile.tar.gz')

                with open('{}/../../../../projects/{}/param.yaml'.format(cwd,project['id']),'r+') as f:
                    model_param = json.dumps(yaml.load(f,Loader=yaml.FullLoader))
                    print("model_param :",model_param)
                    y=json.loads(model_param)
                    model_path = y['session']['model_path']
                    print("model_path :",model_path)
                path = '{}/../../../../projects/{}/{}'.format(cwd,project['id'],model_path)
                model_checksum = hashlib.md5(open(path,'rb').read()).hexdigest()
                print("model_checksum :",model_checksum)
                project['model_file_checksum']=model_checksum
                project['model_file']=model_path
                print("project['model_file'] :",project['model_file'])
                config.seek(0)
                json.dump(project,config)
                config.truncate()
                
                
    if(count == 0):
        raise HTTPException(
            status_code=response_code.NOT_FOUND.value, detail=response_detail.NOT_FOUND.value)
    else:
        return(response_detail.CREATED.value,project['id'])

#GET call endpoint to get project details
@app.get('/project')
def get_projects():
    project_list = []
    count = 0
    for path in glob.iglob('{}/../../../../projects/**'.format(cwd),recursive=True):
        if os.path.isfile(path): # filter dirs
            print(path)
            try:
                with open(path,'r+') as config:
                    project = json.load(config)
                    print(project)
                    project_list.append(project)
                    count = count + 1
            except:
                continue
    if(count == 0):
        raise HTTPException(
            status_code=404, detail="No registered projects found")
    else:
        return(project_list)

""" #GET call endpoint to get project details
@app.get('/project/{id}',status_code=response_code.OK.value)
def get_project_id(id):
    count = 0
    global cwd
    for path in glob.iglob('{}/../../../../projects/**'.format(cwd),recursive=True):
        if os.path.isfile(path): # filter dirs
            print(path)
            try:
                with open(path,'r+') as config:
                    project = json.load(config)
                    print(project)
                    if(project['id'] == id):
                        count = count + 1
                        break
            except:
                continue
    print(count)
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
    for path in glob.iglob('{}/../../../../projects/**'.format(cwd),recursive=True):
        if os.path.isfile(path): # filter dirs
            print(path)
            try:
                with open(path,'r+') as config:
                    project = json.load(config)
                    print(project)
                    print(type(project['id']))
                    if(project['id'] == id):
                        os.system('rm -r {}/../../../../projects/{}'.format(cwd,project['id']))
                        count = count + 1
                        break
            except:
                continue

    if(count == 0):
        raise HTTPException(
            status_code=response_code.NOT_FOUND.value, detail=response_detail.NOT_FOUND.value)
    else:
        return(response_detail.SUCCESS.value)
 """
 #GET call endpoint to get project details
@app.get('/project/{id}',status_code=response_code.OK.value)
def get_project_id(id):
    count = 0
    global cwd
    global project_dir
    if os.path.isdir('{}{}/{}'.format(cwd,project_dir,id)): # filter dirs
            
        with open('{}{}/{}/project.config'.format(cwd,project_dir,id),'r+') as config:
            project = json.load(config)
            print(project)
            if(project['id'] == id):
                count = count + 1
            
    
    print(count)
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
    global project_dir
    
    if os.path.isdir('{}{}/{}'.format(cwd,project_dir,id)): # filter dirs
        
            
        with open('{}{}/{}/project.config'.format(cwd,project_dir,id),'r+') as config:
            project = json.load(config)
            print(project)
            print(type(project['id']))
            if(project['id'] == id):
                os.system('rm -r {}{}/{}'.format(cwd,project_dir,project['id']))
                count = count + 1
    
    if(count == 0):
        raise HTTPException(
            status_code=response_code.NOT_FOUND.value, detail=response_detail.NOT_FOUND.value)
    else:
        return(response_detail.SUCCESS.value)
 
if __name__ == "__main__":

    process_name = 'node'
    for proc in psutil.process_iter():                                                                           
        if process_name in proc.name():                                                                                                                
            pid = proc.pid  
            print(pid)                                                                                                                        
            os.system('kill -9 {}'.format(pid)) 
    if not os.path.isdir('{}{}'.format(cwd,project_dir)):
        os.system('mkdir {}{}'.format(cwd,project_dir)) 
    
    config_yaml_path = ['{}/../../../configs/image_classification.yaml'.format(cwd),'{}/../../../configs/object_detection.yaml'.format(cwd)]
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
                print(y)
            with open(path,'w') as fout:
                yaml.safe_dump(y,fout,sort_keys=False)
            count = 0
    uvicorn.run("device_agent:app",
                host="0.0.0.0", port=8000, reload=True, ws_ping_interval=math.inf, ws_ping_timeout=math.inf)


