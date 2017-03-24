import socket
import os
import sys
import re
import time
import sched
import threading
import pyaudio
import itertools
#import pykka
import speech_recognition as sr
from mpd import MPDClient
#from mopidy.mpd import dispatcher
from wakeonlan import wol
from subprocess import call
import subprocess

call('pulseaudio --start', shell=True)
global abort
abort= False
sch = sched.scheduler(time.time, time.sleep)

############################################################
# SOCKET COMMS

INCOMING_UDP_IP = "192.168.1.114" #This device
INCOMING_UDP_PORT = 1337

DENON_IP ='192.168.1.100'
DENON_PORT = 23

denon = None

incoming = None

def disconnect():
    denon.shutdown(1)
    denon.close()


def denon_cmd(command, parameter, wfr=False):
    cr = b'\x0D'
    command = bytes(command, 'ascii')
    parameter = bytes(parameter, 'ascii')
    denon.send(command + parameter + cr)
    response = None
    if wfr:
        response = denon.recv(4096)
    return response


def denon_cmds(cmd_pmt_pairs, wfr=False):
    cr = b'\x0D'
    to_send = b''
    for pair in cmd_pmt_pairs:
        to_send += bytes(pair[0], 'ascii')
        to_send += bytes(pair[1], 'ascii')
        to_send += cr
        denon.send(to_send)
        to_send = b''
    response = None
    if wfr:
        response = denon.recv(4096)
    return response

####
# Connect to Denon first and foremost

connected = False
while not connected:
    try:
        denon = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        denon.connect(('192.168.1.100', 23))
        connected = True
    except:
        print("Couldn't connect to Denon... Retyring in 10 seconds")
        time.sleep(10)

connected = False
while not connected:
    try:
        incoming = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        incoming.bind((INCOMING_UDP_IP, INCOMING_UDP_PORT))
        connected = True
    except:
        print("Couldn't bind UDP... Retyring in 10 seconds")
        time.sleep(10)


############################################################
# SYSTEM POWER CONTROLS

PC_IP = '192.168.1.104'
PC_MAC = 'BC-5F-F4-09-2A-A5'


def shutdown():
    call("echo \"standby 0\" | cec-client -s", shell=True)
#    os.system("shutdown.exe /h")


def wake():
    wol.send_magic_packet(PC_MAC)
    cec("on 0")
    time.sleep(2)
    denon_cmd("MS", "QUICK1")

def reboot():
    command = "/usr/bin/sudo /sbin/shutdown -r now"
    process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
    output = process.communicate()[0]
    print(output)

def restart():
    global abort
    abort = True
    

############################################################
# AUDIO PRESETS

def game_couch():
    denon_cmds([
        ("CV", "FL 55"),
        ("CV", "FR 55"),
        ("CV", "C 55"),
        ("CV", "SL 45"),
        ("CV", "SR 45"),
        ("CV", "SBL 50"),
        ("CV", "SBR 50"),
        ("MS", "STANDARD")]
    )


def game_desk():
    denon_cmds([
        ("CV", "FL 50"),
        ("CV", "FR 50"),
        ("CV", "C 50"),
        ("CV", "SL 50"),
        ("CV", "SR 50"),
        ("CV", "SBL 55"),
        ("CV", "SBR 55"),
        ("MS", "STANDARD")]
    )


def music_uni():
    denon_cmds([
        ("CV", "FL 55"),
        ("CV", "FR 55"),
        ("CV", "C 55"),
        ("CV", "SL 45"),
        ("CV", "SR 45"),
        ("CV", "SBL 50"),
        ("CV", "SBR 50"),
        ("MS", "MCH STEREO")]
    )


def music_close():
    denon_cmds([
        ("CV", "FL 47"),
        ("CV", "FR 47"),
        ("CV", "C 47"),
        ("CV", "SL 50"),
        ("CV", "SR 50"),
        ("CV", "SBL 55"),
        ("CV", "SBR 55"),
        ("MS", "MCH STEREO")]
    )

def study():
    denon_cmd("ZM", "OFF")


def sleep_time():
    cec("standby 0")
    time.sleep(2)
    denon_cmd("MS", "QUICK2")
    denon_cmd("SLP", "050")
    mpidy.clear()
    madd(["spotify:user:spotify:playlist:76EmNg3KPQoEr0izybtuCN"], False)
    mshuffle()
    time.sleep(1)
    mplay()
    #os.system("shutdown.exe /h")


############################################################
# AUDIO CONTROLS


def mute():
    response = denon_cmd("MU", "?", True)
    if response == b'MUOFF\r':
        denon_cmd("MU", "ON")
    elif response == b'MUON\r':
        denon_cmd("MU", "OFF")


