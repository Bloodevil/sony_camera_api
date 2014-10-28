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


class SonyAPI():

    def __init__(self, QX_ADDR=None, params=None):
        if not QX_ADDR:
            self.QX_ADDR = 'http://10.0.0.1:10000'
        else:
            self.QX_ADDR = QX_ADDR
        if not params:
            self.params = collections.OrderedDict([
            ("method", ""),
            ("params", []),
            ("id", 1),  # move to setting
            ("version", "1.0")])  # move to setting
        else:
            self.params = params

    def _truefalse(self, param):
        params = []
        for x in param:
            if x.lower() == 'true':
                params.append(True)
            elif x.lower() == 'false':
                params.append(False)
            else:
                params.append(x)
        return params

    def _cmd(self, method=None, param=[]):
        true = True
        false = False
        null = None

        if method:
            self.params["method"] = method
        if param:
            self.params["params"] = self._truefalse(param)

        try:
            result = eval(urllib2.urlopen(self.QX_ADDR + "/sony/camera", json.dumps(params)).read())
        except:
            result = "[ERROR] camera doesn't work"
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

    def startLiveviewWithSize(self, param=None):
        if not param:
            print """[ERROR] please enter the param like below
        "L"     XGA size scale (the size varies depending on the camera models,
                and some camera models change the liveview quality instead of
                making the size larger.)
        "M"     VGA size scale (the size varies depending on the camera models)
        """
        return self._cmd(method="startLiveviewWithSize", param=param)

    def getLiveviewSize(self):
        return self._cmd(method="getLiveviewSize")

    def getSupportedLiveviewSize(self):
        return self._cmd(method="getSupportedLiveviewSize")

    def getAvailableLiveviewSize(self):
        return self._cmd(method="getAvailableLiveviewSize")

    def setLiveviewFrameInfo(self, param=None):
        if not param:
            print """
        "frameInfo"
                true - Transfer the liveview frame information
                false - Not transfer
        e.g) SonyAPI.setLiveviewFrameInfo(param=[{"frameInfo": true}])
        """
        return self._cmd(method="setLiveviewFrameInfo")

    def getLiveviewFrameInfo(self):
        return self._cmd(method="getLiveviewFrameInfo")

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

    def getZoomSetting(self)
        return self._cmd(method="getZoomSetting")

    def getSupportedZoomSetting(self)
        return self._cmd(method="getSupportedZoomSetting")
 
    def getAvailableZoomSetting(self)
        return self._cmd(method="getAvailableZoomSetting")

    def actHalfPressShutter(self)
        return self._cmd(method="actHalfPressShutter")

    def cancelHalfPressShutter(self)
        return self._cmd(method="cancelHalfPressShutter")

    def setTouchAFPosition(self, param=None)
        if not param:
            print """ [ X-axis position, Y-axis position]
                X-axis position     Double
                Y-axis position     Double
            e.g) SonyAPI.setTouchAFPosition(param=[ 23.2, 45.2 ])
            """
        return self._cmd(method="setTouchAFPosition", param=param)

    def getTouchAFPosition(self)
        return self._cmd(method="getTouchAFPosition")

    def cancelTouchAFPosition(self)
        return self._cmd(method="cancelTouchAFPosition")

    def actTrackingFocus(self, param=None)
        if not param:
            print """
                "xPosition"     double                X-axis position
                "yPosition"     double                Y-axis position
            e.g) SonyAPI.actTrackingFocus(param={"xPosition":23.2, "yPosition": 45.2})
            """
        return self._cmd(method="actTrackingFocus", param=param)


