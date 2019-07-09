from __future__ import print_function

import pysony
import time
import fnmatch
import six
import argparse

everything = {\
    "getAvailableAudioRecording",\
    "getAvailableAutoPowerOff",\
    "getAvailableBeepMode",\
    "getAvailableCameraFunction",\
    "getAvailableColorSetting",\
    "getAvailableContShootingMode",\
    "getAvailableContShootingSpeed",\
    "getAvailableExposureCompensation",\
    "getAvailableExposureMode",\
    "getAvailableFlashMode",\
    "getAvailableFlipSetting",\
    "getAvailableFNumber",\
    "getAvailableFocusMode",\
    "getAvailableInfraredRemoteControl",\
    "getAvailableIntervalTime",\
    "getAvailableIsoSpeedRate",\
    "getAvailableLiveviewSize",\
    "getAvailableLoopRecTime",\
    "getAvailableMovieFileFormat",\
    "getAvailableMovieQuality",\
    "getAvailablePostviewImageSize",\
    "getAvailableSceneSelection",\
    "getAvailableSelfTimer",\
    "getAvailableShootMode",\
    "getAvailableShutterSpeed",\
    "getAvailableSteadyMode",\
    "getAvailableStillQuality",\
    "getAvailableStillSize",\
    "getAvailableTrackingFocus",\
    "getAvailableTvColorSystem",\
    "getAvailableViewAngle",\
    "getAvailableWhiteBalance",\
    "getAvailableWindNoiseReduction",\
    "getAvailableZoomSetting",\
    "getSupportedAudioRecording",\
    "getSupportedAutoPowerOff",\
    "getSupportedBeepMode",\
    "getSupportedCameraFunction",\
    "getSupportedColorSetting",\
    "getSupportedContShootingMode",\
    "getSupportedContShootingSpeed",\
    "getSupportedExposureCompensation",\
    "getSupportedExposureMode",\
    "getSupportedFlashMode",\
    "getSupportedFlipSetting",\
    "getSupportedFNumber",\
    "getSupportedFocusMode",\
    "getSupportedInfraredRemoteControl",\
    "getSupportedIntervalTime",\
    "getSupportedIsoSpeedRate",\
    "getSupportedLiveviewSize",\
    "getSupportedLoopRecTime",\
    "getSupportedMovieFileFormat",\
    "getSupportedMovieQuality",\
    "getSupportedPostviewImageSize",\
    "getSupportedProgramShift",\
    "getSupportedSceneSelection",\
    "getSupportedSelfTimer",\
    "getSupportedShootMode",\
    "getSupportedShutterSpeed",\
    "getSupportedSteadyMode",\
    "getSupportedStillQuality",\
    "getSupportedStillSize",\
    "getSupportedTrackingFocus",\
    "getSupportedTvColorSystem",\
    "getSupportedViewAngle",\
    "getSupportedWhiteBalance",\
    "getSupportedWindNoiseReduction",\
    "getSupportedZoomSetting"}

parser = argparse.ArgumentParser(prog="dump_camera_capabilities")

parser.add_argument("-a", "--available", action="store_true", dest="available", help="dump available (rather than supported) paramaters")
parser.add_argument("-b", "--brute", action="store_true", dest="brute", help="brute force all know methods")

# Following settings may affect what is 'available' at any one time
parser.add_argument("-E", "--expose", type=int, dest="expose", help="switch to exposure mode 'x'")
parser.add_argument("-S", "--shoot", type=int, dest="shoot", help="switch to shoot mode 'x'")
parser.add_argument("-F", "--func", type=int, dest="func", help="switch to function mode 'x'")

options = parser.parse_args()

print("Searching for camera...")

search = pysony.ControlPoint()
cameras =  search.discover()
# cameras = ['http://192.168.122.1:8080']

if len(cameras):
    print("Found: %s" % cameras[0])
    print("")
    camera = pysony.SonyAPI(QX_ADDR=cameras[0], debug=options.brute)
else:
    print("No camera found, aborting")
    quit()

mode = camera.getAvailableApiList()

# Force Exposure Mode
if options.expose and 'setExposureMode' in (mode['result'])[0]:
    resp = camera.getAvailableExposureMode()
    camera.setExposureMode(resp['result'][1][options.expose-1])

# Force Shoot Mode
if options.shoot and 'setShootMode' in (mode['result'])[0]:
    resp = camera.getAvailableShootMode()
    camera.setShootMode(resp['result'][1][options.shoot-1])

# Force Camera Function
if options.func and 'setCameraFunction' in (mode['result'])[0]:
    resp = camera.getAvailableCameraFunction()
    camera.setCameraFunction(resp['result'][1][options.func-1])
    time.sleep(5)

# For those cameras which need it
if 'startRecMode' in (mode['result'])[0]:
    camera.startRecMode()
    time.sleep(5)

# Re-read capabilities as they may have changed
mode = camera.getAvailableApiList()

if options.brute:
    mode["result"][0] = everything

print("Available calls:")
for x in (mode["result"]):
    for y in x:
        print(y)

    if options.available:
        filtered = fnmatch.filter(x, "*Available*")
    else:
        filtered = fnmatch.filter(x, "*Supported*")

print("--")

for x in filtered:
    print("trying '%s()':" % x)
    function=getattr(camera, x)
    params = function()
    print(params)
    print("")
