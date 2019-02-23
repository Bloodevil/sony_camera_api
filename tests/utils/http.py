import logging

from six.moves.BaseHTTPServer import BaseHTTPRequestHandler

log = logging.getLogger(__name__)


class FileRequestHandler(BaseHTTPRequestHandler):

    FILE = None

    def log_message(self, fmt, *args):
        # Overriding the default version of this
        # that prints to stderr so that test runs
        # are less noisy.
        log.info(fmt.format(*args))

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        with open(self.FILE, 'rb') as fh:
            self.wfile.write(fh.read())