def vol(amount):
    amount = int(amount)
    response = denon_cmd("MV", "?", True).decode('ascii')
    #print(response)
    cur = re.findall(r"MV\d\d\d?", response)[-1]
    #print(cur)
    cur = cur[2:]
    if len(cur) < 3:
        cur += "0"
    cur = int(cur)
    if cur + amount*5 < 400:
        if cur + amount*5 > 0:
            denon_cmd("MV", str(cur+amount*5).zfill(3))
        else:
            denon_cmd("MV", "000")
    else:
        denon_cmd("MV", "400")

############################################################
# HDMI-CEC

def cec(cmd):
    call("echo \"" + cmd + "\" | cec-client -s", shell=True)

############################################################
# MOPIDY CONTROL

mpidy = MPDClient()               # create client object
mpidy.timeout = 20                # network timeout in seconds (floats allowed), default: None
mpidy.idletimeout = None          # timeout for fetching the result of the idle command is handled seperately, default: None
#mpidy.iterate = True
connected = False
while not connected:
    try:
        mpidy.connect("localhost", 6600)  # connect to localhost:6600
        connected = True
    except:
        print("Couldn't connect to Mopidy... Retyring in 10 seconds")
        time.sleep(10)


def mopidy_reconnect():
    mpidy.close() 
    mpidy.disconnect()
    mpidy.connect("localhost", 6600)

def mpause(st=1):
    mpidy.pause(st)

def mplay():
    mpidy.stop()
    mpidy.play()

def mstop():
    mpidy.stop()

def mnext():
    mpidy.next()

def msetpl(uri):
    mpidy.clear()
    mpidy.add(uri)

def msetpl_large(uri):
    mpidy.clear()
    mpidy.load(uri)

def mshuffle():
    mpidy.shuffle()

def mcurpl():
    mpidy.playlist()

def madd(uris, append=True):
    if not append:
        mpidy.clear()
    for x in uris:
        mpidy.add(x)

def mspoti_get(uri):
    uris = []
    res = mpidy.search('filename', uri)
    try:
        res = itertools.islice(res, amount)
        for x in res:
            uris.append(x['file'])
    except:
        print("Couldn't get URI")
    print(uris)
    return uris

def mspoti_search(artist='', title='', album='', genre='', amount=1):
    uris = []
    res = mpidy.search('artist', artist, 'title', title, 'album', album, 'genre', genre)
    try:
        added = 0
        for x in res:
            uri = x['file']
            p = re.compile('spotify:.*:')
            match = p.match(uri).group()
            if match == "spotify:artist:" and artist == '':
                continue
            if match == "spotify:album:" and album == '':
                continue
            uris.append(x['file'])
            added += 1
            if added >= amount:
                break
    except:
        print("Couldn't get URI")
    print(uris)
    return uris

def msearch_and_play(artist='', title='', album='', genre='', amount=1):
    uris = mspoti_search(artist=artist, title=title, album=album, genre=genre, amount=amount)
    madd(uris, append=False)
    mplay()

############################################################
# UDP LOOP



class udp (threading.Thread):
    def __init__(self, threadID, name, counter):
      threading.Thread.__init__(self)
      self.threadID = threadID
      self.name = name
      self.counter = counter

    def run(self):
      print ("Starting " + self.name)
      udp_loop()
      print ("Exiting " + self.name)

def udp_loop(): # Not in class
    global abort
    while not abort:
        failed = False
        completed = False
        while not completed:
            try:
                data, addr = incoming.recvfrom(4096)
                data = data.decode('utf-8')
                cmd = data.split(' ')

                if cmd[0] == "vol":
                    vol(cmd[1])
                    continue

                # AVAILABLE COMMANDS
                do = {
                    'shutdown': shutdown,
                    'couch': game_couch,
                    'desk': game_desk,
                    'music_uni': music_uni,
                    'music_close': music_close,
                    'sleep_time': sleep_time,
                    'mute': mute,
                    'vol': vol,
                    'wake': wake,
                    'reboot': reboot,
                    'terminate_script': terminate_script
                }.get(cmd[0])

                if do == None and len(cmd) == 2:
                    denon_cmd(cmd[0], cmd[1])
                elif do != None and len(cmd) > 1:
                    do(cmd[1:])
                elif do != None:
                    do()
                else:
                    print("Badly formulated arguments:")
            except (ConnectionResetError, BrokenPipeError) as e:
                print("Connection to Denon was lost; Attempting to reconnect,")
                print("and then redo'ing the request")
                try:
                    denon = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    denon.connect(('192.168.1.100', 23))
                except:
                    print("Cannot reconnect to denon...")
                if not failed:
                    failed = True
                else:
                    failed = False # Give up
            except Exception as e:
                print("Error caught: \n" + str(sys.exc_info()[1]))
            finally:
                print("from " + str(addr) + " : " + str(cmd))
                if not failed:
                    completed = True
                print("\n")

udp_thread = udp(1, "UDP-thread", 1)
udp_thread.start()


