import sys
import pprint
from sony_camera_api import SonyAPI

method = None
param = []

if len(sys.argv) > 1:
	method = sys.argv[1]
	if len(sys.argv) > 2:
		param = list(sys.argv[2:])

sony = SonyAPI()
pp = pprint.PrettyPrinter(indent=4)
pp.pprint(sony._cmd(method, param=None))
