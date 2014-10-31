from pysony import SonyAPI, pyload_header

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
    f = urllib2.urlopen(liveview_url)   # move to in SonyAPI class.

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

