#!/usr/bin/env python3
from concurrent.futures import thread
from dataclasses import dataclass
from glob import glob
import socket
import select
import sys
import os
import threading
import time
import pickle
import struct

import logging

#audio imports
import sounddevice as sd
import soundfile as sf
import numpy as np

#global variables
LOGDIR = "./Output/Client/"
workers = []
thread_count = 1
bufferSize = 10000
requestCount = 10
BUFFER = []

#----------------------------------------------------------------------------------------------------------------
def clientThead(server_address):
    print("Starting client thread")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(server_address)
    print("Connected to server")

    stream = sd.OutputStream(device=None, channels=2, dtype="int16", samplerate=40000, blocksize=10000, latency='high')
    stream.start()
    # start reciving data
    key = 111
    buffer = b''
    while True:
        # recive data
        data = sock.recv(bufferSize)
        if data != b'\n':
            buffer += data
        else:
            # print(buffer)
            data = buffer
            data = pickle.loads(data)
            stream.write(data)
            arr = data[0]
            if(arr[1] == key):
                print(chr(arr[0]))
            buffer = b''
    # close socket
    sock.close()
    # t.join()
    print("Client thread finished")

#----------------------------------------------------------------------------------------------------------------
#thread to play audio
def playAudio(stream):
    global BUFFER
    print("Starting audio thread")
    while True:
        if len(BUFFER) > 0:
            data = BUFFER.pop(0)
            stream.write(data)
        else:
            time.sleep(.1)
    print("Audio thread finished")

def main(address, port):
    global BUFFER
    server_address = (address, port)
    print(server_address)
    print("Starting client thread")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(server_address)
    print("Connected to server")
    
    stream = sd.OutputStream(device=None, channels=2, dtype="int16", samplerate=45000, blocksize=1024, latency='high')
    stream.start()

    t= threading.Thread(target=playAudio, args=(stream,))
    t.start()
   
    # start reciving data
    key = 111
    buffer = b''
    while True:
        # recive data
        data = sock.recv(bufferSize)
        if data != b'\n':
            buffer += data
        else:
            data = pickle.loads(buffer)
            BUFFER.append(data)
            arr = data[0]
            if(arr[1] == key):
                print(chr(arr[0]))
            buffer = b''

    # close socket
    sock.close()
    # t.join()
    print("Client thread finished")
    

if __name__ == "__main__":
    #take command line arguments for address and port
    if len(sys.argv) != 3:
        print('usage: %s <address> <port>' % sys.argv[0])
        sys.exit(1)
    main(sys.argv[1], int(sys.argv[2]))