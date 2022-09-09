#! /bin/sh

apt-get update 
apt install sudo 
sudo apt install nodejs
sudo apt-get install gstreamer1.0-plugins-ugly
apt-get install usbutils
apt install udev
apt-get install v4l-utils
pip3 install -r requirements.txt
