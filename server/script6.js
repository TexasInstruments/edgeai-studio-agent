var dgram = require('dgram');
var express = require('express')
var http = require('http')
var net = require('net');
var child = require('child_process');
var EventEmitter = require('events').EventEmitter;
require('log-timestamp');   //adds timestamp in console.log()

var app = express();
app.use(express.static(__dirname + '/'));

var httpServer = http.createServer(app);
const port = 8080;  //change port number is required
const udp_port = 8081;  //change port number is required

var emitter = new EventEmitter();

//send the html page which holds the video tag
app.get('/', function (req, res) {
    res.send('index.html');
});

//send the inference video stream
app.get('/inference_stream', function (req, res) {
    
    res.writeHead(200, {
        'Content-Type': 'video/mp4',
    });

    emitter.on('data', function(data) {
         console.log('data event received...');
	 res.write(data);
    });

	
    emitter.on('end', function() {
        console.log('Response closed.');
	res.end();
    });

    console.log('returning...');
});

//send raw video stream
app.get('/raw_videostream', function (req, res) {
    
    res.writeHead(200, {
        'Content-Type': 'video/mp4',
    });

    emitter.on('data', function(data) {
         console.log('data event received...');
	 res.write(data);
    });

	
    emitter.on('end', function() {
        console.log('Response closed.');
	res.end();
    });

    console.log('returning...');
});

async function myResponse(req, res) {
    console.log(new Date().getTime() + " GET request => " + req.originalUrl);
    await asyncForLoop();
    console.log(new Date().getTime() + " finished for-loop.");
}

async function asyncForLoop() {
    for (let i=0; i<5; i++) {
        console.log(i);
        await wait(1000);
    }
}

function wait(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

const udpServer = dgram.createSocket('udp4');
var client = dgram.createSocket("udp4");

udpServer.on('error', (err) => {
  console.log(`server error:\n${err.stack}`);
  uspServer.close();
});

udpServer.on('message', (msg, rinfo) => {
  emitter.emit('data', msg);
  // console.log(`server got: ${msg} from ${rinfo.address}:${rinfo.port}`);
  // console.log('data event sending...');
});

udpServer.on('listening', () => {
  const address = udpServer.address();
  console.log(`UDP Server listening ${address.address}:${address.port}`);
});


udpServer.bind(udp_port);

httpServer.listen(port);
console.log(`Stream WebApp listening at http://localhost:${port}`)

process.on('uncaughtException', function (err) {
    console.log(err);
});
