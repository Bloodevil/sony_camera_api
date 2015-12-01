# Echo client program
import socket
import sys
import xml
import time

SSDP_ADDR = "239.255.255.250"  # The remote host
SSDP_PORT = 1900    # The same port as used by the server
SSDP_MX = 1
SSDP_ST = "urn:schemas-sony-com:service:ScalarWebAPI:1"
SSDP_TIMEOUT = 10000  #msec
PACKET_BUFFER_SIZE = 1024

# I don't know how I can use this Upnp (...)
class ControlPoint(object):
    def __init__(self):
        self.__bind_sockets()

    def __bind_sockets(self):
        self.__udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.__udp_socket.settimeout(1)
        return

    def discover(self, duration):
        # Set the socket to broadcast mode.
        self.__udp_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL , 2)

        msg = '\r\n'.join(["M-SEARCH * HTTP/1.1",
                           "HOST: 239.255.255.250:1900",
                           "MAN: ssdp:discover",
                           "MX: " + str(duration),
                           "ST: " + SSDP_ST,
                           "USER-AGENT: ",
                           "",
                           ""])

        # Send the message.
        self.__udp_socket.sendto(msg, (SSDP_ADDR, SSDP_PORT))
        # Get the responses.
        packets = self._listen_for_discover(duration)
        return packets

    def _listen_for_discover(self, duration):
        start = time.time()
        packets = []
        while (time.time() < (start + duration)):
            try:
                data, addr = self.__udp_socket.recvfrom(1024)
                packets.append((data, addr))
            except:
                pass
        return packets

import collections
import urllib2
import json

# Common Header
# 0--------1--------2--------+--------4----+----+----+----8
# |0xFF    |payload | sequence number | Time stamp        |
# |        |type    |                 |                   |
# +-------------------------------------------------------+
#
# Payload Header
# 0--------------------------4-------------------7--------8
# | Start code               |  JPEG data size   | Padding|
# +--------------------------4------5---------------------+
# | Reserved                 | 0x00 | ..                  |
# +-------------------------------------------------------+
# | .. 115[B] Reserved                                    |
# +-------------------------------------------------------+
# | ...                                                   |
# ------------------------------------------------------128
#
# Payload Data
# in case payload type = 0x01
# +-------------------------------------------------------+
# | JPEG data size ...                                    |
# +-------------------------------------------------------+
# | ...                                                   |
# +-------------------------------------------------------+
# | Padding data size ...                                 |
# ------------------------------JPEG data size + Padding data size

import binascii

def common_header(bytes):
    start_byte = int(binascii.hexlify(bytes[0]), 16)
    payload_type = int(binascii.hexlify(bytes[1]), 16)
    sequence_number = int(binascii.hexlify(bytes[2:4]), 16)
    time_stemp = int(binascii.hexlify(bytes[4:8]), 16)
    if start_byte != 255: # 0xff fixed
        return '[error] wrong QX livestream start byte'
    if payload_type != 1: # 0x01 - liveview images
        return '[error] wrong QX livestream payload type'
    common_header = {'start_byte': start_byte,
                    'payload_type': payload_type,
                    'sequence_number': sequence_number,
                    'time_stemp': time_stemp, #milliseconds
                    }
    return common_header

def payload_header(bytes):
    start_code = int(binascii.hexlify(bytes[0:4]), 16)
    jpeg_data_size = int(binascii.hexlify(bytes[4:7]), 16)
    padding_size = int(binascii.hexlify(bytes[7]), 16)
    reserved_1 = int(binascii.hexlify(bytes[8:12]), 16)
    flag = int(binascii.hexlify(bytes[12]), 16) # 0x00, fixed
    reserved_2 = int(binascii.hexlify(bytes[13:]), 16)
    if flag != 0:
        return '[error] wrong QX payload header flag'
    if start_code != 607479929:
        return '[error] wrong QX payload header start'

    payload_header = {'start_code': start_code,
                      'jpeg_data_size': jpeg_data_size,
                      'padding_size': padding_size,
                      'reserved_1': reserved_1,
                      'flag': flag,
                      'resreved_2':reserved_2,
                    }
    return payload_header


