from sony_camera_api import sony_api
import json
import urllib2
import socket

liveview_url = sony_api('startLiveview')['result'][0]

print liveview_url
