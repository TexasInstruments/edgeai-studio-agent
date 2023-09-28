# TI EdgeAI Studio Agent Test

Standalone scripts to test TI EdgeAI Studio Agent running on the target

# Steps to Run

## A) Running device agent on target

This step needs to be executed on the target device

1. Navigate to edgeai-studio-agent folder:

    `cd /opt/edgeai-studio-agent/src`

2. Execute device agent script:

    `python3 device_agent.py`

    - Note: Ensure you are inside folder /opt/edgeai-studio-agent/src before
    running device_agent.py


## B) Running the test script

This step needs to be executed on the PC

1. Download a pre-compiled model tarball

    `wget *link_to_model_tarball*`

2. Execute device agent script:
    
    - `sudo python3 test.py -h` //For help

    - `sudo python3 test.py --ip *IP of target* --test_suite sensor_session` // Test creation of sensor_session

    - `sudo python3 test.py --ip *IP of target* --test_suite data_stream` // Test webcam capture

    - `sudo python3 test.py --ip *IP of target* --model_path *path to model tarball* --task_type *classification/detection* --test_suite inference` // Test inference

    - `sudo python3 test.py --ip *IP of target* --model_path *path to model tarball* --task_type *classification/detection*` // Test all


- **Note: If GStreamer and its python bindings are found installed on the machine where test script runs, the script will use it to convert multipart data streamed from target and save it as jpg images. If GStreamer is not found this step will automatically be skipped**