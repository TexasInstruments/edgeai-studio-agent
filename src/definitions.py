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
    PROJECT_DIR = '/../../../../projects'
    CONFIG_DIR = '/../../../configs'
    CONFIG_DIR_FOR_SETUP = '/../../configs'
    SCRIPTS_DIR = '/../../../scripts'
    INFER_DIR = '/../../'

    

  
