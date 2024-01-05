import requests
import json
import time
import os
import tarfile
import shutil
import threading
from argparse import ArgumentParser
from gst_utils import convert_multipart_data_to_jpeg
from utils import colors


parser = ArgumentParser()

parser.add_argument("--ip", help="IP of device agent", required=True)
parser.add_argument(
    "--test_suite",
    action="store",
    choices=["sensor_session", "data_stream", "inference"],
)
parser.add_argument("--model_path", help="Path of sample model tarball")
parser.add_argument(
    "--task_type",
    help="Task type of the sample model",
    action="store",
    choices=["classification", "detection"],
)
parser.add_argument(
    "--no-strict", help="Skip JPEG file check", dest="no_strict", action="store_true"
)

args = parser.parse_args()

if args.test_suite == None or args.test_suite == "inference":
    if args.model_path == None or args.task_type == None:
        parser.error(" requires --model_path and --task_type")


SENSOR_DATA = {
    "name": None,
    "id": None,
    "type": None,
    "device": None,
    "sdk_version": None,
    "device_name": None,
}

URL = "http://%s:8000" % args.ip
VIDEO_URL = "http://%s:8080" % args.ip

ERROR_STR = colors.fg.red + "[ERROR]" + colors.reset
SUCCESS_STR = colors.fg.green + "[SUCCESS]" + colors.reset
WARN_STR = colors.fg.yellow + "[WARNING]" + colors.reset
INFO_STR = colors.fg.blue + "[INFO]" + colors.reset

def create_sensor_session(sensor_type):
    print(INFO_STR, "Getting sensor info...")
    try:
        response = requests.get(URL + "/sensor", timeout=5)
    except requests.exceptions.HTTPError as errh:
        print(ERROR_STR, errh)
        return None
    except requests.exceptions.ConnectionError as errc:
        print(ERROR_STR, errc)
        return None
    except requests.exceptions.Timeout as errt:
        print(ERROR_STR, errt)
        return None
    except requests.exceptions.RequestException as err:
        print(ERROR_STR, err)
        return None

    if response.status_code == 404:
        print(ERROR_STR, "%s" % response.json())
        return None

    SENSOR_DATA["type"] = sensor_type

    if SENSOR_DATA["type"] == "Camera":
        available_devices = []
        for device in response.json()[0]['device']:
            available_devices.append(device['name'])

        if len(available_devices) == 1 and available_devices[0] == "null":
            print(ERROR_STR, "No camera found")
            return None

        print("\n----- Please choose 1 to use -----\n")
        for idx, i in enumerate(available_devices):
            print(idx, "-", i)
        print()
        while 1:
            choice = input("Enter your choice: ")
            if not choice.isdigit() or int(choice) >= len(available_devices):
                print("[ERROR] Enter a valid choice.")
            else:
                choice = int(choice)
                break
        print("\nUsing %s\n" % available_devices[choice])
        SENSOR_DATA["device"] = [response.json()[0]["device"][choice]]
    elif (SENSOR_DATA["type"] == "File"):
        print("\nUsing file input\n")
        SENSOR_DATA["device"] = response.json()[0]["device"]
    else:
        print("\nUsing default input\n")
        SENSOR_DATA["device"] = response.json()[0]["device"]

    # Selecting one of the sources
    SENSOR_DATA["name"] = response.json()[0]["name"]
    SENSOR_DATA["id"] = response.json()[0]["id"]
    SENSOR_DATA["sdk_version"] = response.json()[0]["sdk_version"]
    SENSOR_DATA["device_name"] = response.json()[0]["device_name"]

    print(INFO_STR, "Requesting session...")
    response = requests.post(URL + "/sensor-session", data=json.dumps(SENSOR_DATA))
    if response.status_code == 404 or response.status_code == 405:
        print(ERROR_STR, "%s" % response.json())
        return None

    print(INFO_STR, "Getting session info...")
    response = requests.get(URL + "/sensor-session")
    if response.status_code == 404:
        print(ERROR_STR, "%s" % response.json())
        return None
    sensor_session = response.json()
    sensor_session_id = sensor_session["session"]["id"]
    print(INFO_STR, "Got session id: %s" % sensor_session_id)

    print(INFO_STR, "Getting session-id (%s) info..." % sensor_session_id)
    response = requests.get(URL + "/sensor-session/" + sensor_session_id)
    if response.status_code == 404 or response.status_code == 400:
        print(ERROR_STR, "%s" % response.json())
        return None
    sensor_session = response.json()

    print("\n")
    print("-" * 50 + " Sensor Info " + "-" * 50)
    print(sensor_session["sensor"])
    print("\n")
    print("-" * 50 + " Session Info " + "-" * 50)
    print(sensor_session["session"])
    print("\n")

    return sensor_session


