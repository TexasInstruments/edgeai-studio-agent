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

from enum import Enum
 
class response_code(Enum):
    OK = 200
    CREATED = 201
    ACCEPTED = 202
    BAD_REQUEST = 400
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    CONFLICT= 409

class response_detail(Enum):
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

class server_details(Enum):
    HTTP_PORT = 8080
    HTTP_URL = "/stream"
    WS_PORT = 0
    WS_URL = ""
    UDP_SERVER_PORT = 8081
    UDP_CLIENT_PORT = 0
    TCP_SERVER_PORT = 0
    TCP_CLIENT_PORT = 0
    TCP_STATUS = "Down"
    TCP_PID = 0

class dir_path(Enum):
    PROJECT_DIR = '/../../projects'
    CONFIG_DIR = '/../../edge_ai_apps/configs'
    CONFIG_DIR_FOR_SETUP = '/../edge_ai_apps/configs'
    SCRIPTS_DIR = '/../../edge_ai_apps/scripts'
    INFER_DIR = '/../../edge_ai_apps/apps_python'

    

  
