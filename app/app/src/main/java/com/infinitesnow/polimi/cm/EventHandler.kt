package com.infinitesnow.polimi.cm

import android.util.Log
import java.io.IOException
import java.io.OutputStream
import java.net.Socket
import java.nio.ByteBuffer

class EventHandler(val mContext : MainActivity){
    private val TAG = "EventHandler"
    private val PORT = 10001
    private val SERVER_IP = "192.168.1.100"

    private var output: OutputStream? = null
    private var connectThread: Thread? = null
    private var mCalibrator: Calibrator? = null

    fun connect(){
        mCalibrator = mContext.mCalibrator
        connectThread = Thread {
            Log.i(TAG, "Connecting event thread...")
            val s: Socket
            try {
                s = Socket(SERVER_IP, PORT)
                output = s.getOutputStream()
            } catch (e: IOException){
                Log.e(TAG,"Server not available")
                return@Thread
            }
        }
        connectThread!!.start()
    }

    /*val playSound = Thread {
        connectThread!!.join()
        var mp = MediaPlayer.create(activity.applicationContext, R.raw.sound_fx)
        try {
            val outPacket = ByteArray(PACKET_SIZE)
            val packetBuffer = ByteBuffer.wrap(outPacket)
            val deviceScheduledTime = System.currentTimeMillis()
            //Timer().schedule( timerTask{mp.start()}, Date(deviceScheduledTime + 1000))
            val hostScheduledTime = deviceScheduledTime + deltaT.toLong()
            packetBuffer.putLong(hostScheduledTime)
            output!!.write(outPacket)
        } catch (e: IOException){
            Log.e(TAG,"Output stream not available")
            return@Thread
        }
    }*/

    fun sendEvent(valuesList: ArrayList<FloatArray>, timestampList: ArrayList<Long>){
        if (mCalibrator!!.deltaT==0.0){
            Log.e(TAG,"Not calibrated")
            return
        }

        check(valuesList.size == timestampList.size)
        val packetSize = valuesList.size
        val outPacket = ByteArray(packetSize*(8+3*4))

        val packetBuffer = ByteBuffer.wrap(outPacket)
        for (i in 0 until packetSize){
            val value = valuesList[i]
            packetBuffer.putFloat(value[0])
            packetBuffer.putFloat(value[1])
            packetBuffer.putFloat(value[2])
            packetBuffer.putLong(timestampList[i])
        }

        Thread {
            connectThread!!.join()
            try {
                Log.i(TAG, "Pushing data...")
                output!!.write(outPacket)
            } catch (e: IOException) {
                Log.e(TAG, "Output stream not available")
                mContext.detachSensorListener()
                return@Thread
            }
        }.start()
    }
}