def delete_sensor_session_data_pipe(sensor_session):
    sensor_session_id = sensor_session["session"]["id"]

    print(INFO_STR, "Deleting session-id (%s) data pipeline..." % sensor_session_id)
    response = requests.delete(URL + "/sensor-session/" + sensor_session_id + "/dpipe")
    if response.status_code == 404 or response.status_code == 400:
        print(ERROR_STR, "%s" % response.json())
        return -1
    elif response.status_code == 202:
        print(SUCCESS_STR, "Data pipeline killed successfully.")
    return 0


def delete_sensor_session(sensor_session):
    sensor_session_id = sensor_session["session"]["id"]

    print(INFO_STR, "Deleting session-id (%s)..." % sensor_session_id)
    response = requests.delete(URL + "/sensor-session/" + sensor_session_id)
    if response.status_code == 404 or response.status_code == 400:
        print(ERROR_STR, "%s" % response.json())
        return -1
    elif response.status_code == 202:
        print(SUCCESS_STR, "Node server killed successfully.")
    return 0


def start_raw_stream(sensor_session):
    global data_stream_listner_status

    print(INFO_STR, "Starting raw video capture...")

    sensor_session["session"]["stream_type"] = "image"

    model_data = {
        "session": sensor_session["session"],
        "sensor": sensor_session["sensor"],
        "inference": False,
    }

    sensor_session_id = sensor_session["session"]["id"]

    # Start data listner thread
    video_url = VIDEO_URL + "/raw_imagestream/" + sensor_session_id
    save_as = "data_stream_%s" % sensor_session_id
    data_listner_thread = threading.Thread(
        target=multipart_data_listner, args=(video_url, 1000000, save_as)
    )
    data_listner_thread.start()

    # Start data pipeline
    response = requests.put(
        URL + "/sensor-session/" + sensor_session_id, data=json.dumps(model_data)
    )
    if (
        response.status_code == 404
        or response.status_code == 400
        or response.status_code == 409
    ):
        print(ERROR_STR, "%s" % response.json())
        return -1

    print(INFO_STR, "Getting session-id (%s) info..." % sensor_session_id)
    response = requests.get(URL + "/sensor-session/" + sensor_session_id)
    if response.status_code == 404 or response.status_code == 400:
        print(ERROR_STR, "%s" % response.json())
        return -1
    sensor_session = response.json()

    print("\n")
    print("-" * 50 + " Session Info " + "-" * 50)
    print(sensor_session["session"])
    print("\n")

    if sensor_session["session"]["data_pipeline_status"] == "down":
        print(ERROR_STR, "Error starting raw stream")
        return -1
    else:
        print(SUCCESS_STR, "raw stream pipeline started\n")

    data_listner_thread.join()

    ret = data_stream_listner_status

    if ret == 0:
        print(INFO_STR, "Trying to convert multipart data to jpg file...\n")
        tret = convert_multipart_data_to_jpeg(save_as)
        if tret == -1:
            print(WARN_STR, "Skip saving data as jpg as GStreamer is not present.\n")
        else:
            if not os.path.exists(save_as + ".jpg"):
                print(
                    ERROR_STR,
                    "GStreamer pipeline could not convert data stream to jpg!\n",
                )
                if not args.no_strict:
                    ret = -1
            else:
                print(SUCCESS_STR, "JPEG file saved as %s.jpg\n" % save_as)

    return ret


def create_project(sensor_session):

    sensor_session_id = sensor_session["session"]["id"]

    project_data = {
        "id": sensor_session_id,
        "name": "test_project",
        "task_type": args.task_type,
    }

    print(INFO_STR, "Creating project...")
    response = requests.post(URL + "/project", data=json.dumps(project_data))
    if response.status_code != 201:
        print(ERROR_STR, "%s" % response.json())
        return -1

    print(INFO_STR, "Getting project info...")
    response = requests.get(URL + "/project")
    if response.status_code == 404:
        print(ERROR_STR, "%s" % response.json())
        return -1

    print("\n")
    print("-" * 50 + " Project Info " + "-" * 50)
    print(response.json())
    print("\n")

    return 0


