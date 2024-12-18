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
from multiprocessing import SimpleQueue
from typing import Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import os
import subprocess
from vstream_thread import InferenceProcess, RawvideoProcess
import re
import psutil
import json
from typing import List
from fastapi.responses import FileResponse
import uuid
import glob
import hashlib
from definitions import Response_Code, Response_Details, Server_Details, Dir_Path, SOC_Vals
import yaml
import math
import tarfile
import aiofiles

app = FastAPI()
active_connections: List[WebSocket] = []
# Set CORS setting
origins = ["http://localhost", "http://localhost:3000", "http://localhost:2000", "*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

inference_process = None
rawvideo_process = None
ss_id = 0
sensor_session = None
sensor = []
cwd = os.getcwd()
keyCount = 0
config_yaml_path = None
dev_num = None

# Below classes define request-body using pydantic
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
    stream_type: str = Field(default="null")


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
    sdk_version: str
    device_name: str


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
async def websocket_endpoint(websocket: WebSocket, client_id: int):
    """
    Websocket endpoint to send inference log
    """
    await manager1.connect(websocket)
    try:
        while True:
            """
            Receives log from websocket endpoint in vstream_thread file
            and broadcast to GUI
            """
            data = await websocket.receive_text()
            # Apply regex to remove non readable characters
            text = re.sub(r"(\x9B|\x1B[\[\(\=])[0-?]*[ -\/]*([@-~]|$)", "", data)
            await manager1.broadcast_log(text)
    except Exception as e:
        manager1.disconnect(websocket)


@app.websocket("/ws/{client_id}/inference")
async def websocket_endpoint(websocket: WebSocket, client_id: int):
    """
    Websocket endpoint to send inference parameters
    """
    await manager2.connect(websocket)
    try:
        while True:
            """
            Receives inference parameters from websocket endpoint in vstream_thread file
            and broadcast to GUI
            """
            data = await websocket.receive_text()
            infer_data = json.loads(data)
            await manager2.broadcast_inference(infer_data)
    except Exception as e:
        manager2.disconnect(websocket)


@app.websocket("/ws/{client_id}/usbcam_status")
async def websocket_endpoint(websocket: WebSocket, client_id: int):
    """
    Websocket endpoint to send usb camera status
    """
    await manager3.connect(websocket)
    try:
        while True:
            """
            Receives usb cam status from websocket endpoint in vstream_thread file
            and broadcast to GUI
            """
            data = await websocket.receive_text()
            await manager3.broadcast_status(data)

    except Exception as e:
        manager3.disconnect(websocket)


@app.put("/sensor-session/{id}", status_code=Response_Code.ACCEPTED.value)
def start_sensor_session(id, x: Model):
    """
    Function to start sensor session by setting up all the
    required data access pipeline processes
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
    process_name = "../server/node_webserver.js"
    count = 0
    model_type = None
    # check if node process running or not
    for proc in psutil.process_iter():
        try:
            cmdline = proc.cmdline()
        except psutil.AccessDenied:
            continue
        except (psutil.ZombieProcess, psutil.NoSuchProcess):
            continue
        except Exception as e: # optional and use with care;
            log.exception("something is wrong: " + ' '.join(cmdline))
            continue
        if process_name in cmdline:
            pid = proc.pid
            count = 1
            break
    if count == 0:
        raise HTTPException(
            status_code=Response_Code.NOT_FOUND.value,
            detail=Response_Details.SESSION_NOT_FOUND.value,
        )
    # check the sensor session id with the id sent from ui
    if id != ss_id:
        raise HTTPException(
            status_code=Response_Code.BAD_REQUEST.value,
            detail=Response_Details.INVALID_ID.value,
        )
    # check if inference or raw stream to be started
    if x.inference == False:
        # check if raw thread is running; if no start
        if rawvideo_process is None or not rawvideo_process.is_alive():

            status = SimpleQueue()
            isStreamValid = True

            try:
                # Start raw video stream thread with parameter to indicate device file name
                rawvideo_process = RawvideoProcess(dev_num, x.session.stream_type, status)
                rawvideo_process.start()
                process_name = "python_gst.py"
                time.sleep(SOC_Vals.RAWVIDEOPROCESS_LAUNCH_TIMEOUT.value)
                for proc in psutil.process_iter():
                    if process_name in proc.name():
                        pid = proc.pid
                        print(pid)
                time.sleep(1)
                x.session.data_pipeline_pid = pid
                x.session.data_pipeline_status = "up"
                x.session.ws_status = "up"
                x.session.ws_pid = os.getpid()
                sensor_session = x.dict()
                if status.empty() == False:
                    isStreamValid = status.get()[0]
                status.close()
                if isStreamValid == False:
                    raise Exception("Cannot start stream")
                return x
            except:
                print("Error starting raw stream ")
                x.session.data_pipeline_pid = 0
                x.session.data_pipeline_status = "down"
                sensor_session = x.dict()
                raise HTTPException(
                    status_code=Response_Code.BAD_REQUEST.value,
                    detail=Response_Details.INVALID_INPUT.value
                )

        else:
            raise HTTPException(
                status_code=Response_Code.CONFLICT.value,
                detail=Response_Details.SESSION_CONFLICT.value,
            )

    else:
        # check if inference thread is running
        if inference_process is None or not inference_process.is_alive():
            print("inside inference")
            pcount = 0
            # check if project folder of specified id exists
            if os.path.isdir(
                "{}{}/{}".format(cwd, Dir_Path.PROJECT_DIR.value, x.project.id)
            ):

                with open(
                    "{}{}/{}/project.config".format(
                        cwd, Dir_Path.PROJECT_DIR.value, x.project.id
                    ),
                    "r+",
                ) as config:
                    project = json.load(config)
                    # check project id in project.config file is same, if yes update pcount
                    if project["id"] == x.project.id:
                        pcount = pcount + 1
                        path = "{}{}/{}".format(
                            cwd, Dir_Path.PROJECT_DIR.value, project["id"]
                        )

            if pcount == 0:
                raise HTTPException(
                    status_code=Response_Code.NOT_FOUND.value,
                    detail=Response_Details.PROJECT_NOT_FOUND.value,
                )
            else:
                """
                check the type of inference and set the config file paths and model_type
                variable to be sent as parameter when calling inference thread
                """
                if x.project.task_type == "classification":
                    model_type = "image_classification"
                    config_yaml_path = "../config/image_classification.yaml"
                elif x.project.task_type == "detection":
                    model_type = "object_detection"
                    config_yaml_path = "../config/object_detection.yaml"
                elif x.project.task_type == "segmentation":
                    model_type = "semantic_segmentation"
                    config_yaml_path = "../config/semantic_segmentation.yaml"
                elif x.project.task_type == "keypoint_detection":
                    model_type = "keypoint_detection"
                    config_yaml_path = "../config/keypoint_detection.yaml"
                else:
                    raise HTTPException(
                        status_code=Response_Code.BAD_REQUEST.value,
                        detail=Response_Details.INVALID_TASK_TYPE.value,
                    )
                with open(config_yaml_path, "r+") as f:
                    y = json.dumps(yaml.load(f, Loader=yaml.FullLoader))
                    y = json.loads(y)
                    keyCount = int(len(y["models"]))
                    # Parse threshold value from param.yaml file for detection models and update in config file
                    if model_type == "object_detection":
                        with open("{}/param.yaml".format(path), "r") as fp:
                            z = json.dumps(yaml.load(fp, Loader=yaml.FullLoader))
                            z = json.loads(z)
                            if (
                                "postprocess" in z
                                and "detection_threshold" in z["postprocess"]
                            ):
                                threshold = z["postprocess"]["detection_threshold"]
                            else:
                                threshold = 0.6

                        model = {
                            "model{}".format(keyCount): {
                                "model_path": "{}".format(path),
                                "viz_threshold": threshold,
                            }
                        }
                    # If classification model, set topN as 1
                    if model_type == "image_classification":
                        model = {
                            "model{}".format(keyCount): {
                                "model_path": "{}".format(path),
                                "topN": 1,
                            }
                        }
                    # If semantic segmentation, set alpha to 0.5
                    if model_type == "semantic_segmentation":
                        model = {
                            "model{}".format(keyCount): {
                                "model_path": "{}".format(path),
                                "alpha": 0.5,
                            }
                        }
                    # If keypoint_detection, set viz_threshold to 0.5
                    if model_type == "keypoint_detection":
                        model = {
                            "model{}".format(keyCount): {
                                "model_path": "{}".format(path),
                                "viz_threshold": 0.5,
                            }
                        }
                    y["models"].update(model)
                    y["flows"]["flow0"][1] = "model{}".format(keyCount)
                    y["inputs"]["input0"]["source"] = dev_num
                    if x.session.stream_type == 'image':
                        y["outputs"]["output0"]["encoding"] = 'jpeg'
                    else:
                        y["outputs"]["output0"]["encoding"] = 'mp4'

                with open(config_yaml_path, "w") as fout:
                    yaml.safe_dump(y, fout, sort_keys=False)

                    status = SimpleQueue()
                    isStreamValid = True

                    try:
                        # Start inference thread with the parameter to indicate type of inference
                        inference_process = InferenceProcess(model_type, dev_num, status)
                        inference_process.start()
                        process_name = "optiflow"
                        time.sleep(SOC_Vals.OPTIFLOW_LAUNCH_TIMEOUT.value)
                        # get the pid for inference
                        for proc in psutil.process_iter():
                            if process_name in proc.name():
                                pid = proc.pid
                                print(pid)
                        time.sleep(1)
                        x.session.data_pipeline_pid = pid
                        x.session.data_pipeline_status = "up"
                        x.session.ws_status = "up"
                        x.session.ws_pid = os.getpid()
                        sensor_session = x.dict()
                        if status.empty() == False:
                            isStreamValid = status.get()[0]
                        status.close()
                        if isStreamValid == False:
                            raise Exception("Cannot start stream")
                        return x
                    except:
                        """
                        If exception occurred while starting inference do cleanup as in delete project folder
                        and remove model path updated in config file
                        """
                        dir_name = "{}{}".format(cwd, Dir_Path.PROJECT_DIR.value)
                        for dir in os.listdir(dir_name):
                            path = os.path.join(dir_name, dir)
                            if len(path) != 0:
                                os.system("rm -r {}".format(path))
                        x.session.data_pipeline_pid = 0
                        x.session.data_pipeline_status = "down"
                        x.session.ws_status = "down"
                        x.session.ws_pid = 0
                        sensor_session = x.dict()
                        with open(config_yaml_path, "r") as fin:
                            y = json.dumps(yaml.load(fin, Loader=yaml.FullLoader))
                            y = json.loads(y)
                            x = y["models"]
                            x.popitem()
                            y["models"] = x
                        with open(config_yaml_path, "w") as fout:
                            yaml.safe_dump(y, fout, sort_keys=False)
                        raise HTTPException(
                            status_code=Response_Code.BAD_REQUEST.value,
                            detail=Response_Details.INVALID_INPUT.value
                        )
        else:
            raise HTTPException(
                status_code=Response_Code.CONFLICT.value,
                detail=Response_Details.SESSION_CONFLICT.value,
            )


@app.post("/sensor-session", status_code=Response_Code.ACCEPTED.value)
def initiate_sensor_session(x: Sensor):
    """
    Function to initiate sensor session by starting udp node server
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
    j = 0
    process_name = "../server/node_webserver.js"
    pid = None
    if x.device[0].id != (sensor[0].device[0].id):
        raise HTTPException(
            status_code=Response_Code.METHOD_NOT_ALLOWED.value,
            detail=Response_Details.INVALID_INPUT.value,
        )
    # Check if node process is running or not and update count variable
    for proc in psutil.process_iter():
        try:
            cmdline = proc.cmdline()
        except psutil.AccessDenied:
            continue
        except (psutil.ZombieProcess, psutil.NoSuchProcess):
            continue
        except Exception as e: # optional and use with care;
            log.exception("something is wrong: " + ' '.join(cmdline))
            continue
        if process_name in cmdline:
            pid = proc.pid
            count = 1
            break
    # if count is 0 then start server
    if count != 1:
        print("starting server")
        p = subprocess.Popen(
            "node ../server/node_webserver.js",
            stdout=subprocess.PIPE,
            bufsize=1,
            universal_newlines=True,
            shell=True,
        )
        # pipe stdout terminal log (server initiation)
        for line in p.stdout:
            output = line.rstrip()
            print(output)
            line_count = line_count + 1
            if line_count == 2:
                break
        # get pid of current node process
        for proc in psutil.process_iter():
            if process_name in proc.name():
                pid = proc.pid
                print("newly created node", pid)
        # Generate sensor session id
        ss_id = str(uuid.uuid4())
        session = Model(
            session={
                "id": ss_id,
                "http_status": "started",
                "http_pid": p.pid,
                "udp_status": "started",
                "udp_pid": p.pid,
                "data_pipeline_status": "down",
                "data_pipeline_pid": 0,
            },
            sensor={
                "name": x.name,
                "id": x.id,
                "type": x.type,
                "device": [
                    {
                        "id": x.device[0].id,
                        "type": x.device[0].type,
                        "description": x.device[0].type,
                        "status": x.device[0].status,
                    }
                ],
                "sdk_version": x.sdk_version,
                "device_name": x.device_name
            },
        )
        sensor_session = session.dict()
        return session
    ss_id = str(uuid.uuid4())
    sensor_session['session']['id']=ss_id
    return sensor_session


@app.get("/sensor-session", status_code=Response_Code.OK.value)
def get_sensor_session():
    """
    Function to return sensor session details including initiated and started ones
    """
    global ss_id
    global sensor_session
    # check if sensor session variable used for storing session details is empty
    if sensor_session == None:
        raise HTTPException(
            status_code=Response_Code.NOT_FOUND.value,
            detail=Response_Details.SESSION_NOT_FOUND.value,
        )
    else:
        return sensor_session


@app.get("/sensor-session/{id}", status_code=Response_Code.OK.value)
def get_sensor_session_id(id):
    """
    Function to return sensor session of specified sensor session id
    Args:
        id: Sensor session id parameter
    """
    global ss_id
    global sensor_session
    if sensor_session == None:
        raise HTTPException(
            status_code=Response_Code.NOT_FOUND.value,
            detail=Response_Details.SESSION_NOT_FOUND.value,
        )
    if id != sensor_session["session"]["id"]:
        raise HTTPException(
            status_code=Response_Code.BAD_REQUEST.value,
            detail=Response_Details.INVALID_ID.value,
        )
    else:
        return sensor_session


@app.delete("/sensor-session/{id}", status_code=Response_Code.ACCEPTED.value)
def delete_sensor_session(id):
    """
    Function to stop node udp server
    Args:
        id: Sensor session id
    """
    global ss_id
    global sensor_session
    pid = None
    count = 0
    # Check parameter id and current session id(ss_id) is same before deleting session
    if id != ss_id:
        raise HTTPException(
            status_code=Response_Code.BAD_REQUEST.value,
            detail=Response_Details.INVALID_ID.value,
        )
    process_name = "../server/node_webserver.js"
    # Terminate/kill node server using its process id
    for proc in psutil.process_iter():
        try:
            cmdline = proc.cmdline()
        except psutil.AccessDenied:
            continue
        except (psutil.ZombieProcess, psutil.NoSuchProcess):
            continue
        except Exception as e:
            log.exception("something is wrong: " + ' '.join(cmdline))
            continue
        if process_name in cmdline:
            pid = proc.pid
            count = 1
            os.kill(pid, 2)
            sensor_session = None
            return Response_Details.ACCEPTED.value
    if count == 0:
        raise HTTPException(
            status_code=Response_Code.NOT_FOUND.value,
            detail=Response_Details.SESSION_NOT_FOUND.value,
        )


@app.delete("/sensor-session/{id}/dpipe", status_code=Response_Code.ACCEPTED.value)
def delete_data_pipeline(id):
    """
    Function to terminate data pipeline associated with started session
    Args:
        id: Sensor session id parameter
    """
    global rawvideo_process
    global inference_process
    global sensor_session
    global ss_id
    global keyCount
    global config_yaml_path
    pid = None
    # Check parameter id and current session id(ss_id) is same before deleting pipeline
    if id != ss_id:
        raise HTTPException(
            status_code=Response_Code.BAD_REQUEST.value,
            detail=Response_Details.INVALID_ID.value,
        )
    # Check if raw video or inference video to be deleted
    if sensor_session["inference"] == False:
        # check if raw stream thread is running
        if rawvideo_process is not None and rawvideo_process.is_alive():
            process_name = "python_gst.py"
            # Terminate/kill raw video stream pipeline using its process id
            for proc in psutil.process_iter():
                if process_name in proc.name():
                    pid = proc.pid
                    os.kill(pid, 2)
                    rawvideo_process.terminate()
                    sensor_session["session"]["data_pipeline_status"] = "down"
                    sensor_session["session"]["data_pipeline_pid"] = 0

            return Response_Details.ACCEPTED.value
        else:
            raise HTTPException(
                status_code=Response_Code.NOT_FOUND.value,
                detail=Response_Details.SESSION_NOT_FOUND.value,
            )
    else:
        # check if inference stream thread is running
        if inference_process is not None and inference_process.is_alive():
            process_name = "parse_gst_trace"
            # Terminate/kill inference stream pipeline using its process id
            for proc in psutil.process_iter():
                if process_name in proc.name():
                    pid = proc.pid
                    os.kill(pid, 2)
                    inference_process.terminate()
                    sensor_session["session"]["data_pipeline_status"] = "down"
                    sensor_session["session"]["data_pipeline_pid"] = 0
                    sensor_session["session"]["ws_status"] = "down"
                    sensor_session["session"]["ws_pid"] = 0
                    # Remove json object for model path in config file as part of cleanup
                    with open(config_yaml_path, "r") as fin:
                        y = json.dumps(yaml.load(fin, Loader=yaml.FullLoader))
                        y = json.loads(y)
                        x = y["models"]
                        x.popitem()
                        y["models"] = x
                    with open(config_yaml_path, "w") as fout:
                        yaml.safe_dump(y, fout, sort_keys=False)

                    return Response_Details.ACCEPTED.value
        else:

            raise HTTPException(
                status_code=Response_Code.NOT_FOUND.value,
                detail=Response_Details.SESSION_NOT_FOUND.value,
            )


@app.get("/sensor", status_code=Response_Code.OK.value)
def get_sensor():
    """
    Returns sensor details
    """
    i = 0
    j = 0
    global sensor
    global dev_num
    print("get sensor endpoint called")
    if len(sensor) != 0:
        sensor.clear()
    line_count = 0
    """
    Use setup_cameras.sh sdk script to check camera connection and
    if yes,extract video device file name
    """
    data = subprocess.Popen(
        "{}/setup_cameras.sh".format(Dir_Path.SCRIPTS_DIR.value),
        stdout=subprocess.PIPE,
        bufsize=1,
        universal_newlines=True,
        shell=True,
    )
    line = data.stdout.readline()
    if not line:
        print("sensor not found")
        raise HTTPException(
            status_code=Response_Code.NOT_FOUND.value,
            detail=Response_Details.SENSOR_NOT_FOUND.value,
        )
    else:
        for l in data.stdout:
            output = l.rstrip()
            line_count = line_count + 1
            if line_count == 1:
                break
        parts = output.split(" ")
        # Extracted video device file name copied to dev_num variable
        dev_num = parts[6]
        # Get actual device id
        dev_no = os.readlink(dev_num)
        dev_no = dev_no.strip()
        dev_no = dev_no.replace("/dev/", "")
        # Extract sensor name
        usb_name = subprocess.Popen(
            "cat /sys/class/video4linux/{}/name".format(dev_no),
            stdout=subprocess.PIPE,
            bufsize=1,
            universal_newlines=True,
            shell=True,
        )
        usb_name = usb_name.communicate()[0]
        if len(usb_name) == 0:
            name = "unknown device"
        else:
            name = usb_name.strip()
        device_type = "V4L2"
        sensor_type = "Webcam"
        description = "device available for capture"
        status = "available"
        sdk_version = os.getenv('EDGEAI_VERSION')
        device_name = os.getenv('DEVICE_NAME')
        sensor.append(
            Sensor(
                name=name,
                id="null",
                type=sensor_type,
                device=[
                    DeviceItem(
                        id=dev_num,
                        type=device_type,
                        description=description,
                        status=status,
                    )
                ],
                sdk_version=sdk_version,
                device_name=device_name
            )
        )
        return sensor


@app.post("/project", status_code=Response_Code.CREATED.value)
def post_project(x: Project):
    """
    Create project folder and add Project class object
    in project.config file sent as part of request body
    Args:
        x: Project class object
    """
    global cwd
    project = x.dict()
    dir_name = "{}{}".format(cwd, Dir_Path.PROJECT_DIR.value)
    # Delete previous project inside projects folder
    for dir in os.listdir(dir_name):
        path = os.path.join(dir_name, dir)
        if len(path) != 0:
                os.system("rm -r {}".format(path))
    os.system("mkdir {}{}/{}".format(cwd, Dir_Path.PROJECT_DIR.value, x.id))
    with open(
        "{}{}/{}/project.config".format(cwd, Dir_Path.PROJECT_DIR.value, x.id), "w"
    ) as outfile:
        json.dump(project, outfile)
        return Response_Details.CREATED.value


@app.post("/project/{id}/model", status_code=Response_Code.CREATED.value)
async def upload_model(id, file: UploadFile = File(...)):
    """
    Function to upload model for inference inside the project folder
    Args:
        id: Project id parameter
        file: actual Python file that you can pass directly to other functions
              or libraries that expect a "file-like" object
    """
    global cwd
    try:
        print("FILE:", file)
        print("filename :", file.filename)
        filecontent = await file.read()
        filesize = len(filecontent)
        print("filesize is", filesize)

        filepath = os.path.join("./", os.path.basename("outputFile.tar.gz"))
        # Use aiofiles package to write base 64 file
        async with aiofiles.open(filepath, "wb") as f:
            await f.write(filecontent)
        count = 0

        if os.path.isdir("{}{}/{}".format(cwd, Dir_Path.PROJECT_DIR.value, id)):

            with open(
                "{}{}/{}/project.config".format(cwd, Dir_Path.PROJECT_DIR.value, id),
                "r+",
            ) as config:
                project = json.load(config)
                # confirm project folder before extraction
                if project["id"] == id:
                    count = count + 1
                    name = project["name"]
                    tar = tarfile.open("{}/outputFile.tar.gz".format(cwd))
                    tar.extractall(
                        "{}{}/{}".format(cwd, Dir_Path.PROJECT_DIR.value, project["id"])
                    )
                    print("EXTRACTED")
                    os.remove("{}/outputFile.tar.gz".format(cwd))
                    # to get model file path
                    with open(
                        "{}{}/{}/param.yaml".format(
                            cwd, Dir_Path.PROJECT_DIR.value, project["id"]
                        ),
                        "r+",
                    ) as f:
                        model_param = json.dumps(yaml.load(f, Loader=yaml.FullLoader))
                        y = json.loads(model_param)
                        model_path = y["session"]["model_path"]

                    path = "{}{}/{}/{}".format(
                        cwd, Dir_Path.PROJECT_DIR.value, project["id"], model_path
                    )
                    model_checksum = hashlib.md5(open(path, "rb").read()).hexdigest()
                    project["model_file_checksum"] = model_checksum
                    project["model_file"] = model_path
                    # Update project config file
                    config.seek(0)
                    json.dump(project, config)
                    config.truncate()
    except Exception as e:
        print("Error in uploading model to EVM whose exception is", e)
        raise HTTPException(
            status_code=Response_Code.METHOD_NOT_ALLOWED.value,
            detail=Response_Details.INVALID_INPUT.value,
        )
    if count == 0:
        raise HTTPException(
            status_code=Response_Code.NOT_FOUND.value,
            detail=Response_Details.PROJECT_NOT_FOUND.value,
        )
    else:
        return (Response_Details.CREATED.value, project["id"])


@app.get("/project", status_code=Response_Code.OK.value)
def get_projects():
    """
    Returns project details
    """
    project_list = []
    count = 0
    # iterate through files /folders inside projects folder
    for path in glob.iglob(
        "{}{}/**".format(cwd, Dir_Path.PROJECT_DIR.value), recursive=True
    ):
        if os.path.isfile(path):
            try:
                with open(path, "r+") as config:
                    project = json.load(config)
                    project_list.append(project)
                    count = count + 1
            except:
                continue
    # if count 0, sent project doesnt exist response
    if count == 0:
        raise HTTPException(
            status_code=Response_Code.NOT_FOUND.value,
            detail=Response_Details.PROJECT_NOT_FOUND.value,
        )
    else:
        return project_list


@app.get("/project/{id}", status_code=Response_Code.OK.value)
def get_project_id(id):
    """
    Function to return project details using id
    Args:
        id: Project id parameter
    """
    count = 0
    global cwd
    # check whether specified project exists
    if os.path.isdir("{}{}/{}".format(cwd, Dir_Path.PROJECT_DIR.value, id)):
        with open(
            "{}{}/{}/project.config".format(cwd, Dir_Path.PROJECT_DIR.value, id), "r+"
        ) as config:
            project = json.load(config)
            if project["id"] == id:
                count = count + 1
    # if count 0, sent project doesnt exist response
    if count == 0:
        raise HTTPException(
            status_code=Response_Code.NOT_FOUND.value,
            detail=Response_Details.PROJECT_NOT_FOUND.value,
        )
    else:
        return project


@app.delete("/project/{id}", status_code=Response_Code.OK.value)
def delete_project(id):
    """
    Function to delete project folder
    Args:
        id: Project ID parameter
    """
    count = 0
    global cwd

    # check whether specified project exists
    if os.path.isdir("{}{}/{}".format(cwd, Dir_Path.PROJECT_DIR.value, id)):
        with open(
            "{}{}/{}/project.config".format(cwd, Dir_Path.PROJECT_DIR.value, id), "r+"
        ) as config:
            project = json.load(config)
            # Delete project and update count to 1
            if project["id"] == id:
                os.system(
                    "rm -r {}{}/{}".format(
                        cwd, Dir_Path.PROJECT_DIR.value, project["id"]
                    )
                )
                count = count + 1
    # if count 0, sent project doesnt exist response
    if count == 0:
        raise HTTPException(
            status_code=Response_Code.NOT_FOUND.value,
            detail=Response_Details.PROJECT_NOT_FOUND.value,
        )
    else:
        return Response_Details.SUCCESS.value


# MAIN FUNCTION
if __name__ == "__main__":
    """
    Main function which runs the uvicorn server
    Check if any node process running if yes, kill them
    Check if projects folder for storing model is created, if no create folder.
    """
    process_name = "../server/node_webserver.js"
    # To kill any node process beforehand using pid so as to not affect the udp server initiation
    for proc in psutil.process_iter():
        try:
            cmdline = proc.cmdline()
        except psutil.AccessDenied:
            continue
        except (psutil.ZombieProcess, psutil.NoSuchProcess):
            continue
        except Exception as e:
            log.exception("something is wrong: " + ' '.join(cmdline))
            continue
        if process_name in cmdline:
            pid = proc.pid
            print(pid)
            os.kill(pid, 2)
    if not os.path.isdir("{}{}".format(cwd, Dir_Path.PROJECT_DIR.value)):
        os.system("mkdir {}{}".format(cwd, Dir_Path.PROJECT_DIR.value))

    uvicorn.run(
        "device_agent:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        ws_ping_interval=math.inf,
        ws_ping_timeout=math.inf,
    )
