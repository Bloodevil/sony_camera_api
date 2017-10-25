import queue
import threading

import pysony
from comp_urllib import urlopen


class LiveviewProcessThread(threading.Thread):
    def __init__(self, url):
        super().__init__()
        self.lv_url = url
        self.lilo_jpeg_pool = queue.LifoQueue()

    def run(self):
        sess = urlopen(self.lv_url)

        while True:
            try:
                data = sess.read(8)
                ch = pysony.common_header(data)
                #print(ch)

                data = sess.read(128)
                payload = pysony.payload_header(data, payload_type=ch['payload_type'])
                #print(payload)
            except RuntimeError as e:
                print("[ERROR]" + str(e))

            try:
                data_img = sess.read(payload['jpeg_data_size'])
                assert len(data_img) == payload['jpeg_data_size']
                #print('[i] one image ready')
                self.lilo_jpeg_pool.put(data_img)

                sess.read(payload['padding_size'])
            except Exception as e:
                print("[ERROR]" + str(e))

    def get_latest_view(self):
        return self.lilo_jpeg_pool.get()
