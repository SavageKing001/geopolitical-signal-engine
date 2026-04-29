import sys
import os

# Ensure project root is on sys.path so all package imports resolve
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, request
from main import get_analysis_data

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    keyword    = request.form.get("keyword", "").strip()
    event_type = request.form.get("event_type", "conflict")
    region     = request.form.get("region", "Global")

    data = get_analysis_data(keyword, event_type, region)
    return render_template("results.html", data=data)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
