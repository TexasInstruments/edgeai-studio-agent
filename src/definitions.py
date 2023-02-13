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

import os
from enum import Enum

class Response_Code(Enum):
    """
    Class to store http response codes
    """

    OK = 200
    CREATED = 201
    ACCEPTED = 202
    BAD_REQUEST = 400
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    CONFLICT = 409


class Response_Details(Enum):
    """
    Class to store http response messages
    """

    SUCCESS = "Successful operation"
    CREATED = "Succesfully created"
    ACCEPTED = "Operation accepted"
    INVALID_ID = "Invalid ID supplied"
    SESSION_NOT_FOUND = "Session not found"
    PROJECT_NOT_FOUND = "Project not found"
    SENSOR_NOT_FOUND = "Sensor not found"
    INVALID_INPUT = "Invalid input"
    PROJECT_CONFLICT = "Project already exists"
    SESSION_CONFLICT = "Sensor session alreday running"


class Server_Details(Enum):
    """
    Class to store server details
    """

    HTTP_PORT = 8080
    HTTP_URL = "/raw_videostream"
    WS_PORT = 8000
    WS_URL = ""
    UDP_SERVER_PORT = 8081
    UDP_CLIENT_PORT = 0
    TCP_SERVER_PORT = 0
    TCP_CLIENT_PORT = 0
    TCP_STATUS = "Down"
    TCP_PID = 0


class Dir_Path(Enum):
    """
    Class to store folder paths
    """

    edgeai_gst_apps_path = os.getenv('EDGEAI_GST_APPS_PATH')

    PROJECT_DIR = "/../../projects"
    SCRIPTS_DIR = os.path.join(edgeai_gst_apps_path,"scripts")
    INFER_DIR = os.path.join(edgeai_gst_apps_path,"apps_python")