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
    #import threading
    import pygtk, gtk, gobject
#    from record_gui import RecordControlGui
except Exception, e:
    print "some required imports were not found: %s\n" % e
    sys.exit(1)


gobject.threads_init()


class Recorder():
    
    def __init__(self): 
        self.record_proc = None
        self.mysink = 'waxdisknull'
        self.my_pa_mods = []
        self.current_call = None
        self.gui = None
        self.statusLabel = None

    def setStatusLabel (self, label):
        self.statusLabel = label

    def callstart (self, call):
        self.current_call = call
        self.statusLabel.set_text("call in progress")
        print "call has begun with xid: ", call.theirVideoXid
        self.connectAudio(call.theirAudio)
        self.connectAudio(call.yourAudio)

    def recordstart (self, data=None):
        if self.current_call is None:
            print "No call currently in progress. Not recording.\n"
            return
        print "starting to record."
        print "DO NOT MOVE THE SKYPE CALL WINDOW!"
        if True: 
            recordCMD = ['/usr/bin/recordmydesktop',
                    '--no-cursor',
                    '--fps', '25',
                    '--windowid=%s' % self.current_call.theirVideoXid,
                    '--display=:0.0',
                    '-o', '%s-%s.ogv' % (self.current_call.callWith.replace(' ', '_'), 
                        datetime.datetime.now().strftime("%Y-%m-%dT%H%M%S"))]
            self.record_proc = sub.Popen(recordCMD, env={'PULSE_SOURCE':'waxdisknull.monitor'})
            print "\n\npid = %s\n\n" % self.record_proc.pid 

    def recordstop(self, data=None):
        if self.current_call is None:
            print "No call currently in progress. Ignoring stop.\n"
            return
        print 'RECORDING STOPPED:'
        os.kill(self.record_proc.pid, signal.SIGTERM)
        pass

    def connectAudio(self, source):
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
        self.current_call = None
        os.kill(self.record_proc.pid, signal.SIGTERM)
        for modid in self.my_pa_mods:
            print "removing pa mod: %s" % modid
            paCMD = 'pactl unload-module %s' % modid
            p = sub.Popen(paCMD,shell=True,stdout=sub.PIPE,stderr=sub.PIPE)
            output, errors = p.communicate() 
            print "pactl complete: output '%s' error '%s'" % (output, errors)
        self.my_pa_mods = []

def main_quit(obj):
    """main_quit function, it stops the thread and the gtk's main loop"""
    global s
    #Stopping the thread and the gtk's main loop
    #s.stop()
    gtk.main_quit()


if __name__ == '__main__':
    # get the pid of skype
    skype_pid = None
    ps = sub.Popen(['ps', 'x'], stdout=sub.PIPE)
    out = ps.communicate()[0]
    processes = out.split('\n')
    for proc in processes:
        #bits = string.split(proc, sep=whitespace)
        bits = proc.split()
        try: 
            if bits[4] == 'skype':
                skype_pid = bits[0]
        except IndexError, e:
            print "cannot find skype process." 

    if skype_pid is None:
        print "skype pid cannot be found. Check skype is running."
        os.exit(1)
    print "skype pid found: %s . When a call starts," % skype_pid
    print "you should see a window to allow you to record."
    s = Skype(skype_pid)
    r = Recorder()

    window = gtk.Window()
    startbut = gtk.Button("start recording")
    startbut.connect("clicked", r.recordstart)
    stopbut = gtk.Button("stop recording")
    stopbut.connect("clicked", r.recordstop)
    statuslabel = gtk.Label("")

    fix = gtk.Fixed()
    fix.put(statuslabel, 20, 00)
    fix.put(startbut, 20, 60)
    fix.put(stopbut, 20, 120)
    window.add(fix)
    window.show_all()    
    window.connect('destroy', main_quit)
    
    s.add_callstart_listener(r.callstart)
    s.add_callend_listener(r.callend)

    r.setupAudio()
    r.setStatusLabel(statuslabel)
    s.start()
    gtk.main()

