'''
USAGE: uvicorn inference_log:app --host=0.0.0.0 --reload
REFERENCE: https://fastapi.tiangolo.com/advanced/websockets/
'''

from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
import subprocess
app = FastAPI()

html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <h1>WebSocket Chat</h1>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
            var ws = new WebSocket("ws://10.201.0.211:8000/ws");
            ws.onmessage = function(event) {
                var messages = document.getElementById('messages')
                var message = document.createElement('li')
                var content = document.createTextNode(event.data)
                message.appendChild(content)
                messages.appendChild(message)
            };
            function sendMessage(event) {
                var input = document.getElementById("messageText")
                ws.send(input.value)
                input.value = ''
                event.preventDefault()
            }
        </script>
    </body>
</html>
"""


@app.get("/")
async def get():
    return HTMLResponse(html)

import random
import asyncio

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        with subprocess.Popen(['./app_edgeai.py', '../configs/object_inputcam.yaml'],
                            stdout=subprocess.PIPE,
                            bufsize=1,
                            universal_newlines=True) as process:
            for line in process.stdout:
                line = line.rstrip()
                await websocket.send_text(line)
                await asyncio.sleep(0.1)
    except:
        await websocket.close()
