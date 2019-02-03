package com.infinitesnow.polimi.cm

import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.util.Log
import java.util.*

class AccEventListener( val mEventHandler : EventHandler, val mCalibrator: Calibrator) : SensorEventListener{
    val TAG = "AccListener"

    val BUFFER_SIZE = 3

    private var valueList = LinkedList<FloatArray>()
    private var timestampList = LinkedList<Long>()

    var lastPacketSentTime = System.currentTimeMillis()


    fun init(){
        valueList = LinkedList()
        timestampList = LinkedList()
    }

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {}

    override fun onSensorChanged(e : SensorEvent) {
        val v = e.values!!
        val timestamp = System.currentTimeMillis() + mCalibrator.deltaT.toLong()
        val finalValueList : LinkedList<FloatArray>?
        val finalTimestampList : LinkedList<Long>?

        check(valueList.size==timestampList.size)
        Log.v(TAG,"New value: %.3f,%.3f,%.3f".format(v[0],v[1],v[2]))

        if (valueList.size >= BUFFER_SIZE){
            finalValueList = valueList
            finalTimestampList = timestampList
            valueList = LinkedList()
            timestampList = LinkedList()
            val now = System.currentTimeMillis()
            Log.v(TAG, "Sending event after ${(now-lastPacketSentTime).toFloat()/1000} seconds...")
            lastPacketSentTime = now
            mEventHandler.sendEvent(finalValueList,finalTimestampList)
            Log.v(TAG,"Sent.")
        }
        valueList.add(v.clone())
        timestampList.add(timestamp)
    }
}