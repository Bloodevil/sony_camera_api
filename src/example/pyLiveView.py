#!/usr/bin/env python

# Released under the GPL v2 (or later) by Simon Wood (simon@mungewell.org)
#
# Sample application to connect to camera, and start a video recording
# with or without a GUI LiveView screen

import signal
import threading
import datetime
import time
import argparse
from PIL import Image, ImageDraw
import io
from pysony import SonyAPI, common_header, payload_header
import binascii

# Hack for windows
import platform
from cStringIO import StringIO

try:
   import pygtk
   import gtk
   from gtk import gdk
   import cairo
   gtk.gdk.threads_init()
   _hasPyGTK = True
except ImportError:
   _hasPyGTK = False
'''
_hasPyGTK = False
'''

# Global Variables
options  = None
image_copy = None
image_file = None

display = None
grabber = None

# =====================================================================
class liveview_grabber(threading.Thread):
   def run(self):
      global options, grabber, decoder, display, image_copy

      if options.debug:
         print "using LiveView grabber"
   
      self.active = False
      self.photomode = False

      # grabber control signals
      self.event_start_stream = threading.Event()
      self.event_stop_stream = threading.Event()
      self.event_stopped_stream = threading.Event()
      self.event_terminate = threading.Event()
      self.event_terminated = threading.Event()

      # decoder control signals
      self.event_decoding = threading.Event()
      self.event_decoder_terminated = threading.Event()

      # display control signals
      self.lock_offscreen = threading.Semaphore()

      # export to other threads
      self.frame_count = 0
      grabber = self

      camera = SonyAPI()
      #camera = SonyAPI(QX_ADDR='http://192.168.122.1:8080/')

      # Check if we need to do 'startRecMode'
      mode = camera.getAvailableApiList()

      # Need a better method to check for the presence of a camera
      if type(mode) != dict:
         print "No camera found, aborting"
         display.terminate_clicked()
         self.event_terminated.set()
         return

      if options.debug:
         print "Versions:", camera.getVersions()
         print "API List:", mode

      # For those cameras which need it
      if 'startRecMode' in (mode['result'])[0]:
         camera.startRecMode()

      if 'setLiveviewFrameInfo' in (mode['result'])[0]:
         print "Checking frame info"
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

      incoming_image = None
      frame_sequence = None
      frame_info = None
      frame_data = None

      # Ensure that we're in correct mode (movie by default)
      mode = camera.getAvailableShootMode()
      if type(mode) == dict:
         if options.still:
            if (mode['result'])[0] != 'still':
               if 'still' in (mode['result'])[1]:
                  camera.setShootMode(["still"])
                  self.photomode = True
            else:
               self.photomode = True
         else:
            if (mode['result'])[0] != 'movie':
               if 'movie' in (mode['result'])[1]:
                  camera.setShootMode(["movie"])
               else:
                  self.photomode = True

      while not self.event_terminate.isSet():
         # Handle events from the camera (record start/stop)
         if self.frame_count % 50 == 0:
            mode = camera.getEvent(["false"])
         else:
            mode = None

         if mode and type(mode) == dict:
            status = mode['result'][1]
            if self.active == False and status['cameraStatus'] == 'MovieRecording':
               self.frame_count = 0
               self.start_time = datetime.datetime.now()
               self.active = True
               if options.debug:
                  print "started capture", self.start_time
            elif self.active == True and status['cameraStatus'] == 'IDLE':
               self.active = False
               self.end_time = datetime.datetime.now()
               if options.debug:
                  elapsed = self.end_time - self.start_time
                  print "Stopped capture: frames = ", self.frame_count,
                  print ", delta = ", elapsed.seconds + (float(elapsed.microseconds) / 1000000),
                  print ", fps = ", self.frame_count / (elapsed.seconds + (float(elapsed.microseconds) / 1000000))

         # read next image
         data = incoming.read(8)
         common = common_header(data)
         data = incoming.read(128)

         if common['payload_type']==1:
            payload = payload_header(data)
            image_file = io.BytesIO(incoming.read(payload['jpeg_data_size']))
            incoming_image = Image.open(image_file)
            incoming.read(payload['padding_size'])
         elif common['payload_type']==2:
            frame_info = payload_header(data, 2)
            if frame_info['jpeg_data_size']:
               frame_sequence = common['sequence_number']
               frame_data =  incoming.read(frame_info['jpeg_data_size'])
               incoming.read(frame_info['padding_size'])

         if options.gui == True :
            # Correct display size if changed
            if incoming_image and ((incoming_image.size)[0] != display.width):
               if options.debug:
                  print "adjusted width from", display.width, "to", (incoming_image.size)[0]
               display.width = (incoming_image.size)[0]
               display.offscreen = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, False, 8,
                  display.width, display.height)

            if incoming_image and ((incoming_image.size)[1] != display.height):
               if options.debug:
                  print "adjusted height from", display.height, "to", (incoming_image.size)[1]
               display.height = (incoming_image.size)[1]
               display.offscreen = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, False, 8,
                  display.width, display.height)

            # copy image to the display
            if incoming_image:
               image_copy = incoming_image.convert("RGB")

               # only recent frame info to image
               if frame_info and frame_sequence >= common['sequence_number']-1 \
                     and payload['jpeg_data_size']:
                  left = int(binascii.hexlify(frame_data[0:2]), 16) * display.width / 10000
                  top = int(binascii.hexlify(frame_data[2:4]), 16) * display.height / 10000
                  right = int(binascii.hexlify(frame_data[4:6]), 16) * display.width / 10000
                  bottom = int(binascii.hexlify(frame_data[6:8]), 16) * display.height / 10000

                  dr = ImageDraw.Draw(image_copy)
                  dr.line((left, top, left, bottom), fill="white", width=3)
                  dr.line((right, top, right, bottom), fill="white", width=3)
                  dr.line((left, top, right, top), fill="white", width=3)
                  dr.line((left, bottom, right, bottom), fill="white", width=3)

               display.copy_to_offscreen(image_copy)

         if options.debug:
            print "Frame:", common['sequence_number'], common['time_stemp'], datetime.datetime.now()

         # count frames
         self.frame_count = self.frame_count + 1

         # handle events
         if self.event_start_stream.isSet():
            if self.photomode == True:
               camera.actTakePicture()
            else:
               camera.startMovieRec()
            self.event_start_stream.clear()

         if self.event_stop_stream.isSet():
            camera.stopMovieRec()
            self.event_stop_stream.clear()

         # give OS a breather
         #time.sleep(0.01)

      # declare that we're done...
      self.event_terminated.set()
      self.event_terminate.clear()
            

   def start_stream(self):
      if self.active == False:
         self.event_start_stream.set()
         while self.event_start_stream.isSet():
            time.sleep(0.1)

         self.event_stopped_stream.clear()

   def stop_stream(self):
      if self.active == True:
         self.event_stop_stream.set()

         while self.event_stop_stream.isSet():
            time.sleep(0.1)

   def terminate(self):
      if options.debug:
         print "terminating..."

      if options.gui != True:
         self.stop_stream()
      self.event_terminate.set()

      while self.event_terminate.isSet():
         time.sleep(0.1)
 
      if options.debug:
         print "terminated"

