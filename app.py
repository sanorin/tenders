from flask import Flask, render_template, jsonify, request
import json
import os
import threading
import shutil
from pipeline.runner import run_pipeline
from config import set_config, get_config
from datetime import datetime

app = Flask(__name__)

OUTPUT_FILE = "output/tenders.json"

token = os.getenv("GIGACHAT_TOKEN")

pipeline_state = {
    "running": False,
    "completed": False,
    "last_run": None
}

@app.route("/")
def index():
    return render_template("index.html")


# основа

def run_async_pipeline():
    global pipeline_state
    pipeline_state["running"] = True
    pipeline_state["completed"] = False
    config = get_config()
    try:
        run_pipeline(config, token)
        pipeline_state["completed"] = True
    except Exception as e:
        print("Pipeline error:", e)
        pipeline_state["completed"] = False
    finally:
        pipeline_state["running"] = False
        pipeline_state["last_run"] = datetime.now()

@app.route("/pipeline_status")
def pipeline_status():
    return jsonify(pipeline_state)
@app.route("/start", methods=["POST"])
def start_pipeline():

    data = request.json

    keywords = data.get("keywords", "")
    exclude = data.get("exclude", "")
    region = data.get("region", "spb")
    period = data.get("period", "month")

    exclude_list = [x.strip() for x in exclude.split(",") if x.strip()]

    days_map = {
        "day": 1,
        "week": 7,
        "month": 30,
        "quarter": 90,
        "year": 365
    }

    days = days_map.get(period, 30)

    keywords_list = [
        x.strip()
        for x in keywords.split(",")
        if x.strip()
    ]

    set_config(
        region=region,
        days=days,
        keywords=keywords_list,
        exclude_words = exclude_list
    )


    threading.Thread(target=run_async_pipeline).start()

    return jsonify({"status": "started"})




@app.route("/clear", methods=["POST"])
def clear_tenders():

    # 1. JSON результаты
    if os.path.exists("output/tenders.json"):
        os.remove("output/tenders.json")

    # 2. обработанные
    if os.path.exists("output/processed.json"):
        os.remove("output/processed.json")

    # 3. HTML файлы 
    html_dir = "input"

    if os.path.exists(html_dir):
        shutil.rmtree(html_dir)
        os.makedirs(html_dir, exist_ok=True)

    return jsonify({"status": "cleared"})

# получение результатов

@app.route("/tenders")
def get_tenders():

    if not os.path.exists(OUTPUT_FILE):
        return jsonify([])

    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        return jsonify(data)

    except:
        return jsonify([])




if __name__ == "__main__":
    app.run(debug=True)