def download_model_on_board(sensor_session):

    sensor_session_id = sensor_session["session"]["id"]

    if not os.path.exists(args.model_path):
        print(ERROR_STR, "%s does not exist" % args.model_path)
        return -1

    if not tarfile.is_tarfile(args.model_path):
        print(ERROR_STR, "%s is not a tar file" % args.model_path)
        return -1

    shutil.copyfile(args.model_path, "outputFile.tar.gz")

    with open("outputFile.tar.gz", "rb") as fobj:
        print(INFO_STR, "Downloading model to evm...")
        response = requests.post(
            URL + "/project/" + sensor_session_id + "/model",
            data={"id": sensor_session_id},
            files={"file": fobj},
        )
        if response.status_code != 201:
            print(ERROR_STR, "%s" % response.json())
            return -1

    os.remove("outputFile.tar.gz")

    print(SUCCESS_STR, "Model downloaded successfully!")

    return 0

def download_input_file_on_board(sensor_session):

    sensor_session_id = sensor_session["session"]["id"]

    print("\n----- Please provide input file path -----\n")
    print()
    while 1:
        path = input("Enter path: ")
        if not os.path.exists(path):
            print("[ERROR] Enter a valid path.")
        else:
            break

    shutil.copyfile(path, "inputFile")

    with open("inputFile", "rb") as fobj:
        print(INFO_STR, "Downloading input video file to evm...")
        response = requests.post(
            URL + "/project/" + sensor_session_id + "/input_file",
            data={"id": sensor_session_id},
            files={"file": fobj},
        )
        if response.status_code != 201:
            print(ERROR_STR, "%s" % response.json())
            return -1

    os.remove("inputFile")

    print(SUCCESS_STR, "Video Input file downloaded successfully!")

    return 0


def start_inference(sensor_session):
    global data_stream_listner_status

    sensor_session_id = sensor_session["session"]["id"]

    print(INFO_STR, "Getting project/%s info..." % sensor_session_id)
    response = requests.get(URL + "/project")
    if response.status_code == 404:
        print(ERROR_STR, "%s" % response.json())
        return -1

    project_info = response.json()
    print("\n")
    print("-" * 50 + " Project Info " + "-" * 50)
    print(project_info)
    print("\n")

    # Start data listner thread
    video_url = VIDEO_URL + "/raw_imagestream/" + sensor_session_id
    save_as = "inference_result_%s" % sensor_session_id
    data_listner_thread = threading.Thread(
        target=multipart_data_listner, args=(video_url, 10000000, save_as, 30)
    )
    data_listner_thread.start()

    # Start Inference
    print(INFO_STR, "Starting Inference...")

    sensor_session["session"]["stream_type"] = "image"

    model_data = {
        "session": sensor_session["session"],
        "sensor": sensor_session["sensor"],
        "inference": True,
        "project": project_info[0],
    }

    response = requests.put(
        URL + "/sensor-session/" + sensor_session_id, data=json.dumps(model_data)
    )
    if response.status_code != 202:
        print(ERROR_STR, "%s" % response.json())
        return -1

    print(INFO_STR, "Getting session-id (%s) info..." % sensor_session_id)
    response = requests.get(URL + "/sensor-session/" + sensor_session_id)
    if response.status_code == 404 or response.status_code == 400:
        print(ERROR_STR, "%s" % response.json())
        return -1
    sensor_session = response.json()

    print("\n")
    print("-" * 50 + " Session Info " + "-" * 50)
    print(sensor_session["session"])
    print("\n")

    if sensor_session["session"]["data_pipeline_status"] == "down":
        print(ERROR_STR, "Error starting inference pipeline\n")
        return -1
    else:
        print(SUCCESS_STR, "Inference pipeline started\n")

    data_listner_thread.join()

    ret = data_stream_listner_status

    if ret == 0:
        print(INFO_STR, "Trying to convert multipart data to jpg file...\n")
        tret = convert_multipart_data_to_jpeg(save_as)
        if tret == -1:
            print(WARN_STR, "Skip saving data as jpg as GStreamer is not present.\n")
        else:
            if not os.path.exists(save_as + ".jpg"):
                print(
                    ERROR_STR,
                    "GStreamer pipeline could not convert data stream to jpg!\n",
                )
                if not args.no_strict:
                    ret = -1
            else:
                print(SUCCESS_STR, "JPEG file saved as %s.jpg\n" % save_as)

    return ret


