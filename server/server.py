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

def playsoundThread():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((self.host, EVENT_PORT))
    s.listen()
    while True:
        (conn, addr) = s.accept()
        with conn:
            print('Connected by', addr)
            while True:
                inPacket = conn.recv(Main.EVENT_PACKET_SIZE)
                receiveTime = Main.currentTimeMillis()
                if (len(inPacket)==0): 
                    print("Client is done")
                    break
                [estimatedTime] = struct.unpack(">q",inPacket)
                print("Error: {}".format(receiveTime-estimatedTime))
                ##mScheduler = sched.scheduler(timefunc=time.time)
                ##mScheduler.enterabs((estimatedTime+1000)/1000, 0, lambda: playsound("sound_fx.wav"))
                ##mScheduler.run()

def bFilter(lowcutFreq, fs, filterOrder=5):
    nyquist = 0.5 * fs 
    lowcutFreqNorm = lowcutFreq / nyquist
    filterNum, filterDen = butter(filterOrder, [lowcutFreqNorm], btype='highpass')
    return filterNum, filterDen

class Main():
    STATUS_OK = 0
    STATUS_EXITED = 1
    STATUS_INVALID = 2
    STATUS_FINISHED = 3
    
    CALIBRATION_PORT = 10000
    CALIBRATION_PACKET_SIZE = 16 

    EVENT_PORT = 10001
    N_ELEMENTS = 3 
    ELEMENT_SIZE = (8+3*4) ### Bytes
    EVENT_PACKET_SIZE = N_ELEMENTS*ELEMENT_SIZE 

    PLOT_SIZE = 100

    SAMPLE_RATE = 50
    LOWCUT_FREQ = 0.5
    FILTER_ORDER = 5
    
    def currentTimeMillis():
        return int(round(time.time() * 1000))
    
    def __init__(self,host):
        self.host = host
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.app = QtGui.QApplication([])
        self.win = pg.GraphicsWindow(title="Realtime plot")
        pg.setConfigOptions(antialias=True)
        self.plotDuration = Main.PLOT_SIZE*(1/Main.SAMPLE_RATE)

        self.p1 = self.win.addPlot(title="Acceleration")
        self.lineAccX = self.p1.plot()
        self.lineAccY = self.p1.plot()
        self.lineAccZ = self.p1.plot()
        self.lineAccX.setData(pen='r')
        self.lineAccY.setData(pen='g')
        self.lineAccZ.setData(pen='b')

        self.p2 = self.win.addPlot(title="Velocity")
        self.lineVelX = self.p2.plot()
        self.lineVelY = self.p2.plot()
        self.lineVelZ = self.p2.plot()
        self.lineVelX.setData(pen='r')
        self.lineVelY.setData(pen='g')
        self.lineVelZ.setData(pen='b')

        self.lineZC = self.p2.plot()
        self.lineZC.setData(pen='y')

        initSize = Main.FILTER_ORDER
        self.accX = [0]*initSize
        self.accY = [0]*initSize
        self.accZ = [0]*initSize
        self.velX = [0]*initSize 
        self.velY = [0]*initSize 
        self.velZ = [0]*initSize 
        self.filtVelX = [0]*initSize 
        self.filtVelY = [0]*initSize 
        self.filtVelZ = [0]*initSize 

        self.timestampList = [0]*initSize
        self.zc = [0]*initSize

        self.filterNum, self.filterDen = bFilter(Main.LOWCUT_FREQ,Main.SAMPLE_RATE,Main.FILTER_ORDER)

        self.beginTime = None

        self.calibrationThread = None
        self.eventThread = None

    def clearData(self):
        initSize = Main.FILTER_ORDER
        self.accX = [0]*initSize
        self.accY = [0]*initSize
        self.accZ = [0]*initSize
        self.velX = [0]*initSize 
        self.velY = [0]*initSize 
        self.velZ = [0]*initSize 
        self.filtVelX = [0]*initSize 
        self.filtVelY = [0]*initSize 
        self.filtVelZ = [0]*initSize 
        self.timestampList = [0]*initSize
        self.zc = [0]*initSize

    def getFilterOutput(self,x,y):
        order = self.FILTER_ORDER
        assert(self.filterDen[0]==1)
        xslice = x[-order-1:]
        yslice = y[-order:]
        b = self.filterNum[::-1]
        a = self.filterDen[:0:-1]
        return b.dot(xslice)-a.dot(yslice)
    
    def getEventPacket(conn):
        inPacket = b'' 
        while (len(inPacket)<Main.EVENT_PACKET_SIZE):
            inPacket += conn.recv(Main.EVENT_PACKET_SIZE)
            #print("packet is "+str(len(inPacket))+" bytes long")
        return inPacket    

    def checkPacket(inPacket):
        if (len(inPacket)==0): 
            print("Client is done")
            return Main.STATUS_EXITED
        elif len(inPacket)!=Main.EVENT_PACKET_SIZE:
            print("Received invalid packet of size {} (size is {})".format(len(inPacket),Main.EVENT_PACKET_SIZE))
            return Main.STATUS_INVALID 
        else:
            for i in range(0,Main.EVENT_PACKET_SIZE):
                if (inPacket[i]!=255): 
                    return Main.STATUS_OK
            return Main.STATUS_FINISHED 
    
    def addSamples(self,packetSlice):
       newAccX, newAccY, newAccZ, newTimestamp = struct.unpack(">fffq",packetSlice)
       newTimestamp=newTimestamp/1000-self.beginTime
       print("t: {}".format(newTimestamp))
       self.accX.append(newAccX)
       self.accY.append(newAccY)
       self.accZ.append(newAccZ)
    
       deltaT = newTimestamp-self.timestampList[-1]
    
       newVelX = self.velX[-1]+newAccX*deltaT
       newVelY = self.velY[-1]+newAccY*deltaT
       newVelZ = self.velZ[-1]+newAccZ*deltaT
       self.velX.append(newVelX)
       self.velY.append(newVelY)
       self.velZ.append(newVelZ)
    
       newFiltVelX = self.getFilterOutput(self.velX,self.filtVelX)
       newFiltVelY = self.getFilterOutput(self.velY,self.filtVelY)
       newFiltVelZ = self.getFilterOutput(self.velZ,self.filtVelZ)
       self.filtVelX.append(newFiltVelX)
       self.filtVelY.append(newFiltVelY)
       self.filtVelZ.append(newFiltVelZ)
    
       if ((np.sign(self.filtVelY[-1])-np.sign(self.filtVelY[-2]))>1):
           self.zc[-1]=1
           self.zc.append(1)
       else:
           self.zc.append(0)
       self.timestampList.append(newTimestamp)

    def plot(self):
        assert(len(self.timestampList)==len(self.accX))
        assert(len(self.timestampList)==len(self.accY))
        assert(len(self.timestampList)==len(self.accZ))
        assert(len(self.timestampList)==len(self.velX))
        assert(len(self.timestampList)==len(self.velY))
        assert(len(self.timestampList)==len(self.velZ))
        assert(len(self.timestampList)==len(self.zc))

        T = Main.PLOT_SIZE
        windowTimestamp = self.timestampList[-T:]
        windowZC = self.zc[-T:]
        self.lineZC.setData(windowTimestamp,windowZC)
    
        windowAccX = self.accX[-T:]
        windowAccY = self.accY[-T:]
        windowAccZ = self.accZ[-T:]
        ###lineAccX.setData(windowTimestamp,windowAccX)
        self.lineAccY.setData(windowTimestamp,windowAccY)
        ###lineAccZ.setData(windowTimestamp,windowAccZ)
        self.p1.setXRange(self.timestampList[-1]-self.plotDuration, self.timestampList[-1], padding=0)
    
        windowVelX = self.filtVelX[-T:]
        windowVelY = self.filtVelY[-T:]
        windowVelZ = self.filtVelZ[-T:]
        ###lineVelX.setData(windowTimestamp,windowVelX)
        self.lineVelY.setData(windowTimestamp,windowVelY)
        ###lineVelZ.setData(windowTimestamp,windowVelZ)
        self.p2.setXRange(self.timestampList[-1]-self.plotDuration, self.timestampList[-1], padding=0)

    def eventLoopInnerFun(self,conn):
        inPacket = Main.getEventPacket(conn)
        status = Main.checkPacket(inPacket)
        if(status!=Main.STATUS_OK):
            return status 
        for i in range(0,Main.N_ELEMENTS):
            packetSlice = inPacket[Main.ELEMENT_SIZE*i:Main.ELEMENT_SIZE*i+Main.ELEMENT_SIZE]
            self.addSamples(packetSlice)
        self.plot()
        QtGui.QApplication.processEvents()    
        return Main.STATUS_OK

    def eventThreadFun(self):
        print("Starting event thread")
        self.s.bind((self.host, Main.EVENT_PORT))
        self.s.listen()
        while True:
            (conn, addr) = self.s.accept()
            with conn:
                print('Event thread connected by', addr)
                self.clearData()
                self.beginTime = Main.currentTimeMillis()/1000
                print("Begin timestamp: {}".format(self.beginTime))
                while (True):
                    status = self.eventLoopInnerFun(conn)
                    if (status == Main.STATUS_FINISHED):
                        print("YEE-HAW")
                        break

    def calibrationThreadFun(self):    
        print("Starting calibration thread")
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((self.host, Main.CALIBRATION_PORT))
        s.listen()
        while True:
            (conn, addr) = s.accept()
            with conn:
                print('Calibration thread connected by', addr)
                while True:
                    inPacket = conn.recv(Main.CALIBRATION_PACKET_SIZE)
                    hostReceiveTime = Main.currentTimeMillis()
                    if (len(inPacket)==0): 
                        print("Client is done calibrating")
                        break 
                    [deviceSendTime, deviceReceiveTime] = struct.unpack(">qq",inPacket)
                    hostSendTime = Main.currentTimeMillis()
                    outPacket = struct.pack(">qq",hostReceiveTime,hostSendTime)
                    conn.sendall(outPacket)

    def start(self):
        print("Starting server.")
        self.calibrationThread = threading.Thread(target=self.calibrationThreadFun)
        self.calibrationThread.start()
        self.eventThread = threading.Thread(target=self.eventThreadFun)
        self.eventThread.start()
        pg.QtGui.QApplication.exec_()        

if __name__ == "__main__":
    Main('192.168.1.100').start()
