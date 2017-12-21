[![Build Status](https://travis-ci.org/Bloodevil/sony_camera_api.svg?branch=master)](https://travis-ci.org/Bloodevil/sony_camera_api)

Pysony
===============
python sony camera api

Install
====
using pip:

    pip install pysony

using repo:

    git clone https://github.com/Bloodevil/sony_camera_api.git
    python setup.py install

Usage
====

 simple example:

    >>> api = pysony.SonyAPI()
    >>> api.getAvailableApiList()

api_list
====

 there api list that you can use.

examples
====
liveview
- can see the photo via liveview

timer
- take a picture every n seconds

dump_camera_capabilities
- show every supported api list

pyLiveView
- Released under the GPL v2 (or later) by Simon Wood (simon@mungewell.org)
- Sample application to connect to camera, and start a video recording
- with or without a GUI LiveView screen


