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
except Exception, e:
    print "some required imports were not found: %s\n" % e
    sys.exit(1)

record_proc = None
mysink = 'waxdisknull'
my_pa_mods = []
current_call = None

def callstart (call):
    global record_proc
    global current_call
    print "call has begun with xid: ", call.theirVideoXid
    connectAudio(call.theirAudio)
    connectAudio(call.yourAudio)
    current_call = call


def recordstart ():
    global current_call
    global record_proc
    call = current_call
    print "STARTING RECORDING!"
    print "DO NOT MOVE THE SKYPE WINDOW!"
    if True: 
        recordCMD = ['/usr/bin/recordmydesktop',
                '--no-cursor',
                '--windowid=%s' % call.theirVideoXid,
                '--display=:0.0',
                '%s.ovg' % call.callWith]
        record_proc = sub.Popen(recordCMD, env={'PULSE_SOURCE':'waxdisknull.monitor'})
        if False: 
            nulfp = open(os.devnull, "w")
            parecCMD = ['/usr/bin/parec',
                    '-r',
                    '-d', 'waxdisknull.monitor']
            recordCMD = ['/usr/bin/ffmpeg',
                    '-f','x11grab',
                    '-y',
                    '-r','25',
                    '-s','100x100',
                    '-i',':0.0+100,100',
                    '-vcodec','ffv1',
                    '-f','alsa',
                    '-i','-',
                    '-acodec','pcm_s16le',
                    '-sameq','/tmp/out.avi'
                    ]

            #recordCMD = 'PULSE_SOURCE=%s.monitor recordmydesktop --no-cursor --windowid=%s %s.ovg' % (mysink, call.theirVideoXid, call.callWith)
            print recordCMD
            parec_proc = sub.Popen(parecCMD, stdout=sub.PIPE)
            record_proc = sub.Popen(recordCMD, stdin=parec_proc.stdout)
            #parec_proc.stdout.close()
            parec_proc.communicate()
            record_proc.communicate()

        #record_proc.communicate()
        print "\n\npid = %s\n\n" % record_proc.pid 

def recordstop():
    global record_proc
    print 'RECORDING STOPPED:'
    os.kill(record_proc.pid, signal.SIGTERM)
    pass

def connectAudio(source):
    global my_pa_mods
    paCMD = 'pactl load-module module-loopback source=%s sink=%s' % (source, mysink) 
    #print 'paCMD = %s' % paCMD
    p = sub.Popen(paCMD,shell=True,stdout=sub.PIPE,stderr=sub.PIPE)
    output, errors = p.communicate() 
    print "pactl complete: output '%s' error '%s'" % (output.rstrip(), errors)
    my_pa_mods.append(output.rstrip())


def setupAudio ():
    p = sub.Popen('pactl list | grep waxdisknull',shell=True,stdout=sub.PIPE,stderr=sub.PIPE)
    output, errors = p.communicate() 
    if output is '':
        print 'waxdisknull is not available.' 
        print 'creating null-sink:'
        p = sub.Popen('pactl load-module module-null-sink sink_name="waxdisknull"',shell=True,stdout=sub.PIPE,stderr=sub.PIPE)
        output, errors = p.communicate() 
        print 'errors: %s' % errors

def callend ():
    global record_proc
    global my_pa_mods
    print 'call ended'
    os.kill(record_proc.pid, signal.SIGTERM)
    for modid in my_pa_mods:
        print "removing pa mod: %s" % modid
        paCMD = 'pactl unload-module %s' % modid
        p = sub.Popen(paCMD,shell=True,stdout=sub.PIPE,stderr=sub.PIPE)
        output, errors = p.communicate() 
        print "pactl complete: output '%s' error '%s'" % (output, errors)
    my_pa_mods = []
    #record_proc.send_signal(signal.SIGHUP)
    #record_proc.send_signal(signal.SIGKILL)

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
            print e

    if skype_pid is None:
        print "skype pid cannot be found. Check skype is running."
        os.exit(1)
    print "skype pid found: %s . When a call starts," % skype_pid
    print "you should see a window to allow you to record."
    s = Skype(skype_pid)
    s.add_callstart_listener(callstart)
    s.add_callend_listener(callend)
    s.add_recordstart_listener(recordstart)
    s.add_recordstop_listener(recordstop)
    setupAudio()
    s.start()
