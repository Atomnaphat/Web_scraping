from flask import Flask, render_template, send_file, request
from pymongo import MongoClient
from bson import json_util
from io import BytesIO
import zipfile
import re
from datetime import datetime

app = Flask(__name__)

# Connect to MongoDB
client = MongoClient('localhost', 27017)
EXCLUDED_DBS = {"admin", "config", "local", "your_database_name", "customerDB", "noodleShop"}

@app.route("/")
def index():
    dbs = [db for db in client.list_database_names() if db not in EXCLUDED_DBS]
    return render_template("index.html", dbs=dbs)

@app.route("/view/<db>")
def view_database(db):
    database = client[db]
    colls = database.list_collection_names()

    # ✅ ใช้ regex ดึงวันที่จากชื่อ collection
    def extract_date(name):
        try:
            match = re.search(r'(\d{2}-\d{2}-\d{4}-\d{2}-\d{2})', name)
            if match:
                return datetime.strptime(match.group(1), "%d-%m-%Y-%H-%M")
        except:
            pass
        return datetime.min  # ถ้าแปลงไม่ได้ให้ถือว่าเก่าสุด

    colls.sort(key=extract_date, reverse=True)

    data = {}
    for name in colls:
        records = list(database[name].find({}, {'_id': 0}))
        data[name] = records

    return render_template("view.html", collection=db, colls=colls, data=data)

@app.route("/download_one/<collection>/<coll_name>")
def download_one_collection(collection, coll_name):
    db = client[collection]
    data = list(db[coll_name].find({}, {'_id': 0}))
    json_data = json_util.dumps(data, indent=2, ensure_ascii=False)

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.writestr(f"{coll_name}.json", json_data)

    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"{coll_name}.zip",
        mimetype='application/zip'
    )

@app.route("/download_all/<collection>")
def download_all_collections(collection):
    db = client[collection]
    colls = db.list_collection_names()

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for name in colls:
            data = list(db[name].find({}, {'_id': 0}))
            json_data = json_util.dumps(data, indent=2, ensure_ascii=False)
            zipf.writestr(f"{name}.json", json_data)

    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"{collection}_all_collections.zip",
        mimetype='application/zip'
    )

if __name__ == "__main__":
    app.run(host='0.0.0.0',port =5000, debug=True)
