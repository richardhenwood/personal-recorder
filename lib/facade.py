#This file is part of Skype-record.
#
#Foobar is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#Foobar is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with skype-record.  If not, see <http://www.gnu.org/licenses/>.
#
# copyright 2011, Richard Henwood <rjhenwood@yahoo.co.uk>

import Xlib
import Xlib.display
import Xlib.Xatom
import threading
import gobject, gtk, wnck
#import pygtk
import time 
import os
import sys
import signal
import subprocess as sub

class Skype(threading.Thread): 
    _instance = None

    # @todo: this should be a singleton class.
    def __init__(self, pid):
        threading.Thread.__init__(self)
        self.pid = pid
        self.callstart_listeners = []
        self.callend_listeners = []
        self.call_running = False
        self.call_window = None
        self.current_call = None

    def add_callstart_listener (self, func):
        ''' @todo: this should a list. '''
        self.callstart_listeners.append(func)

    def add_callend_listener (self, func):
        ''' @todo: this should a list. '''
        self.callend_listeners.append(func)

    def signal_call_start (self, call):
        for listener in self.callstart_listeners:
            listener(call)
        pass

    def signal_call_end (self):
        for listener in self.callend_listeners:
            listener()
        pass

    def get_audio (self):
        
        # current getting info relys on default sink monitor and source.:
        p = sub.Popen('pacmd info | grep \'Default sink name\'',shell=True,stdout=sub.PIPE,stderr=sub.PIPE)
        output, errors = p.communicate()
        output = output.rstrip()  # discard the end newline.
        theirvoice = output[19:] + '.monitor'
        p = sub.Popen('pacmd info | grep \'Default source name\'',shell=True,stdout=sub.PIPE,stderr=sub.PIPE)
        output, errors = p.communicate()
        output = output.rstrip()  # discard the end newline.
        yourvoice = output[21:] 
        return (yourvoice, theirvoice)

    def application_change (self, screen, stack):
        current_window = screen.get_active_window()
        if current_window is None:
            time.sleep(0.1)
            current_window = screen.get_active_window()
            if current_window is None:
                print '''cannot get current window. setting call_running = false.'''
                self.call_running = False
                return
        current_app = current_window.get_application()
        # hack to remove the L from the end of the xid after 'hex'ing it:q.
        current_xid = str(hex(current_window.get_xid()))[0:9]
        current_name = current_window.get_name()
        current_pid = current_app.get_pid()
        # skype returns PID 0 from this call.
        # Use a hack (drop back to xprop) to get he real PID.
        # source: http://stackoverflow.com/questions/2041532
        # @todo: re-write this whole program in c.
        #print "current pid = '%s'" % current_pid
        if current_pid == 0:
            current_pid = os.popen("xprop -id %s | awk '/_NET_WM_PID/ {print $NF}' " % current_xid).read()

        if int(current_pid) == int(self.pid) and \
                (self.call_running == False) and \
                ('Call' in current_name):
            yourAudio, theirAudio = self.get_audio()
            #print "audio = %s %s\n\n" % (yourAudio[0], theirAudio[0])
            #print  current_window
            print "pid = ", current_pid, " wid = ", current_xid, " name = ", current_name
            self.call_window = current_window
            self.call_running = True
            call = CallPeople(current_xid, theirAudio, None, yourAudio, current_name)
            self.current_call = call
            self.signal_call_start(call)

    def window_closed (self, current_screen, current_window):
        # this is a nasty hack to see if the call window is closed.
        # it seems gobject still throws an error in this case.
        if str(self.call_window) == str(current_window):
            print 'call window closed.'
            self.call_running = False
            self.signal_call_end()

    def run(self):
        screen = wnck.screen_get_default()
        screen.force_update()
        screen.connect("active_window_changed", self.application_change)
        screen.connect("window_closed", self.window_closed)
        gobject.MainLoop().run()


class CallPeople:
    def __init__(self, theirVideoXid, theirAudio, yourVideo, yourAudio, yourCaller):
        self.theirVideoXid = theirVideoXid
        self.theirAudio = theirAudio
        self.yourVideo = yourVideo
        self.yourAudio = yourAudio
        self.callWith = yourCaller
        return None
