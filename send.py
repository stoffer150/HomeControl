import socket
import pyaudio
import sys

if len(sys.argv) == 1:
    msg = "sleep_time"
else:
    msg = sys.argv[1]
incoming = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
incoming.sendto(msg.encode('utf-8'), ('192.168.1.114', 1337))


