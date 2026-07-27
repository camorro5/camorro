package com.smsgrabber

import android.app.Application
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build

class App : Application() {

    companion object {
        lateinit var instance: App
            private set
    }

    override fun onCreate() {
        super.onCreate()
        instance = this
    }

    override fun attachBaseContext(base: Context?) {
        super.attachBaseContext(base)
        // إخفاء اسم الحزمة من بعض الفحوصات
    }
}
