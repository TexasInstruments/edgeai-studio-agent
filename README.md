# TI EdgeAI Studio Agent

TI EdgeAI Studio Agent is required to be started on a TI Analytics device to use
EdgeAI Studio with the device. To know more about EdgeAI Studio please visit
https://dev.ti.com/edgeaistudio


# Steps to Run

## Fetching IP Address of Device via UART Terminal

### 2. Using UART Terminal

1. Connect the UART cable to PC and open terminal

2. The COM ports(/dev/ttyUSB) can vary. To check all available usb serial ports, use:

    `ls /dev/tty | grep USB`

    ![usb serial ports list output](/images/usb_serial_ports.png)

    [NOTE: TDA4VM,AM68A,AM69A will mostly be on ttyUSB2 while AM62A,AM62X,AM62P are generally on ttyUSB0. Please refer to EdgeAI SDK documentation (Getting Started) for more information.]

3. Start minicom session on PC using:

    `sudo minicom -D /dev/ttyUSBX`

4. Login using "root"

    ![tda4vm login](/images/tda4vm_login.png)

5. Use **ifconfig** to get the ip address, the highlighted one as
shown in the figure below:

    ![ifconfig output](/images/get_ip-address.png)

### 2. Using a display

1. If you have a disply, you can connect display to the board. When the board boots up, it will show the IP address of the device on the default screen.


## B) Running device agent on target

1. Navigate to edgeai-studio-agent folder:

    `cd /opt/edgeai-studio-agent`

2. Execute the script:

    `./run.sh`


# API Documentation
#### GET Requests

<details>
 <summary><code>GET</code> <code><b>/sensor</b></code> <code>(gets all the sensor attached to the target)</code></summary>

##### Details

Find all the sensors attached to the target. This includes all the USB Camera connected to the target.
It also provides other information like SDK version and device type.
##### Parameters

> None

##### Responses

> | http code     | content-type                      | response                                                            |
> |---------------|-----------------------------------|---------------------------------------------------------------------|
> | `200`         | `application/json`                | All attached sensors                                                |
> | `404`         | `application/json`                | `{'detail': 'Sensor not found'}`                                    |

##### Example GET response (200)

```javascript
[
    {
        "name": "UVC Camera (046d:0825)",
        "id": "null",
        "type": "Webcam",
        "device": [
            {
                "id": "/dev/video-usb-cam0",
                "type": "V4L2",
                "description": "device available for capture",
                "status": "available"
            }
        ],
        "sdk_version": "9.0",
        "device_name": "TDA4VM"
    }
]
```

</details>

<details>
 <summary><code>GET</code> <code><b>/sensor-session</b></code> <code>(gets all the sensor sessions)</code></summary>

##### Details

Find all sensor sessions including initiated and started ones. The target device only supports one session at a time.
##### Parameters

> None

##### Responses

> | http code     | content-type                      | response                                                            |
> |---------------|-----------------------------------|---------------------------------------------------------------------|
> | `200`         | `application/json`                |  Sensor session                                                     |
> | `404`         | `application/json`                | `{'detail': 'Session not found'}`                                   |

##### Example GET response (200)

```javascript
{
    "session": {
        "id": "88c046f1-4ef1-456f-9978-c3a20456b05c",
        "http_port": 8080,
        "http_url": "/raw_imagestream",
        "http_status": "started",
        "http_pid": 1231,
        "ws_port": 8000,
        "ws_url": "",
        "ws_status": "down",
        "ws_pid": 0,
        "udp_server_port": 8081,
        "udp_client_port": 0,
        "udp_status": "started",
        "udp_pid": 1231,
        "tcp_server_port": 0,
        "tcp_client_port": 0,
        "tcp_status": "Down",
        "tcp_pid": 0,
        "data_pipeline_status": "down",
        "data_pipeline_pid": 0,
        "stream_type": "null"
    },
    "sensor": {
        "name": "test_name",
        "id": "test_id",
        "type": "test_type",
        "device": [
            {
                "id": "/dev/video-usb-cam0",
                "type": "V4L2",
                "description": "V4L2",
                "status": "available"
            }
        ],
        "sdk_version": "9.0",
        "device_name": "TDA4VM"
    },
    "project": null,
    "inference": null
}
```