class SonyAPI():

    def __init__(self, QX_ADDR=None, params=None):
        if not QX_ADDR:
            self.QX_ADDR = 'http://10.0.0.1:10000'
        else:
            self.QX_ADDR = QX_ADDR
        if not params:
            self.params = {
            "method": "",
            "params": [],
            "id": 1,  # move to setting
            "version": "1.0"}  # move to setting
        else:
            self.params = params

    def _truefalse(self, param):
        params = []
        if type(param) != list:
            param = [param]
        for x in param:
            if x.lower() == 'true':
                params.append(True)
            elif x.lower() == 'false':
                params.append(False)
            else:
                params.append(x)
        return params

    def _cmd(self, method=None, param=[], target=None):
        true = True
        false = False
        null = None

        if not method in ["getAvailableApiList", "liveview"]:
            camera_api_list = self.getAvailableApiList()["result"][0]
            if method not in camera_api_list:
                return "[ERROR] this api is not support in this camera"

        if method:
            self.params["method"] = method
        if param:
            self.params["params"] = self._truefalse(param)
        else:
            self.params["params"] = []

        try:
            if target:
                result = eval(urllib2.urlopen(self.QX_ADDR + "/sony/" + target, json.dumps(self.params)).read())
            else:
                result = eval(urllib2.urlopen(self.QX_ADDR + "/sony/camera", json.dumps(self.params)).read())
        except Exception as e:
            result = "[ERROR] camera doesn't work" + str(e)
        return result

    def liveview(self, param=None):
        if not param:
            liveview = self._cmd(method="startLiveview")
        else:
            liveview = self._cmd(method="startLiveviewWithSize", param=param)
        if isinstance(liveview, dict):
            try:
                url = liveview['result'][0].replace('\\','')
                result = urllib2.urlopen(url)
            except:
                result = "[ERROR] liveview is dict type but there are no result: " + str(liveview['result'])
        else:
            print "[WORN] liveview is not a dict type"
            result = liveview
        return result

    def setShootMode(self, param=None):
        if not param:
            print """[ERROR] please enter the param like below
            "still"            Still image shoot mode
            "movie"            Movie shoot mode
            "audio"            Audio shoot mode
            "intervalstill"    Interval still shoot mode
            """
        return self._cmd(method="setShootMode", param=param)


    def startLiveviewWithSize(self, param=None):
        if not param:
            print """[ERROR] please enter the param like below
        "L"     XGA size scale (the size varies depending on the camera models,
                and some camera models change the liveview quality instead of
                making the size larger.)
        "M"     VGA size scale (the size varies depending on the camera models)
        """

        return self._cmd(method="startLiveviewWithSize", param=param)

    def setLiveviewFrameInfo(self, param=None):
        if not param:
            print """
        "frameInfo"
                true - Transfer the liveview frame information
                false - Not transfer
        e.g) SonyAPI.setLiveviewFrameInfo(param=[{"frameInfo": true}])
        """
        return self._cmd(method="setLiveviewFrameInfo", param=param)

    def actZoom(self, param=None):
        if not param:
            print """ ["direction", "movement"]
            direction
                "in"        Zoom-In
                "out"       Zoom-Out
            movement
                "start"     Long push
                "stop"      Stop
                "1shot"     Short push
            e.g) SonyAPI.actZoom(param=["in", "start"])
            """
        return self._cmd(method="actZoom", param=param)

    def setZoomSetting(self, param=None):
        if not param:
            print """
            "zoom"
                "Optical Zoom Only"                Optical zoom only.
                "On:Clear Image Zoom"              On:Clear Image Zoom.
            e.g) SonyAPI.setZoomSetting(param=[{"zoom": "Optical Zoom Only"}])
            """
        return self._cmd(method="setZoomSetting", param=param)

    def setLiveviewSize(self, param=None):
        return self._cmd(method="setLiveviewSize", param=param)

    def setTouchAFPosition(self, param=None):
        if not param:
            print """ [ X-axis position, Y-axis position]
                X-axis position     Double
                Y-axis position     Double
            e.g) SonyAPI.setTouchAFPosition(param=[ 23.2, 45.2 ])
            """
        return self._cmd(method="setTouchAFPosition", param=param)

    def actTrackingFocus(self, param=None):
        if not param:
            print """
                "xPosition"     double                X-axis position
                "yPosition"     double                Y-axis position
            e.g) SonyAPI.actTrackingFocus(param={"xPosition":23.2, "yPosition": 45.2})
            """
        return self._cmd(method="actTrackingFocus", param=param)

    def setTrackingFocus(self, param=None):
        return self._cmd(method="setTrackingFocus", param=param)

    def setContShootingMode(self, param=None):
        return self._cmd(method="setContShootingMode", param=param)

    def setContShootingSpeed(self, param=None):
        return self._cmd(method="setContShootingSpeed", param=param)

    def setSelfTimer(self, param=None):
        return self._cmd(method="setSelfTimer", param=param)

    def setExposureMode(self, param=None):
        return self._cmd(method="setExposureMode", param=param)

    def setFocusMode(self, param=None):
        return self._cmd(method="setFocusMode", param=param)

    def setExposureCompensation(self, param=None):
        return self._cmd(method="setExposureCompensation", param=param)

    def setFNumber(self, param=None):
        return self._cmd(method="setFNumber", param=param)

    def setShutterSpeed(self, param=None):
        return self._cmd(method="setShutterSpeed", param=param)

    def setIsoSpeedRate(self, param=None):
        return self._cmd(method="setIsoSpeedRate", param=param)

    def setWhiteBalance(self, param=None):
        return self._cmd(method="setWhiteBalance", param=param)

    def setProgramShift(self, param=None):
        return self._cmd(method="setProgramShift", param=param)

    def setFlashMode(self, param=None):
        return self._cmd(method="setFlashMode", param=param)

    def setAutoPowerOff(self, param=None):
        return self._cmd(method="setAutoPowerOff", param=param)

    def setBeepMode(self, param=None):
        return self._cmd(method="setBeepMode", param=param)

    def setCurrentTime(self, param=None):
        return self._cmd(method="setCurrentTime", param=param, target="system")

    def setStillSize(self, param=None):
        return self._cmd(method="setStillSize", param=param)

    def setStillQuality(self, param=None):
        return self._cmd(method="setStillQuality", param=param)

    def setPostviewImageSize(self, param=None):
        return self._cmd(method="setPostviewImageSize", param=param)

    def setMovieFileFormat(self, param=None):
        return self._cmd(method="setMovieFileFormat", param=param)

    def setMovieQuality(self, param=None):
        return self._cmd(method="setMovieQuality", param=param)

    def setSteadyMode(self, param=None):
        return self._cmd(method="setSteadyMode", param=param)

    def setViewAngle(self, param=None):
        return self._cmd(method="setViewAngle", param=param)

    def setSceneSelection(self, param=None):
        return self._cmd(method="setSceneSelection", param=param)

    def setColorSetting(self, param=None):
        return self._cmd(method="setColorSetting", param=param)

    def setIntervalTime(self, param=None):
        return self._cmd(method="setIntervalTime", param=param)

    def setLoopRecTime(self, param=None):
        return self._cmd(method="setLoopRecTime", param=param)

    def setFlipSetting(self, param=None):
        return self._cmd(method="setFlipSetting", param=param)

    def setTvColorSystem(self, param=None):
        return self._cmd(method="setTvColorSystem", param=param)

    def startRecMode(self):
        return self._cmd(method="startRecMode")

    def stopRecMode(self):
        return self._cmd(method="stopRecMode")

    def getCameraFunction(self):
        return self._cmd(method="getCameraFunction")

    def getSupportedCameraFunction(self):
        return self._cmd(method="getSupportedCameraFunction")

    def getAvailableCameraFunction(self):
        return self._cmd(method="getAvailableCameraFunction")

    def getAudioRecording(self):
        return self._cmd(method="getAudioRecording")

    def getSupportedAudioRecording(self):
        return self._cmd(method="getSupportedAudioRecording")

    def getAvailableAudioRecording(self):
        return self._cmd(method="getAvailableAudioRecording")

    def getWindNoiseReduction(self):
        return self._cmd(method="getWindNoiseReduction")

    def getSupportedWindNoiseReduction(self):
        return self._cmd(method="getSupportedWindNoiseReduction")

    def getAvailableWindNoiseReduction(self):
        return self._cmd(method="getAvailableWindNoiseReduction")

    def setCameraFunction(self, param=None):
        return self._cmd(method="setCameraFunction", param=param)

    def setAudioRecording(self, param=None):
        return self._cmd(method="setAudioRecording", param=param)

    def setWindNoiseReduction(self, param=None):
        return self._cmd(method="setWindNoiseReduction", param=param)

    def getSourceList(self, param=None):
        return self._cmd(method="getSourceList", param=param, target="avContent")

    def getContentCount(self, param=None):
        return self._cmd(method="getContentCount", param=param, target="avContent")

    def getContentList(self, param=None):
        return self._cmd(method="getContentList", param=param, target="avContent")

    def setStreamingContent(self, param=None):
        return self._cmd(method="setStreamingContent", param=param, target="avContent")

    def seekStreamingPosition(self, param=None):
        return self._cmd(method="seekStreamingPosition", param=param, target="avContent")

    def requestToNotifyStreamingStatus(self, param=None):
        return self._cmd(method="requestToNotifyStreamingStatus", param=param, target="avContent")

    def deleteContent(self, param=None):
        return self._cmd(method="deleteContent", param=param, target="avContent")

    def setInfraredRemoteControl(self, param=None):
        return self._cmd(method="setInfraredRemoteControl", param=param)

    def getEvent(self, param=None):
        return self._cmd(method="getEvent", param=param)

    def getMethodTypes(self, param=None, target=None): # camera, system and avContent
        return self._cmd(method="getMethodTypes", param=param, target=None)

    def getShootMode(self):
        return self._cmd(method="getShootMode")

    def getSupportedShootMode(self):
        return self._cmd(method="getSupportedShootMode")

    def getAvailableShootMode(self):
        return self._cmd(method="getAvailableShootMode")

    def actTakePicture(self):
        return self._cmd(method="actTakePicture")

    def awaitTakePicture(self):
        return self._cmd(method="awaitTakePicture")

    def startContShooting(self):
        return self._cmd(method="startContShooting")

    def stopContShooting(self):
        return self._cmd(method="stopContShooting")

    def startMovieRec(self):
        return self._cmd(method="startMovieRec")

    def stopMovieRec(self):
        return self._cmd(method="stopMovieRec")

    def startLoopRec(self):
        return self._cmd(method="startLoopRec")

    def stopLoopRec(self):
        return self._cmd(method="stopLoopRec")

    def startAudioRec(self):
        return self._cmd(method="startAudioRec")

    def stopAudioRec(self):
        return self._cmd(method="stopAudioRec")

    def startIntervalStillRec(self):
        return self._cmd(method="startIntervalStillRec")

    def stopIntervalStillRec(self):
        return self._cmd(method="stopIntervalStillRec")

    def startLiveview(self):
        return self._cmd(method="startLiveview")

    def stopLiveview(self):
        return self._cmd(method="stopLiveview")

    def getLiveviewSize(self):
        return self._cmd(method="getLiveviewSize")

    def getSupportedLiveviewSize(self):
        return self._cmd(method="getSupportedLiveviewSize")

    def getAvailableLiveviewSize(self):
        return self._cmd(method="getAvailableLiveviewSize")

    def getLiveviewFrameInfo(self):
        return self._cmd(method="getLiveviewFrameInfo")

    def getZoomSetting(self):
        return self._cmd(method="getZoomSetting")

    def getSupportedZoomSetting(self):
        return self._cmd(method="getSupportedZoomSetting")

    def getAvailableZoomSetting(self):
        return self._cmd(method="getAvailableZoomSetting")

    def actHalfPressShutter(self):
        return self._cmd(method="actHalfPressShutter")

    def cancelHalfPressShutter(self):
        return self._cmd(method="cancelHalfPressShutter")

    def getTouchAFPosition(self):
        return self._cmd(method="getTouchAFPosition")

    def cancelTouchAFPosition(self):
        return self._cmd(method="cancelTouchAFPosition")

    def cancelTrackingFocus(self):
        return self._cmd(method="cancelTrackingFocus")

    def getTrackingFocus(self):
        return self._cmd(method="getTrackingFocus")

    def getSupportedTrackingFocus(self):
        return self._cmd(method="getSupportedTrackingFocus")

    def getAvailableTrackingFocus(self):
        return self._cmd(method="getAvailableTrackingFocus")

    def getContShootingMode(self):
        return self._cmd(method="getContShootingMode")

    def getSupportedContShootingMode(self):
        return self._cmd(method="getSupportedContShootingMode")

    def getAvailableContShootingMode(self):
        return self._cmd(method="getAvailableContShootingMode")

    def getContShootingSpeed(self):
        return self._cmd(method="getContShootingSpeed")

    def getSupportedContShootingSpeed(self):
        return self._cmd(method="getSupportedContShootingSpeed")

    def getAvailableContShootingSpeed(self):
        return self._cmd(method="getAvailableContShootingSpeed")

    def getSelfTimer(self):
        return self._cmd(method="getSelfTimer")

    def getSupportedSelfTimer(self):
        return self._cmd(method="getSupportedSelfTimer")

    def getAvailableSelfTimer(self):
        return self._cmd(method="getAvailableSelfTimer")

    def getExposureMode(self):
        return self._cmd(method="getExposureMode")

    def getSupportedExposureMode(self):
        return self._cmd(method="getSupportedExposureMode")

    def getAvailableExposureMode(self):
        return self._cmd(method="getAvailableExposureMode")

    def getFocusMode(self):
        return self._cmd(method="getFocusMode")

    def getSupportedFocusMode(self):
        return self._cmd(method="getSupportedFocusMode")

    def getAvailableFocusMode(self):
        return self._cmd(method="getAvailableFocusMode")

    def getExposureCompensation(self):
        return self._cmd(method="getExposureCompensation")

    def getSupportedExposureCompensation(self):
        return self._cmd(method="getSupportedExposureCompensation")

    def getAvailableExposureCompensation(self):
        return self._cmd(method="getAvailableExposureCompensation")

    def getFNumber(self):
        return self._cmd(method="getFNumber")

    def getSupportedFNumber(self):
        return self._cmd(method="getSupportedFNumber")

    def getAvailableFNumber(self):
        return self._cmd(method="getAvailabeFNumber")

    def getShutterSpeed(self):
        return self._cmd(method="getShutterSpeed")

    def getSupportedShutterSpeed(self):
        return self._cmd(method="getSupporedShutterSpeed")

    def getAvailableShutterSpeed(self):
        return self._cmd(method="getAvailableShutterSpeed")

    def getIsoSpeedRate(self):
        return self._cmd(method="getIsoSpeedRate")

    def getSupportedIsoSpeedRate(self):
        return self._cmd(method="getSupportedIsoSpeedRate")

    def getAvailableIsoSpeedRate(self):
        return self._cmd(method="getAvailableIsoSpeedRate")

    def getWhiteBalance(self):
        return self._cmd(method="getWhiteBalance")

    def getSupportedWhiteBalance(self):
        return self._cmd(method="getSupportedWhiteBalance")

    def getAvailableWhiteBalance(self):
        return self._cmd(method="getAvailableWhiteBalance")

    def actWhiteBalanceOnePushCustom(self):
        return self._cmd(method="actWhiteBalanceOnePushCustom")

    def getSupportedProgramShift(self):
        return self._cmd(method="getSupportedProgramShift")

    def getFlashMode(self):
        return self._cmd(method="getFlashMode")

    def getSupportedFlashMode(self):
        return self._cmd(method="getSupportedFlashMode")

    def getAvailableFlashMode(self):
        return self._cmd(method="getAvailableFlashMode")

    def getStillSize(self):
        return self._cmd(method="getStillSize")

    def getSupportedStillSize(self):
        return self._cmd(method="getSupportedStillSize")

    def getAvailableStillSize(self):
        return self._cmd(method="getAvailableStillSize")

    def getStillQuality(self):
        return self._cmd(method="getStillQuality")

    def getSupportedStillQuality(self):
        return self._cmd(method="getSupportedStillQuality")

    def getAvailableStillQuality(self):
        return self._cmd(method="getAvailableStillQuality")

    def getPostviewImageSize(self):
        return self._cmd(method="getPostviewImageSize")

    def getSupportedPostviewImageSize(self):
        return self._cmd(method="getSupportedPostviewImageSize")

    def getAvailablePostviewImageSize(self):
        return self._cmd(method="getAvailablePostviewImageSize")

    def getMovieFileFormat(self):
        return self._cmd(method="getMovieFileFormat")

    def getSupportedMovieFileFormat(self):
        return self._cmd(method="getSupportedMovieFileFormat")

    def getAvailableMovieFileFormat(self):
        return self._cmd(method="getAvailableMovieFileFormat")

    def getMovieQuality(self):
        return self._cmd(method="getMovieQuality")

    def getSupportedMovieQuality(self):
        return self._cmd(method="getSupportedMovieQuality")

    def getAvailableMovieQuality(self):
        return self._cmd(method="getAvailableMovieQuality")

    def getSteadyMode(self):
        return self._cmd(method="getSteadyMode")

    def getSupportedSteadyMode(self):
        return self._cmd(method="getSupportedSteadyMode")

    def getAvailableSteadyMode(self):
        return self._cmd(method="getAvailableSteadyMode")

    def getViewAngle(self):
        return self._cmd(method="getViewAngle")

    def getSupportedViewAngle(self):
        return self._cmd(method="getSupportedViewAngle")

    def getAvailableViewAngle(self):
        return self._cmd(method="getAvailableViewAngle")

    def getSceneSelection(self):
        return self._cmd(method="getSceneSelection")

    def getSupportedSceneSelection(self):
        return self._cmd(method="getSupportedSceneSelection")

    def getAvailableSceneSelection(self):
        return self._cmd(method="getAvailableSceneSelection")

    def getColorSetting(self):
        return self._cmd(method="getColorSetting")

    def getSupportedColorSetting(self):
        return self._cmd(method="getSupportedColorSetting")

    def getAvailableColorSetting(self):
        return self._cmd(method="getAvailableColorSetting")

    def getIntervalTime(self):
        return self._cmd(method="getIntervalTime")

    def getSupportedIntervalTime(self):
        return self._cmd(method="getSupportedIntervalTime")

    def getAvailableIntervalTime(self):
        return self._cmd(method="getAvailableIntervalTime")

    def getLoopRecTime(self):
        return self._cmd(method="getLoopRecTime")

    def getSupportedLoopRecTime(self):
        return self._cmd(method="getSupportedLoopRecTime")

    def getAvailableLoopRecTime(self):
        return self._cmd(method="getAvailableLoopRecTime")

    def getFlipSetting(self):
        return self._cmd(method="getFlipSetting")

    def getSupportedFlipSetting(self):
        return self._cmd(method="getSupportedFlipSetting")

    def getAvailableFlipSetting(self):
        return self._cmd(method="getAvailableFlipSetting")

    def getTvColorSystem(self):
        return self._cmd(method="getTvColorSystem")

    def getSupportedTvColorSystem(self):
        return self._cmd(method="getSupportedTvColorSystem")

    def getAvailableTvColorSystem(self):
        return self._cmd(method="getAvailableTvColorSystem")

    def startStreaming(self):
        return self._cmd(method="startStreaming", target="avContent")

    def pauseStreaming(self):
        return self._cmd(method="pauseStreaming", target="avContent")

    def stopStreaming(self):
        return self._cmd(method="stopStreaming", target="avContent")

    def getInfraredRemoteControl(self):
        return self._cmd(method="getInfraredRemoteControl")

    def getSupportedInfraredRemoteControl(self):
        return self._cmd(method="getSupportedInfraredRemoteControl")

    def getAvailableInfraredRemoteControl(self):
        return self._cmd(method="getAvailableInfraredRemoteControl")

    def getAutoPowerOff(self):
        return self._cmd(method="getAutoPowerOff")

    def getSupportedAutoPowerOff(self):
        return self._cmd(method="getSupportedAutoPowerOff")

    def getAvailableAutoPowerOff(self):
        return self._cmd(method="getAvailableAutoPowerOff")

    def getBeepMode(self):
        return self._cmd(method="getBeepMode")

    def getSupportedBeepMode(self):
        return self._cmd(method="getSupportedBeepMode")

    def getAvailableBeepMode(self):
        return self._cmd(method="getAvailableBeepMode")

    def getSchemeList(self):
        return self._cmd(method="getSchemeList", target="avContent")

    def getStorageInformation(self):
        return self._cmd(method="getStorageInformation")

    def actFormatStorage(self):
        return self._cmd(method="actFormatStorage")

    def getAvailableApiList(self):
        return self._cmd(method="getAvailableApiList")

    def getApplicationInfo(self):
        return self._cmd(method="getApplicationInfo")

    def getVersions(self, target=None):
        return self._cmd(method="getVersions", target=target)


