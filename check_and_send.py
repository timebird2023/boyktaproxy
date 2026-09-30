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
GITHUB_TOKEN = os.environ.get("GH_PAT")  # توكن صلاحيات GitHub لتحديث الملف آلياً
REPO_NAME = os.environ.get("GITHUB_REPOSITORY")  # مثال: username/repo
OUTPUT_FILE = "active_proxies.txt"

TEST_URL = "http://httpbin.org/ip" 
TIMEOUT = 5
MAX_WORKERS = 150

# ============================================
# 🌐 مصادر HTTP/HTTPS قوية وموثوقة ومطلوبة بشدة
# ============================================
SOURCES = [
    # المصادر الأساسية السريعة
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "https://api.proxyscrape.com/v4/free-proxy-list/get?request=get_proxies&proxy_format=ipport&format=text&protocol=http",
    "https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS_RAW.txt",
    "https://raw.githubusercontent.com/mmpx12/proxy-list/master/http.txt",
    
    # مصادر إضافية مشهورة بموثوقيتها وتجديدها المستمر
    "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt", # يحتوي على HTTP مدمج أحياناً
    "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/proxy-list.txt",
    "https://raw.githubusercontent.com/rdavydov/proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/zevtyardt/proxy-list/main/http.txt",
    "https://www.proxy-list.download/api/v1/get?type=http",
    "https://www.proxy-list.download/api/v1/get?type=https"
]

def fetch_proxies():
    print("📥 جاري سحب البروكسيات من أحدث المصادر الموثوقة...")
    proxies = set()
    for url in SOURCES:
        try:
            response = requests.get(url, timeout=10)
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
            print(f"⚠️ فشل الجلب من {url}: {e}")
    
    print(f"✅ تم جمع {len(proxies)} بروكسي فريد للبدء بفحصه.")
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
    """رفع وتحديث الملف تلقائياً إلى مستودع GitHub"""
    if not GITHUB_TOKEN or not REPO_NAME:
        print("⚠️ GITHUB_TOKEN أو REPO_NAME غير متوفر، تخطي الرفع التلقائي للمستودع.")
        return

    print("🚀 جاري رفع الملف المحدث إلى مستودع GitHub...")
    api_url = f"https://api.github.com/repos/{REPO_NAME}/contents/{file_path}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    try:
        with open(file_path, "rb") as f:
            content_bytes = f.read()
        content_encoded = base64.b64encode(content_bytes).decode("utf-8")

        # 1. جلب SHA الخاص بالملف القديم إن وجد (مطلوب للتحديث في GitHub API)
        sha = None
        get_res = requests.get(api_url, headers=headers)
        if get_res.status_code == 200:
            sha = get_res.json().get("sha")

        # 2. إرسال البيانات الجديدة
        data = {
            "message": "🔄 Auto-update active proxies list",
            "content": content_encoded,
            "branch": "main"
        }
        if sha:
            data["sha"] = sha

        put_res = requests.put(api_url, headers=headers, json=data)
        if put_res.status_code in [200, 201]:
            print("✅ تم تحديث ورفع ملف active_proxies.txt في المستودع بنجاح!")
        else:
            print(f"❌ فشل رفع الملف لـ GitHub: {put_res.text}")
    except Exception as e:
        print(f"❌ خطأ أثناء الرفع لـ GitHub: {e}")

def send_to_telegram(file_path, valid_count, total_count):
    if not BOT_TOKEN or not CHAT_ID:
        return
    print(f"📤 جاري إرسال الملف إلى تيليجرام ({valid_count} بروكسي شغال)...")
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    caption = (
        f"✅ <b>اكتمل فحص البروكسيات بنجاح!</b>\n\n"
        f"🔍 إجمالي المفحوص: {total_count}\n"
        f"🟢 الشغالة (HTTP/S): {valid_count}\n"
        f"🔄 تم التحديث في المستودع تلقائياً\n"
        f"⏱️ وقت الفحص: {time.strftime('%Y-%m-%d %H:%M:%S UTC')}"
    )
    with open(file_path, 'rb') as f:
        files = {'document': f}
        data = {'chat_id': CHAT_ID, 'caption': caption, 'parse_mode': 'HTML'}
        try:
            requests.post(url, data=data, files=files, timeout=30)
        except:
            pass

def main():
    raw_proxies = fetch_proxies()
    if not raw_proxies:
        print("❌ لم يتم جلب أي بروكسي.")
        return

    print(f"🔄 جاري الفحص باستخدام {MAX_WORKERS} خيط معالجة...")
    valid_proxies = []
    start_time = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = executor.map(check_proxy, raw_proxies)
        for res in results:
            if res:
                valid_proxies.append(res)
    
    end_time = time.time()
    print(f"🏁 انتهى الفحص في {round(end_time - start_time, 2)} ثانية.")
    print(f"🟢 البروكسيات الشغالة: {len(valid_proxies)}")

    if valid_proxies:
        with open(OUTPUT_FILE, "w") as f:
            for p in valid_proxies:
                f.write(p + "\n")
        
        # 1. تحديث الملف في المستودع تلقائياً ليصبح رابط الـ Raw ثابتاً ومحدثاً
        update_github_file(OUTPUT_FILE)
        
        # 2. إرسال نسختها لتيليجرام
        send_to_telegram(OUTPUT_FILE, len(valid_proxies), len(raw_proxies))
    else:
        print("⚠️ لم يتم العثور على أي بروكسي شغال.")

if __name__ == "__main__":
    main()
