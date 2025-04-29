import requests
from datetime import datetime, timedelta, timezone
from pymongo import MongoClient
from dotenv import load_dotenv
import os

# โหลดค่าจาก .env
load_dotenv()

# ดึงค่า URI และ DB name จาก environment
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017')
DB_NAME = os.getenv('DB_NAME', 'TPSO_logs')

def get_database():
    """
    สร้างและส่งคืน database object จาก MongoDB
    """
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        return db
    except Exception as e:
        print(f"❌ Error connecting to MongoDB: {e}")
        return None

def store_price_data(data, collection_name=None):
    """
    เก็บข้อมูลลงใน MongoDB
    รองรับทั้ง insert_one (dict) และ insert_many (list of dicts)
    จะสร้าง collection แยกตามวันที่และเวลา
    """
    try:
        db = get_database()
        if db is None:
            return False

        # เวลาประเทศไทย (UTC+7)
        thailand_time = datetime.now(timezone(timedelta(hours=7)))

        # ถ้าไม่ได้ระบุชื่อ collection ให้ใช้วันที่และเวลาเป็นชื่อ collection
        if not collection_name:
            # ใช้วันที่และเวลา (ชั่วโมง-นาที)
            collection_name = thailand_time.strftime("TPSO_Data_%d-%m-%Y-%H-%M")

        collection = db[collection_name]

        # เช็คประเภทข้อมูล
        if isinstance(data, list):
            if not data:
                print("⚠️ No data to insert.")
                return False
            result = collection.insert_many(data)
            print(f"✅ Inserted {len(result.inserted_ids)} documents into '{collection_name}'")
        else:
            result = collection.insert_one(data)
            print(f"✅ Inserted 1 document with ID: {result.inserted_id} into '{collection_name}'")

        return True
    except Exception as e:
        print(f"❌ Error storing data in MongoDB: {e}")
        return False

def fetch_and_store_data():
    url = "https://index-api.tpso.go.th/api/cmip/filter"

    # Modify data to allow dynamic period for current year
    current_year = datetime.now().year + 543  # Thai Buddhist calendar (current year + 543)
    current_month = datetime.now().month

    data = {
        "YearBase": 2558,
        "Categories": [],
        "HeadCategories": [
            "checkAll", "01", "02", "03", "04", "05", "06", "07", "08", "09",
            "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21"
        ],
        "Period": {
            "StartYear": str(current_year),
            "StartMonth": 1,
            "EndYear": str(current_year),
            "EndMonth": current_month
        },
        "Search": "",
        "TimeOption": True,
        "Types": ["14"]
    }

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    }

    try:
        response = requests.post(url, json=data, headers=headers, timeout=30)
        response.raise_for_status()  # Will raise an exception for HTTP error codes
    except requests.exceptions.Timeout:
        print("⏰ Request timed out, please try again later.")
        return
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return

    print("✅ Success! Fetching data...")

    try:
        response_data = response.json()
    except ValueError as e:
        print(f"❌ Failed to parse JSON response: {e}")
        return

    thailand_time = datetime.now(timezone(timedelta(hours=7)))
    date_str = thailand_time.strftime('%d-%m-%Y-%H-%M')

    documents = [{
        "item": item,
        "timestamp": thailand_time,
        "request_parameters": data
    } for item in response_data]

    # Try storing in MongoDB
    if store_price_data(documents, collection_name=f"TPSO_Data_{date_str}"):
        print(f"✅ Stored {len(documents)} documents in MongoDB")
        print(f"📌 Current Thailand time: {thailand_time.strftime('%Y-%m-%d %H:%M:%S')} TH")
    else:
        print("❌ Failed to store data in MongoDB")

if __name__ == "__main__":
    print("🚀 Starting data fetch...")
    fetch_and_store_data()
    print("✅ Program completed")
