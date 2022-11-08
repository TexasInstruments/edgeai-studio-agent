#! /bin/sh

pip3 install -r requirements.txt
cd server
npm install express --save
npm install cors --save
npm install log-timestamp --save
