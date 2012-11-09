#!/usr/bin/env python
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

try:
    from lib.facade import Skype, CallPeople
    import os
    import sys
    import signal
    import subprocess as sub
    import datetime
    import time
    import re
    #import threading
    #import pygtk, gtk, gobject
    from RfPulse.src.RfPulseClient import RfPulseClient
    from gi.repository import GObject
    from gi.repository import Gtk
    from gi.repository import Gdk
    #from gi.repository import WebKit
except ImportError, e:
    print "some required imports were not found: %s\n" % e
    sys.exit(1)
    #    import pygtk
    #    pygtk.require("2.0")
    #    import glib as GObject
    #    import gtk as Gtk
    #    import webkit as WebKit
#    from record_gui import RecordControlGui
except Exception, e:
    print "some required imports were not found: %s\n" % e
    sys.exit(1)


GObject.threads_init()


class Recorder():
    
    def __init__(self): 
        self.record_them_proc = None
        self.record_me_proc = None
        self.mysink = 'waxdisknull'
        self.my_pa_mods = []
        self.current_call = None
        self.gui = None
        self.statusLabel = None
        self.myvideo = '/dev/video2'

    def setStatusLabel (self, label):
        self.statusLabel = label

    def callstart (self, call):
        self.current_call = call
        self.statusLabel.set_text("call in progress")
        print "call has begun with xid: ", call.theirVideoXid
        #self.connectAudio(call.theirAudio)
        #self.connectAudio(call.yourAudio)

    def recordstart (self, data=None):
        if self.current_call is None:
            print "No call currently in progress. Not recording.\n"
            return
        print "starting to record."
        print "DO NOT MOVE THE SKYPE CALL WINDOW!"
        if True: 
            recordthemCMD = ['/usr/bin/recordmydesktop',
                    '--no-cursor',
                    '--fps', '25',
                    '--device', 'pulse',
                    '--windowid=%s' % self.current_call.theirVideoXid,
                    '--display=:0.0',
                    '-o', 'them_%s-%s.ogv' % (self.current_call.callWith.replace(' ', '_').replace('/','-'), 
                        datetime.datetime.now().strftime("%Y-%m-%dT%H%M%S"))]
            #print " ".join(recordthemCMD)
            #self.record_them_proc = sub.Popen(recordCMD, env={'PULSE_SOURCE':'waxdisknull.monitor'})
            recordmeCMD = ['/usr/bin/ffmpeg',
                    '-f', 'alsa',
                    '-i', 'pulse',
                    '-acodec','vorbis',
                    '-f', 'video4linux2',
                    '-s','640x480',
                    '-i',self.myvideo,
                    '-r','25',
                    '-f','mpegts',
                    #'-vcodec','libtheora',
                    'me_%s-%s.mpeg' % (self.current_call.callWith.replace(' ', '_').replace('/','-'),
                        datetime.datetime.now().strftime("%Y-%m-%dT%H%M%S"))]


            print "THEIR AUDIO %s\n\n\n\n" % self.current_call.theirAudio
            self.record_them_proc = sub.Popen(recordthemCMD, env={'PULSE_SOURCE':self.current_call.theirAudio})
            self.record_me_proc = sub.Popen(recordmeCMD, env={'PULSE_SOURCE':self.current_call.yourAudio})
            print "\n\ntheir record pid = %s\n\n" % self.record_them_proc.pid 
            print "\n\nme record pid = %s\n\n" % self.record_me_proc.pid 

    def recordstop(self, data=None):
        if self.current_call is None:
            print "No call currently in progress. Ignoring stop.\n"
            return
        print 'RECORDING STOPPED:'
        os.kill(self.record_them_proc.pid, signal.SIGTERM)
        os.kill(self.record_me_proc.pid, signal.SIGTERM)
        self.current_call = None
        pass

    ''' debricated. '''
    def __connectAudio(self, source):
        paCMD = 'pactl load-module module-loopback source=%s sink=%s' % (source, self.mysink) 
        #print 'paCMD = %s' % paCMD
        p = sub.Popen(paCMD,shell=True,stdout=sub.PIPE,stderr=sub.PIPE)
        output, errors = p.communicate() 
        #print "pactl complete: output '%s' error '%s'" % (output.rstrip(), errors)
        self.my_pa_mods.append(output.rstrip())


    def setupAudio (self):
        p = sub.Popen('pactl list | grep %s' % self.mysink, shell=True,stdout=sub.PIPE,stderr=sub.PIPE)
        output, errors = p.communicate() 
        #print "is waxdisk available?: output '%s' error '%s'" % (output, errors)
        if output.rstrip() == '':
            print 'waxdisknull is not available.' 
            print 'creating null-sink:'
            p = sub.Popen('pactl load-module module-null-sink sink_name="waxdisknull"',shell=True,stdout=sub.PIPE,stderr=sub.PIPE)
            output, errors = p.communicate() 
            print 'errors: %s' % errors

    def callend (self):
        print 'call ended'
        self.statusLabel.set_text("")
        #self.cleanupAudio()

    def cleanupAudio(self):
        print "Checking for dangling skype-record audio hooks.",
        try: 
            self.waiting_to_connect = True
            pa = RfPulseClient("skyperec tidyup")
            pa.events['contextConnected'].append(self.paConnectHandler)
            pa.connect()
            while self.waiting_to_connect:
                time.sleep(0.1)

            pa.getModuleInfoList()
            self.waiting_to_connect = True
            pa.events['moduleInfoList'].append(self.paDataReady)
            while self.waiting_to_connect:
                time.sleep(0.1)
            for mod in pa.modules:
                if mod.name == "module-loopback":
                    if "sink=waxdisknull" in mod.argument:
                        self.paModRemove(mod.index)
                        print "removing dangling hook: %s %s" % (mod.index, mod.argument)
            pa.disconnect()
        except Exception, e:
            print "broken: %s" % e
        print "skype-record audio hook check complete."

    def paConnectHandler(self, userData):
        self.waiting_to_connect = False

    def paDataReady(self, userData):
        self.waiting_to_connect = False

    def paModRemove(self, index):
        paCMD = 'pactl unload-module %s' % index
        p = sub.Popen(paCMD,shell=True,stdout=sub.PIPE,stderr=sub.PIPE)
        output, errors = p.communicate()
        print "removed mod index %s: output '%s' error '%s'" % (index, output, errors)

    def cleanup(self):
        self.cleanupAudio()
        self.current_call = None
        if self.record_them_proc is not None:
            os.kill(self.record_them_proc.pid, signal.SIGTERM)
        self.record_them_proc = None
        if self.record_me_proc is not None:
            os.kill(self.record_me_proc.pid, signal.SIGTERM)
        self.record_me_proc = None



