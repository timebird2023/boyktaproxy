import os
import time
import requests
import concurrent.futures

# ============================================
# ⚙️ الإعدادات (يتم جلبها من GitHub Secrets)
# ============================================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
OUTPUT_FILE = "active_proxies.txt"

# رابط محايد وسريع لفحص استجابة البروكسي
TEST_URL = "http://httpbin.org/ip" 
TIMEOUT = 5
MAX_WORKERS = 150  # عدد الخيوط لفحص 150 بروكسي في نفس اللحظة

# ============================================
# 🌐 مصادر بروكسيات HTTP/HTTPS قوية ومتجددة
# ============================================
SOURCES = [
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "https://api.proxyscrape.com/v4/free-proxy-list/get?request=get_proxies&proxy_format=ipport&format=text&protocol=http",
    "https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS_RAW.txt",
    "https://raw.githubusercontent.com/mmpx12/proxy-list/master/http.txt"
]

def fetch_proxies():
    print("📥 جاري سحب البروكسيات من المصادر...")
    proxies = set()
    for url in SOURCES:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                lines = response.text.splitlines()
                for line in lines:
                    line = line.strip()
                    if ":" in line and not line.startswith("#"):
                        # تنسيق البروكسي ليكون جاهزاً للاستخدام
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
        # فحص البروكسي عبر طلب بسيط
        res = requests.get(TEST_URL, proxies=proxies, timeout=TIMEOUT)
        if res.status_code == 200:
            return proxy_url
    except:
        pass
    return None

def send_to_telegram(file_path, valid_count, total_count):
    print(f"📤 جاري إرسال الملف إلى تيليجرام ({valid_count} بروكسي شغال)...")
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    
    caption = (
        f"✅ <b>اكتمل فحص البروكسيات بنجاح!</b>\n\n"
        f"🔍 إجمالي المفحوص: {total_count}\n"
        f"🟢 الشغالة (HTTP/S): {valid_count}\n"
        f"⏱️ وقت الفحص: {time.strftime('%Y-%m-%d %H:%M:%S UTC')}"
    )
    
    with open(file_path, 'rb') as f:
        files = {'document': f}
        data = {'chat_id': CHAT_ID, 'caption': caption, 'parse_mode': 'HTML'}
        try:
            response = requests.post(url, data=data, files=files, timeout=30)
            if response.status_code == 200:
                print("✅ تم إرسال الملف بنجاح إلى البوت!")
            else:
                print(f"❌ فشل إرسال الملف لتيليجرام: {response.text}")
        except Exception as e:
            print(f"❌ خطأ في الاتصال بتيليجرام: {e}")

def main():
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ خطأ: المتغيرات BOT_TOKEN و CHAT_ID غير متوفرة.")
        return

    # 1. سحب البروكسيات
    raw_proxies = fetch_proxies()
    if not raw_proxies:
        print("❌ لم يتم جلب أي بروكسي.")
        return

    # 2. فحص البروكسيات
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

    # 3. حفظ النتيجة وإرسالها
    if valid_proxies:
        with open(OUTPUT_FILE, "w") as f:
            for p in valid_proxies:
                f.write(p + "\n")
        
        send_to_telegram(OUTPUT_FILE, len(valid_proxies), len(raw_proxies))
    else:
        print("⚠️ لم يتم العثور على أي بروكسي شغال.")

if __name__ == "__main__":
    main()