# =====================================================================
class liveview_display:
   def copy_to_offscreen(self, image):
      global options, grabber, display

      # Convert a PIL Image to a gtk.gdk.Pixbuf  
      if (platform.system() == 'Linux'):
         file1 = io.BytesIO()
      else:
         file1 = StringIO()
      if (file1 != False):
         image.save(file1, "ppm")  
         contents = file1.getvalue()  

         loader = gtk.gdk.PixbufLoader("pnm")  
         loader.write(contents, len(contents))  
         pixbuf = loader.get_pixbuf()  
         loader.close() 

      file1.close()

      # copy Pixbuf to offscreen area/Pixbuf
      grabber.lock_offscreen.acquire()
      gtk.gdk.threads_enter()
      pixbuf.copy_area(0, 0, display.width, display.height, 
         self.offscreen, 0, 0)

      # Report status
      if grabber.active:
          display.bartext.set_text("Recording")
      else:
          display.bartext.set_text("")

      # Force an 'expose' event for screen
      display.expose_event(display.drawing_area, None)
      gtk.gdk.threads_leave()
      grabber.lock_offscreen.release()

      return True

   def expose_event(self, widget, event):
      global options, grabber, display

      gc = self.drawing_area.get_style().black_gc
      self.drawing_area.set_size_request(self.width, self.height)
      self.drawing_area.window.draw_pixbuf(gc, self.offscreen, 0, 0, 0, 0, width=-1, height=-1, 
         dither=gtk.gdk.RGB_DITHER_NORMAL, x_dither=0, y_dither=0)

   def button1_clicked(self, widget):
      global grabber

      gtk.gdk.threads_leave()
      grabber.start_stream()
      gtk.gdk.threads_enter()

   def button2_clicked(self, widget):
      global grabber

      gtk.gdk.threads_leave()
      grabber.stop_stream()
      gtk.gdk.threads_enter()

   def terminate_clicked(self, widget=None, event=None, data=None):
      global grabber

      if options.gui:
         gtk.gdk.threads_leave()

      grabber.terminate()

      if options.gui:
         gtk.gdk.threads_enter()
         gtk.main_quit()
      return False

   def __init__(self):
      global options, display, grabber, image_file

      # export to other threads
      display = self

      # define a default size
      self.width = 800
      self.height = 512

      if not options.gui:
         options.autostart = True
      else:
         gtk.gdk.threads_init()

         # create the main window, and attach delete_event signal to terminating
         # the application
         window = gtk.Window(gtk.WINDOW_TOPLEVEL)
         window.set_title("pyLiveView")
         window.set_resizable(0)
         window.connect("delete_event", self.terminate_clicked)
         window.set_border_width(10)

         # a vertical box to seperate screen and buttons
         vbox = gtk.VBox()
         vbox.show()

         # Drawable area on the screen
         self.drawing_area = gtk.DrawingArea()
         self.drawing_area.set_size_request(self.width, self.height)
         vbox.add(self.drawing_area)
         self.drawing_area.show()
         self.drawing_area.connect("expose_event", self.expose_event)

         # Off-screen Pixbuf for storing image
         self.offscreen = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, False, 8, 
            self.width, self.height)
         self.offscreen.fill(0x000000FF)

         # Text box to display status
         self.bartext = gtk.Label()
         self.bartext.set_single_line_mode(True)
         self.bartext.show()
         vbox.add(self.bartext)

         # a horizontal box to hold the buttons
         hbox = gtk.HBox()
         hbox.show()

         # Start and Stop buttons
         button1 = gtk.Button(label="Start")
         button1.show()
         hbox.pack_start(button1)
         button1.connect("clicked", self.button1_clicked)

         button2 = gtk.Button(label="Stop")
         button2.show()
         hbox.pack_start(button2)
         button2.connect("clicked", self.button2_clicked)

         vbox.add(hbox)

         # show GTK window
         window.add(vbox)
         window.show()

      # Attempt to find camera and use it
      grabber = liveview_grabber()
      grabber.start()

      if options.autostart or options.gui != True:
         time.sleep(1)
         grabber.start_stream()