s = None
r = None

def main_quit(obj):
    """main_quit function, it stops the thread and the gtk's main loop"""
    global s, r
    #Stopping the thread and the gtk's main loop
    s.stop()
    #r.cleanup()
    Gtk.main_quit()


def main():
    global s, r
    GObject.threads_init(None)

    if not os.path.exists("/dev/video2"):
        print '''can't find /dev/video2: please check you have 
        completed setup: 
        http://sites.google.com/site/richardhenwood/project/skype-record'''
        sys.exit(2)

    # get the pid of skype
    # and while stepping through pids, 
    # check to see that gst is running.
    skype_pid = None
    gst_pid = None
    ps = sub.Popen(['ps', 'x'], stdout=sub.PIPE)
    out = ps.communicate()[0]
    processes = out.split('\n')
    for proc in processes:
        bits = proc.split()
        try: 
            if bits[4] == 'skype':
                skype_pid = bits[0]
                #break
            if re.match(r'^gst.*$', bits[4]):
                if bits[5] == 'v4l2src':
                    gst_pid = bits[0]
        except IndexError, e:
            print "Problem searching for skype in process list: %s" % e

    if gst_pid is None:
        print '''can't find gst. You must start it manually:
        http://sites.google.com/site/richardhenwood/project/skype-record
        TODO automate this step.'''
        sys.exit(3)
    if skype_pid is None:
        print "skype pid cannot be found. Check skype is running."
        sys.exit(4)
    print "skype pid found: %s ." % skype_pid
    print "--skype record has started ----"
    print ""
    print "You should see a small window to allow you to control recording."
    print "DO NOT CLOSE THIS TERMINAL WINDOW UNTIL YOUR RECORDING IS COMPLETE"
    print ""
    s = Skype(skype_pid)
    r = Recorder()
    # clean up incase we startying in a dirty state (i.e. s-r crashed last run)
    #r.cleanupAudio()

    window = Gtk.Window()
    startbut = Gtk.Button("start recording")
    startbut.connect("clicked", r.recordstart)
    stopbut = Gtk.Button("stop recording")
    stopbut.connect("clicked", r.recordstop)
    statuslabel = Gtk.Label("")

    fix = Gtk.Fixed()
    fix.put(statuslabel, 20, 00)
    fix.put(startbut, 20, 60)
    fix.put(stopbut, 20, 120)
    window.add(fix)
    window.show_all()    
    window.connect('destroy', main_quit)
    
    s.add_callstart_listener(r.callstart)
    s.add_callend_listener(r.callend)

    #r.setupAudio()
    r.setStatusLabel(statuslabel)
    Gdk.threads_enter()
    s.start()
    #Gtk.main()
    Gdk.threads_leave()

if __name__ == '__main__':
    sys.exit(main())
