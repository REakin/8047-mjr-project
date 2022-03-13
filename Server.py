#!/usr/bin/env python3
#Simple epoll echo server 

from __future__ import print_function
from contextlib import contextmanager
import socket
import pickle
import select
import sys
from threading import Thread
from xmlrpc.client import Server
import time
import os
import sounddevice as sd
import numpy as np
import soundfile as sf
import pyogg


#Logging imports
import logging

LOGDIR = "./Output/Server/"
ServerPort = 8000   # Listening port
MAXCONN = 10000        # Maximum connections
BUFLEN = 2048        # Max buffer size
THREADNUM = 1      # number of threads in pool
TESTSTRING = "Hello World"
#----------------------------------------------------------------------------------------------------------------


#----------------------------------------------------------------------------------------------------------------
# Main server function 
def EpollServer (address):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt (socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)   # Allow multiple bindings to port
    server.bind(address)
    server.listen (MAXCONN)
    server.setblocking (0)
    server.setsockopt (socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)   # Set socket to non-blocking
    print ("Listening on Port:",ServerPort)

    epollmain = select.epoll()
    epollmain.register(server.fileno(), select.EPOLLIN)

    Client_SD = []
    Server_Response = []
    server_SD = server.fileno() #get the server socket descriptor 

    #Logging Variables
    DataTransfered = []
    RequestCounts = []
    IpAddr = []
    #Client Variables
    epolls = []
    Client_SD = []
    Client_req = []
    workers = []
    audioworkers = []

    for i in range(THREADNUM):
        # Create mutiple epoll objects for the threads
        temp_epoll = select.epoll()
        epolls.append(temp_epoll)
        tmp_Client_SD = {}
        Client_SD.append(tmp_Client_SD)
        tmp_Client_req = {}
        Client_req.append(tmp_Client_req)
        tmp_Server_rsp = {}
        Server_Response.append(tmp_Server_rsp)
        tmp_DataTransfered = {}
        DataTransfered.append(tmp_DataTransfered)
        tmp_RequestCounts = {}
        RequestCounts.append(tmp_RequestCounts)
        tmp_IP = {}
        IpAddr.append(tmp_IP)
        # set thread to manage data collection and logging
        t = Thread(target=handle_connection, args=(Client_SD[i], Client_req[i], Server_Response[i], epolls[i], DataTransfered[i], RequestCounts[i], IpAddr[i]))
        a = Thread(target=AudioStreaming, args=(Client_SD[i], epolls[i]))
        workers.append(t)
        audioworkers.append(a)

    #start the threads
    for t in workers:
        t.start()
    for a in audioworkers:
        a.start()

    iteration = 0
    while True:
        events = epollmain.poll(1)
        for sockdes, event in events:
            if sockdes == server_SD:
                init_connection (server, Client_SD[iteration], Client_req[iteration], Server_Response[iteration], epolls[iteration], DataTransfered[iteration], RequestCounts[iteration], IpAddr[iteration])
                iteration = (iteration + 1)%THREADNUM #distributes connections evenly amongst threads

#----------------------------------------------------------------------------------------------------------------
#handle connection
def handle_connection (Client_SD, Client_Reqs, Server_Response, epoll, DataTransfered, RequestCounts, IpAddr):
    while True:
        events = epoll.poll(1)
        for sockdes, event in events:
            if sockdes in Client_SD:
                if event & select.EPOLLIN:  #receive data from client
                    Receive_Message (sockdes, Client_Reqs, Client_SD, Server_Response, epoll, DataTransfered, RequestCounts, IpAddr)
                elif event & select.EPOLLOUT: #send data to client
                    # Echo_Response (sockdes, Client_SD, Server_Response, epoll)
                    pass
#----------------------------------------------------------------------------------------------------------------
# Process Client Connections
def init_connection (server, Client_SD, Client_Reqs, Server_Response, epoll, dataTransfered, requestCounts, ipAddr):
    connection, address = server.accept()
    connection.setblocking(0)
    print ('Client Connected:', address)    #print client IP
    fd = connection.fileno()
    #register the fd in the EPOLL
    epoll.register(fd, select.EPOLLIN)
    Client_SD[fd] = connection
    Server_Response[fd] = ''
    Client_Reqs[fd] = ''
    # Logging
    dataTransfered[fd] = 0
    requestCounts[fd] = 0
    ipAddr[fd] = address