Note: **"id": "88c046f1-4ef1-456f-9978-c3a20456b05c"** is the unique id of the sensor-session

</details>

<details>
  <summary><code>GET</code> <code><b>/sensor-session/{id}</b></code> <code>(gets sensor session by id)</code></summary>

##### Details

Find the unique sensor sessions by id.
##### Parameters

> | name   |  type      | data type      | description                                                  |
> |--------|------------|----------------|--------------------------------------------------------------|
> | `id`   |  required  | string         | The specific unique idendifier                               |

##### Responses

> | http code     | content-type                      | response                                                            |
> |---------------|-----------------------------------|---------------------------------------------------------------------|
> | `200`         | `application/json`                |  Sensor session with given id                                       |
> | `400`         | `application/json`                | `{'detail': 'Invalid ID supplied'}`                                 |
> | `404`         | `application/json`                | `{'detail': 'Session not found'}`                                   |

##### Example GET response (200)

```javascript
{
    "session": {
        "id": "88c046f1-4ef1-456f-9978-c3a20456b05c",
        "http_port": 8080,
        "http_url": "/raw_imagestream",
        "http_status": "started",
        "http_pid": 1288,
        "ws_port": 8000,
        "ws_url": "",
        "ws_status": "down",
        "ws_pid": 0,
        "udp_server_port": 8081,
        "udp_client_port": 0,
        "udp_status": "started",
        "udp_pid": 1288,
        "tcp_server_port": 0,
        "tcp_client_port": 0,
        "tcp_status": "Down",
        "tcp_pid": 0,
        "data_pipeline_status": "down",
        "data_pipeline_pid": 0,
        "stream_type": "null"
    },
    "sensor": {
        "name": "test_name",
        "id": "test_id",
        "type": "test_type",
        "device": [
            {
                "id": "/dev/video-usb-cam0",
                "type": "V4L2",
                "description": "V4L2",
                "status": "available"
            }
        ],
        "sdk_version": "9.0",
        "device_name": "TDA4VM"
    },
    "project": null,
    "inference": null
}
```

</details>

<details>
  <summary><code>GET</code> <code><b>/project</b></code> <code>(gets registered project)</code></summary>

##### Details

Find registered project
##### Parameters

> None

##### Responses

> | http code     | content-type                      | response                                                            |
> |---------------|-----------------------------------|---------------------------------------------------------------------|
> | `200`         | `application/json`                | Project                                                             |
> | `404`         | `application/json`                | `{'detail': 'Project not found'}`                                   |

##### Example GET response (200)

```javascript
[
    {
        "id": "88c046f1-4ef1-456f-9978-c3a20456b05c",
        "name": "test_project",
        "sensor": "null",
        "task_type": "classification",
        "model": "null",
        "target_device": "null",
        "model_file": "null",
        "model_file_checksum": "null"
    }
]
```

</details>

<details>
  <summary><code>GET</code> <code><b>/project/{id}</b></code> <code>(gets registered project by id)</code></summary>

##### Details

Find the registered project by id.
##### Parameters

> | name   |  type      | data type      | description                                                  |
> |--------|------------|----------------|--------------------------------------------------------------|
> | `id`   |  required  | string         | The specific unique idendifier                               |

##### Responses

> | http code     | content-type                      | response                                                            |
> |---------------|-----------------------------------|---------------------------------------------------------------------|
> | `200`         | `application/json`                | Project with given id                                               |
> | `404`         | `application/json`                | `{'detail': 'Project not found'}`                                   |

##### Example GET response (200)

