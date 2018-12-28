package com.infinitesnow.polimi.cm

import android.media.MediaPlayer
import android.util.Log
import java.io.IOException
import java.io.OutputStream
import java.net.Socket
import java.nio.ByteBuffer
import java.util.*
import kotlin.concurrent.schedule
import kotlin.concurrent.timerTask

class EventHandler(val activity: MainActivity){
    val TAG = "EventHandler"
    val PACKET_SIZE = 8
    val PORT = 10001
    val SERVER_IP = "192.168.1.100"

    var deltaT = 0.0

    var output: OutputStream? = null
    var connectThread: Thread? = null

    fun connect(){
        if (output!=null) {
            Log.d(TAG,"Not initiating another connection")
            return
        }
        connectThread = Thread {
            val s: Socket
            try {
                s = Socket(SERVER_IP, PORT)
                output = s!!.getOutputStream()
            } catch (e: IOException){
                Log.e(TAG,"Server not available")
                return@Thread
            }
        }
        connectThread!!.start()
    }

    fun sendEvent(){
        if (this.deltaT==0.0){
            Log.e(TAG,"Not calibrated")
            return
        }
        Thread {
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
                Log.e(TAG,"Server not available")
                return@Thread
            }
        }.start()
    }
}