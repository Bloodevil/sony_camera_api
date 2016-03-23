
from pysony import SonyAPI, ControlPoint, common_header, payload_header
import argparse
import struct
import time
import io
import pygame
import os

# Global Variables
options  = None
incoming_image = None
frame_sequence = None
frame_info = None
frame_data = None
done = False

parser = argparse.ArgumentParser(prog="pygameLiveView")

# General Options
parser.set_defaults(debug=None, file=None, width=None, height=None)
parser.add_argument("-l", "--large", action="store_true", dest="large", help="Use HighRes liveview (if available)" )
parser.add_argument("-i", "--info", action="store_true", dest="info", help="Enable LiveFrameInfo (if available)" )
parser.add_argument("-z", "--zoom", action="store_true", dest="zoom", help="Zoom image to fill screen" )

options = parser.parse_args()

# Connect and set-up camera
search = ControlPoint()
cameras =  search.discover()

if len(cameras):
   camera = SonyAPI(QX_ADDR=cameras[0])
else:
   print "No camera found, aborting"
   quit()

mode = camera.getAvailableApiList()

# For those cameras which need it
if 'startRecMode' in (mode['result'])[0]:
   camera.startRecMode()
   time.sleep(5)

   # and re-read capabilities
   mode = camera.getAvailableApiList()

if 'setLiveviewFrameInfo' in (mode['result'])[0]:
   if options.info:
      camera.setLiveviewFrameInfo([{"frameInfo": True}])
   else:
      camera.setLiveviewFrameInfo([{"frameInfo": False}])

if 'getAvailableLiveviewSize' in (mode['result'])[0]:
   if options.large and len((camera.getAvailableLiveviewSize()['result'])[0]) > 1:
      incoming = camera.liveview(["L"])
   else:
      incoming = camera.liveview()
else:
   incoming = camera.liveview()

# Use PyGame to display images full screen
disp_no = os.getenv("DISPLAY")
found = False
if disp_no:
   pygame.display.init()
   found = True
else:
   drivers = ['directfb', 'fbcon', 'svgalib', 'dga', 'ggi', 'vgl', 'aalib']

   for driver in drivers:
      if not os.getenv('SDL_VIDEODRIVER'):
         os.putenv('SDL_VIDEODRIVER', driver)
      try:
         pygame.display.init()
      except pygame.error:
         print 'Driver: {0} failed.'.format(driver)
         continue
      found = True
      break

if not found:
   raise Exception('No suitable video driver found!')

infoObject = pygame.display.Info()
screen = pygame.display.set_mode((infoObject.current_w, infoObject.current_h), \
        pygame.HWSURFACE)
screen.set_alpha(None)

# Loop forever, or until user quits or presses 'ESC' key
pygame.event.set_allowed([pygame.QUIT, pygame.KEYDOWN])
while not done:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            done = True
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                done = True

    # read next image
    data = incoming.read(8)
    common = common_header(data)
    data = incoming.read(128)

    if common['payload_type']==1:
       payload = payload_header(data)
       image_file = io.BytesIO(incoming.read(payload['jpeg_data_size']))
       incoming_image = pygame.image.load(image_file).convert()
       if options.zoom:
          incoming_image = pygame.transform.scale(incoming_image, \
             (infoObject.current_w, infoObject.current_h))
       incoming.read(payload['padding_size'])
    elif common['payload_type']==2:
       frame_info = payload_header(data, 2)
       if frame_info['jpeg_data_size']:
          frame_sequence = common['sequence_number']
          frame_data =  incoming.read(frame_info['jpeg_data_size'])
          incoming.read(frame_info['padding_size'])

    # copy image to the display
    if incoming_image:
       (origin_x, origin_y, width, height) = incoming_image.get_rect()
       screen.blit(incoming_image,(0,0))

       if frame_info and frame_sequence >= common['sequence_number']-1 \
             and frame_info['jpeg_data_size']:
          for x in range(frame_info['frame_count']):
             x = x * frame_info['frame_size']

             (left, top, right, bottom) = struct.unpack(">HHHH", frame_data[x:x+8])
             left = left * width / 10000
             top = top * height / 10000
             right = right * width / 10000
             bottom = bottom * height / 10000

             pygame.draw.lines(screen, 0xffffff, True, \
                [(left, top), (right, top), (right, bottom), (left, bottom)], 2)

       # pygame.display.flip()
       pygame.display.update((origin_x, origin_y, width, height))

# clean up
pygame.quit()
