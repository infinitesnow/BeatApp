package com.infinitesnow.polimi.cm

import android.app.Activity
import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.os.Bundle
import android.widget.Button
import android.widget.TextView


class MainActivity : Activity() {
    var mCalibrator : Calibrator? = null
    var mEventHandler : EventHandler? = null
    var mSensorManager : SensorManager? = null
    var mSensor : Sensor? = null
    var mAccEventListener : AccEventListener? = null


    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        mCalibrator = Calibrator(this)
        mEventHandler = EventHandler(this)
        mSensorManager = getSystemService(Context.SENSOR_SERVICE) as SensorManager
        mSensor = mSensorManager!!.getDefaultSensor(Sensor.TYPE_LINEAR_ACCELERATION)
        mAccEventListener = AccEventListener(mEventHandler!!,mCalibrator!!)

        val calibrateButton = findViewById<Button>(R.id.calibrate_button)
        calibrateButton.setOnClickListener {
            findViewById<TextView>(R.id.calibrate_button).setText(R.string.calibrating)
            mCalibrator!!.calibrate()
        }
    }

    fun calibrationCallback(deltaT: Double, mse: Double){
        val mseTextView = findViewById<TextView>(R.id.mse_textview)
        mseTextView.post {
            mseTextView.text = "Calibrated: %dms. MSE: %.2fms".format(deltaT.toLong(), mse)
        }
        val calibrateButton = findViewById<TextView>(R.id.calibrate_button)
        calibrateButton.post{
            calibrateButton.setText(R.string.calibrate)
        }
        mEventHandler!!.connect()
        mSensorManager!!.registerListener(mAccEventListener!!,mSensor!!,SensorManager.SENSOR_DELAY_GAME)
    }

    fun detachSensorListener(){
        mSensorManager!!.unregisterListener(mAccEventListener!!)
    }

}
