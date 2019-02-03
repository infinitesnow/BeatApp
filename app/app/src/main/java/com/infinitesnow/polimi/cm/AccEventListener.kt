package com.infinitesnow.polimi.cm

import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.util.Log
import java.util.*

class AccEventListener( val mEventHandler : EventHandler, val mCalibrator: Calibrator) : SensorEventListener{
    val TAG = "AccListener"

    val BUFFER_SIZE = 3

    var valueList = LinkedList<FloatArray>()
    var timestampList = LinkedList<Long>()

    var lastPacketSentTime = System.currentTimeMillis()

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {}

    override fun onSensorChanged(e : SensorEvent) {
        if (mCalibrator.deltaT==0.0){
            Log.e(TAG,"Not calibrated")
            return
        }

        val v = e.values!!
        val timestamp = System.currentTimeMillis() + /*((e.timestamp - System.nanoTime()) / 1000000) +*/ mCalibrator.deltaT.toLong()
        val finalValueList : LinkedList<FloatArray>?
        val finalTimestampList : LinkedList<Long>?

        check(valueList.size==timestampList.size)
        Log.i(TAG,"New value: %.3f,%.3f,%.3f".format(v[0],v[1],v[2]))

        if (valueList.size >= BUFFER_SIZE){
            finalValueList = valueList
            finalTimestampList = timestampList
            valueList = LinkedList()
            timestampList = LinkedList()
            val now = System.currentTimeMillis()
            Log.i(TAG, "Sending event after ${(now-lastPacketSentTime).toFloat()/1000} seconds...")
            lastPacketSentTime = now
            mEventHandler.sendEvent(finalValueList,finalTimestampList)
            Log.i(TAG,"Sent.")
        }
        valueList.add(v.clone())
        timestampList.add(timestamp)
    }
}