```javascript
[
    {
        "id": "88c046f1-4ef1-456f-9978-c3a20456b05c",
        "name": "test_project",
        "sensor": "null",
        "task_type": "classification",
        "model": "null",
        "target_device": "null",
        "model_file": "null",
        "model_file_checksum": "null"
    }
]
```

</details>

------------------------------------------------------------------------------------------

#### POST Requests

<details>
 <summary><code>POST</code> <code><b>/sensor-session</b></code> <code>(initiate a sensor session)</code></summary>

##### Details

Initiate a unique sensor session by generating a unique id and setting up all the required client and server processes

##### Example POST data

```javascript
{
    "name": "test_name",
    "id": "test_id",
    "type": "test_type",
    "device": [
        {
            "id": "/dev/video-usb-cam0",
            "type": "V4L2",
            "description": "device available for capture",
            "status": "available"
        }
    ],
    "sdk_version": "9.0",
    "device_name": "TDA4VM"
}
```

##### Responses

> | http code     | content-type                      | response                                                            |
> |---------------|-----------------------------------|---------------------------------------------------------------------|
> | `202`         | `application/json`                | Sensor session with generated unique id                             |
> | `405`         | `application/json`                | `{'detail': 'Invalid input'}`                                       |

</details>

<details>
 <summary><code>POST</code> <code><b>/project</b></code> <code>(register a project)</code></summary>

##### Details

Register a project to the target and set up project entry with all required parameters supplied

##### Example POST data

```javascript
{
    "id": "88c046f1-4ef1-456f-9978-c3a20456b05c",
    "name": "test_project",
    "task_type": "classification"
    "sensor": "null"
    "model": "null"
    "target_device": "null"
    "model_file": "null"
    "model_file_checksum": "null"
}
```

##### Responses

> | http code     | content-type                      | response                                                            |
> |---------------|-----------------------------------|---------------------------------------------------------------------|
> | `201`         | `text/html;charset=utf-8`         | `Succesfully created`                                               |

</details>

<details>
 <summary><code>POST</code> <code><b>/project/{id}/model</b></code> <code>(upload model to the target)</code></summary>

##### Details

Upload model tarball to the target as **outputFile.tar.gz**. Each call will overwrite the previous file and checksum with the new file.

##### Parameters

> | name   |  type      | data type      | description                                                  |
> |--------|------------|----------------|--------------------------------------------------------------|
> | `id`   |  required  | string         | The specific unique idendifier                               |
##### Example POST data

File object of the model tarball renamed as outputFile.tar.gz

##### Responses

> | http code     | content-type                      | response                                                            |
> |---------------|-----------------------------------|---------------------------------------------------------------------|
> | `201`         | `text/html;charset=utf-8`         | `Succesfully created, {id}`                                         |
> | `404`         | `application/json`                | `{'detail': 'Project not found'}`                                   |
> | `405`         | `application/json`                | `{'detail': 'Invalid input'}`                                       |

</details>

------------------------------------------------------------------------------------------

#### PUT Requests

<details>
  <summary><code>PUT</code> <code><b>/sensor-session/{id}</b></code> <code>(start session and associated data pipeline)</code></summary>

##### Details

Start sensor session by setting up the required data pipeline (inference or raw capture). Whether to start inference pipeline or raw capture pipeline is decided by the key "inference" in the PUT data. Client creates the project_session object by aggregating the initiated session object, project object and inference parameter. Sensor session object and project object will be validated, data pipeline process will be started for direct sensor data or inference output based on the value of inference parameter. If successfully started, the response will have data_pipeline_status as 'started' and data_pipeline_pid with the PID of the pipeline process supplying data to the UDP/TCP server/client. This API can also produce and stream data over websockets for browser front end application to display on the UI, for e.g., for log streaming, memory usage, inference time etc. If websocket interface is started, the response will have ws_status as 'started', ws_url & ws_port duly filled, and ws_pid with the PID of the websocket server process supplying data to the Javascript front end application.

##### Parameters

> | name   |  type      | data type      | description                                                  |
> |--------|------------|----------------|--------------------------------------------------------------|
> | `id`   |  required  | string         | The specific unique idendifier                               |

