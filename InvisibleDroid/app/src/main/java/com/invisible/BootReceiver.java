package com.invisible;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.os.Build;

/**
 * مستقبل BOOT - يشغل الخدمة تلقائياً بعد إعادة تشغيل الجهاز
 */
public class BootReceiver extends BroadcastReceiver {

    @Override
    public void onReceive(Context context, Intent intent) {
        String action = intent.getAction();
        if (action == null) return;

        switch (action) {
            case Intent.ACTION_BOOT_COMPLETED:
            case "android.intent.action.QUICKBOOT_POWERON":
                startService(context);
                // تأخير ثم إعادة تشغيل للاحتياط
                scheduleRetry(context, 10000);
                break;

            case Intent.ACTION_USER_PRESENT:
            case Intent.ACTION_SCREEN_ON:
                // تشغيل احتياطي عند فتح الشاشة
                startService(context);
                break;
        }
    }

    private void startService(Context context) {
        try {
            Intent si = new Intent(context, MainService.class);
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(si);
            } else {
                context.startService(si);
            }
        } catch (Exception ignored) {}
    }

    private void scheduleRetry(final Context context, long delayMs) {
        new android.os.Handler(context.getMainLooper()).postDelayed(new Runnable() {
            @Override
            public void run() {
                startService(context);
            }
        }, delayMs);
    }
}
