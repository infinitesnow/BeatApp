package com.infinitesnow.polimi.cm

import android.app.Activity
import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorManager
import android.os.Bundle
import android.view.View
import android.widget.Button
import android.widget.TextView


class MainActivity : Activity() {
    var mCalibrator : Calibrator? = null
    var mEventHandler : EventHandler? = null
    var mSensorManager : SensorManager? = null
    var mSensor : Sensor? = null
    var mAccEventListener : AccEventListener? = null

    private var startstopButton: Button? = null
    val stopOnClickListener = View.OnClickListener{
        mEventHandler!!.stopFlag = true
        startstopButton!!.setOnClickListener(null)
    }
    val startOnClickListener = View.OnClickListener{
        mAccEventListener!!.init()
        mEventHandler!!.connect()
        mSensorManager!!.registerListener(mAccEventListener!!,mSensor!!,SensorManager.SENSOR_DELAY_GAME)
        startstopButton!!.setOnClickListener(stopOnClickListener)
    }

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
        startstopButton = findViewById<Button>(R.id.startstop_button)
        startstopButton!!.setOnClickListener(startOnClickListener)
    }

    fun calibrationCallback(done: Boolean, deltaT: Double, mse: Double){
        val calibrateButton = findViewById<TextView>(R.id.calibrate_button)
        calibrateButton.post{
            calibrateButton.setText(R.string.calibrate)
        }

        val mseTextView = findViewById<TextView>(R.id.mse_textview)
        if(done) {
            calibrateButton.post {
                calibrateButton.setBackgroundColor(this.getColor(R.color.green))
            }
            mseTextView.post {
                mseTextView.text = getString(R.string.calibration_info).format(deltaT.toLong(), mse)
            }
        } else {
            calibrateButton.post {
                calibrateButton.setBackgroundColor(this.getColor(R.color.red))
            }
            mseTextView.post {
                mseTextView.text = getString(R.string.calibration_failed).format(deltaT.toLong(), mse)
            }
        }
    }

    fun stopCallback(){
        mSensorManager!!.unregisterListener(mAccEventListener!!)
        startstopButton!!.setOnClickListener(startOnClickListener)
    }

}
