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

# تقليل الـ Timeout لضمان استبعاد أي بروكسي بطيء فوراً
TEST_URL = "http://httpbin.org/ip" 
TIMEOUT = 6 
MAX_WORKERS = 200  # زيادة عدد الخيوط لفحص عدد هائل في ثوانٍ

# ============================================
# 🚀 أقوى وأسرع مصادر البروكسي (High-Speed & Fresh APIs)
# ============================================
SOURCES = [
    # 1. ProxyScrape API المباشر (سريع جداً ومحدث دائماً)
    "https://api.proxyscrape.com/v4/free-proxy-list/get?request=get_proxies&proxy_format=ipport&format=text&protocol=http",
    
    # 2. مستودع Monosans (أحد أنظف وأسرع القوائم المحدثة كل دقائق)
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    
    # 3. مستودع TheSpeedX الشهير للـ HTTP
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    
    # 4. مستودع Zevtyardt المحدث باستمرار
    "https://raw.githubusercontent.com/zevtyardt/proxy-list/main/http.txt",
    
    # 5. مستودع Rdavydov النظيف
    "https://raw.githubusercontent.com/rdavydov/proxy-list/main/proxies/http.txt"
]

def fetch_proxies():
    print("📥 جاري سحب البروكسيات من أسرع المصادر العالمية...")
    proxies = set()
    
    # استخدام Session لتسريع طلبات التحميل من المصادر
    session = requests.Session()
    for url in SOURCES:
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
    
    print(f"✅ تم جمع {len(proxies)} بروكسي فريد، جاري الفحص الخاطف...")
    return list(proxies)

def check_proxy(proxy_url):
    proxies = {
        "http": proxy_url,
        "https": proxy_url
    }
    try:
        # فحص صارم وسريع (3 ثواني كحد أقصى) للتأكد من السرعة
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
            "message": "⚡ Fast auto-update proxies",
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
        f"⚡ <b>تم الفحص السريع بنجاح!</b>\n\n"
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
    
    # فحص فائق السرعة بـ 200 خيط معالجة متزامن
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
