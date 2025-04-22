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

# 🟢 URL ของหน้าเว็บ Dohome
web = 'https://www.dohome.co.th/th/construction-materials-request-for-quotation/steel.html'

# 🟢 สร้างชื่อ Collection ตามวันเวลา
timestamp = datetime.now().strftime("%d-%m-%Y-%H-%M")
collection_name = f"Dohome_Data_{timestamp}"

# 🟢 เชื่อมต่อ MongoDB
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["Dohome_logs"]
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
    print("รอโหลดหน้าเว็บ...")
    time.sleep(random.uniform(15, 20))

    wait = WebDriverWait(driver, 30)
    try:
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'product-item-info')))
        print("พบสินค้าในหน้าเว็บ")
    except Exception as e:
        print(f"ไม่พบ element สินค้า: {str(e)}")

    print("กำลังเลื่อนหน้าจอ...")
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
    time.sleep(random.uniform(5, 8))
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(random.uniform(5, 8))

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    products = soup.find_all('div', class_='product-item-info')
    print(f"พบสินค้าทั้งหมด: {len(products)} รายการ")

    if len(products) == 0:
        print("\nDebug: ตรวจสอบ HTML ที่ได้:")
        print(driver.page_source[:2000])
        raise Exception("ไม่พบข้อมูลสินค้าในหน้าเว็บ")

    data = []
    incomplete_count = 0

    for product in products:
        try:
            title_elem = product.find('strong', class_='product-item-name')
            title = title_elem.text.strip() if title_elem else "ไม่พบชื่อสินค้า"

            price_unit_elem = product.find('div', class_='wrap-product-price-unit')
            if price_unit_elem:
                price_unit_text = price_unit_elem.text.strip()
                # แยกราคาและหน่วย (ถ้าแยกไม่ได้ ให้ใส่ไว้รวมกัน)
                parts = price_unit_text.split('/')
                price = parts[0].strip() if len(parts) > 0 else "ไม่มีราคา"
                unit = parts[1].strip() if len(parts) > 1 else "ไม่พบหน่วย"
            else:
                price = "ไม่มีราคา"
                unit = "ไม่พบหน่วย"

            link = "ไม่มีลิงก์"
            link_elem = product.find('a', href=True)
            if link_elem:
                link = link_elem['href']
                if not link.startswith('http'):
                    link = f"https://www.dohome.co.th{link}"

            print(f"✅ {title} | {price} | {unit} | {link}")

            data.append({
                "title": title,
                "price": price,
                "unit": unit,
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
