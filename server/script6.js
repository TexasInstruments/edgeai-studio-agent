var dgram = require('dgram');
var express = require('express')
var http = require('http')
var EventEmitter = require('events').EventEmitter;
let cors = require("cors");
var bodyParser = require('body-parser')
//require('log-timestamp');   //adds timestamp in console.log()

var app = express();
app.use(express.static(__dirname + '/'));

const port = 8080;  //change port number is required
const udp_port = 8081;  //change port number is required

//Set Cors settings
const corsOptions = {
    origin: '*',
    optionsSuccessStatus: 200 // For legacy browser support
};
app.use(cors(corsOptions));
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));

/* respond headers */
// Add Access Control Allow Origin headers
app.use((req, res, next) => {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.header(
    "Access-Control-Allow-Headers",
    "Origin, X-Requested-With, Content-Type, Accept"
  );
  next();
});

var httpServer = http.createServer(app);
var emitter = new EventEmitter();

//send raw video stream
app.get('/raw_videostream/:id', function (req, res) {
    
    res.writeHead(200, {
        'Content-Type': 'video/mp4',
    });
    console.log(req.params.id)
    emitter.on('data', function(data) {
         
         console.log('data event received...');
         const chunk = data.length
         if(chunk > 0){
            res.write(data)
         }
         else{
         console.log('empty')
         res.status(500).end('stop')
         
         }
     
    });

    emitter.on('end', function() {
        console.log('Response closed.');
	res.end();
    });

    console.log('returning...');
});
//Stop udp server from sending pending data after dpipe
app.get('/test', function (req, res) {
   
   emitter.emit('data', '');
   res.status(200).send('Stopped stream')

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

udpServer.on('error', (err) => {
  console.log(`server error:\n${err.stack}`);
  udpServer.close();
});

udpServer.on('message', (msg, rinfo) => {
  emitter.emit('data', msg);
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
