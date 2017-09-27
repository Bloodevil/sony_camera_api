'''
PySony FILE FOR REMOTE COMMUNICATION WITH A SSUPPORTED SONY CAMERA

Improved with code from 'https://github.com/storborg/sonypy' under MIT license.
Luka Golinar (21.8.2017):
  - Pep8 complaint
  - Added support for multiple versions of Sony SDK APIs
  - Maintaining legacy support
'''
import socket
import time
import re
import comp_urllib
import json
import binascii


SSDP_ADDR = "239.255.255.250"  # The remote host
SSDP_PORT = 1900  # The same port as used by the server
SSDP_MX = 1
SSDP_ST = "urn:schemas-sony-com:service:ScalarWebAPI:1"
SSDP_TIMEOUT = 10000  # msec
PACKET_BUFFER_SIZE = 1024

BIND_PORT_NUMBER = 12346  # Seems arbitrary
# Find all available cameras using uPNP
# Improved with code from 'https://github.com/storborg/sonypy' under MIT license.

class ControlPoint(object):

    def __init__(self, ip='192.168.122.10', retries=10):
        self.retries = retries
        self.ip = ip

    def connect(self):
        while self.retries > 0:
            print "Retrying connection: %d" % self.retries
            if not self.__bind_sockets():
                self.retries -= 1
                time.sleep(1)
            else:
                return True
        return False

    def __bind_sockets(self):
        try:
            self.__udp_socket = socket.socket(
                socket.AF_INET, socket.SOCK_DGRAM)
            self.__udp_socket.setsockopt(
                socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.__udp_socket.bind((self.ip, BIND_PORT_NUMBER))
            self.__udp_socket.settimeout(.1)
        except:
            print "Could not bind socket to specified IP address. Retrying..."
            #  self.disconnect()
            return False
        return True

    def disconnect(self):
        print "Closing socket"
        if self.__udp_socket:
            self.__udp_socket.close()

    def discover(self, duration=None):
        # Default timeout of 1s
        if duration is None:
            duration = 1
        # Set the socket to broadcast mode.
        self.__udp_socket.setsockopt(
            socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)

        msg = '\r\n'.join(
            [
                "M-SEARCH * HTTP/1.1", "HOST: 239.255.255.250:1900",
                "MAN: ssdp:discover", "MX: " + str(duration),
                "ST: " + SSDP_ST, "USER-AGENT: ", "", ""])

        # Send the message.
        self.__udp_socket.sendto(msg, (SSDP_ADDR, SSDP_PORT))

        # Get the responses.
        packets = self._listen_for_discover(duration)
        endpoints = []
        for host, addr, data in packets:
            resp = self._parse_ssdp_response(data)
            try:
                endpoint = self._read_device_definition(resp['location'])
                endpoints.append(endpoint)
            except:
                pass
        return endpoints

    def _listen_for_discover(self, duration):
        start = time.time()
        packets = []
        while (time.time() < (start + duration)):
            try:
                data, (host, port) = self.__udp_socket.recvfrom(1024)

                # Assemble any packets from multiple cameras
                found = False
                for x in xrange(len(packets)):
                    ohost, oport, odata = packets[x]
                    if host == ohost and port == oport:
                        packets.append((host, port, odata+data))
                        packets.pop(x)
                        found = True

                if not found:
                    packets.append((host, port, data))
            except:
                pass
        return packets

    def _parse_ssdp_response(self, data):
        lines = data.split('\r\n')
        assert lines[0] == 'HTTP/1.1 200 OK'
        headers = {}
        for line in lines[1:]:
            if line:
                try:
                    key, val = line.split(': ', 1)
                    headers[key.lower()] = val
                except:
                    pass
        return headers

    def _parse_device_definition(self, doc):
        """
        Parse the XML device definition file.
        """
        dd_regex = (
            '<av:X_ScalarWebAPI_Service>'
            '\s*'
            '<av:X_ScalarWebAPI_ServiceType>'
            '(.+?)'
            '</av:X_ScalarWebAPI_ServiceType>'
            '\s*'
            '<av:X_ScalarWebAPI_ActionList_URL>'
            '(.+?)'
            '/sony'                               # and also strip '/sony'
            '</av:X_ScalarWebAPI_ActionList_URL>'
            '\s*'
            '<av:X_ScalarWebAPI_AccessType\s*/>'  # Note: QX10 has 'Type />', HX60 has 'Type/>'
            '\s*'
            '</av:X_ScalarWebAPI_Service>')

        services = {}
        for m in re.findall(dd_regex, doc):
            service_name = m[0]
            endpoint = m[1]
            services[service_name] = endpoint
        return services

    def _read_device_definition(self, url):
        """
        Fetch and parse the device definition, and extract the URL endpoint for
        the camera API service.
        """
        r = comp_urllib.urlopen(url)
        services = self._parse_device_definition(r.read())

        return services['camera']


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
def common_header(bytes):
    start_byte = int(binascii.hexlify(bytes[0]), 16)
    payload_type = int(binascii.hexlify(bytes[1]), 16)
    sequence_number = int(binascii.hexlify(bytes[2:4]), 16)
    time_stamp = int(binascii.hexlify(bytes[4:8]), 16)
    if start_byte != 255:  # 0xff fixed
        return '[error] wrong QX livestream start byte'

    common_header = {
        'start_byte': start_byte,
        'payload_type': payload_type,
        'sequence_number': sequence_number,
        'time_stamp': time_stamp,  # milliseconds
                    }
    return common_header


def payload_header(bytes, payload_type=None):
    if payload_type is None:
        payload_type = 1  # Assume JPEG
    start_code = int(binascii.hexlify(bytes[0:4]), 16)
    jpeg_data_size = int(binascii.hexlify(bytes[4:7]), 16)
    padding_size = int(binascii.hexlify(bytes[7]), 16)

    if start_code != 607479929:
        return '[error] wrong QX payload header start'

    payload_header = {
        'start_code': start_code,
        'jpeg_data_size': jpeg_data_size,
        'padding_size': padding_size,
    }

    if payload_type == 1:
        payload_header.update(payload_header_jpeg(bytes))
    elif payload_type == 2:
        payload_header.update(payload_header_frameinfo(bytes))
    else:
        return '[error] unknown payload type'

    return payload_header


def payload_header_jpeg(bytes):
    reserved_1 = int(binascii.hexlify(bytes[8:12]), 16)
    flag = int(binascii.hexlify(bytes[12]), 16)  # 0x00, fixed
    reserved_2 = int(binascii.hexlify(bytes[13:]), 16)
    if flag != 0:
        return '[error] wrong QX payload header flag'

    payload_header = {
        'reserved_1': reserved_1,
        'flag': flag,
        'reserved_2': reserved_2,
    }

    return payload_header


def payload_header_frameinfo(bytes):
    version = int(binascii.hexlify(bytes[8:10]), 16)
    frame_count = int(binascii.hexlify(bytes[10:12]), 16)
    frame_size = int(binascii.hexlify(bytes[12:14]), 16)
    reserved_2 = int(binascii.hexlify(bytes[14:]), 16)

    payload_header = {
        'version': version,
        'frame_count': frame_count,
        'frame_size': frame_size,
        'reserved_2': reserved_2,
    }

    return payload_header


class SonyAPI():

    def __init__(self, QX_ADDR=None, params=None, version='1.0'):
        if not QX_ADDR:
            self.QX_ADDR = 'http://10.0.0.1:10000'
        else:
            self.QX_ADDR = QX_ADDR

        if not params:
            self.params = {
                "method": "", "params": [], "id": 1, "version": version}
        else:
            self.params = params

    def _truefalse(self, param):
        params = []
        if type(param) != list:
            param = [param]
        for x in param:
            if type(x) != str:
                params.append(x)
            else:
                if x.lower() == 'true':
                    params.append(True)
                elif x.lower() == 'false':
                    params.append(False)
                else:
                    params.append(x)
        return params

    def _cmd(self, method=None, param=[], target=None, version=None):
        true = True
        false = False
        null = None
        if method:
            self.params["method"] = method
        if param:
            self.params["params"] = self._truefalse(param)
        else:
            self.params["params"] = []

        # Add a version to the JSON parameters
        if version:
            self.params['version'] = version
        try:
            if target:
                result = eval(comp_urllib.urlopen(
                    self.QX_ADDR + "/sony/" + target,
                    json.dumps(self.params)).read())
            else:
                result = eval(comp_urllib.urlopen(
                    self.QX_ADDR + "/sony/camera",
                    json.dumps(self.params)).read())
        except Exception as e:
            result = "[ERROR] camera doesn't work: " + str(e)
        return result

    def liveview(self, param=None):
        if not param:
            liveview = self._cmd(method="startLiveview")
        else:
            liveview = self._cmd(method="startLiveviewWithSize", param=param)
        if isinstance(liveview, dict):
            try:
                url = liveview['result'][0].replace('\\', '')
                result = comp_urllib.urlopen(url)
            except:
                result = "[ERROR] liveview is dict type but there are no "
                "result: " + str(liveview['result'])
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
            e.g) In[26]:  camera.setShootMode(param=['still'])
                 Out[26]: {'id': 1, 'result': [0]}
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
        e.g) SonyAPI.setLiveviewFrameInfo(param=[{"frameInfo": True}])
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
            print("""
            "zoom"
                "Optical Zoom Only"                Optical zoom only.
                "On:Clear Image Zoom"              On:Clear Image Zoom.
            e.g) SonyAPI.setZoomSetting(param=[{"zoom": "Optical Zoom Only"}])
            """)
        return self._cmd(method="setZoomSetting", param=param)

    def setLiveviewSize(self, param=None):
        return self._cmd(method="setLiveviewSize", param=param)

    def setTouchAFPosition(self, param=None):
        if not param:
            print(""" [ X-axis position, Y-axis position]
                X-axis position     Double
                Y-axis position     Double
            e.g) SonyAPI.setTouchAFPosition(param=[ 23.2, 45.2 ])
            """)
        return self._cmd(method="setTouchAFPosition", param=param)

    def actTrackingFocus(self, param=None):
        if not param:
            print("""
                "xPosition"     double                X-axis position
                "yPosition"     double                Y-axis position
            e.g) SonyAPI.actTrackingFocus(param={"xPosition":23.2,
            "yPosition": 45.2})
            """)
        return self._cmd(method="actTrackingFocus", param=param)

    def setTrackingFocus(self, param=None, version='1.0'):
        return self._cmd(
            method="setTrackingFocus", param=param, version=version)

    def setContShootingMode(self, param=None, version='1.0'):
        return self._cmd(
            method="setContShootingMode", param=param, version=version)

    def setContShootingSpeed(self, param=None, version='1.0'):
        return self._cmd(
            method="setContShootingSpeed", param=param, version=version)

    def setSelfTimer(self, param=None, version='1.0'):
        return self._cmd(
            method="setSelfTimer", param=param, version=version)

    def setExposureMode(self, param=None, version='1.0'):
        return self._cmd(
            method="setExposureMode", param=param, version=version)

    def setFocusMode(self, param=None, version='1.0'):
        return self._cmd(method="setFocusMode", param=param, version=version)

    def setExposureCompensation(self, param=None, version='1.0'):
        return self._cmd(
            method="setExposureCompensation", param=param, version=version)

    def setFNumber(self, param=None, version='1.0'):
        return self._cmd(method="setFNumber", param=param, version=version)

    def setShutterSpeed(self, param=None, version='1.0'):
        return self._cmd(
            method="setShutterSpeed", param=param, version=version)

    def setIsoSpeedRate(self, param=None, version='1.0'):
        return self._cmd(
            method="setIsoSpeedRate", param=param, version=version)

    def setWhiteBalance(self, param=None, version='1.0'):
        return self._cmd(
            method="setWhiteBalance", param=param, version=version)

    def setProgramShift(self, param=None, version='1.0'):
        return self._cmd(
            method="setProgramShift", param=param, version=version)

    def setFlashMode(self, param=None, version='1.0'):
        return self._cmd(
            method="setFlashMode", param=param, version=version)

    def setAutoPowerOff(self, param=None, version='1.0'):
        return self._cmd(
            method="setAutoPowerOff", param=param, version=version)

    def setBeepMode(self, param=None, version='1.0'):
        return self._cmd(method="setBeepMode", param=param, version=version)

    def setCurrentTime(self, param=None, version='1.0'):
        return self._cmd(
            method="setCurrentTime", param=param,
            target="system", version=version)

    def setStillSize(self, param=None, version='1.0'):
        return self._cmd(method="setStillSize", param=param, version=version)

    def setStillQuality(self, param=None, version='1.0'):
        return self._cmd(
            method="setStillQuality", param=param, version=version)

    def setPostviewImageSize(self, param=None, version='1.0'):
        return self._cmd(
            method="setPostviewImageSize", param=param, version=version)

    def setMovieFileFormat(self, param=None, version='1.0'):
        return self._cmd(
            method="setMovieFileFormat", param=param, version=version)

    def setMovieQuality(self, param=None, version='1.0'):
        return self._cmd(
            method="setMovieQuality", param=param, version=version)

    def setSteadyMode(self, param=None, version='1.0'):
        return self._cmd(
            method="setSteadyMode", param=param, version=version)

    def setViewAngle(self, param=None, version='1.0'):
        return self._cmd(
            method="setViewAngle", param=param, version=version)

    def setSceneSelection(self, param=None, version='1.0'):
        return self._cmd(
            method="setSceneSelection", param=param, version=version)

    def setColorSetting(self, param=None, version='1.0'):
        return self._cmd(
            method="setColorSetting", param=param, version=version)

    def setIntervalTime(self, param=None, version='1.0'):
        return self._cmd(
            method="setIntervalTime", param=param, version=version)

    def setLoopRecTime(self, param=None, version='1.0'):
        return self._cmd(method="setLoopRecTime", param=param, version=version)

    def setFlipSetting(self, param=None, version='1.0'):
        return self._cmd(method="setFlipSetting", param=param, version=version)

    def setTvColorSystem(self, param=None, version='1.0'):
        return self._cmd(
            method="setTvColorSystem", param=param, version=version)

    def startRecMode(self):
        return self._cmd(method="startRecMode")

    def stopRecMode(self):
        return self._cmd(method="stopRecMode")

    def getCameraFunction(self, version='1.0'):
        return self._cmd(method="getCameraFunction", version=version)

    def getSupportedCameraFunction(self, version='1.0'):
        return self._cmd(method="getSupportedCameraFunction", version=version)

    def getAvailableCameraFunction(self, version='1.0'):
        return self._cmd(method="getAvailableCameraFunction", version=version)

    def getAudioRecording(self, version='1.0'):
        return self._cmd(method="getAudioRecording", version=version)

    def getSupportedAudioRecording(self, version='1.0'):
        return self._cmd(method="getSupportedAudioRecording", version=version)

    def getAvailableAudioRecording(self, version='1.0'):
        return self._cmd(method="getAvailableAudioRecording", version=version)

    def getWindNoiseReduction(self, version='1.0'):
        return self._cmd(method="getWindNoiseReduction", version=version)

    def getSupportedWindNoiseReduction(self, version='1.0'):
        return self._cmd(
            method="getSupportedWindNoiseReduction", version=version)

    def getAvailableWindNoiseReduction(self, version='1.0'):
        return self._cmd(
            method="getAvailableWindNoiseReduction", version=version)

    def setCameraFunction(self, param=None, version='1.0'):
        return self._cmd(
            method="setCameraFunction", param=param, version=version)

    def setAudioRecording(self, param=None, version='1.0'):
        return self._cmd(
            method="setAudioRecording", param=param, version=version)

    def setWindNoiseReduction(self, param=None, version='1.0'):
        return self._cmd(
            method="setWindNoiseReduction", param=param, version=version)

    def getSourceList(self, param=None, version='1.0'):
        return self._cmd(
            method="getSourceList", param=param,
            target="avContent", version=version)

    def getContentCount(self, param=None, version='1.0'):
        return self._cmd(
            method="getContentCount", param=param,
            target="avContent", version=version)

    def getContentList(self, param=None, version='1.0'):
        return self._cmd(
            method="getContentList", param=param,
            target="avContent", version=version)

    def setStreamingContent(self, param=None, version='1.0'):
        return self._cmd(
            method="setStreamingContent", param=param,
            target="avContent", version=version)

    def seekStreamingPosition(self, param=None, version='1.0'):
        return self._cmd(
            method="seekStreamingPosition", param=param,
            target="avContent", version=version)

    def requestToNotifyStreamingStatus(self, param=None, version='1.0'):
        return self._cmd(
            method="requestToNotifyStreamingStatus",
            param=param, target="avContent", version=version)

    def deleteContent(self, param=None, version='1.0'):
        return self._cmd(
            method="deleteContent", param=param,
            target="avContent", version=version)

    def setInfraredRemoteControl(self, param=None, version='1.0'):
        return self._cmd(
            method="setInfraredRemoteControl", param=param, version=version)

    def getEvent(self, param=None, version='1.0'):
        return self._cmd(method="getEvent", param=param, version=version)

    def getMethodTypes(self, param=None, target=None, version='1.0'):
        return self._cmd(
            method="getMethodTypes", param=param, target=None, version=version)

    def getShootMode(self, version='1.0'):
        return self._cmd(method="getShootMode", version=version)

    def getSupportedShootMode(self, version='1.0'):
        return self._cmd(method="getSupportedShootMode", version=version)

    def getAvailableShootMode(self, version='1.0'):
        return self._cmd(method="getAvailableShootMode", version=version)

    def actTakePicture(self, version='1.0'):
        return self._cmd(method="actTakePicture", version=version)

    def awaitTakePicture(self, version='1.0'):
        return self._cmd(method="awaitTakePicture", version=version)

    def startContShooting(self, version='1.0'):
        return self._cmd(method="startContShooting", version=version)

    def stopContShooting(self, version='1.0'):
        return self._cmd(method="stopContShooting", version=version)

    def startMovieRec(self, version='1.0'):
        return self._cmd(method="startMovieRec", version=version)

    def stopMovieRec(self, version='1.0'):
        return self._cmd(method="stopMovieRec", version=version)

    def startLoopRec(self, version='1.0'):
        return self._cmd(method="startLoopRec", version=version)

    def stopLoopRec(self, version='1.0'):
        return self._cmd(method="stopLoopRec", version=version)

    def startAudioRec(self, version='1.0'):
        return self._cmd(method="startAudioRec", version=version)

    def stopAudioRec(self, version='1.0'):
        return self._cmd(method="stopAudioRec", version=version)

    def startIntervalStillRec(self, version='1.0'):
        return self._cmd(method="startIntervalStillRec", version=version)

    def stopIntervalStillRec(self, version='1.0'):
        return self._cmd(method="stopIntervalStillRec", version=version)

    def startLiveview(self, version='1.0'):
        return self._cmd(method="startLiveview", version=version)

    def stopLiveview(self, version='1.0'):
        return self._cmd(method="stopLiveview", version=version)

    def getLiveviewSize(self, version='1.0'):
        return self._cmd(method="getLiveviewSize", version=version)

    def getSupportedLiveviewSize(self, version='1.0'):
        return self._cmd(method="getSupportedLiveviewSize", version=version)

    def getAvailableLiveviewSize(self, version='1.0'):
        return self._cmd(method="getAvailableLiveviewSize", version=version)

    def getLiveviewFrameInfo(self, version='1.0'):
        return self._cmd(method="getLiveviewFrameInfo", version=version)

    def getZoomSetting(self, version='1.0'):
        return self._cmd(method="getZoomSetting", version=version)

    def getSupportedZoomSetting(self, version='1.0'):
        return self._cmd(method="getSupportedZoomSetting", version=version)

    def getAvailableZoomSetting(self, version='1.0'):
        return self._cmd(method="getAvailableZoomSetting", version=version)

    def actHalfPressShutter(self, version='1.0'):
        return self._cmd(method="actHalfPressShutter", version=version)

    def cancelHalfPressShutter(self, version='1.0'):
        return self._cmd(method="cancelHalfPressShutter", version=version)

    def getTouchAFPosition(self, version='1.0'):
        return self._cmd(method="getTouchAFPosition", version=version)

    def cancelTouchAFPosition(self, version='1.0'):
        return self._cmd(method="cancelTouchAFPosition", version=version)

    def cancelTrackingFocus(self, version='1.0'):
        return self._cmd(method="cancelTrackingFocus", version=version)

    def getTrackingFocus(self, version='1.0'):
        return self._cmd(method="getTrackingFocus", version=version)

    def getSupportedTrackingFocus(self, version='1.0'):
        return self._cmd(method="getSupportedTrackingFocus", version=version)

    def getAvailableTrackingFocus(self, version='1.0'):
        return self._cmd(method="getAvailableTrackingFocus", version=version)

    def getContShootingMode(self, version='1.0'):
        return self._cmd(method="getContShootingMode", version=version)

    def getSupportedContShootingMode(self, version='1.0'):
        return self._cmd(
            method="getSupportedContShootingMode", version=version)

    def getAvailableContShootingMode(self, version='1.0'):
        return self._cmd(
            method="getAvailableContShootingMode", version=version)

    def getContShootingSpeed(self, version='1.0'):
        return self._cmd(method="getContShootingSpeed", version=version)

    def getSupportedContShootingSpeed(self, version='1.0'):
        return self._cmd(
            method="getSupportedContShootingSpeed", version=version)

    def getAvailableContShootingSpeed(self, version='1.0'):
        return self._cmd(
            method="getAvailableContShootingSpeed", version=version)

    def getSelfTimer(self, version='1.0'):
        return self._cmd(method="getSelfTimer", version=version)

    def getSupportedSelfTimer(self, version='1.0'):
        return self._cmd(method="getSupportedSelfTimer", version=version)

    def getAvailableSelfTimer(self, version='1.0'):
        return self._cmd(method="getAvailableSelfTimer", version=version)

    def getExposureMode(self, version='1.0'):
        return self._cmd(method="getExposureMode", version=version)

    def getSupportedExposureMode(self, version='1.0'):
        return self._cmd(method="getSupportedExposureMode", version=version)

    def getAvailableExposureMode(self, version='1.0'):
        return self._cmd(method="getAvailableExposureMode", version=version)

    def getFocusMode(self, version='1.0'):
        return self._cmd(method="getFocusMode", version=version)

    def getSupportedFocusMode(self, version='1.0'):
        return self._cmd(method="getSupportedFocusMode", version=version)

    def getAvailableFocusMode(self, version='1.0'):
        return self._cmd(method="getAvailableFocusMode", version=version)

    def getExposureCompensation(self, version='1.0'):
        return self._cmd(method="getExposureCompensation", version=version)

    def getSupportedExposureCompensation(self, version='1.0'):
        return self._cmd(
            method="getSupportedExposureCompensation", version=version)

    def getAvailableExposureCompensation(self, version='1.0'):
        return self._cmd(
            method="getAvailableExposureCompensation", version=version)

    def getFNumber(self, version='1.0'):
        return self._cmd(method="getFNumber", version=version)

    def getSupportedFNumber(self, version='1.0'):
        return self._cmd(method="getSupportedFNumber", version=version)

    def getAvailableFNumber(self, version='1.0'):
        return self._cmd(method="getAvailableFNumber", version=version)

    def getShutterSpeed(self, version='1.0'):
        return self._cmd(method="getShutterSpeed", version=version)

    def getSupportedShutterSpeed(self, version='1.0'):
        return self._cmd(method="getSupportedShutterSpeed", version=version)

    def getAvailableShutterSpeed(self, version='1.0'):
        return self._cmd(method="getAvailableShutterSpeed", version=version)

    def getIsoSpeedRate(self, version='1.0'):
        return self._cmd(method="getIsoSpeedRate", version=version)

    def getSupportedIsoSpeedRate(self, version='1.0'):
        return self._cmd(method="getSupportedIsoSpeedRate", version=version)

    def getAvailableIsoSpeedRate(self, version='1.0'):
        return self._cmd(method="getAvailableIsoSpeedRate", version=version)

    def getWhiteBalance(self, version='1.0'):
        return self._cmd(method="getWhiteBalance", version=version)

    def getSupportedWhiteBalance(self, version='1.0'):
        return self._cmd(method="getSupportedWhiteBalance", version=version)

    def getAvailableWhiteBalance(self, version='1.0'):
        return self._cmd(method="getAvailableWhiteBalance", version=version)

    def actWhiteBalanceOnePushCustom(self, version='1.0'):
        return self._cmd(
            method="actWhiteBalanceOnePushCustom", version=version)

    def getSupportedProgramShift(self, version='1.0'):
        return self._cmd(method="getSupportedProgramShift", version=version)

    def getFlashMode(self, version='1.0'):
        return self._cmd(method="getFlashMode", version=version)

    def getSupportedFlashMode(self, version='1.0'):
        return self._cmd(method="getSupportedFlashMode", version=version)

    def getAvailableFlashMode(self, version='1.0'):
        return self._cmd(method="getAvailableFlashMode", version=version)

    def getStillSize(self, version='1.0'):
        return self._cmd(method="getStillSize", version=version)

    def getSupportedStillSize(self, version='1.0'):
        return self._cmd(method="getSupportedStillSize", version=version)

    def getAvailableStillSize(self, version='1.0'):
        return self._cmd(method="getAvailableStillSize", version=version)

    def getStillQuality(self, version='1.0'):
        return self._cmd(method="getStillQuality", version=version)

    def getSupportedStillQuality(self, version='1.0'):
        return self._cmd(method="getSupportedStillQuality", version=version)

    def getAvailableStillQuality(self, version='1.0'):
        return self._cmd(method="getAvailableStillQuality", version=version)

    def getPostviewImageSize(self, version='1.0'):
        return self._cmd(method="getPostviewImageSize", version=version)

    def getSupportedPostviewImageSize(self, version='1.0'):
        return self._cmd(
            method="getSupportedPostviewImageSize", version=version)

    def getAvailablePostviewImageSize(self, version='1.0'):
        return self._cmd(
            method="getAvailablePostviewImageSize", version=version)

    def getMovieFileFormat(self, version='1.0'):
        return self._cmd(method="getMovieFileFormat", version=version)

    def getSupportedMovieFileFormat(self, version='1.0'):
        return self._cmd(method="getSupportedMovieFileFormat", version=version)

    def getAvailableMovieFileFormat(self, version='1.0'):
        return self._cmd(method="getAvailableMovieFileFormat", version=version)

    def getMovieQuality(self, version='1.0'):
        return self._cmd(method="getMovieQuality", version=version)

    def getSupportedMovieQuality(self, version='1.0'):
        return self._cmd(method="getSupportedMovieQuality", version=version)

    def getAvailableMovieQuality(self, version='1.0'):
        return self._cmd(method="getAvailableMovieQuality", version=version)

    def getSteadyMode(self, version='1.0'):
        return self._cmd(method="getSteadyMode", version=version)

    def getSupportedSteadyMode(self, version='1.0'):
        return self._cmd(method="getSupportedSteadyMode", version=version)

    def getAvailableSteadyMode(self, version='1.0'):
        return self._cmd(method="getAvailableSteadyMode", version=version)

    def getViewAngle(self, version='1.0'):
        return self._cmd(method="getViewAngle", version=version)

    def getSupportedViewAngle(self, version='1.0'):
        return self._cmd(method="getSupportedViewAngle", version=version)

    def getAvailableViewAngle(self, version='1.0'):
        return self._cmd(method="getAvailableViewAngle", version=version)

    def getSceneSelection(self, version='1.0'):
        return self._cmd(method="getSceneSelection", version=version)

    def getSupportedSceneSelection(self, version='1.0'):
        return self._cmd(method="getSupportedSceneSelection", version=version)

    def getAvailableSceneSelection(self, version='1.0'):
        return self._cmd(method="getAvailableSceneSelection", version=version)

    def getColorSetting(self, version='1.0'):
        return self._cmd(method="getColorSetting", version=version)

    def getSupportedColorSetting(self, version='1.0'):
        return self._cmd(method="getSupportedColorSetting", version=version)

    def getAvailableColorSetting(self, version='1.0'):
        return self._cmd(method="getAvailableColorSetting", version=version)

    def getIntervalTime(self, version='1.0'):
        return self._cmd(method="getIntervalTime", version=version)

    def getSupportedIntervalTime(self, version='1.0'):
        return self._cmd(method="getSupportedIntervalTime", version=version)

    def getAvailableIntervalTime(self, version='1.0'):
        return self._cmd(method="getAvailableIntervalTime", version=version)

    def getLoopRecTime(self, version='1.0'):
        return self._cmd(method="getLoopRecTime", version=version)

    def getSupportedLoopRecTime(self, version='1.0'):
        return self._cmd(method="getSupportedLoopRecTime", version=version)

    def getAvailableLoopRecTime(self, version='1.0'):
        return self._cmd(method="getAvailableLoopRecTime", version=version)

    def getFlipSetting(self, version='1.0'):
        return self._cmd(method="getFlipSetting", version=version)

    def getSupportedFlipSetting(self, version='1.0'):
        return self._cmd(method="getSupportedFlipSetting", version=version)

    def getAvailableFlipSetting(self, version='1.0'):
        return self._cmd(method="getAvailableFlipSetting", version=version)

    def getTvColorSystem(self, version='1.0'):
        return self._cmd(method="getTvColorSystem", version=version)

    def getSupportedTvColorSystem(self, version='1.0'):
        return self._cmd(method="getSupportedTvColorSystem", version=version)

    def getAvailableTvColorSystem(self, version='1.0'):
        return self._cmd(method="getAvailableTvColorSystem", version=version)

    def startStreaming(self, version='1.0'):
        return self._cmd(
            method="startStreaming", target="avContent", version=version)

    def pauseStreaming(self, version='1.0'):
        return self._cmd(
            method="pauseStreaming", target="avContent", version=version)

    def stopStreaming(self, version='1.0'):
        return self._cmd(
            method="stopStreaming", target="avContent", version=version)

    def getInfraredRemoteControl(self, version='1.0'):
        return self._cmd(method="getInfraredRemoteControl", version=version)

    def getSupportedInfraredRemoteControl(self, version='1.0'):
        return self._cmd(
            method="getSupportedInfraredRemoteControl", version=version)

    def getAvailableInfraredRemoteControl(self, version='1.0'):
        return self._cmd(
            method="getAvailableInfraredRemoteControl", version=version)

    def getAutoPowerOff(self, version='1.0'):
        return self._cmd(method="getAutoPowerOff", version=version)

    def getSupportedAutoPowerOff(self, version='1.0'):
        return self._cmd(method="getSupportedAutoPowerOff", version=version)

    def getAvailableAutoPowerOff(self, version='1.0'):
        return self._cmd(method="getAvailableAutoPowerOff", version=version)

    def getBeepMode(self, version='1.0'):
        return self._cmd(method="getBeepMode", version=version)

    def getSupportedBeepMode(self, version='1.0'):
        return self._cmd(method="getSupportedBeepMode", version=version)

    def getAvailableBeepMode(self, version='1.0'):
        return self._cmd(method="getAvailableBeepMode", version=version)

    def getSchemeList(self, version='1.0'):
        return self._cmd(
            method="getSchemeList", target="avContent", version=version)

    def getStorageInformation(self, version='1.0'):
        return self._cmd(method="getStorageInformation", version=version)

    def actFormatStorage(self, version='1.0'):
        return self._cmd(method="actFormatStorage", version=version)

    def getAvailableApiList(self, version='1.0'):
        return self._cmd(method="getAvailableApiList", version=version)

    def getApplicationInfo(self, version='1.0'):
        return self._cmd(method="getApplicationInfo", version=version)

    def getVersions(self, target=None, version='1.0'):
        return self._cmd(method="getVersions", target=target, version=version)
