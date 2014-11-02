from pysony import SonyAPI, payload_header
import urllib2
import thread
import time
import shutil
from flask import Flask, url_for

app = Flask(__name__)
@app.route("/")
def view():
    return """<html>
                <head>
                    <meta http-equiv="refresh" content="1">
                </head>
                <img src="http://localhost:5000%s">
               </html>""" % url_for('static', filename='live.jpg')

def liveview_and_save(timer=5):
    camera = SonyAPI()
    try:
        live = camera.startLiveview()
        liveview_url = live['result'][0]
        f = urllib2.urlopen(liveview_url)
    except:
        print live
        raise
    photo_num = 1
    time = timer
    while 1:
        data = f.read(8)
        data = f.read(128)
        payload = payload_header(data)
        live = open('./static/live.jpg', 'w')
        live.write(f.read(payload['jpeg_data_size']))
        live.close()
        if not time:
            save = shutil.copy('./static/live.jpg', './static/saved')
            time = timer
        f.read(payload['padding_size'])
        time.sleep(1)
        time = time - 1


if __name__ == "__main__":
    thread.start_new_thread(liveview_and_save, ())
    if app:
        app.run()
