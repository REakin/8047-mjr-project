#!/usr/bin/env python3
import socket
import sys
import os
import threading
import time
import pickle
import _thread

#audio imports
import sounddevice as sd
import soundfile as sf
import numpy as np

#GUI imports
import tkinter as tk
from tkinter import ttk as ttk
from tkinter import *

#global variables
LOGDIR = "./Output/Client/"
workers = []
thread_count = 1
bufferSize = 10000
requestCount = 10
BUFFER = []
SONGNAME=""

#----------------------------------------------------------------------------------------------------------------
# UI class
class GUI(threading.Thread):
    def __init__(self, address, port):
        threading.Thread.__init__(self)
        self.address = address
        self.port = port
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
        #create treeview
        self.conninfo = ttk.Treeview(self.widget_frame, columns=('conninfo', 'values'), show="headings")
        self.conninfo.heading('conninfo', text='Connection Info')
        self.conninfo.heading('values', text='Values')
        self.conninfo.grid(column=0, row=0, sticky=(W, E))
        #show connection info
        self.conninfo.insert("", "end", values=("connected to IP Address:", self.address))
        self.conninfo.insert("", "end", values=("connected to Port:", self.port))
        self.conninfo.insert("", "end", values=("Song Name:", "None"))
        #create a text box to display the messages
        self.messagebox = Text(self.widget_frame, state='disabled')
        self.messagebox.grid(row=1, column=0, sticky=(W, E))
        #create a button to save the message
        self.button = ttk.Button(self.widget_frame, text="Save", command=self.save_text_to_file)
        self.button.grid(column=0, row=2, sticky=(W, E))
        self.root.protocol("WM_DELETE_WINDOW", lambda: self.end())
        self.root.mainloop()

    def add_text(self, text):
        self.messagebox.configure(state='normal')
        self.messagebox.insert("end", text)
        self.messagebox.configure(state='disabled')
    
    def save_text_to_file(self, text):
        with open("message.txt", "a") as f:
            f.write(text)
            f.close()
        self.messagebox.delete("1.0", "end")
        tk.messagebox.showinfo(title="Message Saved", message="Message saved to message.txt")

    def end(self):
        self.root.destroy()
        _thread.interrupt_main()

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

#----------------------------------------------------------------------------------------------------------------
#main thread
def main(address, port):
    #global variables
    global BUFFER
    #create UI thread
    UI = GUI(address, port)
    #create socket
    server_address = (address, port)
    print(server_address)
    print("Starting client thread")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(server_address)
    print("Connected to server")
    
    stream = sd.OutputStream(device=None, channels=2, dtype="int16", samplerate=45000, blocksize=1024, latency='high')
    stream.start()

    t= threading.Thread(target=playAudio, args=(stream,))
    t.daemon = True
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
                # print(chr(arr[0]))
                UI.add_text(chr(arr[0]))
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