package com.infinitesnow.polimi.cm

import android.util.Log
import java.io.IOException
import java.io.InputStream
import java.io.OutputStream
import java.net.Socket
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.*
import kotlin.math.exp
import kotlin.math.pow
import kotlin.math.sqrt

class Calibrator(val activity: MainActivity)
{
    val TAG = "Calibrator"

    val PACKET_SIZE = 16
    val PORT = 10000
    val SERVER_IP = "192.168.1.100"
    val N_CALIBRATION_STEPS = 500
    val OUTLIER_FILTER_COEFF = 1
    val DELTAT_ALPHA_0 = 1.0
    val DELTAT_ALPHA_BAR = 0.01
    val DELTAT_ALPHA_DECAY = 0.1
    val DELTAT_N_STEPS_REGIME = 10

    private var output : OutputStream? = null

    private val deviceSendTimeList = LinkedList<Long>()
    private val hostReceiveTimeList = LinkedList<Long>()
    private val hostSendTimeList = LinkedList<Long>()
    private val deviceReceiveTimeList = LinkedList<Long>()

    private var meanDeviceRTT = 0.0
    private var meanHostRTT = 0.0
    private var sigmaDeviceRTT = 0.0
    private var sigmaHostRTT = 0.0
    var deltaT = 0.0
    private var mse = 0.0

    private fun calibrateStep(output: OutputStream, input: InputStream)
    {
        val outPacket = ByteArray(PACKET_SIZE)
        val inPacket = ByteArray(PACKET_SIZE)

        val packetBuffer = ByteBuffer.wrap(outPacket)
        packetBuffer.putLong(deviceSendTimeList.peekLast())
        packetBuffer.putLong(deviceReceiveTimeList.peekLast())

        val deviceSendTime = System.currentTimeMillis()
        output.write(outPacket)
        input.read(inPacket)
        val deviceReceiveTime = System.currentTimeMillis()

        val hostValuesBuffer = ByteBuffer.wrap(inPacket).order(ByteOrder.BIG_ENDIAN).asLongBuffer()
        val hostValuesArray = LongArray(2)
        hostValuesBuffer.get(hostValuesArray)

        deviceSendTimeList.add(deviceSendTime)
        hostReceiveTimeList.add(hostValuesArray[0])
        hostSendTimeList.add(hostValuesArray[1])
        deviceReceiveTimeList.add(deviceReceiveTime)
    }

    fun calibrate()
    {
        deviceSendTimeList.add(-1)
        deviceReceiveTimeList.add(-1)

        Thread {
            val s: Socket
            try {
                s = Socket(SERVER_IP, PORT)
            } catch (e: IOException){
                Log.e(TAG,"Server not available")
                return@Thread
            }

            output = s.getOutputStream()
            val input = s.getInputStream()
            for (i in 0 until N_CALIBRATION_STEPS+1)
                calibrateStep(output!!,input)

            deviceSendTimeList.removeFirst()
            deviceReceiveTimeList.removeFirst()

            input.close()
            output!!.close()
            s.close()

            computeMeanRTT()
            Log.d(TAG, "Mean RTT: %.2f, %.2f".format(meanDeviceRTT,meanHostRTT))
            computeDeltaT()
            activity.mseCallback(this.deltaT,this.mse)
        }.start()
    }
    
    private fun computeDeltaT()
    {
        deltaT = 0.0
        var alpha = DELTAT_ALPHA_0
        var transmissionDelay: Double
        val errorList = LinkedList<Double>()
        for (i in 0 until N_CALIBRATION_STEPS){
            val deviceSendTime = deviceSendTimeList[i]
            val hostSendTime = hostSendTimeList[i]
            val deviceReceiveTime = deviceReceiveTimeList[i]
            val hostReceiveTime = hostReceiveTimeList[i]
            val nextHostReceiveTime = hostReceiveTimeList[i+1]
            val deviceRTT = deviceReceiveTime-deviceSendTime
            val hostRTT = nextHostReceiveTime-hostSendTime

            if (isOutlier(deviceRTT,meanDeviceRTT,sigmaDeviceRTT) ||
                isOutlier(hostRTT,meanHostRTT,sigmaHostRTT))
                continue
            transmissionDelay = (deviceRTT+hostRTT).toDouble() / 4
            val estimatedArrivalTime = deviceSendTime + (transmissionDelay + deltaT).toLong()
            val err = (estimatedArrivalTime-hostReceiveTime).toDouble()
            errorList.add(err)
            deltaT -= alpha * err
            alpha = DELTAT_ALPHA_BAR + (DELTAT_ALPHA_0-DELTAT_ALPHA_BAR)*exp(-DELTAT_ALPHA_DECAY * i)
        }
        repeat(DELTAT_N_STEPS_REGIME,{errorList.removeFirst()})
        this.mse = sqrt(errorList.map { el -> el.pow(2) }.average())
    }

    private fun computeMeanRTT()
    {
        val deviceRTTarray = LongArray(N_CALIBRATION_STEPS)
        val hostRTTarray = LongArray(N_CALIBRATION_STEPS)
        var rtt: Long
        for (i in 0 until N_CALIBRATION_STEPS) {
            rtt = deviceReceiveTimeList[i]-deviceSendTimeList[i]
            deviceRTTarray[i] = rtt
            rtt = hostReceiveTimeList[i+1]-hostSendTimeList[i]
            hostRTTarray[i] = rtt
        }

        meanDeviceRTT = deviceRTTarray.average()
        meanHostRTT = hostRTTarray.average()
        val sigmaDeviceRTTarray = deviceRTTarray.map { el -> (el-meanDeviceRTT).pow(2.0) }.toDoubleArray()
        val sigmaHostRTTarray = hostRTTarray.map { el -> (el-meanHostRTT).pow(2.0) }.toDoubleArray()
        sigmaDeviceRTT = sqrt(sigmaDeviceRTTarray.average())
        sigmaHostRTT = sqrt(sigmaHostRTTarray.average())

        filterMean()
    }

    private fun filterMean()
    {
        val filteredDeviceRTTlist = LinkedList<Long>()
        val filteredHostRTTlist = LinkedList<Long>()
        var rtt: Long
        for (i in 0 until N_CALIBRATION_STEPS) {
            rtt = deviceReceiveTimeList[i]-deviceSendTimeList[i]
            if (!isOutlier(rtt,meanDeviceRTT,sigmaDeviceRTT))
                filteredDeviceRTTlist.add(rtt)
            rtt = hostReceiveTimeList[i+1]-hostSendTimeList[i]
            if (!isOutlier(rtt,meanHostRTT,sigmaHostRTT))
                filteredHostRTTlist.add(rtt)
        }

        this.meanDeviceRTT = filteredDeviceRTTlist.toLongArray().average()
        this.meanHostRTT = filteredHostRTTlist.toLongArray().average()
    }
    
    private fun isOutlier( value: Long, mean: Double, sigma: Double) : Boolean 
    {
        return value-mean>OUTLIER_FILTER_COEFF*sigma
    }
}
