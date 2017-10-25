#!/usr/bin/env python

# Credentials shamelessly stolen from:
# https://github.com/Tsar/sony_qx_controller/blob/master/sony_qx_controller.py#L144

import pysony
import base64, hashlib
import six

print("Searching for camera...")

search = pysony.ControlPoint()
cameras =  search.discover()

if len(cameras):
    camera = pysony.SonyAPI(QX_ADDR=cameras[0])
else:
    print("No camera found, aborting")
    quit()

# This call fails with a '403 - Permission Error' on the HDR-AS15 (fw V3.0)
# Once authenticated it will complete sucessfully
# print("Get Movie Quality: %s" % camera.getMovieQuality())


# Tied to Methods list below, 64 _ASCII_ characters = 256 bit equivilant
AUTH_CONST_STRING = "90adc8515a40558968fe8318b5b023fdd48d3828a2dda8905f3b93a3cd8e58dc"
METHODS_TO_ENABLE = "\
camera/setFlashMode:\
camera/getFlashMode:\
camera/getSupportedFlashMode:\
camera/getAvailableFlashMode:\
camera/setExposureCompensation:\
camera/getExposureCompensation:\
camera/getSupportedExposureCompensation:\
camera/getAvailableExposureCompensation:\
camera/setSteadyMode:\
camera/getSteadyMode:\
camera/getSupportedSteadyMode:\
camera/getAvailableSteadyMode:\
camera/setViewAngle:\
camera/getViewAngle:\
camera/getSupportedViewAngle:\
camera/getAvailableViewAngle:\
camera/setMovieQuality:\
camera/getMovieQuality:\
camera/getSupportedMovieQuality:\
camera/getAvailableMovieQuality:\
camera/setFocusMode:\
camera/getFocusMode:\
camera/getSupportedFocusMode:\
camera/getAvailableFocusMode:\
camera/setStillSize:\
camera/getStillSize:\
camera/getSupportedStillSize:\
camera/getAvailableStillSize:\
camera/setBeepMode:\
camera/getBeepMode:\
camera/getSupportedBeepMode:\
camera/getAvailableBeepMode:\
camera/setCameraFunction:\
camera/getCameraFunction:\
camera/getSupportedCameraFunction:\
camera/getAvailableCameraFunction:\
camera/setLiveviewSize:\
camera/getLiveviewSize:\
camera/getSupportedLiveviewSize:\
camera/getAvailableLiveviewSize:\
camera/setTouchAFPosition:\
camera/getTouchAFPosition:\
camera/cancelTouchAFPosition:\
camera/setFNumber:\
camera/getFNumber:\
camera/getSupportedFNumber:\
camera/getAvailableFNumber:\
camera/setShutterSpeed:\
camera/getShutterSpeed:\
camera/getSupportedShutterSpeed:\
camera/getAvailableShutterSpeed:\
camera/setIsoSpeedRate:\
camera/getIsoSpeedRate:\
camera/getSupportedIsoSpeedRate:\
camera/getAvailableIsoSpeedRate:\
camera/setExposureMode:\
camera/getExposureMode:\
camera/getSupportedExposureMode:\
camera/getAvailableExposureMode:\
camera/setWhiteBalance:\
camera/getWhiteBalance:\
camera/getSupportedWhiteBalance:\
camera/getAvailableWhiteBalance:\
camera/setProgramShift:\
camera/getSupportedProgramShift:\
camera/getStorageInformation:\
camera/startLiveviewWithSize:\
camera/startIntervalStillRec:\
camera/stopIntervalStillRec:\
camera/actFormatStorage:\
system/setCurrentTime"

# Request random nonce from camera
resp = camera.actEnableMethods([{"methods": "", "developerName": "", \
    "developerID": "", "sg": ""}])
dg = resp["result"][0]["dg"]

# Append nonce to AUTH string and hash
h = hashlib.sha256()
h.update(bytes(AUTH_CONST_STRING + dg))
sg = base64.b64encode(h.digest()).decode("UTF-8")

# Pass credentials to camera, which will eval with secret method/values
resp = camera.actEnableMethods([{"methods": METHODS_TO_ENABLE, \
   "developerName": "Sony Corporation", \
   "developerID": "7DED695E-75AC-4ea9-8A85-E5F8CA0AF2F3", "sg": sg}])

print "Authenicated:", resp

