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

import yaml
import json
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/src/")

from definitions import dir_path
cwd = os.getcwd()
os.system('./req_native.sh') 
config_yaml_path = ['{}{}/image_classification.yaml'.format(cwd,dir_path.CONFIG_DIR_FOR_SETUP.value),'{}{}/object_detection.yaml'.format(cwd,dir_path.CONFIG_DIR_FOR_SETUP.value)]
for path in config_yaml_path:
        
    with open(path,'r+') as f:
        y = json.dumps(yaml.load(f,Loader=yaml.FullLoader))
        y=json.loads(y)
        keyCount  = int(len(y["outputs"]))
        sink = {"output{}".format(keyCount):{"sink":"remote","host":"127.0.0.1","port":8081,"width":1280,"height":720,"payloader":"mp4mux"}}
        y["outputs"].update(sink)
        y["flows"]["flow0"][2] = 'output{}'.format(keyCount)
        input = {"input0":{"source":"/dev/video2","format":"jpeg","width":640,"height":360,"framerate":30}}
        y["inputs"].update(input)
        y["flows"]["flow0"][0] = "input0"
        y["flows"]["flow0"][3][2] = 640
        y["flows"]["flow0"][3][3] = 360
        
    with open(path,'w') as fout:
        yaml.safe_dump(y,fout,sort_keys=False)
