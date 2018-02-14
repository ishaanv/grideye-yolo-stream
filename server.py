import asyncio
import csv
import json
import logging
import math
import os
import sys
import time
from collections import deque
from datetime import datetime

import numpy as np
import websockets
from flask import Flask, render_template
from scipy.interpolate import griddata

from GridEyeKit import GridEYEKit

app = Flask(__name__, static_url_path='')
app.jinja_env.auto_reload = True
app.config['TEMPLATES_AUTO_RELOAD'] = True

# logging.basicConfig(level=logging.DEBUG)

shape = (8, 8)
frames = deque([], 1)
yolos = deque([], 1)
grideye_connections = []
web_connections = []
yolo_connections = []

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
    except:
        print("could not connect to grideye...")
        g.close()
        os._exit(1)


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
def get_grideye():
    while True:
        try:
            for index, connection in enumerate(grideye_connections):
                data = yield from connection.recv()
                # import pdb; pdb.set_trace()
                json_data = json.loads(data)
                frames.append(json_data['data'])
            yield from asyncio.sleep(0.5)
        except Exception as e:
            del grideye_connections[index]
            print(e)


@asyncio.coroutine
def get_yolo():
    while True:
        try:
            for index, connection in enumerate(yolo_connections):
                data = yield from connection.recv()
                json_data = json.loads(data)
                yolos.append(json_data['data'])
            yield from asyncio.sleep(0.5)
        except Exception as e:
            del yolo_connections[index]
            print(e)


@asyncio.coroutine
def send_to_web():
    # send thermal grid
    yield from asyncio.sleep(2)
    while True:
        try:
            yield from asyncio.sleep(0.5)
            for index, connection in enumerate(web_connections):
                if frames:
                    yield from connection.send(
                        json.dumps({
                            'type': 'grideye',
                            'data': frames[0]
                        }))
                if yolos:
                    # import pdb; pdb.set_trace()
                    yield from connection.send(
                        json.dumps({
                            'type': 'yolo',
                            'data': yolos[0]
                        }))
            if yolos:
                yolos.pop()  # empty yolo buffer
        except Exception as e:
            del web_connections[index]
            print("removing index {}, ".format(index), e)


async def ws_handler(ws, path):
    ra = ws.remote_address
    listener_task = asyncio.ensure_future(ws.recv())
    done, pending = await asyncio.wait(
        [listener_task], return_when=asyncio.FIRST_COMPLETED)
    if listener_task in done:
        message = listener_task.result()
        if message is None:
            return
        else:
            # import pdb; pdb.set_trace()
            json_message = json.loads(message)
            if json_message['device'] == 'grideye':
                grideye_connections.append(ws)
            elif json_message['device'] == 'yolo':
                yolo_connections.append(ws)
            else:
                web_connections.append(ws)
    while True:
        await asyncio.sleep(1)


def run(host):
    '''
    '''
    start_server = websockets.serve(ws_handler, host, 8888)
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.async(get_grideye())
    asyncio.async(get_yolo())
    asyncio.async(send_to_web())
    asyncio.get_event_loop().run_forever()


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else '0.0.0.0')
