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
import pygtk
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
        self.recordstart_listeners = []
        self.recordstop_listeners = []
        self.call_running = False
        self.call_window = None
        self.gui = False

    def add_callstart_listener (self, func):
        ''' @todo: this should a list. '''
        self.callstart_listeners.append(func)

    def add_callend_listener (self, func):
        ''' @todo: this should a list. '''
        self.callend_listeners.append(func)

    def add_recordstart_listener (self, func):
        ''' @todo: this should a list. '''
        self.recordstart_listeners.append(func)

    def add_recordstop_listener (self, func):
        ''' @todo: this should a list. '''
        self.recordstop_listeners.append(func)


    def signal_call_start (self, call):
        for listener in self.callstart_listeners:
            listener(call)
        if not self.gui:
            self.gui = True
            gui = RecordControlGui(self) 
            gui.main()
        pass

    def signal_call_end (self):
        for listener in self.callend_listeners:
            listener(call)
        pass

    def signal_record_start(self):
        for listener in self.recordstart_listeners:
            listener(call)
        pass

    def signal_record_stop(self):
        for listener in self.recordstop_listeners:
            listener(call)
        pass

    def get_audio (self):
        ################################################
        # this is a initial attempt at getting this info:
        #p = sub.Popen('pacmd list-source-outputs | grep source: | head -1 | awk \'{print $NF}\'',shell=True,stdout=sub.PIPE,stderr=sub.PIPE)
        #output, errors = p.communicate()
        #output = output.rstrip()  # discard the end newline.
        #devices = [output[1:-1]]
        #p = sub.Popen('pacmd list-sources | grep card: | uniq | awk \'{print $NF}\'', shell=True, stdout=sub.PIPE, stderr=sub.PIPE)
        #output, errors = p.communicate()
        #sinks = output.splitlines() 

        #for sink in sinks:
        #    devices.append(sink[1:-1])
        #print "outputs: %s" % devices
        ################################################
        
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

        #return ('alsa_input.usb-045e_Microsoft_LifeChat_LX-3000-00-default.analog-mono', 'alsa_output.usb-045e_Microsoft_LifeChat_LX-3000-00-default.analog-stereo.monitor')
        #return (sources, devices)

    def application_change (self, screen, stack):
        current_window = screen.get_active_window()
        if current_window is None:
            time.sleep(0.1)
            current_window = screen.get_active_window()
            if current_window is None:
                print ''' give up trying to get current window. Lets assume the window closed.'''
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



class RecordControlGui:

    # This is a callback function. The data arguments are ignored
    # in this example. More on callbacks below.
    def recordStart(self, widget, data=None):
        print "start recording"
        self.skype.signal_record_start()
        
    def recordStop(self, widget, data=None):
        print "start recording"
        self.skype.signal_record_stop()

    def delete_event(self, widget, event, data=None):
        # If you return FALSE in the "delete_event" signal handler,
        # GTK will emit the "destroy" signal. Returning TRUE means
        # you don't want the window to be destroyed.
        # This is useful for popping up 'are you sure you want to quit?'
        # type dialogs.
        print "delete event occurred"

        # Change FALSE to TRUE and the main window will not be destroyed
        # with a "delete_event".
        return False

    def destroy(self, widget, data=None):
        print "destroy signal occurred"
        gtk.main_quit()

    def __init__(self, skype):
        self.skype = skype
        # create a new window
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)

        # When the window is given the "delete_event" signal (this is given
        # by the window manager, usually by the "close" option, or on the
        # titlebar), we ask it to call the delete_event () function
        # as defined above. The data passed to the callback
        # function is NULL and is ignored in the callback function.
        self.window.connect("delete_event", self.delete_event)

        # Here we connect the "destroy" event to a signal handler.  
        # This event occurs when we call gtk_widget_destroy() on the window,
        # or if we return FALSE in the "delete_event" callback.
        #self.window.connect("destroy", self.destroy)

        # Sets the border width of the window.
        self.window.set_border_width(10)
        self.window.set_size_request(300, 280)

        # Creates a new button with the label "Hello World".
        self.button = gtk.Button("start recording")

        # When the button receives the "clicked" signal, it will call the
        # function hello() passing it None as its argument.  The hello()
        # function is defined above.
        self.button.connect("clicked", self.recordStart, None)

        self.button1 = gtk.Button("stop recording")
        self.button1.connect("clicked", self.recordStop, None)
        # This will cause the window to be destroyed by calling
        # gtk_widget_destroy(window) when "clicked".  Again, the destroy
        # signal could come from here, or the window manager.
        #self.button.connect_object("clicked", gtk.Widget.destroy, self.window)

        # This packs the button into the window (a GTK container).
        fix = gtk.Fixed()
        fix.put(self.button, 20, 20)
        fix.put(self.button1, 20, 120)
        self.window.add(fix)
        #self.window.add(self.button)
        #self.window.add(self.button1)

        # The final step is to display this newly created widget.
        #self.button.show()

        # and the window
        self.window.show_all()

    def main(self):
        # All PyGTK applications must have a gtk.main(). Control ends here
        # and waits for an event to occur (like a key press or mouse event).
        gtk.main()


class CallPeople:
    def __init__(self, theirVideoXid, theirAudio, yourVideo, yourAudio, yourCaller):
        self.theirVideoXid = theirVideoXid
        self.theirAudio = theirAudio
        self.yourVideo = yourVideo
        self.yourAudio = yourAudio
        self.callWith = yourCaller
        return None
