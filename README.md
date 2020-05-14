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

Running tests
=============

You will likely want to set up a [virtualenv](https://virtualenv.pypa.io/en/stable/) first and complete the following steps inside it.

Install requirements:

	pip install -r test-requirements.txt

Run tests:

	python -m unittest discover

(The `run_tests.sh` script does both of these automatically)

By default, the test suite verifies behavior locally using dummy services.

If you want to run tests live against your real camera, connect to the camera's
wireless access point and set the `TEST_LIVE_CAMERA` environment variable.
For example:

	TEST_LIVE_CAMERA=1 python -m unittest discover

**CAUTION:** Use with your camera at your own risk. This is free software that offers no warranty. For details, see LICENSE.


Usage
====

 simple example:

    >>> api = pysony.SonyAPI()
    >>> api.getAvailableApiList()

api_list
====

 there api list that you can use.

branches
====
 - develop : please request merge here.
 - master : pip live

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


