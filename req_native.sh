#! /bin/sh

pip3 install -r ./doc/req_native.txt
cd server
npm install express --save
npm install cors --save