# =====================================================================
def Run():
   global options, display

   parser = argparse.ArgumentParser(prog="pyLiveView")

   # General Options
   parser.set_defaults(debug=None, file=None, width=None, height=None)
   parser.add_argument("-d", "--debug", action="store_true", dest="debug", help="Display additional debug information" )
   parser.add_argument("-l", "--large", action="store_true", dest="large", help="Use HighRes liveview (if available)" )
   parser.add_argument("-s", "--still", action="store_true", dest="still", help="Still photo mode" )
   parser.add_argument("-i", "--info", action="store_true", dest="info", help="Enable LiveFrameInfo" )

   # Gui related
   parser.set_defaults(gui=None, autostart=None)
   if _hasPyGTK:
      parser.add_argument("-g", "--gui", action="store_true", dest="gui", default=None,
              help="Display LiveView images using pyGTK GUI" )
      parser.add_argument("-a", "--autostart", action="store_true", dest="autostart", default=None,
              help="Automatically start capturing video (default if no GUI)" )

   options = parser.parse_args()

   display = liveview_display()

   # capture Control C to close application
   signal.signal(signal.SIGINT, display.terminate_clicked)

   if options.gui:
      gtk.gdk.threads_enter()
      gtk.main()
      gtk.gdk.threads_leave()
   else:
      while not grabber.event_terminated.isSet():
         time.sleep(.1)

if __name__ == '__main__':
   Run()
