from __future__ import print_function

import pysony
import six

search = pysony.ControlPoint()
cameras =  search.discover(5)

print("Available cameras: %s" % cameras)
print("")

for x in cameras:
    print("Checking Camera: %s" % x)
    camera = pysony.SonyAPI(QX_ADDR=x)

    mode = camera.getAvailableApiList()
    print(mode)
    print("")

