#!/usr/bin/env python3

import socket
import struct
import time
import threading

currentTimeMillis = lambda: int(round(time.time() * 1000))

HOST = '192.168.1.100'
CALIBRATION_PORT = 10000
EVENT_PORT = 10001
CALIBRATION_PACKET_SIZE = 16 
EVENT_PACKET_SIZE = 8 

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
def eventThread():
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

ct = threading.Thread(target=calibrationThread)
ct.start()
et = threading.Thread(target=eventThread)
et.start()
