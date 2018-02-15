import asyncio
import csv
import json
import logging
from logging.handlers import RotatingFileHandler

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

# logging.basicConfig(level=logging.INFO) # take this value from the command line
logger = logging.getLogger("mylog")
formatter = logging.Formatter(
    '%(asctime)s | %(name)s |  %(levelname)s: %(message)s')
logger.setLevel(logging.DEBUG)

stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
stream_handler.setFormatter(formatter)

logFilePath = "./debug.log"
file_handler = RotatingFileHandler(
    filename=logFilePath, maxBytes=5*1024*1024, backupCount=2)  # maybe make this a size limit rotation
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.DEBUG)

logger.addHandler(file_handler)
logger.addHandler(stream_handler)

shape = (8, 8)
frames = deque([], 1)
yolos = deque([], 1)
grideye_connections = []
web_connections = []
yolo_connections = []


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
            logging.info("removing grideye connection {}, ".format(index))


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
            logging.info("removing yolo connection {}, ".format(index))


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
            logging.info("removing web connection {}, ".format(index))


async def ws_handler(ws, path):
    logging.info('Incoming ws connection {}'.format(ws))
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
                logging.info('adding grideye connection #{}'.format(len(grideye_connections)))
                grideye_connections.append(ws)
            elif json_message['device'] == 'yolo':
                logging.info('adding yolo connection #{}'.format(len(yolo_connections)))                
                yolo_connections.append(ws)
            else:
                logging.info('adding web connection #{}'.format(
                    len(web_connections)))
                web_connections.append(ws)
    while True:
        await asyncio.sleep(1)


def run(host):
    start_server = websockets.serve(ws_handler, host, 8888)
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.async(get_grideye())
    asyncio.async(get_yolo())
    asyncio.async(send_to_web())
    asyncio.get_event_loop().run_forever()


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else '0.0.0.0')
