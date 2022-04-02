#!/usr/bin/env python3
#Simple epoll echo server 

from __future__ import print_function
from contextlib import contextmanager
import socket
import pickle
import select
import sys
from threading import Thread
import _thread
from xmlrpc.client import Server
import time
import os

#audio import
import sounddevice as sd
import numpy as np
import soundfile as sf
import pyogg

#UI import
import tkinter as tk
from tkinter import *
from tkinter import ttk

#Logging imports
import logging

#Global Variables
LOGDIR = "./Output/Server/"
ServerPort = 8000   # Listening port
MAXCONN = 10000        # Maximum connections
BUFLEN = 10000        # Max buffer size
THREADNUM = 1      # number of threads in pool
TESTSTRING = "Hello World"
KEY = 111
#----------------------------------------------------------------------------------------------------------------
# UI Class
class UI(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.files = os.listdir(os.getcwd())
        self.daemon = True
        self.start()

    def run(self):
        self.root = Tk()
        self.root.title("Audio Player")
        self.root.resizable(False, False)
        self.root.configure(background='black')
        #create widgets
        self.widget_frame = ttk.Frame(self.root, padding="3 3 12 12")
        self.widget_frame.grid(column=0, row=0, sticky=(N, W, E, S))
        self.widget_frame.columnconfigure(0, weight=1)
        self.widget_frame.rowconfigure(0, weight=1)
        self.entry = ttk.Entry(self.widget_frame)
        self.entry.bind("<Return>", self.send_message)
        self.entry.grid(column=0, row=1, sticky=(W, E))
        self.button = ttk.Button(self.widget_frame, text="Send", command=self.send_message)
        self.button.grid(column=0, row=2, sticky=(W, E))
        #create a list of all files in the directory
        self.treeview = ttk.Treeview(self.root)
        self.populate()
        #create a text box to display the messages
        self.extratext = Text(self.root, width=25, height=10)
        self.extratext.grid(row=1, column=1)
        #on exit close the window
        self.root.protocol("WM_DELETE_WINDOW", lambda: self.end())
        self.root.mainloop()

    def add_text(self, text):
        try:self.extratext.insert("end", chr(text))
        except:pass

    def end(self):
        self.root.destroy()
        print("Exiting")
        _thread.interrupt_main()

    def send_message(self, event=None):
        global TESTSTRING
        message = self.entry.get()
        if message == "":
            return
        self.entry.delete(0, 'end')
        TESTSTRING += message

    def populate(self):
        for file in self.files:
            if file[-4:] == ".ogg":
                self.treeview.insert("", "end", file, text=file)
        self.treeview.bind("<Double-1>", self.on_double_click)
        self.treeview.grid(row=0, column=1)

    def on_double_click(self, event):
        global file
        item = self.treeview.selection()[0]
        # self.text.insert("1.0", item)
        file = pyogg.VorbisFileStream(item)

#----------------------------------------------------------------------------------------------------------------
# Main server function 
def EpollServer (address):
    #create UI
    ui = UI()
    #create a socket
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
    global file
    global TESTSTRING
    key = KEY
    time.sleep(2)
    pyogg.pyoggSetStreamBufferSize(BUFLEN)
    file = pyogg.VorbisFileStream("vtest.ogg")
    while True:
        try:data = file.get_buffer()[0]
        except:
            file = pyogg.VorbisFileStream("vtest.ogg")
            data = file.get_buffer()[0]
        data = np.frombuffer(data, dtype=np.int16)
        #convert to two channels
        data = np.reshape(data, (-1, 2))
        newdata = data.copy()
        try:newdata[0] = [ord(TESTSTRING[0]), key]
        except:pass
        newdata = pickle.dumps(newdata)
        for sockdes in Client_SD:
            if sockdes in Client_SD:
                epoll.modify(sockdes, select.EPOLLOUT)
                Client_SD[sockdes].send(newdata)
                Client_SD[sockdes].send(b'\n')
        TESTSTRING = TESTSTRING[1:]
        time.sleep(0.08)

    print("Audio Streaming Finished")
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