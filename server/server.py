#!/usr/bin/env python3

import socket
import struct
import time
import threading

currentTimeMillis = lambda: int(round(time.time() * 1000))

HOST = '192.168.1.100'
CALIBRATION_PORT = 10000
CALIBRATION_PACKET_SIZE = 16 

def calibrationThread():    
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((HOST, CALIBRATION_PORT))
    s.listen()
    while True:
        (conn, addr) = s.accept()
        with conn:
            print('Connected by', addr)
            while True:
                inPacket = conn.recv(CALIBRATION_PACKET_SIZE)
                hostReceiveTime = currentTimeMillis()
                if (len(inPacket)==0): 
                    print("Client is done")
                    break 
                [deviceSendTime, deviceReceiveTime] = struct.unpack(">qq",inPacket)
                hostSendTime = currentTimeMillis()
                outPacket = struct.pack(">qq",hostReceiveTime,hostSendTime)
                conn.sendall(outPacket)

import sched
from playsound import playsound
def playsoundThread():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((HOST, EVENT_PORT))
    s.listen()
    while True:
        (conn, addr) = s.accept()
        with conn:
            print('Connected by', addr)
            while True:
                inPacket = conn.recv(EVENT_PACKET_SIZE)
                receiveTime = currentTimeMillis()
                if (len(inPacket)==0): 
                    print("Client is done")
                    break
                [estimatedTime] = struct.unpack(">q",inPacket)
                print("Error: {}".format(receiveTime-estimatedTime))
                ##mScheduler = sched.scheduler(timefunc=time.time)
                ##mScheduler.enterabs((estimatedTime+1000)/1000, 0, lambda: playsound("sound_fx.wav"))
                ##mScheduler.run()

EVENT_PORT = 10001
N_ELEMENTS = 10 
ELEMENT_SIZE = (8+3*4) ### Bytes
EVENT_PACKET_SIZE = N_ELEMENTS*ELEMENT_SIZE 
PLOT_SIZE = 5000

from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph as pg

def eventThread():
    app = QtGui.QApplication([])
    win = pg.GraphicsWindow(title="Acceleration data")
    pg.setConfigOptions(antialias=True)
    p = win.addPlot(title="Realtime plot")
    lineX = p.plot()
    lineX.setData(pen='r')
    lineY = p.plot()
    lineY.setData(pen='g')
    lineZ = p.plot()
    lineZ.setData(pen='b')

    x = []
    y = []
    z = []
    timestampList = [] 
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((HOST, EVENT_PORT))
    s.listen()
    while True:
        (conn, addr) = s.accept()
        with conn:
            print('Connected by', addr)
            while True:
                beginTime = currentTimeMillis()
                inPacket = b'' 
                while (len(inPacket)<EVENT_PACKET_SIZE):
                    inPacket += conn.recv(EVENT_PACKET_SIZE)
                    #print("packet is "+str(len(inPacket))+" bytes long")
                if (len(inPacket)==0): 
                    print("Client is done")
                    break
                if len(inPacket)!=EVENT_PACKET_SIZE:
                    print("Received invalid packet of size {} (size is {})".format(len(inPacket),EVENT_PACKET_SIZE))
                    continue 
                else:
                    for i in range(0,N_ELEMENTS):
                        slice = inPacket[ELEMENT_SIZE*i:ELEMENT_SIZE*i+ELEMENT_SIZE]
                        #print("Slice {} has length {}".format(i,len(slice)))
                        newX, newY, newZ, timestamp = struct.unpack(">fffq",slice)
                        #print(str(values),str(timestamp))
                        x.append(newX)
                        y.append(newY)
                        z.append(newZ)
                        timestampList.append(timestamp)
                        #print("Lists are of size {},{}".format(len(valuesList),len(timestampList)))
                    assert(len(timestampList)==len(x))
                    assert(len(timestampList)==len(y))
                    assert(len(timestampList)==len(z))
                    lineX.setData(timestampList[-PLOT_SIZE:],x[-PLOT_SIZE:])
                    lineY.setData(timestampList[-PLOT_SIZE:],y[-PLOT_SIZE:])
                    lineZ.setData(timestampList[-PLOT_SIZE:],z[-PLOT_SIZE:])
                    p.setXRange(timestampList[-1]-PLOT_SIZE, timestampList[-1], padding=0)
                    QtGui.QApplication.processEvents()    

    pg.QtGui.QApplication.exec_()        

ct = threading.Thread(target=calibrationThread)
ct.start()
et = threading.Thread(target=eventThread())
et.start()
