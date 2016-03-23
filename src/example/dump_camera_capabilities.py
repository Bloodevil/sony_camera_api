import pysony
import time
import fnmatch

print "Searching for camera"

search = pysony.ControlPoint()
cameras =  search.discover()

if len(cameras):
    camera = pysony.SonyAPI(QX_ADDR=cameras[0])
else:
    print "No camera found, aborting"
    quit()

mode = camera.getAvailableApiList()

# For those cameras which need it
if 'startRecMode' in (mode['result'])[0]:
    camera.startRecMode()
    time.sleep(5)

    # and re-read capabilities
    mode = camera.getAvailableApiList()

print "Available calls:"
for x in (mode["result"]):
    for y in x:
        print y
    filtered = fnmatch.filter(x, "*Supported*")

print "--"

for x in filtered:
    print x, ":"
    function=getattr(camera, x)
    params = function()
    print params
    print
