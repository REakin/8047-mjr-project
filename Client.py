#!/usr/bin/env python3
from concurrent.futures import thread
import socket
import select
import sys
import os
import threading
import time

import logging
import pyaudio

#global variables
LOGDIR = "./Output/Client/"
workers = []
thread_count = 10000
bufferSize = 1025
requestCount = 10


#----------------------------------------------------------------------------------------------------------------

def clientThead(server_address, p):
    print("Starting client thread")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(server_address)
    print("Connected to server")
    # write reciving data to array
    data = []
    # start playing
    stream = p.open(format=pyaudio.paInt16, channels=1, rate=44100, output=True)
    # start reciving data
    while True:
        # recive data
        data = sock.recv(bufferSize)
        # if no data recived, break
        if not data:
            break
        # write data to array
        stream.write(data)
    # close stream
    stream.stop_stream()
    stream.close()
    # close socket
    sock.close()
    # close pyaudio
    p.terminate()
    print("Client thread finished")

def main(address, port):
    server_address = (address, port)
    p = pyaudio.PyAudio()
    print(server_address)
    t = threading.Thread(target=clientThead, args=(server_address, p))
    for t in workers:
        t.join()   # wait for all threads to finish before closing the program
    

if __name__ == "__main__":
    #take command line arguments for address and port
    if len(sys.argv) != 3:
        print('usage: %s <address> <port>' % sys.argv[0])
        sys.exit(1)
    main(sys.argv[1], int(sys.argv[2]))