import asyncio
import json
import math
import os
import time
from datetime import datetime
import sys
from collections import deque
import numpy as np
import csv
import websockets
from flask import Flask, render_template
from scipy.interpolate import griddata

from flask_sockets import Sockets
from GridEyeKit import GridEYEKit

app = Flask(__name__, static_url_path='')
app.jinja_env.auto_reload = True
app.config['TEMPLATES_AUTO_RELOAD'] = True
sockets = Sockets(app)

frames = deque([], 10)
grideye_connections = []
web_connections = []

N = 8  #number of pixels per row in original
M = 32j  #number of pixels per row wanted (complex)
points = [(math.floor(ix / N), (ix % N)) for ix in range(0, N * N)]
grid_x, grid_y = np.mgrid[0:(N - 1):M, 0:(N - 1):M]

def init_grideye():
    g = GridEYEKit()
    print("Connecting to Grideye")
    try:
        g_status_connect = g.connect()
        print(g_status_connect)
        if not g_status_connect:
            g.close()
            print("could not connect to grideye...")
            os._exit(1)
        print("Connected\n")
    except :
        print("could not connect to grideye...")
        g.close()
        os._exit(1)


# @sockets.route('/serve_data')
# def qa_socket(ws):
#     while not ws.closed:
#         # import pdb;pdb.set_trace()
#         pixels = g.get_temperatures()
#         bicubic = griddata(
#             points, pixels.flatten(), (grid_x, grid_y), method='cubic')
#         pixels = bicubic.reshape(32, 32).tolist()
#         therm = g.get_thermistor()
#         ws.send(json.dumps(pixels))
#         # ws.send(json.dumps(pixels.tolist()))
#         if not np.any(pixels):
#             import pdb
#             pdb.set_trace()
#         time.sleep(0.5)


async def add_frame():
    while True:
        with open('training-Thermal.csv') as f:
            for frame in csv.reader(f):
                frames.append([[float(x) for x in row]
                         for row in np.reshape(frame, (8, 8)).tolist()])
                await asyncio.sleep(0.5)


@app.route('/')
def hello():
    return render_template('bvn.html')


@asyncio.coroutine
def test_get():
    with open('training-Thermal.csv') as f:
        for pixels in csv.reader(f):
            bicubic = griddata(
                points, pixels, (grid_x, grid_y), method='cubic')
            # pixels = [float(x) for x in bicubic.reshape(32, 32).tolist()]
            frames.append(pixels)
            yield from asyncio.sleep(0.5)

@asyncio.coroutine
def test_send():
    yield from asyncio.sleep(2)
    while True:
        yield from asyncio.sleep(0.5)
        for connection in web_connections:
            yield from connection.send(json.dumps(frames[0]))


def ws_message_handle(ws, message):
    ra = ws.remote_address
    # client = self.ra_to_client.get(ra, None)
    # if client is not None and message == "bump":
    #     client.bump()
    #     you_status = client.hstr()
    #     client.json_pre_send({
    #         'you': you_status,
    #         'size': len(self.ra_to_client),
    #         client.i: you_status
    #     })
    #     self.client_publish_to_peers(client)

async def ws_handler(ws, path):
    ra = ws.remote_address
    web_connections.append(ws)
    # client = Client(len(self.ra_to_client), ws)
    # self.ra_to_client[ra] = client

    # producer_task = asyncio.ensure_future(add_frame()) # so does this listen to events here?
    listener_task = asyncio.ensure_future(ws.recv())
    # self.introduce(client)
    done, pending = await asyncio.wait(
            [listener_task],
            return_when=asyncio.FIRST_COMPLETED)
    if listener_task in done:
        message = listener_task.result()
        if message is None:
            return
            # client.alive = False
        else:
            json_message = json.loads(message)
            if json_message['device'] == 'pi':
                grideye_connections.append(ws)
            else:
                web_connections.append(ws)
    while True:
        time.sleep(1)

def run(host):
    '''
    '''
    start_server = websockets.serve(ws_handler, host, 9677)
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.async(test_get())
    asyncio.async(test_send())
    asyncio.get_event_loop().run_forever()

if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else 'localhost')
