import threading
import unittest
from os import environ, path
from uuid import uuid1

from six.moves.urllib_parse import urlparse
from six.moves.BaseHTTPServer import HTTPServer

import pysony
from .utils.http import FileRequestHandler
from .utils.ssdp import SSDPServer

HERE = path.dirname(path.abspath(__file__))
DD_FILE = path.abspath(path.join(HERE, 'data/DSC-HX400V_dd.xml'))

LIVE_CAMERA = int(environ.get('TEST_LIVE_CAMERA', 0))


class TestDiscovery(unittest.TestCase):

    def setUp(self):
        if LIVE_CAMERA:
            multicast_ip = pysony.SSDP_ADDR
        else:
            multicast_ip = '224.0.0.111'
            self.ssdp_server = SSDPServer(multicast_ip)
            self.ssdp_server.register(
                manifestation=None,
                usn=uuid1().urn,
                st=pysony.SSDP_ST,
                location='http://127.0.0.1:64321/dd.xml',
            )
            FileRequestHandler.FILE = DD_FILE
            self.http = HTTPServer(('localhost', 64321), FileRequestHandler)
            threading.Thread(target=self.ssdp_server.run).start()
            threading.Thread(target=self.http.serve_forever).start()
        self.cp = pysony.ControlPoint(multicast_ip)

    def tearDown(self):
        self.cp.close()
        if not LIVE_CAMERA:
            self.ssdp_server.kill.set()
            self.http.shutdown()
            self.http.socket.close()

    def test_discover(self):
        result = self.cp.discover()
        assert result == ['http://192.168.122.1:8080']

    def test_ssdp_cycle(self):
        self.cp._send_ssdp(duration=1)
        responses = list(self.cp._listen_for_discover(duration=1))
        self.assertEqual(len(responses), 1)
        output = self.cp._parse_ssdp_response(responses[0])
        loc = urlparse(output['location'])
        if LIVE_CAMERA:
            assert loc.hostname == '192.168.122.1'
        else:
            assert loc.hostname == '127.0.0.1'
        assert loc.path.endswith('dd.xml')
        assert loc.port is not None
        assert output['st'] == pysony.SSDP_ST

    def test_parse_device_definition(self):
        with open(DD_FILE, 'rb') as fh:
            result = self.cp._parse_device_definition(fh)
        expected = {
            'camera': 'http://192.168.122.1:8080/sony',
            'accessControl': 'http://192.168.122.1:8080/sony',
            'guide': 'http://192.168.122.1:8080/sony',
        }
        assert result == expected
