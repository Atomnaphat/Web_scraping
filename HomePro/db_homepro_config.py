from pymongo import MongoClient
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import pytz  # สำหรับ timezone

# โหลดจาก .env
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("DB_NAME", "scraping_db")
COLLECTION_NAME = "homepro_logs"

# TTL = 60 วินาที
TTL_SECONDS = 7776000

# ใช้ timezone ประเทศไทย
TH_TIMEZONE = pytz.timezone('Asia/Bangkok')

def get_database():
    try:
        client = MongoClient(MONGO_URI)
        return client[DB_NAME]
    except Exception as e:
        print(f"❌ MongoDB connection error: {e}")
        return None

def setup_ttl_index():
    db = get_database()
    if db is None:
        return False

    collection = db[COLLECTION_NAME]

    for index in collection.list_indexes():
        if index["name"] != "_id_":
            collection.drop_index(index["name"])
            print(f"🧹 Dropped old index: {index['name']}")

    collection.create_index(
        [("scraped_at", 1)],
        expireAfterSeconds=TTL_SECONDS,
        name="scraped_at_ttl_index"
    )
    print(f"✅ Created TTL index on 'scraped_at' (expires after {TTL_SECONDS} seconds)")
    return True

def store_scraped_data(data):
    db = get_database()
    if db is None:
        return False

    collection = db[COLLECTION_NAME]

    try:
        now = datetime.now(TH_TIMEZONE)  # เวลาไทย
        expired_at = now + timedelta(seconds=TTL_SECONDS)

        # ใส่ timestamp เดียวกันให้ทุกเอกสาร
        for doc in data:
            doc['scraped_at'] = now

        collection.insert_many(data)

        # พิมพ์สรุป
        print(f"🕓 ข้อมูลถูกบันทึกเมื่อ: {now.strftime('%Y-%m-%d %H:%M:%S')} (เวลาไทย)")
        print(f"🧨 ข้อมูลจะถูกลบโดยประมาณเวลา: {expired_at.strftime('%Y-%m-%d %H:%M:%S')} (เวลาไทย)")

        return True
    except Exception as e:
        print(f"❌ Insert error: {e}")
        return False

# setup TTL ตอนรัน
setup_ttl_index()
