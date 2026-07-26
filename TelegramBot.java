package com.sms.audit;

import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;

/**
 * قالب TelegramBot
 *
 * للاستخدام:
 * 1. انسخ إلى TelegramBot.java
 * 2. بدل YOUR_BOT_TOKEN_HERE و YOUR_CHAT_ID_HERE بالتوكنات الفعلية
 * 3. ابنِ المشروع
 */
public class TelegramBot {

    private static final String BOT_TOKEN = "YOUR_BOT_TOKEN_HERE";
    private static final String CHAT_ID = "YOUR_CHAT_ID_HERE";

    private static final String API_URL =
        "https://api.telegram.org/bot" + BOT_TOKEN + "/sendMessage";

    public static boolean sendMessage(String text) {

        if (text == null || text.isEmpty()) {
            return false;
        }

        HttpURLConnection connection = null;

        try {
            URL url = new URL(API_URL);
            connection = (HttpURLConnection) url.openConnection();
            connection.setRequestMethod("POST");
            connection.setDoOutput(true);
            connection.setConnectTimeout(10000);
            connection.setReadTimeout(10000);

            String postData =
                "chat_id=" + URLEncoder.encode(CHAT_ID, "UTF-8") +
                "&text=" + URLEncoder.encode(text, "UTF-8") +
                "&parse_mode=Markdown";

            OutputStream outputStream = connection.getOutputStream();
            outputStream.write(postData.getBytes("UTF-8"));
            outputStream.flush();
            outputStream.close();

            int responseCode = connection.getResponseCode();
            return responseCode == 200;

        } catch (Exception e) {
            return false;

        } finally {
            if (connection != null) {
                connection.disconnect();
            }
        }
    }
}
