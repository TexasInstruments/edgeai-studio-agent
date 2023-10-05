#!/bin/bash

EDGEAI_STUDIO_AGENT_PATH=$(dirname "$(readlink -f "$BASH_SOURCE")")

if [ "$SOC" == "" ]; then
    cd /opt/edgeai-gst-apps
    source ./init_script.sh
fi

cd $EDGEAI_STUDIO_AGENT_PATH/src
python3 device_agent.py
