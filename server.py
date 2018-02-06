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
connections = []

def init_grideye():
    N = 8  #number of pixels per row in original
    M = 32j  #number of pixels per row wanted (complex)
    points = [(math.floor(ix / N), (ix % N)) for ix in range(0, N * N)]
    grid_x, grid_y = np.mgrid[0:(N - 1):M, 0:(N - 1):M]
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


@sockets.route('/serve_data')
def qa_socket(ws):
    while not ws.closed:
        # import pdb;pdb.set_trace()
        pixels = g.get_temperatures()
        bicubic = griddata(
            points, pixels.flatten(), (grid_x, grid_y), method='cubic')
        pixels = bicubic.reshape(32, 32).tolist()
        therm = g.get_thermistor()
        ws.send(json.dumps(pixels))
        # ws.send(json.dumps(pixels.tolist()))
        if not np.any(pixels):
            import pdb
            pdb.set_trace()
        time.sleep(0.5)


async def add_frame():
    while True:
        with open('training-Thermal.csv') as f:
            for frame in csv.reader(f):
                # ws.send(
                #     json.dumps(
                #         [[float(x) for x in row]
                #          for row in np.reshape(frame, (8, 8)).tolist()]))
                frames.append([[float(x) for x in row]
                         for row in np.reshape(frame, (8, 8)).tolist()])
                await asyncio.sleep(0.5)


@app.route('/')
def hello():
    return render_template('bvn.html')


class GraceFuture(asyncio.Future):
    def __init__(self):
        asyncio.Future.__init__(self)

    def set_result_default(self, result):
        if not self.done():
            self.set_result(result)
        return self.result()

class Client:
    def __init__(self, i, ws):
        self.i = i
        self.ws = ws
        self.counter = 0
        self.time = time.time()
        self.alive = True
        self.future = GraceFuture()

    def bump(self):
        self.counter += 1
        self.time = time.time()

    async def produce(self):
        await self.future
        result = self.future.result()
        self.future = GraceFuture()
        return result

    def future_state(self):
        f = self.future
        return "future: @%s cancelled=%s, done=%s, state=%s" % (hex(id(f)),
                                                                f.cancelled(),
                                                                f.done(),
                                                                f._state)

    def pre_send(self, message):
        self.future.set_result_default([]).append(message)

    def json_pre_send(self, message):
        self.pre_send(json.dumps(message))

    def hstr(self):
        address = "%s:%d" % self.ws.remote_address
        return "@%s &emsp; %s &emsp; %d" % (address, timestr(self.time),
                                            self.counter)


def timestr(t):
    int_t = int(t)
    gmta = time.gmtime(int_t)
    microsec = ("%.6f" % (t - int_t))[1:]
    s = "%d/%02d/%02d:%02d:%02d:%02d" % gmta[0:6]
    s += microsec
    return s

@asyncio.coroutine
def test_get():
    with open('training-Thermal.csv') as f:
        for frame in csv.reader(f):
            frames.append(frame)
            yield from asyncio.sleep(0.5)

@asyncio.coroutine
def test_send():
    yield from asyncio.sleep(2)
    while True:
        yield from asyncio.sleep(0.5)
        for connection in connections:
            yield from connection.send(json.dumps([[float(x) for x in row]
                         for row in np.reshape(frames[0], (8, 8)).tolist()]))

class Bumps(object):
    def __init__(self):
        self.rc = 0
        self.ra_to_client = {}  # remote-address -> client mapping

    def clients(self):
        return self.ra_to_client.values()

    def client_publish_to_peers(self, client):
        clients = self.clients()
        peers = list(filter(lambda c: c is not client, clients))
        js_peer_message = json.dumps({
            'size': len(self.ra_to_client),
            client.i: client.hstr()
        })
        for peer in peers:
            peer.pre_send(js_peer_message)

    def introduce(self, client):
        clients = self.clients()
        message = dict(map(lambda c: (c.i, c.hstr()), clients))
        message['you'] = client.hstr()
        message['size'] = len(clients)
        client.json_pre_send(message)
        self.client_publish_to_peers(client)

    def ws_message_handle(self, ws, message):
        ra = ws.remote_address
        client = self.ra_to_client.get(ra, None)
        if client is not None and message == "bump":
            client.bump()
            you_status = client.hstr()
            client.json_pre_send({
                'you': you_status,
                'size': len(self.ra_to_client),
                client.i: you_status
            })
            self.client_publish_to_peers(client)

    async def ws_handler(self, ws, path):
        ra = ws.remote_address
        connections.append(ws)
        client = Client(len(self.ra_to_client), ws)
        self.ra_to_client[ra] = client

        # producer_task = asyncio.ensure_future(add_frame()) # so does this listen to events here?
        listener_task = asyncio.ensure_future(ws.recv())
        # self.introduce(client)

        while client.alive:
            done, pending = await asyncio.wait(
                [listener_task],
                return_when=asyncio.FIRST_COMPLETED)

            if producer_task in done:
                messages = producer_task.result()
                if ws.open:
                    for message in messages:
                        await ws.send(message)
                    producer_task = asyncio.ensure_future(client.produce())
                else:
                    client.alive = False
            if listener_task in done:
                message = listener_task.result()
                if message is None:
                    client.alive = False
                else:
                    self.ws_message_handle(ws, message)
                    listener_task = asyncio.ensure_future(ws.recv())

        del self.ra_to_client[ra]

    def run(self, host):
        start_server = websockets.serve(self.ws_handler, host, 9677)
        asyncio.get_event_loop().run_until_complete(start_server)
        asyncio.async(test_get())
        asyncio.async(test_send())
        asyncio.get_event_loop().run_forever()

if __name__ == "__main__":
    bumps = Bumps()
    bumps.run(sys.argv[1] if len(sys.argv) > 1 else 'localhost')
    sys.exit(bumps.rc)
