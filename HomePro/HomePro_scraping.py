from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from datetime import datetime
import pymongo
import random
import time

# 🟢 URL สินค้า HomePro (หมวดท่อ/อุปกรณ์ประปา)
url = "https://www.homepro.co.th/c/CON"

# 🟢 ตั้งชื่อ Collection ตามวันเวลา
timestamp = datetime.now().strftime("%d-%m-%Y-%H-%M")
collection_name = f"HomePro_Data_{timestamp}"

# 🟢 เชื่อมต่อ MongoDB
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["Homepro_logs"]
collection = db[collection_name]

# 🟢 ตั้งค่า Chrome Options
options = Options()
options.add_argument('--headless=new')
options.add_argument('--disable-gpu')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--window-size=1920,1080')
options.add_argument('--disable-blink-features=AutomationControlled')
options.add_argument('--disable-extensions')
options.add_argument('--disable-infobars')
options.add_argument('--disable-notifications')
options.add_argument('--disable-popup-blocking')
options.add_argument('--disable-web-security')
options.add_argument('--ignore-certificate-errors')
options.add_argument('--ignore-ssl-errors')
options.add_argument(f'--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(90, 120)}.0.0.0 Safari/537.36')
options.add_experimental_option('excludeSwitches', ['enable-automation', 'enable-logging'])
options.add_experimental_option('useAutomationExtension', False)

try:
    driver = webdriver.Chrome(options=options)

    # ป้องกันตรวจจับ automation
    driver.execute_cdp_cmd('Network.setUserAgentOverride', {
        "userAgent": f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(90, 120)}.0.0.0 Safari/537.36'
    })
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
    })

    print(f"📡 เข้าถึง URL: {url}")
    driver.get(url)
    time.sleep(random.uniform(10, 15))

    # รอจนกว่าจะเจอ product element
    wait = WebDriverWait(driver, 30)
    try:
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'product-card-mkp-s2')))
        print("✅ โหลดสินค้าเรียบร้อย")
    except:
        print("❌ ไม่พบสินค้า")
        raise Exception("ไม่พบสินค้า")

    # เลื่อนหน้าจอจนสุดเพื่อโหลดสินค้าเพิ่มเติม
    print("🔃 กำลังเลื่อนหน้าจอเพื่อโหลดสินค้า...")
    SCROLL_PAUSE_TIME = 2
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(SCROLL_PAUSE_TIME)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

    # ดึงข้อมูลสินค้า
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    products = soup.find_all('div', class_='product-card-mkp-s2')
    print(f"🔍 พบสินค้าทั้งหมด: {len(products)} รายการ")

    data = []
    incomplete_count = 0

    for product in products:
        try:
            link_tag = product.find('a', href=True)
            if not link_tag:
                raise Exception("ไม่พบลิงก์สินค้า")

            product_url = link_tag['href']
            if not product_url.startswith("http"):
                product_url = f"https://www.homepro.co.th{product_url}"

            driver.get(product_url)
            time.sleep(random.uniform(2, 4))
            product_soup = BeautifulSoup(driver.page_source, 'html.parser')

            title_tag = product_soup.find('h1')
            title = title_tag.get_text(strip=True) if title_tag else "ไม่มีชื่อสินค้า"

            price_tag = product_soup.find('div', class_='discount-price')
            price = price_tag.get_text(strip=True) if price_tag else "ไม่มีราคา"

            unit_tag = product_soup.find('div', class_='span.product-unit')
            unit = unit_tag.get_text(strip=True) if unit_tag else "ไม่มีหน่วย"

           
            data.append({
                "title": title,
                "price": price,
                "unit": unit,
                "link": product_url,
                "scraped_at": datetime.now()
            })

        except Exception as e:
            incomplete_count += 1
            print(f"⚠️ ข้อมูลไม่สมบูรณ์: {e}")

    print(f"\n📦 สมบูรณ์: {len(data)} รายการ")
    print(f"❌ ไม่สมบูรณ์: {incomplete_count} รายการ")

    if data:
        collection.insert_many(data)
        print(f"📌 บันทึกลง MongoDB ใน collection `{collection_name}` เรียบร้อย")

except Exception as e:
    print(f"❌ เกิดข้อผิดพลาด: {e}")
finally:
    if 'driver' in locals():
        driver.quit()
