from sony_camera_api import SonyAPI
import json
import urllib2
import socket

# Common Header
# 0--------1--------2--------+--------4----+----+----+----8
# |0xFF    |payload | sequence number | Time stamp        |
# |        |type    |                 |                   |
# +-------------------------------------------------------+
#
# Payload Header
# 0--------------------------4-------------------7--------8
# | Start code               |  JPEG data size   | Padding|
# +--------------------------4------5---------------------+
# | Reserved                 | 0x00 | ..                  |
# +-------------------------------------------------------+
# | .. 115[B] Reserved                                    |
# +-------------------------------------------------------+
# | ...                                                   |
# ------------------------------------------------------128
#
# Payload Data
# in case payload type = 0x01
# +-------------------------------------------------------+
# | JPEG data size ...                                    |
# +-------------------------------------------------------+
# | ...                                                   |
# +-------------------------------------------------------+
# | Padding data size ...                                 |
# ------------------------------JPEG data size + Padding data size

import binascii

def common_header(bytes):
    start_byte = int(binascii.hexlify(bytes[0]), 16)
    payload_type = int(binascii.hexlify(bytes[1]), 16)
    sequence_number = int(binascii.hexlify(bytes[2:4]), 16)
    time_stemp = int(binascii.hexlify(bytes[4:8]), 16)
    if start_byte != 255: # 0xff fixed
        return '[error] wrong QX livestream start byte'
    if payload_type != 1: # 0x01 - liveview images
        return '[error] wrong QX livestream payload type'
    common_header = {'start_byte': start_byte,
                    'payload_type': payload_type,
                    'sequence_number': sequence_number,
                    'time_stemp': time_stemp, #milliseconds
                    }
    return common_header

def payload_header(bytes):
    start_code = int(binascii.hexlify(bytes[0:4]), 16)
    jpeg_data_size = int(binascii.hexlify(bytes[4:7]), 16)
    padding_size = int(binascii.hexlify(bytes[7]), 16)
    reserved_1 = int(binascii.hexlify(bytes[8:12]), 16)
    flag = int(binascii.hexlify(bytes[12]), 16) # 0x00, fixed
    reserved_2 = int(binascii.hexlify(bytes[13:]), 16)
    if flag != 0:
        return '[error] wrong QX payload header flag'
    if start_code != 607479929:
        return '[error] wrong QX payload header start'
    payload_header = {'start_code': start_code,
                    'jpeg_data_size': jpeg_data_size,
                    'padding_size': padding_size,
                    'reserved_1': reserved_1,
                    'flag': flag,
                    'resreved_2':reserved_2,
                    }
    return payload_header

import urllib2
import thread
try:
    from flask import Flask, url_for
    app = Flask(__name__)
    @app.route("/")
    def view():
        return """<html>
                <head>
                    <meta http-equiv="refresh" content="1">
                </head>
                <img src="http://localhost:5000%s">
                </html>""" % url_for('static', filename='test.jpg')
except:
    app = None

def liveview():
    camera = SonyAPI()
    liveview_url = camera.startLiveview()['result'][0]
    f = urllib2.urlopen(liveview_url)

    while 1:
        data = f.read(8)
        data = f.read(128)
        payload = payload_header(data)
        # [TODO] when debug mode, print payload for debug
        # if app.config('DEBUG'):
        #     print payload
        test = open('./static/test.jpg', 'w')
        test.write(f.read(payload['jpeg_data_size']))
        test.close()
        f.read(payload['padding_size'])

if __name__ == "__main__":
    thread.start_new_thread(liveview, ())
    if app:
        app.run()

