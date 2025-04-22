from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import pymongo
import time
from datetime import datetime
import re
import random

# 🟢 ฟังก์ชันสำหรับดึงลิงก์จาก onclick
def extract_link_from_onclick(onclick_text):
    match = re.search(r"['\"](/p/[^'\"]+)['\"]", onclick_text)
    return f"https://www.nocnoc.com{match.group(1)}" if match else "ไม่มีลิงก์"

# 🟢 URL ของหน้าเว็บ NocNoc
web = 'https://nocnoc.com/pl/All?area=search&st=%E0%B8%A7%E0%B8%B1%E0%B8%AA%E0%B8%94%E0%B8%B8&entry_point=Home'

# 🟢 สร้างชื่อ Collection ตามวันเวลา
timestamp = datetime.now().strftime("%d-%m-%Y-%H-%M")
collection_name = f"NocNoc_Data_{timestamp}"

# 🟢 เชื่อมต่อ MongoDB
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["NocNoc_logs"]
collection = db[collection_name]

# 🟢 ตั้งค่า Chrome
chrome_options = Options()
chrome_options.add_argument('--headless=new')
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--window-size=1920,1080')
chrome_options.add_argument('--disable-blink-features=AutomationControlled')
chrome_options.add_argument('--disable-extensions')
chrome_options.add_argument('--disable-infobars')
chrome_options.add_argument('--disable-notifications')
chrome_options.add_argument('--disable-popup-blocking')
chrome_options.add_argument('--disable-web-security')
chrome_options.add_argument('--ignore-certificate-errors')
chrome_options.add_argument('--ignore-ssl-errors')
chrome_options.add_argument(f'--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(90, 120)}.0.0.0 Safari/537.36')
chrome_options.add_experimental_option('excludeSwitches', ['enable-automation', 'enable-logging'])
chrome_options.add_experimental_option('useAutomationExtension', False)

try:
    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_cdp_cmd('Network.setUserAgentOverride', {
        "userAgent": f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(90, 120)}.0.0.0 Safari/537.36'
    })
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': '''
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        '''
    })

    print(f"กำลังเข้าถึง URL: {web}")
    driver.get(web)
    print("รอการโหลดหน้าเว็บ...")  # ให้เวลาในการโหลดหน้า
    time.sleep(random.uniform(15, 20))

    wait = WebDriverWait(driver, 30)
    try:
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'product-tile-link')))
        print("พบ element สินค้า")
    except Exception as e:
        print(f"ไม่พบ element สินค้า: {str(e)}")

    print("กำลังเลื่อนหน้าจอ...")  # เลื่อนหน้าจอเพื่อโหลดสินค้าเพิ่มเติม
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
    time.sleep(random.uniform(5, 8))
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(random.uniform(5, 8))

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    products = soup.find_all('a', class_='product-tile-link bu-flex bu-h-full bu-flex-col')
    print(f"พบสินค้าทั้งหมด: {len(products)} รายการ")

    if len(products) == 0:
        print("\nDebug: ตรวจสอบ HTML ที่ได้:")
        print(driver.page_source[:2000])
        raise Exception("ไม่พบข้อมูลสินค้าในหน้าเว็บ")

    data = []
    incomplete_count = 0

    for product in products:
        try:
            # แก้ไข class สำหรับชื่อสินค้า
            title_elem = product.find('p', class_='bu-line-clamp-2 bu-min-h-[3.6rem] !bu-text-black bu-typography-body-3 md:bu-typography-body-2 lg:bu-min-h-[4.4rem]')
            title = title_elem.text.strip() if title_elem else "ไม่พบชื่อสินค้า"

            # ราคาเต็ม (ราคาปกติ)
            price_elem = product.find('div', class_='price without-discount')
            price = price_elem.text.strip() if price_elem else "ไม่มีราคา"

            # ราคาโปรโมชั่น (ราคาที่ลดแล้ว)
            discounted_price_elem = product.find('div', class_='price with-discount')
            discounted_price = discounted_price_elem.text.strip() if discounted_price_elem else "ไม่มีราคาโปรโมชั่น"

            link_elem = product.get('href', None)
            link = f"https://www.nocnoc.com{link_elem}" if link_elem else "ไม่มีลิงก์"

            print(f"✅ {title} | {price} | {discounted_price} | {link}")

            data.append({
                "title": title,
                "price": price,
                "discounted_price": discounted_price,
                "link": link,
                "scraped_at": datetime.now()
            })

        except Exception as e:
            incomplete_count += 1
            print(f"⚠️ เกิดข้อผิดพลาดในการประมวลผลสินค้า: {str(e)}")

    print(f"\n📦 ข้อมูลสมบูรณ์: {len(data)} รายการ")
    print(f"❌ ข้อมูลไม่สมบูรณ์: {incomplete_count} รายการ")

    if data:
        collection.insert_many(data)
        print(f"📌 บันทึกลง MongoDB: `{collection_name}` สำเร็จ")

except Exception as e:
    print(f"❌ เกิดข้อผิดพลาด: {str(e)}")
finally:
    if 'driver' in locals():
        driver.quit()
