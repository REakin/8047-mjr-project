#!/usr/bin/env python3
from concurrent.futures import thread
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
thread_count = 10000
bufferSize = 8192
requestCount = 10


#----------------------------------------------------------------------------------------------------------------
def clientThead(server_address):
    print("Starting client thread")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(server_address)
    print("Connected to server")

    stream = sd.OutputStream(device=None, channels=2, dtype="int16", samplerate=48000, blocksize=2000, latency='high')
    stream.start()
    # t = threading.Thread(target=audioThread, args=(stream,))
    # t.start()
    # start reciving data
    key = -100
    buffer = b''
    while True:
        # recive data
        data = sock.recv(bufferSize)
        if not data:
            break
        if data != b'\n':
            buffer += data
        else:
            # print(buffer)
            data = pickle.loads(buffer)
            # print(data)
            #implment staganography decryption
            extract = data[data[:,1] == key]
            try:print(chr(extract[0][0]))
            except:pass
            stream.write(data.astype(np.int16))
            buffer = b''
    # close socket
    sock.close()
    # t.join()
    print("Client thread finished")
#----------------------------------------------------------------------------------------------------------------
def audioThread(stream):
    stream.start()
    while True:
        pass


def main(address, port):
    server_address = (address, port)
    print(server_address)
    t=threading.Thread(target=clientThead, args=(server_address,))
    t.start()
    t.join()
    

if __name__ == "__main__":
    #take command line arguments for address and port
    if len(sys.argv) != 3:
        print('usage: %s <address> <port>' % sys.argv[0])
        sys.exit(1)
    main(sys.argv[1], int(sys.argv[2]))