# Echo client program
import socket
import sys
import xml
import time

SSDP_ADDR = "239.255.255.250"  # The remote host
SSDP_PORT = 1900	# The same port as used by the server
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

QX_ADDR = 'http://10.0.0.1:10000'

def truefalse(param):
	params = []
	for x in param:
		if x.lower() == 'true':
			params.append(True)
		elif x.lower() == 'false':
			params.append(False)
		else:
			params.append(x)
	return params

def sony_api(method=None, param=[]):
	true = True
	false = False
	null = None

	# [TODO] discover camera.
	params = collections.OrderedDict([
			("method", "getAvailableApiList"),
			("params", []),
			("id", 1),
			("version", "1.0")])
	if method:
		params["method"] = method
	if param:
		params["params"] = truefalse(param)

	return eval(urllib2.urlopen(QX_ADDR + "/sony/camera", json.dumps(params)).read())

