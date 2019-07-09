from __future__ import print_function

from pysony import SonyAPI, ControlPoint
from struct import unpack
import argparse
import time
import io
import pygame
import os
import six

# Global Variables
options  = None
incoming_image = None
done = False

# =====================================================================
import datetime

class rate_eval:
   def __init__(self, max_depth = None):
      if max_depth == None:
         self.max_depth = 10
      else:
         self.max_depth = max_depth
      self.depth = 0
      self.camera_total = 0
      self.display_total = 0
      self.samples = []

   def add(self, camera_timestamp = None, display_timestamp = None):
      if camera_timestamp == None:
         return
      if display_timestamp == None:
         now = datetime.datetime.now()
         display_timestamp = (now.second * 1000) + (now.microsecond / 1000)

      # special case for first data point
      if self.depth == 0:
         self.last_camera_timestamp = camera_timestamp
         self.last_display_timestamp = display_timestamp

      camera_delta = camera_timestamp - self.last_camera_timestamp
      display_delta = display_timestamp - self.last_display_timestamp

      # Rollover
      if camera_delta < 0:
         camera_delta += (1 << 32) - 1
      if display_delta < 0:
         display_delta += 1000

      self.last_camera_timestamp = camera_timestamp
      self.last_display_timestamp = display_timestamp
      self.camera_total += camera_delta
      self.display_total += display_delta

      # FIFO
      self.samples.append((camera_delta, display_delta))
      if self.depth >= self.max_depth:
         self.camera_total -= self.samples[0][0]
         self.display_total -= self.samples[0][1]
         del self.samples[0]
      else:
         self.depth += 1

   def too_slow(self, camera_timestamp = None, display_timestamp = None):
      if camera_timestamp:
         self.add(camera_timestamp, display_timestamp)

      if self.camera_total < self.display_total:
         return True
      else:
         return False

# =====================================================================

parser = argparse.ArgumentParser(prog="pygameLiveView")

# General Options
parser.set_defaults(debug=None, file=None, width=None, height=None)
parser.add_argument("-l", "--large", action="store_true", dest="large", help="Use HighRes liveview (if available)" )
parser.add_argument("-i", "--info", action="store_true", dest="info", help="Enable LiveFrameInfo (if available)" )
parser.add_argument("-z", "--zoom", action="store_true", dest="zoom", help="Zoom image to fill screen" )
parser.add_argument("-s", "--skip", action="store_true", dest="skip", help="Skip frames if computer too slow" )

options = parser.parse_args()

# Connect and set-up camera
search = ControlPoint()
cameras =  search.discover()

if len(cameras):
   camera = SonyAPI(QX_ADDR=cameras[0])
else:
   print("No camera found, aborting")
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
      url = camera.liveview(["L"])
   else:
      url = camera.liveview()
else:
   url = camera.liveview()

lst = SonyAPI.LiveviewStreamThread(url)
lst.start()

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
         print('Driver: {0} failed.'.format(driver))
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

if options.skip:
    rate = rate_eval()

while not done:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            done = True
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                done = True

    # check for header, confirms image is also ready to read
    header = lst.get_header()

    if header:
       # only interested in timestamp so unpack ourselves
       # could use 'common_header()' if need be
       time_stamp = unpack('>I', header[4:8])[0]

       # Check display rate is better than capture rate
       # only really needed on slow computers (ie. Raspberry Pi)
       if options.skip and rate.too_slow(time_stamp):
          lst.get_latest_view()
          continue

       image_file = io.BytesIO(lst.get_latest_view())
       incoming_image = pygame.image.load(image_file).convert()

       if options.zoom:
          incoming_image = pygame.transform.scale(incoming_image, \
             (infoObject.current_w, infoObject.current_h))

    # copy image to the display
    if incoming_image:
       (origin_x, origin_y, width, height) = incoming_image.get_rect()

       if options.info:
          frame_info = lst.get_frameinfo()

          if frame_info:
             screen.blit(incoming_image,(0,0))

             for x in range(len(frame_info)):
                left = frame_info[x]['left'] * width / 10000
                top = frame_info[x]['top'] * height / 10000
                right = frame_info[x]['right'] * width / 10000
                bottom = frame_info[x]['bottom'] * height / 10000

                category = frame_info[x]['category']
                status = frame_info[x]['status']

                if category == 1: # Constrast AF
                   # Brackets
                   pygame.draw.lines(screen, 0x00ff00, False, \
                      [(left + 10, top), (left, top), (left, bottom), (left + 10, bottom)], 2)
                   pygame.draw.lines(screen, 0x00ff00, False, \
                      [(right - 10, top), (right, top), (right, bottom), (right - 10, bottom)], 2)
                elif category == 4: # face
                   # Square
                   if status == 2:
                      color = 0xffffff
                   elif status == 3:
                      color = 0x808080
                   else:
                      color = 0x00ff00
                   pygame.draw.lines(screen, color, True, \
                      [(left, top), (right, top), (right, bottom), (left, bottom)], 2)
                elif category == 5: # Tracking
                   # Triangle Corners
                   pygame.draw.lines(screen, 0x00ff00, True, \
                      [(left + 10, top), (left, top), (left, top + 10)], 2)
                   pygame.draw.lines(screen, 0x00ff00, True, \
                      [(right - 10, top), (right, top), (right, top + 10)], 2)
                   pygame.draw.lines(screen, 0x00ff00, True, \
                      [(left + 10, bottom), (left, bottom), (left, bottom - 10)], 2)
                   pygame.draw.lines(screen, 0x00ff00, True, \
                      [(right - 10, bottom), (right, bottom), (right, bottom - 10)], 2)
                else:
                   # Corners
                   pygame.draw.lines(screen, 0x00ff00, False, \
                      [(left + 10, top), (left, top), (left, top + 10)], 2)
                   pygame.draw.lines(screen, 0x00ff00, False, \
                      [(right - 10, top), (right, top), (right, top + 10)], 2)
                   pygame.draw.lines(screen, 0x00ff00, False, \
                      [(left + 10, bottom), (left, bottom), (left, bottom - 10)], 2)
                   pygame.draw.lines(screen, 0x00ff00, False, \
                      [(right - 10, bottom), (right, bottom), (right, bottom - 10)], 2)
          else:
             screen.blit(incoming_image,(0,0))
       elif header:
           # Only blit if it's a new image
           screen.blit(incoming_image,(0,0))

       pygame.display.update((origin_x, origin_y, width, height))

# clean up
pygame.quit()