def multipart_data_listner(url, max_data_length, save_as, wait_timeout=15):
    global data_stream_listner_status
    print(INFO_STR, "Listening to data stream on %s ....\n" % url)
    try:
        data_length = 0
        complete_data = b""
        with requests.get(url, stream=True, timeout=wait_timeout) as r:
            for data in r.iter_content(chunk_size=4096):
                complete_data += data
                data_length += len(data)
                if data_length > max_data_length:
                    break
            if data_length <= 0:
                print(ERROR_STR, "Got no data from stream\n")
                data_stream_listner_status = -1
            else:
                print(SUCCESS_STR, "Got data from stream\n")
                with open(save_as, "wb") as f:
                    f.write(complete_data)
                print(SUCCESS_STR, "Data saved as %s\n" % save_as)
                data_stream_listner_status = 0
    except requests.exceptions.Timeout as errt:
        print(ERROR_STR, "Data listner thread connection timed out! ")
        print(ERROR_STR, errt)
        print("\n")
        data_stream_listner_status = -1


def main():
    SENSOR_SESSION_TEST = "FAIL"
    RAW_VIDEOTEST = "FAIL"
    INFERENCE_TEST = "FAIL"

    if args.test_suite == "sensor_session":
        RAW_VIDEOTEST = "NA"
        INFERENCE_TEST = "NA"
        sensor_session = create_sensor_session("Default")
        if sensor_session == None:
            return (SENSOR_SESSION_TEST, RAW_VIDEOTEST, INFERENCE_TEST)
        delete_sensor_session(sensor_session)
        SENSOR_SESSION_TEST = "PASS"

    else:
        if args.test_suite == None or args.test_suite == "data_stream":
            sensor_session = create_sensor_session("Camera")
            if sensor_session == None:
                return (SENSOR_SESSION_TEST, RAW_VIDEOTEST, INFERENCE_TEST)
            SENSOR_SESSION_TEST = "PASS"
            ret = start_raw_stream(sensor_session)
            delete_sensor_session_data_pipe(sensor_session)
            delete_sensor_session(sensor_session)
            if ret == -1:
                return (SENSOR_SESSION_TEST, RAW_VIDEOTEST, INFERENCE_TEST)
            RAW_VIDEOTEST = "PASS"
        else:
            RAW_VIDEOTEST = "NA"

        if args.test_suite == None or args.test_suite == "inference":
            print("\n----- Please choose input for inference -----\n")
            print("0. Camera")
            print("1. Video File (H264)")
            print("2. Default")
            print()
            while 1:
                choice = input("Enter your choice: ")
                if choice not in ["0","1","2"] :
                    print("[ERROR] Enter a valid choice.")
                else:
                    break

            if choice == "0":
                sensor_session = create_sensor_session("Camera")
            elif choice == "1":
                sensor_session = create_sensor_session("File")
            else:
                sensor_session = create_sensor_session("null")
            if sensor_session == None:
                return (SENSOR_SESSION_TEST, RAW_VIDEOTEST, INFERENCE_TEST)
            SENSOR_SESSION_TEST = "PASS"

            ret = create_project(sensor_session)
            if ret == -1:
                delete_sensor_session(sensor_session)
                return (SENSOR_SESSION_TEST, RAW_VIDEOTEST, INFERENCE_TEST)

            ret = download_model_on_board(sensor_session)
            if ret == -1:
                delete_sensor_session(sensor_session)
                return (SENSOR_SESSION_TEST, RAW_VIDEOTEST, INFERENCE_TEST)

            if choice == "1":
                ret = download_input_file_on_board (sensor_session)
                if ret == -1:
                    delete_sensor_session(sensor_session)
                    return (SENSOR_SESSION_TEST, RAW_VIDEOTEST, INFERENCE_TEST)

            ret = start_inference(sensor_session)
            delete_sensor_session_data_pipe(sensor_session)
            delete_sensor_session(sensor_session)
            if ret == -1:
                return (SENSOR_SESSION_TEST, RAW_VIDEOTEST, INFERENCE_TEST)
            INFERENCE_TEST = "PASS"
        else:
            INFERENCE_TEST = "NA"

    return (SENSOR_SESSION_TEST, RAW_VIDEOTEST, INFERENCE_TEST)


if __name__ == "__main__":

    result = main()
    result_colored = []
    for i in result:
        if i == "PASS":
            color = colors.fg.green
        elif i == "FAIL":
            color = colors.fg.red
        else:
            color = colors.fg.lightgrey
        result_colored.append(color + i + colors.reset)

    print(
        "\n\nTEST_SENSOR_SESSION = %s\nTEST_DATA_STREAM = %s\nTEST_INFERENCE = %s\n"
        % tuple(result_colored)
    )

    res = colors.fg.green + "PASS"
    for i in result:
        if i == "FAIL":
            res = colors.fg.red + "FAIL"
            break
    print("[RESULT] %s" % res)
