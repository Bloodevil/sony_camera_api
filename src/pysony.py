# Echo client program
import socket
import threading
import time
import re
import json
from struct import unpack, unpack_from
import logging
import sys

if sys.version_info < (3, 0):
    from Queue import LifoQueue
    from urllib2 import urlopen
else:
    from queue import LifoQueue
    from urllib.request import urlopen

SSDP_ADDR = "239.255.255.250"  # The remote host
SSDP_PORT = 1900    # The same port as used by the server
SSDP_MX = 1
SSDP_ST = "urn:schemas-sony-com:service:ScalarWebAPI:1"
SSDP_TIMEOUT = 10000  #msec
PACKET_BUFFER_SIZE = 1024

logger = logging.getLogger('pysony')


# Find all available cameras using uPNP
# Improved with code from 'https://github.com/storborg/sonypy' under MIT license.

class ControlPoint(object):
    def __init__(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(0.1)
        # Set the socket to broadcast mode.
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL , 2)
        self.__udp_socket = sock

    def discover(self, duration=1):
        msg = '\r\n'.join(["M-SEARCH * HTTP/1.1",
                           "HOST: 239.255.255.250:1900",
                           "MAN: \"ssdp:discover\"",
                           "MX: " + str(duration),
                           "ST: " + SSDP_ST,
                           "USER-AGENT: pysony",
                           "",
                           ""])

        # Send the message.
        msg_bytes = bytearray(msg, 'utf8')
        self.__udp_socket.sendto(msg_bytes, (SSDP_ADDR, SSDP_PORT))

        # Get the responses.
        packets = self._listen_for_discover(duration)
        endpoints = []
        for host,addr,data in packets:
            resp = self._parse_ssdp_response(data)
            endpoint = self._read_device_definition(resp['location'])
            endpoints.append(endpoint)
        return endpoints

    def _listen_for_discover(self, duration):
        start = time.time()
        packets = {}  # {(host, port): data}
        while (time.time() < (start + duration)):
            try:
                data, (host, port) = self.__udp_socket.recvfrom(1024)
            except socket.timeout:
                break
        packets.setdefault((host, port), b'')
        packets[host, port] += data
        return [(host, port, data) for (host, post), data in packets.items()]

    def _parse_ssdp_response(self, data):
        data_str = data.decode('utf8')
        lines = data_str.split('\r\n')
        assert lines[0] == 'HTTP/1.1 200 OK'
        headers = {}
        for line in lines[1:]:
            if line:
                try:
                    key, val = line.split(': ', 1)
                    headers[key.lower()] = val
                except:
                    logger.debug("Cannot parse SSDP response for this line: %s", line)
                    pass
        return headers

    def _parse_device_definition(self, doc):
        """
        Parse the XML device definition file.
        """
        dd_regex = ('<av:X_ScalarWebAPI_Service>'
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

        doc_str = doc.decode('utf8')
        services = {}
        for m in re.findall(dd_regex, doc_str):
            service_name = m[0]
            endpoint = m[1]
            services[service_name] = endpoint
        return services

    def _read_device_definition(self, url):
        """
        Fetch and parse the device definition, and extract the URL endpoint for
        the camera API service.
        """
        r = urlopen(url)
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


def common_header(data):
    start_byte,payload_type,sequence_number,time_stamp = unpack('!BBHI', data)
    if start_byte != 255: # 0xff fixed
        raise RuntimeError('[error] wrong QX livestream start byte')

    common_header = {'start_byte': start_byte,
                    'payload_type': payload_type,
                    'sequence_number': sequence_number,
                    'time_stamp': time_stamp, #milliseconds
                    }
    return common_header

def payload_header(data, payload_type=1):
    # payload_type = 1, assume JPEG
    start_code,jpeg_data_size_2,jpeg_data_size_1,jpeg_data_size_0,padding_size = unpack_from('!IBBBB',data)
    if start_code != 607479929:
        raise RuntimeError('[error] wrong QX payload header start')

    # This seems silly, but it's a 3-byte-integer !
    jpeg_data_size = jpeg_data_size_0 * 2**0 + jpeg_data_size_1 * 2**8 + jpeg_data_size_2 * 2**16

    if jpeg_data_size > 100000:
        logger.debug("Possibly wrong image size (%s)?", jpeg_data_size)

    payload_header = {
        'start_code': start_code,
        'jpeg_data_size': jpeg_data_size,
        'padding_size': padding_size,
    }

    if payload_type == 1:
        payload_header.update(payload_header_jpeg(data))
    elif payload_type == 2:
        payload_header.update(payload_header_frameinfo(data))
    else:
        raise RuntimeError('Unknown payload type: {}'.format(payload_type))

    return payload_header

def payload_header_jpeg(data):
    reserved_1, flag = unpack_from('!IB', data, offset=8)
    if flag != 0:
        raise RuntimeError('Wrong QX payload header flag: {}'.format(flag))

    payload_header = {
        'reserved_1': reserved_1,
        'flag': flag
    }
    return payload_header

def payload_header_frameinfo(data):
    version, frame_count, frame_size = unpack_from('!HHH', data, offset=8)
    payload_header = {
        'version': version,
        'frame_count': frame_count,
        'frame_size': frame_size
    }
    return payload_header

def payload_frameinfo(data):
    left, top, right, bottom = unpack_from(">HHHH", data)
    category, status, additional = unpack_from("BBB", data, offset=8)
    payload_frameinfo = {
        'left': left,
        'top': top,
        'right': right,
        'bottom': bottom,
        'category': category,
        'status': status,
        'additional': additional
    }
    return payload_frameinfo


class SonyAPI():
    def __init__(self, QX_ADDR='http://10.0.0.1:10000', params=None, debug=None, maxversion=None):
        self.QX_ADDR = QX_ADDR
        if not params:
            self.params = {
                "method": "",
                "params": [],
                "id": 1,  # move to setting
                "version": "1.0"
            }
        else:
            self.params = params
        if not debug:
            self.debug = False
        else:
            self.debug = debug
        self.camera_api_list = None

        if not maxversion:
            self.maxversion = '1.4' # will need to be updated when new API is released
        else:
            self.maxversion = maxversion

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

    def _access(self, method=None, param=[]):
        true = True
        false = False
        null = None

        if method:
            self.params["method"] = method
        if param:
            self.params["params"] = param
        else:
            self.params["params"] = []

        try:
            result = eval(urllib2.urlopen(self.QX_ADDR + "/sony/accessControl", json.dumps(self.params)).read())
        except Exception as e:
            result = "[ERROR] camera doesn't work" + str(e)
        return result

    def actEnableMethods(self, param=None):
        if not param:
            print ("""[ERROR] please enter the param like below""")
        return self._access(method="actEnableMethods", param=param)

    def _cmd(self, method=None, param=[], target=None):
        true = True
        false = False
        null = None

        if self.maxversion < minversion:
            raise ValueError("Method %s with 'minversion' %s exceeds user supplied 'maxversion' %s", method, minversion, self.maxversion)
        
        if version < minversion:
            version = minversion
        if version > self.maxversion:
            version = self.maxversion
        self.params["version"] = version

        if method:
            self.params["method"] = method
        if param:
            self.params["params"] = self._truefalse(param)
        else:
            self.params["params"] = []

        if target:
            url = self.QX_ADDR + "/sony/" + target
        else:
            url = self.QX_ADDR + "/sony/camera"
        json_dump = json.dumps(self.params)
        json_dump_bytes = bytearray(json_dump, 'utf8')
        read = urlopen(url, json_dump_bytes).read()
        result = eval(read)

        if method in ["getAvailableApiList"]:
            self.camera_api_list = result["result"][0]
        return result

    # Reading from the streaming data is a part of sony apis
    class LiveviewStreamThread(threading.Thread):
        def __init__(self, url):
            # Direct class call `threading.Thread` instead of `super()` for python2 capability
            threading.Thread.__init__(self)
            self.lv_url = url
            self._lilo_head_pool = LifoQueue()
            self._lilo_jpeg_pool = LifoQueue()

            self.header = None
            self.frameinfo = []

        def run(self):
            sess = urlopen(self.lv_url)

            while True:
                header = sess.read(8)
                ch = common_header(header)

                data = sess.read(128)
                payload = payload_header(data, payload_type=ch['payload_type'])

                if ch['payload_type'] == 1:
                    data_img = sess.read(payload['jpeg_data_size'])
                    assert len(data_img) == payload['jpeg_data_size']

                    self._lilo_head_pool.put(header)
                    self._lilo_jpeg_pool.put(data_img)

                elif ch['payload_type'] == 2:
                    self.frameinfo = []

                    for x in range(payload['frame_count']):
                        data_img = sess.read(payload['frame_size'])
                        self.frameinfo.append(payload_frameinfo(data_img))

                sess.read(payload['padding_size'])

        def get_header(self):
            if not self.header:
                try:
                    self.header = self._lilo_head_pool.get_nowait()
                except Exception as e:
                    self.header = None
            return self.header

        def get_latest_view(self):
            # note this is a blocking call
            data_img = self._lilo_jpeg_pool.get()

            # retrive next header
            try:
                self.header = self._lilo_head_pool.get_nowait()
            except Exception as e:
                self.header = None

            return data_img

        def get_frameinfo(self):
            return self.frameinfo

    def liveview(self, param=None, version='1.0'):
        if param:
            liveview = self._cmd(method="startLiveviewWithSize", param=param, version=version)
        else:
            liveview = self._cmd(method="startLiveview", version=version)
        if isinstance(liveview, dict):
            try:
                url = liveview['result'][0].replace('\\', '')
                result = url
            except:
                # Sometimes `liveview` just return json without `result` field (maybe an `error` field instead)
                logger.error("Starting liveview returned unkown results: %s", liveview)
                raise
        else:
            logger.debug("Starting liveview did not returned a dict type: %s", liveview)
            result = liveview
        return result

    def setShootMode(self, param=None, version='1.0'):
        if not param:
            logger.info("""[ERROR] please enter the param like below
            "still"            Still image shoot mode
            "movie"            Movie shoot mode
            "audio"            Audio shoot mode
            "intervalstill"    Interval still shoot mode
            e.g) In[26]:  camera.setShootMode(param=['still'])
                 Out[26]: {'id': 1, 'result': [0]}
            """)
        return self._cmd(method="setShootMode", param=param, version=version)

    def startLiveviewWithSize(self, param=None, version='1.0'):
        if not param:
            logger.info("""[ERROR] please enter the param like below
        "L"     XGA size scale (the size varies depending on the camera models,
                and some camera models change the liveview quality instead of
                making the size larger.)
        "M"     VGA size scale (the size varies depending on the camera models)
        """)

        return self._cmd(method="startLiveviewWithSize", param=param, version=version)

    def setLiveviewFrameInfo(self, param=None, version='1.0'):
        if not param:
            logger.info("""
        "frameInfo"
                true - Transfer the liveview frame information
                false - Not transfer
        e.g) SonyAPI.setLiveviewFrameInfo(param=[{"frameInfo": True}])
        """)
        return self._cmd(method="setLiveviewFrameInfo", param=param, version=version)

    def actZoom(self, param=None, version='1.0'):
        if not param:
            logger.info(""" ["direction", "movement"]
            direction
                "in"        Zoom-In
                "out"       Zoom-Out
            movement
                "start"     Long push
                "stop"      Stop
                "1shot"     Short push
            e.g) SonyAPI.actZoom(param=["in", "start"])
            """)
        return self._cmd(method="actZoom", param=param, version=version)

    def setZoomSetting(self, param=None, version='1.0'):
        if not param:
            logger.info("""
            "zoom"
                "Optical Zoom Only"                Optical zoom only.
                "On:Clear Image Zoom"              On:Clear Image Zoom.
            e.g) SonyAPI.setZoomSetting(param=[{"zoom": "Optical Zoom Only"}])
            """)
        return self._cmd(method="setZoomSetting", param=param)

    def setLiveviewSize(self, param=None, version='1.0'):
        return self._cmd(method="setLiveviewSize", param=param, version=version)

    def setTouchAFPosition(self, param=None, version='1.0'):
        if not param:
            logger.info(""" [ X-axis position, Y-axis position]
                X-axis position     Double
                Y-axis position     Double
            e.g) SonyAPI.setTouchAFPosition(param=[ 23.2, 45.2 ])
            """)
        return self._cmd(method="setTouchAFPosition", param=param, version=version)

    def actTrackingFocus(self, param=None, version='1.0'):
        if not param:
            logger.info("""
                "xPosition"     double                X-axis position
                "yPosition"     double                Y-axis position
            e.g) SonyAPI.actTrackingFocus(param={"xPosition":23.2, "yPosition": 45.2})
            """)
        return self._cmd(method="actTrackingFocus", param=param, version=version)

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

    def startRecMode(self, version='1.0'):
        return self._cmd(method="startRecMode", version=version)

    def stopRecMode(self, version='1.0'):
        return self._cmd(method="stopRecMode", version=version)

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

    def getContentCount(self, param=None, version='1.2'):
        return self._cmd(
            method="getContentCount", param=param,
            target="avContent", version=version, minversion='1.2')

    def getContentList(self, param=None, version='1.3'):
        return self._cmd(
            method="getContentList", param=param,
            target="avContent", version=version, minversion='1.3')

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

    def deleteContent(self, param=None, version='1.1'):
        return self._cmd(
            method="deleteContent", param=param,
            target="avContent", version=version, minversion='1.1')

    def setInfraredRemoteControl(self, param=None, version='1.0'):
        return self._cmd(
            method="setInfraredRemoteControl", param=param, version=version)

    def getEvent(self, param=None, version='1.3'):
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
