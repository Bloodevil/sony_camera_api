#!/usr/bin/env python
'''
this example is for those who use multiple network interface
In my case, I connected my Raspberry pi's interface
 eth0 : to internet
 wlan0 : to sony camera, a5100 specifically
Normally pysony doesn't work in this case. Because socket sends ssdp only to eth0
I modified ControlPoint's init function so socket object in ControlPoint to be bound to wlan0
'''

import pysony

print("Searching for camera...")

search = pysony.ControlPoint(interface='wlan0')
cameras =  search.discover()

if len(cameras):
    camera = pysony.SonyAPI(QX_ADDR=cameras[0])
else:
    print("No camera found, aborting")
    quit()