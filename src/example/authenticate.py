#!/usr/bin/env python

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


# Tied to Methods list below, 64 _ASCII_ characters = 256 bit equivalant
AUTH_CONST_STRING = "35fc6c85705f5b37eb0f31f60c8412644fb2755ff55701e04a82d671c4b5d998"

# Enable _Everything_ we know about...
# $ grep -e '    def [^_]' src/pysony.py | grep -v -e 'discover(' | sed -e 's/    def /camera\//g' -e 's/(.*/:\\/g' | sort
METHODS_TO_ENABLE = "\
avContent/deleteContent:\
avContent/getContentCount:\
avContent/getContentList:\
avContent/getSchemeList:\
avContent/getSourceList:\
avContent/pauseStreaming:\
avContent/requestToNotifyStreamingStatus:\
avContent/seekStreamingPosition:\
avContent/setStreamingContent:\
avContent/startStreaming:\
avContent/stopStreaming:\
camera/actFormatStorage:\
camera/actHalfPressShutter:\
camera/actTakePicture:\
camera/actTrackingFocus:\
camera/actWhiteBalanceOnePushCustom:\
camera/actZoom:\
camera/awaitTakePicture:\
camera/cancelHalfPressShutter:\
camera/cancelTouchAFPosition:\
camera/cancelTrackingFocus:\
camera/getApplicationInfo:\
camera/getAudioRecording:\
camera/getAutoPowerOff:\
camera/getAvailableApiList:\
camera/getAvailableAudioRecording:\
camera/getAvailableAutoPowerOff:\
camera/getAvailableBeepMode:\
camera/getAvailableCameraFunction:\
camera/getAvailableColorSetting:\
camera/getAvailableContShootingMode:\
camera/getAvailableContShootingSpeed:\
camera/getAvailableExposureCompensation:\
camera/getAvailableExposureMode:\
camera/getAvailableFlashMode:\
camera/getAvailableFlipSetting:\
camera/getAvailableFNumber:\
camera/getAvailableFocusMode:\
camera/getAvailableInfraredRemoteControl:\
camera/getAvailableIntervalTime:\
camera/getAvailableIsoSpeedRate:\
camera/getAvailableLiveviewSize:\
camera/getAvailableLoopRecTime:\
camera/getAvailableMovieFileFormat:\
camera/getAvailableMovieQuality:\
camera/getAvailablePostviewImageSize:\
camera/getAvailableSceneSelection:\
camera/getAvailableSelfTimer:\
camera/getAvailableShootMode:\
camera/getAvailableShutterSpeed:\
camera/getAvailableSteadyMode:\
camera/getAvailableStillQuality:\
camera/getAvailableStillSize:\
camera/getAvailableTrackingFocus:\
camera/getAvailableTvColorSystem:\
camera/getAvailableViewAngle:\
camera/getAvailableWhiteBalance:\
camera/getAvailableWindNoiseReduction:\
camera/getAvailableZoomSetting:\
camera/getBeepMode:\
camera/getCameraFunction:\
camera/getColorSetting:\
camera/getContShootingMode:\
camera/getContShootingSpeed:\
camera/getEvent:\
camera/getExposureCompensation:\
camera/getExposureMode:\
camera/getFlashMode:\
camera/getFlipSetting:\
camera/getFNumber:\
camera/getFocusMode:\
camera/getInfraredRemoteControl:\
camera/getIntervalTime:\
camera/getIsoSpeedRate:\
camera/getLiveviewFrameInfo:\
camera/getLiveviewSize:\
camera/getLoopRecTime:\
camera/getMethodTypes:\
camera/getMovieFileFormat:\
camera/getMovieQuality:\
camera/getPostviewImageSize:\
camera/getSceneSelection:\
camera/getSelfTimer:\
camera/getShootMode:\
camera/getShutterSpeed:\
camera/getSteadyMode:\
camera/getStillQuality:\
camera/getStillSize:\
camera/getStorageInformation:\
camera/getSupportedAudioRecording:\
camera/getSupportedAutoPowerOff:\
camera/getSupportedBeepMode:\
camera/getSupportedCameraFunction:\
camera/getSupportedColorSetting:\
camera/getSupportedContShootingMode:\
camera/getSupportedContShootingSpeed:\
camera/getSupportedExposureCompensation:\
camera/getSupportedExposureMode:\
camera/getSupportedFlashMode:\
camera/getSupportedFlipSetting:\
camera/getSupportedFNumber:\
camera/getSupportedFocusMode:\
camera/getSupportedInfraredRemoteControl:\
camera/getSupportedIntervalTime:\
camera/getSupportedIsoSpeedRate:\
camera/getSupportedLiveviewSize:\
camera/getSupportedLoopRecTime:\
camera/getSupportedMovieFileFormat:\
camera/getSupportedMovieQuality:\
camera/getSupportedPostviewImageSize:\
camera/getSupportedProgramShift:\
camera/getSupportedSceneSelection:\
camera/getSupportedSelfTimer:\
camera/getSupportedShootMode:\
camera/getSupportedShutterSpeed:\
camera/getSupportedSteadyMode:\
camera/getSupportedStillQuality:\
camera/getSupportedStillSize:\
camera/getSupportedTrackingFocus:\
camera/getSupportedTvColorSystem:\
camera/getSupportedViewAngle:\
camera/getSupportedWhiteBalance:\
camera/getSupportedWindNoiseReduction:\
camera/getSupportedZoomSetting:\
camera/getTouchAFPosition:\
camera/getTrackingFocus:\
camera/getTvColorSystem:\
camera/getVersions:\
camera/getViewAngle:\
camera/getWhiteBalance:\
camera/getWindNoiseReduction:\
camera/getZoomSetting:\
camera/liveview:\
camera/setAudioRecording:\
camera/setAutoPowerOff:\
camera/setBeepMode:\
camera/setCameraFunction:\
camera/setColorSetting:\
camera/setContShootingMode:\
camera/setContShootingSpeed:\
camera/setExposureCompensation:\
camera/setExposureMode:\
camera/setFlashMode:\
camera/setFlipSetting:\
camera/setFNumber:\
camera/setFocusMode:\
camera/setInfraredRemoteControl:\
camera/setIntervalTime:\
camera/setIsoSpeedRate:\
camera/setLiveviewFrameInfo:\
camera/setLiveviewSize:\
camera/setLoopRecTime:\
camera/setMovieFileFormat:\
camera/setMovieQuality:\
camera/setPostviewImageSize:\
camera/setProgramShift:\
camera/setSceneSelection:\
camera/setSelfTimer:\
camera/setShootMode:\
camera/setShutterSpeed:\
camera/setSteadyMode:\
camera/setStillQuality:\
camera/setStillSize:\
camera/setTouchAFPosition:\
camera/setTrackingFocus:\
camera/setTvColorSystem:\
camera/setViewAngle:\
camera/setWhiteBalance:\
camera/setWindNoiseReduction:\
camera/setZoomSetting:\
camera/startAudioRec:\
camera/startContShooting:\
camera/startIntervalStillRec:\
camera/startLiveview:\
camera/startLiveviewWithSize:\
camera/startLoopRec:\
camera/startMovieRec:\
camera/startRecMode:\
camera/stopAudioRec:\
camera/stopContShooting:\
camera/stopIntervalStillRec:\
camera/stopLiveview:\
camera/stopLoopRec:\
camera/stopMovieRec:\
camera/stopRecMode:\
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
   "developerName": "Rubber Duck Paradise", \
   "developerID": "22222222-2222-2222-2222-222222222222", "sg": sg}])

print "Authenicated:", resp

