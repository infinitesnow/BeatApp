#!/usr/bin/env python3
import socket
import struct
import time
import threading
import sched
from playsound import playsound
from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph as pg
import numpy as np
from scipy.signal import butter

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
N_ELEMENTS = 3 
ELEMENT_SIZE = (8+3*4) ### Bytes
EVENT_PACKET_SIZE = N_ELEMENTS*ELEMENT_SIZE 
PLOT_SIZE = 100
SAMPLE_RATE = 50
plotDuration = PLOT_SIZE*(1/SAMPLE_RATE)
lowcutFreq = 0.5
filterOrder = 5

def bFilter(lowcutFreq, filterOrder=5):
    nyquist = 0.5 * SAMPLE_RATE 
    lowcutFreqNorm = lowcutFreq / nyquist
    filterNum, filterDen = butter(filterOrder, [lowcutFreqNorm], btype='highpass')
    return filterNum, filterDen

def filter(filterNum,filterDen,x,y):
    order = len(filterNum)-1
    assert(filterDen[0]==1)
    xslice = x[-order-1:]
    yslice = y[-order:]
    b = filterNum[::-1]
    a = filterDen[:0:-1]
    return b.dot(xslice)-a.dot(yslice)
 
def eventThread():
    app = QtGui.QApplication([])
    win = pg.GraphicsWindow(title="Realtime plot")
    p1 = win.addPlot(title="Acceleration")
    pg.setConfigOptions(antialias=True)
    lineAccX = p1.plot()
    lineAccX.setData(pen='r')
    lineAccY = p1.plot()
    lineAccY.setData(pen='g')
    lineAccZ = p1.plot()
    lineAccZ.setData(pen='b')
    p2 = win.addPlot(title="Velocity")
    pg.setConfigOptions(antialias=True)
    lineVelX = p2.plot()
    lineVelX.setData(pen='r')
    lineVelY = p2.plot()
    lineVelY.setData(pen='g')
    lineVelZ = p2.plot()
    lineVelZ.setData(pen='b')
    lineZC = p2.plot()
    lineZC.setData(pen='y')

    accX = [0]*filterOrder
    accY = [0]*filterOrder
    accZ = [0]*filterOrder
    velX = [0]*filterOrder 
    velY = [0]*filterOrder 
    velZ = [0]*filterOrder 
    filtVelX = [0]*filterOrder 
    filtVelY = [0]*filterOrder 
    filtVelZ = [0]*filterOrder 
    timestampList = [0]*filterOrder
    zc = [0]*filterOrder
    filterNum, filterDen = bFilter(lowcutFreq,filterOrder)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((HOST, EVENT_PORT))
    s.listen()
    while True:
        (conn, addr) = s.accept()
        with conn:
            print('Connected by', addr)
            beginTime = None
            while True:
                inPacket = b'' 
                while (len(inPacket)<EVENT_PACKET_SIZE):
                    inPacket += conn.recv(EVENT_PACKET_SIZE)
                    if (not beginTime): 
                        beginTime = currentTimeMillis()/1000
                        print("BeginTime: {}".format(beginTime))
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

                        newAccX, newAccY, newAccZ, newTimestamp = struct.unpack(">fffq",slice)
                        newTimestamp=newTimestamp/1000-beginTime
                        accX.append(newAccX)
                        accY.append(newAccY)
                        accZ.append(newAccZ)

                        deltaT = newTimestamp-timestampList[-1]

                        newVelX = velX[-1]+newAccX*deltaT
                        newVelY = velY[-1]+newAccY*deltaT
                        newVelZ = velZ[-1]+newAccZ*deltaT
                        velX.append(newVelX)
                        velY.append(newVelY)
                        velZ.append(newVelZ)

                        newFiltVelX = filter(filterNum,filterDen,velX,filtVelX)
                        newFiltVelY = filter(filterNum,filterDen,velY,filtVelY)
                        newFiltVelZ = filter(filterNum,filterDen,velZ,filtVelZ)
                        filtVelX.append(newFiltVelX)
                        filtVelY.append(newFiltVelY)
                        filtVelZ.append(newFiltVelZ)

                        if ((np.sign(filtVelY[-1])-np.sign(filtVelY[-2]))>1):
                            zc[-1]=1
                            zc.append(1)
                        else:
                            zc.append(0)
                        timestampList.append(newTimestamp)

                    assert(len(timestampList)==len(accX))
                    assert(len(timestampList)==len(accY))
                    assert(len(timestampList)==len(accZ))

                    timestampWindow = timestampList[-PLOT_SIZE:]
                    windowZC = zc[-PLOT_SIZE:]
                    lineZC.setData(timestampWindow,windowZC)

                    windowAccX = accX[-PLOT_SIZE:]
                    windowAccY = accY[-PLOT_SIZE:]
                    windowAccZ = accZ[-PLOT_SIZE:]
                    ###lineAccX.setData(timestampWindow,windowAccX)
                    lineAccY.setData(timestampWindow,windowAccY)
                    ###lineAccZ.setData(timestampWindow,windowAccZ)
                    p1.setXRange(timestampList[-1]-plotDuration, timestampList[-1], padding=0)

                    windowVelX = filtVelX[-PLOT_SIZE:]
                    windowVelY = filtVelY[-PLOT_SIZE:]
                    windowVelZ = filtVelZ[-PLOT_SIZE:]
                    ###lineVelX.setData(timestampWindow,windowVelX)
                    lineVelY.setData(timestampWindow,windowVelY)
                    ###lineVelZ.setData(timestampWindow,windowVelZ)
                    p2.setXRange(timestampList[-1]-plotDuration, timestampList[-1], padding=0)

                    QtGui.QApplication.processEvents()    

    pg.QtGui.QApplication.exec_()        

ct = threading.Thread(target=calibrationThread)
ct.start()
et = threading.Thread(target=eventThread())
et.start()
