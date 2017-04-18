#!/usr/bin/env python

"""
Kindle VNC Server 1.0
(c) 2016 Jerzy Glowacki
Apache 2.0 License
"""

import PIL.Image
import http.server
import socketserver
import socket
import io
import os
import sys
import time
try:
    import PIL.ImageGrab
    import PIL.ImageDraw
    import AppKit
except ImportError:
    # import pyscreenshot as PIL.ImageGrab
    PIL.ImageGrab = None
    pass

HOST = [(s.connect(('8.8.8.8', 53)), s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 5900
ROTATE = True
GRAYSCALE = True
BB = (0, 0, 700, 600)
SCR_WIDTH = 1280
SCR_HEIGHT = 1024
TIMING = False

lastimg = None
class VNCServer(http.server.SimpleHTTPRequestHandler):
    def getFrame(self):
        t0 = time.time()
        global lastimg
        if PIL.ImageGrab == None:
            screen = open("/dev/fb0", "rb")
        img = None
        unchanged = 0
        t1 = time.time()
        while img == None:
            if PIL.ImageGrab == None:
                screen.seek(0)
                data = screen.read(SCR_WIDTH * SCR_HEIGHT * 4)
                img = PIL.Image.frombuffer("RGBX", (SCR_WIDTH, SCR_HEIGHT), data, "raw", "RGBX", 0, 1)
                img = img.crop(BB)
                b, g, r, a = img.split() # reorder the colors
                img = PIL.Image.merge("RGB", (r, g, b))
            else:
                img = PIL.ImageGrab.grab(BB)
                #x, y = win32gui.GetCursorPos(point)
                pos = AppKit.NSEvent.mouseLocation()
                x = pos.x
                y = AppKit.NSScreen.mainScreen().frame().size.height - pos.y
                draw = PIL.ImageDraw.Draw(img)
                SIZE = 2
                draw.arc((x - SIZE, y - SIZE, x + SIZE, y + SIZE), start=0, end=360, fill="white")
                draw.arc((x - SIZE * 0.6, y - SIZE * 0.6, x + SIZE * 0.6, y + SIZE * 0.6), start=0, end=360, fill="black")
                del draw
            if GRAYSCALE:
                img = img.convert("L")
                #img = img.convert("P", palette="ADAPTIVE", colors=2)
            else: # PNG wants RBG mode color
                img = img.convert("RGB")
            if ROTATE:
                img = img.transpose(PIL.Image.ROTATE_90)
            if img.tobytes() == lastimg:
                img = None
                time.sleep(0.05)
                unchanged += 1
        lastimg = img.tobytes()
        t2 = time.time()
        png = io.BytesIO()
        img.save(png, format="png", compress_level=1)
        t3 = time.time()
        if TIMING:
            print("getFrame", t1 - t0, t2 - t1, t3 - t2)
        return png

    def do_GET(self):
        self.path = self.path.split('?')[0]
        if self.path == '/frame.png':
            t0 = time.time()
            frame = self.getFrame()
            t1 = time.time()
            self.send_response(200)
            self.send_header('Content-Type', 'image/png')
            self.end_headers()
            t2 = time.time()
            frame.seek(0)
            self.wfile.write(frame.read())
            frame.close()
            t3 = time.time()
            if TIMING:
                print("do_GET", t1 - t0, t2 - t1, t3 - t2)
        elif self.path == "/":
            http.server.SimpleHTTPRequestHandler.do_GET(self)
        else:
            self.send_response(404)

if __name__ == '__main__':
    httpd = socketserver.TCPServer((HOST, PORT), VNCServer)
    httpd.allow_reuse_address = True
    print('Kindle VNC Server started at http://%s:%s' % (HOST, PORT))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
       pass
    httpd.server_close()
    print('Server stopped')
