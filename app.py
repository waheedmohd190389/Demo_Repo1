from flask import Flask, request, render_template
from user_agents import parse
import requests
import sqlite3
from datetime import datetime, timezone

app = Flask(__name__)

DB = "visitors.db"


def init_db():
    conn = sqlite3.connect(DB)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS visitors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            visit_time TEXT,
            ip TEXT,
            user_agent TEXT,
            browser TEXT,
            browser_version TEXT,
            os TEXT,
            os_version TEXT,
            device TEXT,
            referrer TEXT,
            country TEXT,
            region TEXT,
            city TEXT,
            latitude REAL,
            longitude REAL,
            isp TEXT
        )
    """)

    conn.commit()
    conn.close()


def get_ip():
    # When deployed behind a trusted reverse proxy,
    # configure the proxy correctly before trusting forwarded IPs.
    return request.remote_addr


def get_ip_location(ip):
    try:
        response = requests.get(
            f"https://ipapi.co/{ip}/json/",
            timeout=5
        )

        if response.ok:
            data = response.json()

            return {
                "country": data.get("country_name"),
                "region": data.get("region"),
                "city": data.get("city"),
                "latitude": data.get("latitude"),
                "longitude": data.get("longitude"),
                "isp": data.get("org")
            }

    except requests.RequestException:
        pass

    return {
        "country": None,
        "region": None,
        "city": None,
        "latitude": None,
        "longitude": None,
        "isp": None
    }


@app.route("/")
def landing():

    ip = get_ip()
    ua_string = request.headers.get("User-Agent", "")

    ua = parse(ua_string)

    location = get_ip_location(ip)

    visitor = {
        "visit_time": datetime.now(timezone.utc).isoformat(),
        "ip": ip,
        "user_agent": ua_string,

        "browser": ua.browser.family,
        "browser_version": ua.browser.version_string,

        "os": ua.os.family,
        "os_version": ua.os.version_string,

        "device": ua.device.family,

        "referrer": request.headers.get("Referer", ""),

        **location
    }

    conn = sqlite3.connect(DB)

    conn.execute("""
        INSERT INTO visitors (
            visit_time,
            ip,
            user_agent,
            browser,
            browser_version,
            os,
            os_version,
            device,
            referrer,
            country,
            region,
            city,
            latitude,
            longitude,
            isp
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        visitor["visit_time"],
        visitor["ip"],
        visitor["user_agent"],
        visitor["browser"],
        visitor["browser_version"],
        visitor["os"],
        visitor["os_version"],
        visitor["device"],
        visitor["referrer"],
        visitor["country"],
        visitor["region"],
        visitor["city"],
        visitor["latitude"],
        visitor["longitude"],
        visitor["isp"]
    ))

    conn.commit()
    conn.close()

    return render_template("landing.html")


@app.route("/dashboard")
def dashboard():

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    visitors = conn.execute("""
        SELECT *
        FROM visitors
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        visitors=visitors
    )


if __name__ == "__main__":
    init_db()

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )