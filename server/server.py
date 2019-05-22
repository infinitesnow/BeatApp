#!/usr/bin/env python3
import socket
import struct
import time
import threading
import sched
from pyqtgraph.Qt import QtGui, QtCore
import PyQt5.QtCore
import pyqtgraph as pg
import numpy as np
from scipy.signal import butter
import pickle as p
import subprocess
import json

def bFilter(lowcutFreq, fs, filterOrder=5):
    nyquist = 0.5 * fs 
    lowcutFreqNorm = lowcutFreq / nyquist
    filterNum, filterDen = butter(filterOrder, [lowcutFreqNorm], btype='highpass')
    return filterNum, filterDen

class Main(QtCore.QObject):
    STATUS_OK = 0
    STATUS_EXITED = 1
    STATUS_INVALID = 2
    STATUS_FINISHED = 3
    
    CALIBRATION_PORT = 10000
    CALIBRATION_PACKET_SIZE = 16 

    EVENT_PORT = 10001
    EVENT_TIMEOUT = 600
    N_ELEMENTS = 3 
    ELEMENT_SIZE = (8+3*4) ### Bytes
    EVENT_PACKET_SIZE = N_ELEMENTS*ELEMENT_SIZE 

    PLOT_SIZE = 100

    SAMPLE_RATE = 50
    LOWCUT_FREQ = 0.5
    FILTER_ORDER = 5

    PLAY_PORT = 10002
    PLAY_PACKET_SIZE = 8 
    PLAY_TIMEOUT = 600
    SCORE_WINDOW_LENGTH = 5
    BEAT_GRID_SIZE = 0.03
    WEIGHT_FUN_EXP = 2.0 
    REPRODUCTION_DELAY = 0.05
    VEL_MODULE_CHECK_THRESHOLD = 0.5
    VEL_MODULE_CHECK_WINLENGTH = 5

    SCORE_FONT_SIZE = 75

    
    def currentTimeMillis():
        return int(round(time.time() * 1000))
    
    scoreSignal = QtCore.Signal(float,name="score")

    def __init__(self,host):
        QtCore.QObject.__init__(self)
        self.host = host
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.app = QtGui.QApplication([])
        self.win = pg.GraphicsWindow(title="Realtime plot")
        pg.setConfigOptions(antialias=True)
        self.plotDuration = Main.PLOT_SIZE*(1/Main.SAMPLE_RATE)

        self.scoreViewBox = pg.ViewBox() 
        self.scoreView = pg.TextItem("score", anchor=(0.5,0.5), border='w')
        self.scoreView.setPos(0.5,0.5)
        self.scoreView.setFont(pg.Qt.QtGui.QFont("Monospace", Main.SCORE_FONT_SIZE))
        self.scoreViewBox.addItem(self.scoreView, ignoreBounds=True) 
        self.scoreSignal.connect(self.setScore)

        self.velPlot = pg.PlotItem() 
        self.lineVelX = self.velPlot.plot()
        self.lineVelY = self.velPlot.plot()
        self.lineVelZ = self.velPlot.plot()
        self.lineVelX.setData(pen='r')
        self.lineVelY.setData(pen='g')
        self.lineVelZ.setData(pen='b')
        self.lineZC = self.velPlot.plot()
        self.lineZC.setData(pen='y')
        self.lineBeat = self.velPlot.plot()
        self.lineBeat.setData(pen='w')

        self.layout = pg.GraphicsLayout()
        self.layout.addItem(self.scoreViewBox,0,0)
        self.layout.addItem(self.velPlot,0,0)

        self.win.addItem(self.layout)

        self.filterNum, self.filterDen = bFilter(Main.LOWCUT_FREQ,Main.SAMPLE_RATE,Main.FILTER_ORDER)

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
        self.beatGrid = [0]*initSize
        self.zcEvents = list()
        self.beats = None

        self.beginTime = None
        self.playTime = None
        self.playDelay = None

        self.calibrationThread = None
        self.eventThread = None
        self.playThread = None
        self.playProcess = None

    def clearData(self):
        print("Clearing data")
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
        self.beatGrid = [0]*initSize
        self.zcEvents = list()

        self.beginTime = None
        self.playTime = None
        self.playDelay = 0

    def loadSongData(self):
        with open("song.json") as f:
            songData = json.load(f)
        
        beatsData = songData['annotations'][0]['data']
        self.beats = list()
        for beat in beatsData:
            self.beats.append(beat['time']-230)

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
            conn.settimeout(Main.EVENT_TIMEOUT)
            try:
                inPacket += conn.recv(Main.EVENT_PACKET_SIZE)
            except:
                return [] 
            #print("packet is "+str(len(inPacket))+" bytes long")
        return inPacket    

    def checkPacket(inPacket):
        if (len(inPacket)==0): 
            return Main.STATUS_EXITED
        elif len(inPacket)!=Main.EVENT_PACKET_SIZE:
            print("Received invalid packet of size {} (size is {})".format(len(inPacket),Main.EVENT_PACKET_SIZE))
            return Main.STATUS_INVALID 
        else:
            for i in range(0,Main.EVENT_PACKET_SIZE):
                if (inPacket[i]!=255): 
                    return Main.STATUS_OK
            print("Received event stop packet")
            return Main.STATUS_FINISHED 
    
    def addSamples(self,packetSlice):
       newAccX, newAccY, newAccZ, newTimestamp = struct.unpack(">fffq",packetSlice)
       newTimestamp=newTimestamp/1000-self.beginTime-Main.REPRODUCTION_DELAY
       ###print("t: {}".format(newTimestamp))
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
    
       eventTimestamp = (newTimestamp+self.timestampList[-1])/2
       if ( (np.sign(self.filtVelY[-1])-np.sign(self.filtVelY[-2]))>1 and\
            abs(sum(self.filtVelY[-Main.VEL_MODULE_CHECK_WINLENGTH:]))>Main.VEL_MODULE_CHECK_THRESHOLD):
           self.zcEvents.append(eventTimestamp)
           self.zc[-1]=1
           self.zc.append(1)
       else:
           self.zc.append(0)
       beatDistancesFromTimestamp = [ abs(eventTimestamp-self.playDelay-b) for b in self.beats ]
       
       if (min(beatDistancesFromTimestamp)<Main.BEAT_GRID_SIZE):
           self.beatGrid.append(1) 
       else: self.beatGrid.append(0)

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
        windowBeat = self.beatGrid[-T:]
        self.lineBeat.setData(windowTimestamp,windowBeat)
    
        windowVelX = self.filtVelX[-T:]
        windowVelY = self.filtVelY[-T:]
        windowVelZ = self.filtVelZ[-T:]
        ###lineVelX.setData(windowTimestamp,windowVelX)
        self.lineVelY.setData(windowTimestamp,windowVelY)
        ###lineVelZ.setData(windowTimestamp,windowVelZ)
        self.velPlot.setXRange(self.timestampList[-1]-self.plotDuration, self.timestampList[-1], padding=0)

    @QtCore.pyqtSlot(float)
    def setScore(self,val):
        self.scoreView.setText("{0:.3f}".format(val))

    def computeScore(self):
        firstWindowTime = self.beats[Main.SCORE_WINDOW_LENGTH]
        currentSongTime = Main.currentTimeMillis()/1000-self.beginTime-self.playDelay
        if (currentSongTime<firstWindowTime): return
        lastPlayedBeat = np.argmax([b for b in self.beats if b<currentSongTime])
        windowBeats = self.beats[lastPlayedBeat-Main.SCORE_WINDOW_LENGTH:lastPlayedBeat+1]
        windowStartTime = windowBeats[0]
        shiftedEvents = [ e-self.playDelay for e in self.zcEvents ]
        windowEvents = [e for e in shiftedEvents if e>windowStartTime]
        if (len(windowEvents)==0): return
        score=[]
        for i in range(0,len(windowBeats)-1):
            thisBeatStart = windowBeats[i]
            thisBeatEnd = windowBeats[i+1]
            thisBeatLength = thisBeatEnd-thisBeatStart
            halfBeatLength = thisBeatLength/2
            wf = lambda x: 1/(halfBeatLength**(Main.WEIGHT_FUN_EXP-1)) * (x**Main.WEIGHT_FUN_EXP)
            distanceFromBeatStart = [wf(abs(e-thisBeatStart)) for e in windowEvents]
            distanceFromBeatEnd = [wf(abs(e-thisBeatEnd)) for e in windowEvents]
            score.append(max([ 10*(halfBeatLength - min([min(distanceFromBeatStart),min(distanceFromBeatEnd)]))/halfBeatLength ,0]))
        score=np.average(score)    
        self.scoreSignal.emit(score)
        ###print("***** \033[31mSCORE: {}\033[0m *****".format(score))

    def eventLoopInnerFun(self,conn):
        inPacket = Main.getEventPacket(conn)
        status = Main.checkPacket(inPacket)
        if(status!=Main.STATUS_OK):
            return status 
        if (self.beginTime is None or self.playDelay is None):
            print("Did not receive play packet yet, skipping")
            return Main.STATUS_OK
        for i in range(0,Main.N_ELEMENTS):
            packetSlice = inPacket[Main.ELEMENT_SIZE*i:Main.ELEMENT_SIZE*i+Main.ELEMENT_SIZE]
            self.addSamples(packetSlice)
            self.computeScore()
        self.plot()
        QtGui.QApplication.processEvents()    
        return Main.STATUS_OK

    def eventSessionLoop(self,conn):
       status = self.eventLoopInnerFun(conn)
       if (status == Main.STATUS_FINISHED):
           print("Acquisition finished!")
           ### print("***** \033[31mSCORE: {}\033[0m *****".format(self.computeScore()))
           with open("data.p","wb") as f:
               p.dump(self.zcEvents,f)
           self.clearData()
           return Main.STATUS_FINISHED 
       if (status == Main.STATUS_EXITED):
           print("Client disconnected from event handler.")
           self.stopSong()
           return Main.STATUS_EXITED

    def eventThreadFun(self):
        print("Starting event thread")
        self.s.bind((self.host, Main.EVENT_PORT))
        self.s.listen()
        while True:
            (conn, addr) = self.s.accept()
            print('Event thread connected by', addr)
            with conn:
                while True:
                    status = self.eventSessionLoop(conn)
                    if (status==Main.STATUS_EXITED):
                        break

    def calibrationSessionLoop(self,conn):
        inPacket = conn.recv(Main.CALIBRATION_PACKET_SIZE)
        hostReceiveTime = Main.currentTimeMillis()
        if (len(inPacket)==0): 
            print("Client is done calibrating")
            return Main.STATUS_FINISHED 
        [deviceSendTime, deviceReceiveTime] = struct.unpack(">qq",inPacket)
        hostSendTime = Main.currentTimeMillis()
        outPacket = struct.pack(">qq",hostReceiveTime,hostSendTime)
        conn.sendall(outPacket)
        return Main.STATUS_OK

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
                    status = self.calibrationSessionLoop(conn)
                    if (status==Main.STATUS_FINISHED):
                        break
    
    def startPlayProcess(self):
        self.playProcess = subprocess.Popen(['cvlc','','song.wav'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL )

    def stopSong(self):
        if not self.playProcess is None:
            self.playProcess.kill()

    def playSong(self):
        print("Playing at time ",self.playTime-self.beginTime)
        mScheduler = sched.scheduler(timefunc=time.time)
        mScheduler.enterabs(self.playTime, 0, self.startPlayProcess)
        mScheduler.run()

    def playSessionLoop(self,conn):
        conn.settimeout(Main.PLAY_TIMEOUT)
        try:
            inPacket = conn.recv(Main.PLAY_PACKET_SIZE)
        except:
            inPacket = []
        if (list(inPacket) == [255]*8):
            print("Received song stop packet")
            self.stopSong()
            return Main.STATUS_FINISHED
        if (len(inPacket)==0): 
            print("Client disconnected from audio player")
            self.stopSong()
            return Main.STATUS_EXITED
        if (len(inPacket)!=8): 
            print("Invalid packet of length ",len(inPacket))
            return Main.STATUS_INVALID
        self.beginTime = Main.currentTimeMillis()/1000
        print("Begin timestamp: {}".format(self.beginTime))
        [self.playTime] = struct.unpack(">q",inPacket)
        self.playTime/=1000
        self.playDelay = self.playTime-self.beginTime
        self.playSong()
        return Main.STATUS_OK

    def playThreadFun(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((self.host, Main.PLAY_PORT))
        s.listen()
        while True:
            (conn, addr) = s.accept()
            print('Audio player connected by ', addr)
            with conn:
                while True:
                    status = self.playSessionLoop(conn)
                    if (status==Main.STATUS_EXITED):
                        break

    def start(self):
        print("Starting server.")
        self.loadSongData()
        self.calibrationThread = threading.Thread(target=self.calibrationThreadFun)
        self.calibrationThread.start()
        self.eventThread = threading.Thread(target=self.eventThreadFun)
        self.eventThread.start()
        self.playThread = threading.Thread(target=self.playThreadFun)
        self.playThread.start()
        pg.QtGui.QApplication.exec_()        

if __name__ == "__main__":
    Main('192.168.1.100').start()
