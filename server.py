import json
import math
import os
import time
from datetime import datetime
from sys import exit

import numpy as np
from flask import Flask, render_template
from scipy.interpolate import griddata

from flask_sockets import Sockets
from GridEyeKit import GridEYEKit

app = Flask(__name__, static_url_path='')
app.jinja_env.auto_reload = True
app.config['TEMPLATES_AUTO_RELOAD'] = True
sockets = Sockets(app)

# @sockets.route('/recv_data')
# def data_socket(ws):
#     while not ws.closed:
#         data_frames.append(ws.receive())

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
except:
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


@app.route('/')
def hello():
    return render_template('bvn.html')


if __name__ == "__main__":
    # TODO understand where gevent fits into the whole picture
    from gevent import pywsgi
    from geventwebsocket.handler import WebSocketHandler
    port = 8585
    server = pywsgi.WSGIServer(('', port), app, handler_class=WebSocketHandler)
    # server = pywsgi.WSGIServer(('', 8585), app, handler_class=WebSocketHandler, keyfile='./server.key', certfile='./server.crt')
    print("serving on http://localhost:{}".format(port))
    server.serve_forever()