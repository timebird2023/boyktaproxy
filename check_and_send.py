import os
import time
import requests
import concurrent.futures
import base64
import urllib3

# إخفاء تحذيرات SSL المزعجة عند استخدام بروكسيات مجانية
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ============================================
# ⚙️ الإعدادات (من GitHub Secrets)
# ============================================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY")
GH_PAT = os.environ.get("GH_PAT")
OUTPUT_FILE = "active_proxies.txt"

# 💡 التعديل الجذري: الفحص يتم مباشرة على سيرفرات أوريدو لضمان تجاوز حماية Cloudflare!
TEST_URL = "https://apis.ooredoo.dz/api/ooredoo-bff/users/status?msisdn=213550000000"
TEST_HEADERS = {
    "User-Agent": "Dart/3.11 (dart:io)",
    "accept-encoding": "gzip",
    "x-platform-origin": "mobile-android",
    "platform": "android",
    "x-version": "1.5.15"
}

TIMEOUT = 5 # رفعنا الوقت قليلاً لأن أوريدو محمية
MAX_WORKERS = 350

# ============================================
# 🚀 أسرع وأقوى مصادر البروكسي العالمية + GeoNode API
# ============================================
TEXT_SOURCES = [
    "https://api.proxyscrape.com/v4/free-proxy-list/get?request=get_proxies&proxy_format=ipport&format=text&protocol=http",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/zevtyardt/proxy-list/main/http.txt",
    "https://raw.githubusercontent.com/rdavydov/proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt"
]

GEONODE_API = "https://proxylist.geonode.com/api/proxy-list?limit=300&page=1&sort_by=last_checked&sort_type=desc&protocols=http%2Chttps"

def fetch_proxies():
    print("📥 جاري سحب البروكسيات من المصادر...")
    proxies = set()
    session = requests.Session()
    
    for url in TEXT_SOURCES:
        try:
            response = session.get(url, timeout=5)
            if response.status_code == 200:
                lines = response.text.splitlines()
                for line in lines:
                    line = line.strip()
                    if ":" in line and not line.startswith("#"):
                        if not line.startswith("http"):
                            proxies.add(f"http://{line}")
                        else:
                            proxies.add(line)
        except Exception as e:
            pass

    try:
        res = session.get(GEONODE_API, timeout=6)
        if res.status_code == 200:
            data = res.json().get("data", [])
            for item in data:
                ip = item.get("ip")
                port = item.get("port")
                if ip and port:
                    proxies.add(f"http://{ip}:{port}")
    except Exception as e:
        pass
    
    print(f"✅ إجمالي البروكسيات الفريدة: {len(proxies)}")
    return list(proxies)

def check_proxy(proxy_url):
    proxies = {
        "http": proxy_url,
        "https": proxy_url
    }
    try:
        # الفحص الصارم: نرسل الطلب لأوريدو بهيدرات الموبايل
        res = requests.get(TEST_URL, headers=TEST_HEADERS, proxies=proxies, timeout=TIMEOUT, verify=False)
        
        # إذا ردت أوريدو بكود سليم (200) أو حتى (400) يعني أن البروكسي اخترق الحماية ولم يتم حظره!
        if res.status_code in [200, 400, 404]:
            # تأكيد إضافي: يجب ألا يعيد البروكسي صفحة HTML (كابتشا من Cloudflare)
            if "html" not in res.text.lower():
                return proxy_url
    except:
        pass
    return None

def update_github_file(file_path):
    if not GH_PAT or not GITHUB_REPOSITORY:
        return
    print("🚀 جاري تحديث الملف في المستودع...")
    api_url = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/contents/{file_path}"
    headers = {
        "Authorization": f"Bearer {GH_PAT}",
        "Accept": "application/vnd.github+json"
    }
    try:
        with open(file_path, "rb") as f:
            content_encoded = base64.b64encode(f.read()).decode("utf-8")
        
        sha = None
        get_res = requests.get(api_url, headers=headers)
        if get_res.status_code == 200:
            sha = get_res.json().get("sha")

        data = {
            "message": "⚡ Strict Auto-Update: Ooredoo Checked Proxies",
            "content": content_encoded,
            "branch": "main"
        }
        if sha:
            data["sha"] = sha

        requests.put(api_url, headers=headers, json=data)
    except:
        pass

def send_to_telegram(file_path, valid_count, total_count):
    if not BOT_TOKEN or not CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    caption = (
        f"⚡ <b>تم الفحص الصارم (Ooredoo Bypass) بنجاح!</b>\n\n"
        f"🔍 المفحوص: {total_count}\n"
        f"🎯 الدبابات الشغالة فعلياً: {valid_count}\n"
        f"⏱️ الوقت: {time.strftime('%Y-%m-%d %H:%M:%S UTC')}"
    )
    with open(file_path, 'rb') as f:
        try:
            requests.post(url, data={'chat_id': CHAT_ID, 'caption': caption, 'parse_mode': 'HTML'}, files={'document': f}, timeout=15)
        except:
            pass

def main():
    raw_proxies = fetch_proxies()
    if not raw_proxies:
        return

    valid_proxies = []
    start_time = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = executor.map(check_proxy, raw_proxies)
        for res in results:
            if res:
                valid_proxies.append(res)
    
    end_time = time.time()
    print(f"🏁 انتهى الفحص في {round(end_time - start_time, 2)} ثانية.")
    print(f"🟢 البروكسيات المتوافقة مع أوريدو: {len(valid_proxies)}")

    if valid_proxies:
        with open(OUTPUT_FILE, "w") as f:
            for p in valid_proxies:
                f.write(p + "\n")
        
        update_github_file(OUTPUT_FILE)
        send_to_telegram(OUTPUT_FILE, len(valid_proxies), len(raw_proxies))

if __name__ == "__main__":
    main()
