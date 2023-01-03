import yaml
import json
import os
import sys
sys.path.append('/opt/edge_ai_apps/apps_python/ti-edgeai-studio-evm-agent/src/')

from definitions import dir_path
cwd = os.getcwd()
os.system('./req_native.sh') 
config_yaml_path = ['{}{}/image_classification.yaml'.format(cwd,dir_path.CONFIG_DIR_FOR_SETUP.value),'{}{}/object_detection.yaml'.format(cwd,dir_path.CONFIG_DIR_FOR_SETUP.value)]
for path in config_yaml_path:
        
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
        yaml.safe_dump(y,fout,sort_keys=False)
