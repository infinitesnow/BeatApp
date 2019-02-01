package com.infinitesnow.polimi.cm

import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.util.Log

class AccEventListener( val mEventHandler : EventHandler, val mCalibrator: Calibrator) : SensorEventListener{
    val TAG = "AccListener"

    val BUFFER_SIZE = 10

    var valueList = ArrayList<FloatArray>(0)
    var timestampList = ArrayList<Long>(0)

    var lastPacketSentTime = System.currentTimeMillis()

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {}

    override fun onSensorChanged(e : SensorEvent) {
        if (mCalibrator.deltaT==0.0){
            Log.e(TAG,"Not calibrated")
            return
        }

        val v = e.values!!
        val timestamp = (e.timestamp.toDouble()/1000000).toLong() + mCalibrator.deltaT.toLong()
        val finalValueList : ArrayList<FloatArray>?
        val finalTimestampList : ArrayList<Long>?

        if (valueList.size >= BUFFER_SIZE && timestampList.size >= BUFFER_SIZE){
            finalValueList = valueList
            finalTimestampList = timestampList
            valueList = ArrayList(0)
            timestampList = ArrayList(0)
            val now = System.currentTimeMillis()
            Log.i(TAG, "Sending event after ${(now-lastPacketSentTime).toFloat()/1000} seconds...")
            lastPacketSentTime = now
            mEventHandler.sendEvent(finalValueList,finalTimestampList)
            Log.i(TAG,"Sent.")
        }
        valueList.add(v)
        timestampList.add(timestamp)
    }
}