import pysony
import fnmatch

camera = pysony.SonyAPI()
#camera = pysony.SonyAPI(QX_ADDR='http://192.168.122.1:8080/')

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
