from pysony import SonyAPI

import time

flask_app = None
try:
    import flask
    from flask import Flask
    flask_app = Flask(__name__)
except ImportError:
    print("Cannot import `flask`, liveview on web is not available")

if flask_app:
    flask_app.get_frame_handle = None

    flask_app.config['DEBUG'] = False

    @flask_app.route("/")
    def index():
        return flask.render_template_string("""
            <html>
              <head>
                <title>SONY Camera LiveView Streaming</title>
              </head>
              <body>
                <h1>SONY LiveView Streaming</h1>
                <img src="{{ url_for('video_feed') }}">
              </body>
            </html>
                    """)

    def gen():
        while True:
            if flask_app.get_frame_handle is not None:
                frame = flask_app.get_frame_handle()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

    @flask_app.route('/video_feed')
    def video_feed():
        return flask.Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')


def liveview():
    camera = SonyAPI(QX_ADDR='http://192.168.122.1:8080')

    # a7r need `startRecMode` before we can use liveview
    #   For those camera which doesn't require this, just comment out the following 2 lines
    camera.startRecMode()
    # Wait for the camera waking up
    time.sleep(2)

    sizes = camera.getLiveviewSize()
    print('Supported liveview size:', sizes)
    # url = camera.liveview("M")
    url = camera.liveview()

    lst = SonyAPI.LiveviewStreamThread(url)
    lst.start()
    print('[i] LiveviewStreamThread started.')
    return lst.get_latest_view


if __name__ == "__main__":
    handler = liveview()
    if flask_app:
        flask_app.get_frame_handle = handler
        flask_app.run()
