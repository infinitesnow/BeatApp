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

import matplotlib.pyplot as plt
import numpy
EVENT_PORT = 10001
N_ELEMENTS = 10 
ELEMENT_SIZE = (8+3*4) ### Bytes
EVENT_PACKET_SIZE = N_ELEMENTS*ELEMENT_SIZE 
PLOT_SIZE = 500

def eventThread():
    valuesList = [] 
    timestampList = [] 
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((HOST, EVENT_PORT))
    s.listen()
    while True:
        (conn, addr) = s.accept()
        with conn:
            print('Connected by', addr)
            axis = plt.gca()
            axis.set_autoscale_on(True)
            lineX,lineY,lineZ = axis.plot([], [], [], [], [], [])
            plt.ion()
            while True:
                beginTime = currentTimeMillis()
                inPacket = conn.recv(EVENT_PACKET_SIZE)
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
                        x, y, z, timestamp = struct.unpack(">fffq",slice)
                        values = [x,y,z]
                        print(str(values),str(timestamp))
                        valuesList.extend(values) 
                        timestampList.append(timestamp)
                        #print("Lists are of size {},{}".format(len(valuesList),len(timestampList)))
                    
                    assert(3*len(timestampList)==len(valuesList))
                    if len(timestampList)>PLOT_SIZE:
                        timestampList = timestampList[-PLOT_SIZE:]
                        valuesList = valuesList[-3*PLOT_SIZE:]
                    lineX.set_xdata(timestampList)
                    lineX.set_ydata(valuesList[0::3])
                    lineY.set_xdata(timestampList)
                    lineY.set_ydata(valuesList[1::3])
                    lineZ.set_xdata(timestampList)
                    lineZ.set_ydata(valuesList[2::3])
                    axis.relim()
                    axis.autoscale_view(True,True,True)
                    plt.draw()
                    plt.pause(0.001)

ct = threading.Thread(target=calibrationThread)
ct.start()
et = threading.Thread(target=eventThread)
et.start()
