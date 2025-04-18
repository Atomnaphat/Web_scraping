# homepro_scraper.py
import requests
from bs4 import BeautifulSoup
import csv
from datetime import datetime, timezone
import re
from db_homepro_config import store_scraped_data

def extract_link_from_onclick(onclick_text):
    match = re.search(r"['\"](/product/[^'\"]+)['\"]", onclick_text)
    return f"https://www.homepro.co.th{match.group(1)}" if match else "ไม่มีลิงก์"

web = 'https://www.homepro.co.th/?gad_source=1'

try:
    response = requests.get(web)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, 'html.parser')
    products = soup.find_all('div', class_='product-plp-card')

    print(f"🔍 พบสินค้าทั้งหมด: {len(products)} รายการ")

    data = []
    incomplete_count = 0
    now_utc = datetime.utcnow().replace(tzinfo=timezone.utc)

    for product in products:
        try:
            title = product.find('div', class_='item-title').text.strip()
            price = product.find('div', class_='original-price').text.strip()

            link_element = product.find('a', href=True)
            if link_element and link_element.has_attr('data-url'):
                link = f"https://www.homepro.co.th{link_element['data-url']}"
            elif link_element and link_element.has_attr('onclick'):
                link = extract_link_from_onclick(link_element['onclick'])
            elif link_element:
                link = link_element['href']
                if not link.startswith('http'):
                    link = f"https://www.homepro.co.th{link}"
            else:
                link = "ไม่มีลิงก์"

            data.append({
                "title": title,
                "price": price,
                "link": link,
                "scraped_at": now_utc  # ใช้ UTC สำหรับ TTL index
            })

        except AttributeError:
            incomplete_count += 1
            print("⚠️ ข้อมูลสินค้าไม่สมบูรณ์ ข้ามรายการนี้")

    print(f"✅ บันทึกข้อมูลสำเร็จ: {len(data)} รายการ | ❌ ไม่สมบูรณ์: {incomplete_count}")

    # ⏺ บันทึกลง MongoDB
    if data:
        store_scraped_data(data)

    # ⏺ บันทึก CSV
    csv_filename = "homepro_products.csv"
    with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Title', 'Price', 'Link', 'Scraped_At'])
        for item in data:
            writer.writerow([item["title"], item["price"], item["link"], item["scraped_at"]])

    print(f"📁 บันทึกไฟล์ CSV: {csv_filename}")

except requests.exceptions.RequestException as e:
    print(f"❌ เกิดข้อผิดพลาดในการดึงเว็บ: {e}")
