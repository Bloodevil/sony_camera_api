import sys
from sony_camera_api import sony_api

method = None
param = []
if len(sys.argv) > 1:
	method = sys.argv[1]
	if len(sys.argv) > 2:
		param = list(sys.argv[2:])

print sony_api(method, param)['result']
