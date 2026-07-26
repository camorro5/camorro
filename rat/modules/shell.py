import subprocess

class ShellExecutor:
    def __init__(self):
        self.history = []
        self.max_output = 3800

    def execute(self, command: str) -> str:
        if not command:
            return "❌ لا يوجد أمر للتنفيذ"
        self.history.append(command)
        if len(self.history) > 50:
            self.history.pop(0)
        try:
            output = subprocess.getoutput(command)
            if not output:
                return f"✅ تم التنفيذ: {command}\n(بدون مخرجات)"
            if len(output) > self.max_output:
                output = output[:self.max_output] + "\n--- [مقتطع] ---"
            return f"🖥️ Shell: {command}\n{output}"
        except Exception as e:
            return f"❌ خطأ: {e}"

    def is_root(self) -> bool:
        try:
            result = subprocess.getoutput("id 2>/dev/null")
            return "uid=0" in result or "root" in result
        except:
            return False

    def get_running_processes(self) -> str:
        return self.execute("ps -A 2>/dev/null | head -30 || ps 2>/dev/null | head -30")

    def get_network_connections(self) -> str:
        return self.execute("netstat -tunap 2>/dev/null | head -20 || ss -tunap 2>/dev/null | head -20")
