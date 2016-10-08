from pysony import SonyAPI, payload_header

import urllib2
import thread
import time
import os

try:
    from flask import Flask, url_for
    app = Flask(__name__)

    #if you want to see the payload, set Debug = True.
    app.config['DEBUG'] = False
    @app.route("/")
    def view():
        return """<html>
                <head>
                    <meta http-equiv="refresh" content="1">
                </head>
                <img src="http://127.0.0.1:5000%s">
                </html>""" % url_for('static', filename='test.jpg')
except Exception as e:
    print(e)
    app = None

def liveview():
    camera = SonyAPI()

    # [TODO]
    # replace liveview function to camera.liveview function.
    # liveview function will do everything in this liveview function not just a file.
    f = camera.liveview()
    #st = os.stat(f.name())

    if not os.path.exists("./static"):
        os.makedirs("./static")

    pos = 0
    while True:
        # read f size and control.
        #if st.st_size - pos < 136:
        #    continue
        #else:
        #    pos += 136
        data = f.read(8)
        data = f.read(128)
        payload = payload_header(data)
        # [TODO] when debug mode, print payload for debug
        if False: #app.config('DEBUG'):
            print(payload)
        try:
            data_size = f.read(payload['jpeg_data_size'])
            test = open('./static/test.jpg', 'wb')
            # wait until get pyload jpeg data size.
            test.write(data_size)
            test.close()
            f.read(payload['padding_size'])
        except Exception as e:
            print("[ERROR]" + str(e))

if __name__ == "__main__":
    thread.start_new_thread(liveview, ())
    if app:
        app.run()

