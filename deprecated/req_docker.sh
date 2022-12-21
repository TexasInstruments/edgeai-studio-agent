#! /bin/sh

apt-get update 
apt-get install gstreamer1.0-plugins-ugly
apt install nodejs
apt-get install npm
apt-get install usbutils
apt install udev
apt-get install v4l-utils
pip3 install -r requirements.txt
cd server
npm install express --save
npm install cors --save
npm install log-timestamp --save
