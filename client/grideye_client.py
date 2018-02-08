import asyncio
import json
import math
import os
import sys
import time
from collections import deque
from datetime import datetime

import numpy as np
import websockets
from scipy.interpolate import griddata

# GridEyeKit import GridEYEKit


SHAPE = (32, 32)
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


async def test_send(url):
    async with websockets.connect(url
        ) as ws:
        await ws.send(json.dumps({'device': 'pi'}))
        while True:
            await asyncio.sleep(0.5)
            # yield from connection.send(json.dumps([[float(x) for x in row]
            #                 for row in np.reshape(frames[0], (8, 8)).tolist()]))
            pixels = g.get_temperatures()
            bicubic = griddata(
                points, pixels.flatten(), (grid_x, grid_y), method='cubic')
            pixels = bicubic.reshape(SHAPE).tolist()
            therm = g.get_thermistor()
            await ws.send(json.dumps(pixels))


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else 'ws://localhost:9677'
    asyncio.async(test_send(url))
    asyncio.get_event_loop().run_forever()