##### Example PUT data

```javascript
{
    "session": {
        "id": "88c046f1-4ef1-456f-9978-c3a20456b05c",
        "http_port": 8080,
        "http_url": "/raw_imagestream",
        "http_status": "started",
        "http_pid": 1999,
        "ws_port": 8000,
        "ws_url": "",
        "ws_status": "down",
        "ws_pid": 0,
        "udp_server_port": 8081,
        "udp_client_port": 0,
        "udp_status": "started",
        "udp_pid": 1999,
        "tcp_server_port": 0,
        "tcp_client_port": 0,
        "tcp_status": "Down",
        "tcp_pid": 0,
        "data_pipeline_status": "down",
        "data_pipeline_pid": 0,
        "stream_type": "image"
    },
    "sensor": {
        "name": "test_name",
        "id": "test_id",
        "type": "test_type",
        "device": [
            {
                "id": "/dev/video-usb-cam0",
                "type": "V4L2",
                "description": "V4L2",
                "status": "available"
            }
        ],
        "sdk_version": "9.0",
        "device_name": "TDA4VM"
    },
    "inference": false
}
```

##### Responses

> | http code     | content-type                      | response                                                            |
> |---------------|-----------------------------------|---------------------------------------------------------------------|
> | `202`         | `application/json`                | `Data with updated datapipeline and websocket status`               |
> | `400`         | `application/json`                | `{'detail': 'Invalid ID supplied'}`                                 |
> | `404`         | `application/json`                | `{'detail': 'Session not found'}`                                   |
> | `404`         | `application/json`                | `{'detail': 'Project not found'}`                                   |
> | `409`         | `application/json`                | `{'detail': 'Sensor session alreday running'}`                      |

</details>

------------------------------------------------------------------------------------------

#### DELETE Requests

<details>
  <summary><code>DELETE</code> <code><b>/sensor-session/{id}</b></code> <code>(deletes sensor session by id)</code></summary>

##### Details

Delete sensor session with given id. All processes and resources associated to the sensor sessions will be cleared and freed.
##### Responses

> | http code     | content-type                      | response                                                            |
> |---------------|-----------------------------------|---------------------------------------------------------------------|
> | `202`         | `text/html;charset=utf-8`         | `Operation accepted`                                                |
> | `400`         | `application/json`                | `{'detail': 'Invalid ID supplied'}`                                 |
> | `404`         | `application/json`                | `{'detail': 'Session not found'}`                                   |

</details>

<details>
  <summary><code>DELETE</code> <code><b>/sensor-session/{id}/dpipe</b></code> <code>(deletes data pipeline associated with sensor session)</code></summary>

##### Details

Deletes only the data pipeline associated with sensor session having the given id. The data pipeline are the inference or raw data capture pipelines running on the target. The websockets interface associated with the data pipelines are also terminated. The same data pipeline associated with session can be later restarted using PUT method on /sensor-session/{id}.

##### Responses

> | http code     | content-type                      | response                                                            |
> |---------------|-----------------------------------|---------------------------------------------------------------------|
> | `202`         | `text/html;charset=utf-8`         | `Operation accepted`                                                |
> | `400`         | `application/json`                | `{'detail': 'Invalid ID supplied'}`                                 |
> | `404`         | `application/json`                | `{'detail': 'Session not found'}`                                   |

</details>

<details>
  <summary><code>DELETE</code> <code><b>/project/{id}</b></code> <code>(deletes project by id)</code></summary>

##### Details

Deletes the registered project with given id. All the resources including model files, artifacts and configuration files related to this project will be cleared and freed.

##### Responses

> | http code     | content-type                      | response                                                            |
> |---------------|-----------------------------------|---------------------------------------------------------------------|
> | `200`         | `text/html;charset=utf-8`         | `Successful operation`                                              |
> | `404`         | `application/json`                | `{'detail': 'Project not found'}`                                   |

</details>