#----------------------------------------------------------------------------------------------------------------
# Receive a request and send an ACK with echo
def Receive_Message (sockdes, Client_Reqs, Client_SD, Server_Response, epoll, DataTransfered, RequestCounts, IpAddr):
    data = Client_SD[sockdes].recv(BUFLEN)
    Client_Reqs[sockdes] += data.decode()

    # Make sure client connection is still open 
    if Client_Reqs[sockdes] == 'quit\n' or Client_Reqs[sockdes] == '':
        print('[{:02d}] Client Connection Closed!'.format(sockdes))
        epoll.unregister(sockdes)
        Client_SD[sockdes].close()
        del Client_SD[sockdes], Client_Reqs[sockdes], Server_Response[sockdes], DataTransfered[sockdes], RequestCounts[sockdes], IpAddr[sockdes]
        return

    elif '\n' in Client_Reqs[sockdes]:
        epoll.modify(sockdes, select.EPOLLOUT)
        msg = Client_Reqs[sockdes][:-1]
        RequestCounts[sockdes] += 1
        Server_Response[sockdes] = Client_Reqs[sockdes]
        Client_Reqs[sockdes] = ''
#----------------------------------------------------------------------------------------------------------------
# Send a response to the client
def Echo_Response (sockdes, Client_SD, data, epoll):
    Client_SD[sockdes].send(data)
    epoll.modify(sockdes, select.EPOLLIN)
    # print ("Response Sent")
#----------------------------------------------------------------------------------------------------------------
# Audio Streaming
def AudioStreaming(Client_SD, epoll):
    test = TESTSTRING
    key = -100
    time.sleep(2)
    pyogg.pyoggSetStreamBufferSize(BUFLEN)
    with pyogg.VorbisFileStream("vtest.ogg") as f:
        while f.tell() < f.frames:
            data = f.get_buffer()[0]
            data = np.frombuffer(data, dtype=np.int16)
            data = np.reshape(data, (-1, 2))
            newdata = data.copy()
            try:newdata[1] = [ord(test[0]), key] 
            except:pass
            newdata = pickle.dumps(newdata)
            for sockdes in Client_SD:
                if sockdes in Client_SD:
                    epoll.modify(sockdes, select.EPOLLOUT)
                    Client_SD[sockdes].send(newdata)
                    Client_SD[sockdes].send(b'\n')
            time.sleep(0.05)
            test = test[1:]


    print("Audio Streaming Finished")

    # wf = wave.open('test.wav', 'rb')
    # data = np.fromfile('test.wav', dtype=np.int16)
    # stream = sd.InputStream(samplerate=44100, channels=1, dtype='int16', callback=callback)
    # stream.start()
    # stream.write(data)


    # send 10 packets then wait 2 seconds
    # for i in range(0, len(data),50):
    #     #encode data
    #     data_encoded = data[i:i+50]
    #     print(data_encoded)
    #     data_string = pickle.dumps(data_encoded)
    #     #send data
    #     for sockdes in Client_SD:
    #         epoll.modify(sockdes, select.EPOLLOUT)
    #         Client_SD[sockdes].send(data_string)
    # wf  = wave.open("test.wav", 'rb')
    # data = wf.readframes(BUFLEN)
    # while data != '':
    #     data = wf.readframes(BUFLEN)
    #     for sockdes in Client_SD:
    #         Echo_Response (sockdes, Client_SD, data, epoll)

#----------------------------------------------------------------------------------------------------------------
# callback
def callback(indata, frames, time, status):
    print(indata)
    # print(frames)
# Use context manager to free socket resources upon termination
@contextmanager   # Socket Context (resource) manager
def socketcontext(*args, **kwargs):
    sd = socket.socket(*args, **kwargs)
    try:
        yield sd
    finally:
        print ("Listening Socket Closed")
        sd.close()

#----------------------------------------------------------------------------------------------------------------
# Use context manager to free epoll resources upon termination
@contextmanager # epoll loop Context manager
def epollcontext (*args, **kwargs):
    eps = select.epoll()
    eps.register(*args, **kwargs)
    try:
        yield eps
    finally:
        print("\nExiting epoll loop")
        eps.unregister(args[0])
        eps.close()
#----------------------------------------------------------------------------------------------------------------
# Start the epoll server & Process keyboard interrupt CTRL-C
if __name__ == '__main__':
    try:
        EpollServer (("0.0.0.0", ServerPort))
    except KeyboardInterrupt as e:
        print("Server Shutdown")
        exit()      # Don't really need this because of context managers