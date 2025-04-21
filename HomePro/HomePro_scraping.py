from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import time
import pymongo
from datetime import datetime

# --- ตั้งค่า Selenium ---
options = Options()
options.add_argument('--headless')
options.add_argument('--disable-gpu')
driver = webdriver.Chrome(options=options)

# --- MongoDB ---
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["scraping_db"]
collection = db["Homepro_logs"]

# --- เริ่มที่หน้าหลักของสินค้าหมวดหมู่ ---
url = "https://www.homepro.co.th/c/CON"  # ตัวอย่าง: ท่อ/อุปกรณ์ประปา
driver.get(url)
time.sleep(5)

# --- โหลดสินค้าทั้งหมด ---
SCROLL_PAUSE_TIME = 2
last_height = driver.execute_script("return document.body.scrollHeight")
while True:
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(SCROLL_PAUSE_TIME)
    new_height = driver.execute_script("return document.body.scrollHeight")
    if new_height == last_height:
        break
    last_height = new_height

soup = BeautifulSoup(driver.page_source, 'html.parser')
products = soup.find_all('div', class_='product-card-mkp-s2')

data = []

print(f"พบสินค้าทั้งหมด: {len(products)} รายการ")

for product in products:
    try:
        link_tag = product.find('a', href=True)
        if not link_tag:
            continue
        product_url = link_tag['href']
        if not product_url.startswith("http"):
            product_url = f"https://www.homepro.co.th{product_url}"

        # 👉 เข้าไปดูรายละเอียดในแต่ละหน้า
        driver.get(product_url)
        time.sleep(2)
        product_soup = BeautifulSoup(driver.page_source, 'html.parser')

        # ดึงชื่อสินค้า
        title_tag = product_soup.find('h1')
        title = title_tag.get_text(strip=True) if title_tag else "ไม่มีชื่อ"

        # ดึงราคา
        price_tag = product_soup.find('div', class_='discount-price')
        price = price_tag.get_text(strip=True) if price_tag else "ไม่มีราคา"

        # ดึงหน่วยสินค้า เช่น /ม้วน (contain 30 เมตร)
        unit_tag = product_soup.find('div', class_='span.product-unit')
        unit = unit_tag.get_text(strip=True) if unit_tag else "ไม่มีหน่วย"

        # print(f"✅ {title} | {price} | {product_url}")

        data.append({
            "title": title,
            "price": price,
            "link": product_url,
            "scraped_at": datetime.utcnow()
        })

        collection.insert_one(data[-1])

    except Exception as e:
        print(f"⚠️ ดึงข้อมูลไม่สำเร็จ: {e}")

driver.quit()
print(f"\nบันทึกสำเร็จ: {len(data)} รายการ")
