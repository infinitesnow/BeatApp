package com.infinitesnow.polimi.cm

import android.app.Activity
import android.os.Bundle
import android.widget.Button
import android.widget.TextView


class MainActivity : Activity() {
    var mCalibrator = Calibrator(this)
    val mEventHandler = EventHandler(this)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        val calibrateButton = findViewById<Button>(R.id.calibrate_button)
        calibrateButton.setOnClickListener {
            findViewById<TextView>(R.id.calibrate_button).setText(R.string.calibrating)
            mCalibrator = Calibrator(this)
            mCalibrator.calibrate()
        }
        val playButton = findViewById<Button>(R.id.play_button)
        playButton.setOnClickListener {
            mEventHandler.deltaT = mCalibrator.deltaT
            mEventHandler.connect()
            mEventHandler.sendEvent()
        }
    }

    fun mseCallback(deltaT: Double,mse: Double){
        val mseTextView = findViewById<TextView>(R.id.mse_textview)
        mseTextView.post {
            mseTextView.text = "Calibrated: %dms. MSE: %.2fms".format(deltaT.toLong(), mse)
        }
        val calibrateButton = findViewById<TextView>(R.id.calibrate_button)
        calibrateButton.post{
            calibrateButton.setText(R.string.calibrate)
        }
    }

}
