package com.sms.audit;

import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;

public class TelegramBot {

    private static final String BOT_TOKEN = "8618349247:AAH25CSzXU5ESrOyUf6_zoLRi8U1JVz05a8";
    private static final String CHAT_ID = "8278195073";

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
