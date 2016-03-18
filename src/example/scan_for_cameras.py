import pysony

search = pysony.ControlPoint()
cameras =  search.discover(5)

print "Available cameras", cameras
print

for x in cameras:
    print "Checking Camera", ":", x
    camera = pysony.SonyAPI(QX_ADDR=x)

    mode = camera.getAvailableApiList()
    print mode
    print