############################################################
# VOICE-RECOGNITION LOOP

class voice_rec (threading.Thread):
    def __init__(self, threadID, name, counter):
      threading.Thread.__init__(self)
      self.threadID = threadID
      self.name = name
      self.counter = counter

    def run(self):
      print ("Starting " + self.name)
      micAdjust()
      voice_rec_loop()
      print ("Exiting " + self.name)

def interpret_phrase(phrase):
    prefix = r".*(?:(?:go go)|(?:google)) gadget(?:s)? "
    # AVAILABLE COMMANDS
    cmd_map= {
        prefix + r"shut\s?down" : shutdown,
        prefix + r"couch gaming": game_couch,
        prefix + r"desk gaming": game_desk,
        prefix + r"room music": music_uni,
        prefix + r"desk music": music_close,
        prefix + r"(?:(?:sleep(?: time)?)|(?:good\s?night))": sleep_time,
        prefix + r"mute": mute,
        prefix + r"up": lambda: vol(5),
        prefix + r"down": lambda: vol(-5),
        prefix + r"wake pc": wake,
        prefix + r"reboot": reboot,
        prefix + r"restart": restart,
        prefix + r"play(?: some)? (\w+)": lambda gnr: msearch_and_play(genre=gnr, amount=20)
    }

    matched = False
    for r, cmd in cmd_map.items():
        print(r)
        mtch = re.match(r, phrase, re.I)
        if mtch:
            args = mtch.groups()
            print(args)
            cmd(*args)
            matched = True
            break
    if not matched:
        print("\"" + phrase + "\" is not a know command")
    

def get_phrase(recognizer, audio):
    print("Energy_th: " + str(r.energy_threshold)) 
    try:
        # for testing purposes, we're just using the default API key
        # to use another API key, use `r.recognize_google(audio, key="GOOGLE_SPEECH_RECOGNITION_API_KEY")`
        # instead of `r.recognize_google(audio)`
        print("Waiting for google...")
        phrase = recognizer.recognize_google(audio)
        interpret_phrase(phrase)
        print("PHRASE: " + phrase )
    except sr.RequestError as e:
        print("Could not request results from Google Speech Recognition service; {0}".
              format(e))
    except Exception as e:
        print("Could not request results from Google Speech Recognition service; {0}".
              format(e))
    print("Waiting for audio...")

## Stolen from speech_recognizer 3.6.3
## https://github.com/Uberi/speech_recognition/blob/master/speech_recognition/__init__.py
def listen_in_background(recog, source, callback, phrase_time_limit=None):
        """
        Spawns a thread to repeatedly record phrases from ``source`` (an ``AudioSource`` instance) into an ``AudioData`` instance and call ``callback`` with that ``AudioData`` instance as soon as each phrase are detected.
        Returns a function object that, when called, requests that the background listener thread stop, and waits until it does before returning. The background thread is a daemon and will not stop the program from exiting if there are no other non-daemon threads.
        Phrase recognition uses the exact same mechanism as ``recognizer_instance.listen(source)``. The ``phrase_time_limit`` parameter works in the same way as the ``phrase_time_limit`` parameter for ``recognizer_instance.listen(source)``, as well.
        The ``callback`` parameter is a function that should accept two parameters - the ``recognizer_instance``, and an ``AudioData`` instance representing the captured audio. Note that ``callback`` function will be called from a non-main thread.
        """
        running = [True]

        def threaded_listen():
            with source as s:
                while running[0]:
                    try:  # listen for 1 second, then check again if the stop function has been called
                        audio = recog.listen(s, 1, phrase_time_limit)
                    except Exception as e:  # listening timed out, just try again
                        pass
                    else:
                        if running[0]: callback(recog, audio)

        def stopper():
            running[0] = False
            listener_thread.join()  # block until the background thread is done, which can be up to 1 second

        listener_thread = threading.Thread(target=threaded_listen)
        listener_thread.daemon = True
        listener_thread.start()
        return stopper

## end steal

r = sr.Recognizer()
m = sr.Microphone(sample_rate = 44100)

with m as source:
    r.adjust_for_ambient_noise(source, 3)

r.dynamic_energy_threshold = True

r.operation_timeout = 5

r.pause_threshold = 0.5

stop_listening = listen_in_background(r, source=m, callback=get_phrase, phrase_time_limit = 5)

p = pyaudio.PyAudio()
print(p.get_default_input_device_info())

print(m.list_microphone_names())


##mtch = re.match(r"go go gadget shut\s?down", "go go gadget shut down", re.I)
##if mtch:
##    print(mtch.groups())
##    print("Hi")
##else:
##    print("No mtch")
############################################################
#PHYSICAL BUTTON INPUT

############################################################
# WEBSOCKET

############################################################
# Infinity

while not abort:
    time.sleep(10)

udp_thread.join()
print("UDP-loop stopped")
#stop_listening()
