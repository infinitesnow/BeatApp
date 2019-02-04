package com.infinitesnow.polimi.cm

import android.media.midi.MidiOutputPort
import android.util.Log
import java.io.IOException
import java.io.OutputStream
import java.net.Socket
import java.nio.ByteBuffer

class EventHandler(val mContext : MainActivity){
    private val TAG = "EventHandler"
    private val SERVER_IP = "192.168.1.100"
    private val EVENT_PORT = 10001
    private val PLAY_PORT = 10002
    private val PLAY_DELAY = 3000L

    private var eventOutput: OutputStream? = null
    private var playOutput: OutputStream? = null
    private var connectThread: Thread? = null
    private var mCalibrator: Calibrator? = null

    var stopFlag = false
    var connected = false
    var playing = false

    fun connect(){
        if(connected) return
        mCalibrator = mContext.mCalibrator
        connectThread = Thread {
            Log.d(TAG, "Connecting event and play thread...")
            val es: Socket
            val ps: Socket
            try {
                es = Socket(SERVER_IP, EVENT_PORT)
                ps = Socket(SERVER_IP, PLAY_PORT)
                eventOutput = es.getOutputStream()
                Log.i(TAG, "Play thread connected")
                playOutput = ps.getOutputStream()
                Log.i(TAG, "Event thread connected")
                connected = true
            } catch (e: IOException){
                Log.e(TAG,"Server not available")
                mContext.stopCallback()
                return@Thread
            }
        }
        connectThread!!.start()
    }

    fun play(){
        if (!mCalibrator!!.calibrated){
            Log.e(TAG,"Not calibrated")
            mContext.stopCallback()
            return
        }
        val outPacket = ByteArray(8)
        val packetBuffer = ByteBuffer.wrap(outPacket)
        val curTime = System.currentTimeMillis()
        val playTime = curTime+PLAY_DELAY+mCalibrator!!.deltaT.toLong()
        packetBuffer.putLong(playTime)
        sendPlayPacket(outPacket, true)
    }

    fun stop(eventPacketLength : Int){
        stopFlag=false
        val stopEventPacket = ByteArray(eventPacketLength)
        val stopEventBuffer = ByteBuffer.wrap(stopEventPacket)
        Log.i(TAG,"Exiting...")
        for (i in 0 until eventPacketLength){
            stopEventBuffer.put(0xFF.toByte())
        }
        sendEventPacket(stopEventPacket)
        val stopPlayPacket = byteArrayOf(0xFF.toByte(),0xFF.toByte(),0xFF.toByte(),0xFF.toByte(),
            0xFF.toByte(),0xFF.toByte(),0xFF.toByte(),0xFF.toByte())
        sendPlayPacket(stopPlayPacket,false)

        mContext.stopCallback()
    }

    fun sendPlayPacket(outPacket: ByteArray, value: Boolean){
        Thread {
            connectThread!!.join()
            if(!connected) {
                Log.e(TAG,"Not connected, not sending")
                return@Thread
            }
            try {
                Log.v(TAG, "Sending request...")
                playOutput!!.write(outPacket)
                Log.v(TAG, "Done.")
                playing = value
            } catch (e: IOException) {
                Log.e(TAG, "Output stream not available")
                connected = false
                mContext.stopCallback()
                return@Thread
            }
        }.start()
    }

    fun sendEventPacket(outPacket: ByteArray){
        Thread {
            connectThread!!.join()
            if(!connected) {
                Log.e(TAG,"Not connected, not sending")
                return@Thread
            }
            if(!playing) {
                Log.e(TAG,"Not playing, not sending")
                return@Thread
            }
            try {
                Log.v(TAG, "Pushing data...")
                eventOutput!!.write(outPacket)
            } catch (e: IOException) {
                Log.e(TAG, "Output stream not available")
                connected = false
                mContext.stopCallback()
                return@Thread
            }
        }.start()
    }

    fun sendEvent(valuesList: List<FloatArray>, timestampList: List<Long>){
        if (!mCalibrator!!.calibrated){
            Log.e(TAG,"Not calibrated")
            mContext.stopCallback()
            return
        }
        check(valuesList.size == timestampList.size)
        val packetLength = valuesList.size
        val packetSize = packetLength*(8+3*4)
        val outPacket = ByteArray(packetSize)

        val packetBuffer = ByteBuffer.wrap(outPacket)
        if (stopFlag==true){
            stop(packetSize)
            return
        }
        for (i in 0 until packetLength){
            val value = valuesList[i]
            packetBuffer.putFloat(value[0])
            packetBuffer.putFloat(value[1])
            packetBuffer.putFloat(value[2])
            packetBuffer.putLong(timestampList[i])
        }

        sendEventPacket(outPacket)
    }
}