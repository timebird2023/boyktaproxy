import os
import time
import requests
import concurrent.futures
import base64

# ============================================
# ⚙️ الإعدادات (من GitHub Secrets)
# ============================================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY")
GH_PAT = os.environ.get("GH_PAT")
OUTPUT_FILE = "active_proxies.txt"

TEST_URL = "http://httpbin.org/ip" 
TIMEOUT = 6 
MAX_WORKERS = 200

# ============================================
# 🚀 أسرع وأقوى مصادر البروكسي العالمية + GeoNode API
# ============================================
TEXT_SOURCES = [
    # 1. ProxyScrape API المباشر (سريع جداً ومحدث دائماً)
    "https://api.proxyscrape.com/v4/free-proxy-list/get?request=get_proxies&proxy_format=ipport&format=text&protocol=http",
    
    # 2. مستودع Monosans (أحد أنظف وأسرع القوائم المحدثة)
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    
    # 3. مستودع TheSpeedX الشهير للـ HTTP
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    
    # 4. مستودع Zevtyardt المحدث باستمرار
    "https://raw.githubusercontent.com/zevtyardt/proxy-list/main/http.txt",
    
    # 5. مستودع Rdavydov النظيف
    "https://raw.githubusercontent.com/rdavydov/proxy-list/main/proxies/http.txt",
    
    # 6. مستودع Hookzof للـ Proxy المدمج
    "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt"
]

# GeoNode Free Proxy API المعتمد (يسحب أفضل البروكسيات المرتبة حسب وقت الفحص)
GEONODE_API = "https://proxylist.geonode.com/api/proxy-list?limit=300&page=1&sort_by=last_checked&sort_type=desc&protocols=http%2Chttps"

def fetch_proxies():
    print("📥 جاري سحب البروكسيات من أسرع وأقوى المصادر العالمية و GeoNode...")
    proxies = set()
    session = requests.Session()
    
    # 1. سحب المصادر النصية
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
            print(f"⚠️ تجاوزنا مصدراً بطيئاً: {e}")

    # 2. سحب من GeoNode API وتحويلها بصيغة IP:Port
    try:
        res = session.get(GEONODE_API, timeout=6)
        if res.status_code == 200:
            data = res.json().get("data", [])
            for item in data:
                ip = item.get("ip")
                port = item.get("port")
                if ip and port:
                    proxies.add(f"http://{ip}:{port}")
            print(f"✅ تم سحب بروكسيات GeoNode بنجاح.")
    except Exception as e:
        print(f"⚠️ فشل جلب مصادر GeoNode: {e}")
    
    print(f"✅ إجمالي البروكسيات الفريدة التي تم جمعها: {len(proxies)}")
    return list(proxies)

def check_proxy(proxy_url):
    proxies = {
        "http": proxy_url,
        "https": proxy_url
    }
    try:
        res = requests.get(TEST_URL, proxies=proxies, timeout=TIMEOUT)
        if res.status_code == 200:
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
            "message": "⚡ Fast auto-update proxies with GeoNode",
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
        f"⚡ <b>تم الفحص السريع بنجاح (مع GeoNode)!</b>\n\n"
        f"🔍 المفحوص: {total_count}\n"
        f"🟢 السريعة والشغالة: {valid_count}\n"
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
    print(f"🏁 انتهى الفحص في {round(end_time - start_time, 2)} ثانية فقط!")
    print(f"🟢 البروكسيات الصاروخية الشغالة: {len(valid_proxies)}")

    if valid_proxies:
        with open(OUTPUT_FILE, "w") as f:
            for p in valid_proxies:
                f.write(p + "\n")
        
        update_github_file(OUTPUT_FILE)
        send_to_telegram(OUTPUT_FILE, len(valid_proxies), len(raw_proxies))

if __name__ == "__main__":
    main()
