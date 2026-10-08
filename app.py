from flask import Flask, request, render_template, jsonify
from user_agents import parse
import requests
import sqlite3
import json
import uuid
from datetime import datetime, timezone

app = Flask(__name__)

DB = "visitors.db"


# =========================================================
# DATABASE
# =========================================================

def init_db():

    conn = sqlite3.connect(DB)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS visitors (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            visit_time TEXT,

            session_id TEXT,

            ip TEXT,

            user_agent TEXT,

            browser TEXT,
            browser_version TEXT,

            os TEXT,
            os_version TEXT,

            device TEXT,
            device_brand TEXT,
            device_model TEXT,

            referrer TEXT,
            page_url TEXT,
            landing_page TEXT,

            country TEXT,
            country_code TEXT,
            region TEXT,
            city TEXT,
            postal_code TEXT,

            latitude REAL,
            longitude REAL,

            isp TEXT,
            organization TEXT,
            asn TEXT,

            timezone TEXT,

            language TEXT,
            languages TEXT,

            screen_width INTEGER,
            screen_height INTEGER,

            viewport_width INTEGER,
            viewport_height INTEGER,

            device_pixel_ratio REAL,

            color_scheme TEXT,

            touch_support INTEGER,

            online_status INTEGER,

            connection_type TEXT,
            connection_effective_type TEXT,

            cookies_enabled INTEGER,

            java_enabled INTEGER,

            timezone_offset INTEGER,

            traffic_source TEXT,

            utm_source TEXT,
            utm_medium TEXT,
            utm_campaign TEXT,
            utm_term TEXT,
            utm_content TEXT,

            is_returning INTEGER DEFAULT 0,

            time_on_page REAL,

            scroll_depth INTEGER,

            gps_permission TEXT,
            gps_latitude REAL,
            gps_longitude REAL,
            gps_accuracy REAL,

            extra_data TEXT
        )
    """)

    conn.commit()
    conn.close()


# =========================================================
# DATABASE MIGRATION
# =========================================================

def ensure_columns():

    conn = sqlite3.connect(DB)

    columns = {
        row[1]
        for row in conn.execute(
            "PRAGMA table_info(visitors)"
        ).fetchall()
    }

    required = {

        "session_id": "TEXT",
        "device_brand": "TEXT",
        "device_model": "TEXT",
        "country_code": "TEXT",
        "postal_code": "TEXT",
        "organization": "TEXT",
        "asn": "TEXT",
        "timezone": "TEXT",
        "language": "TEXT",
        "languages": "TEXT",

        "screen_width": "INTEGER",
        "screen_height": "INTEGER",

        "viewport_width": "INTEGER",
        "viewport_height": "INTEGER",

        "device_pixel_ratio": "REAL",

        "color_scheme": "TEXT",

        "touch_support": "INTEGER",
        "online_status": "INTEGER",

        "connection_type": "TEXT",
        "connection_effective_type": "TEXT",

        "cookies_enabled": "INTEGER",
        "java_enabled": "INTEGER",

        "timezone_offset": "INTEGER",

        "traffic_source": "TEXT",

        "utm_source": "TEXT",
        "utm_medium": "TEXT",
        "utm_campaign": "TEXT",
        "utm_term": "TEXT",
        "utm_content": "TEXT",

        "is_returning": "INTEGER DEFAULT 0",

        "time_on_page": "REAL",
        "scroll_depth": "INTEGER",

        "gps_permission": "TEXT",

        "gps_latitude": "REAL",
        "gps_longitude": "REAL",
        "gps_accuracy": "REAL",

        "extra_data": "TEXT"
    }

    for column, datatype in required.items():

        if column not in columns:

            try:

                conn.execute(
                    f"ALTER TABLE visitors ADD COLUMN {column} {datatype}"
                )

            except sqlite3.OperationalError:
                pass

    conn.commit()
    conn.close()


# =========================================================
# GET CLIENT IP
# =========================================================

def get_ip():

    forwarded_for = request.headers.get(
        "X-Forwarded-For"
    )

    if forwarded_for:

        return forwarded_for.split(",")[0].strip()

    return request.remote_addr


# =========================================================
# IP GEOLOCATION
# =========================================================

def get_ip_location(ip):

    empty = {

        "country": None,
        "country_code": None,
        "region": None,
        "city": None,
        "postal_code": None,

        "latitude": None,
        "longitude": None,

        "isp": None,
        "organization": None,
        "asn": None,

        "timezone": None
    }

    if not ip:
        return empty

    # Local IP
    if (
        ip.startswith("127.")
        or ip.startswith("10.")
        or ip.startswith("192.168.")
        or ip == "::1"
    ):
        return empty

    try:

        response = requests.get(

            f"https://ipapi.co/{ip}/json/",

            timeout=5,

            headers={
                "User-Agent":
                "VisitorAnalyticsDemo/1.0"
            }
        )

        if response.ok:

            data = response.json()

            return {

                "country":
                    data.get("country_name"),

                "country_code":
                    data.get("country_code"),

                "region":
                    data.get("region"),

                "city":
                    data.get("city"),

                "postal_code":
                    data.get("postal"),

                "latitude":
                    data.get("latitude"),

                "longitude":
                    data.get("longitude"),

                "isp":
                    data.get("org"),

                "organization":
                    data.get("org"),

                "asn":
                    data.get("asn"),

                "timezone":
                    data.get("timezone")
            }

    except Exception:
        pass

    return empty


# =========================================================
# HOME PAGE
# =========================================================

@app.route("/")
def landing():

    ip = get_ip()

    ua_string = request.headers.get(
        "User-Agent",
        ""
    )

    ua = parse(ua_string)

    location = get_ip_location(ip)

    session_id = request.cookies.get(
        "analytics_session"
    )

    returning = 1 if session_id else 0

    if not session_id:

        session_id = str(uuid.uuid4())

    visitor = {

        "visit_time":
            datetime.now(timezone.utc).isoformat(),

        "session_id":
            session_id,

        "ip":
            ip,

        "user_agent":
            ua_string,

        "browser":
            ua.browser.family,

        "browser_version":
            ua.browser.version_string,

        "os":
            ua.os.family,

        "os_version":
            ua.os.version_string,

        "device":
            ua.device.family,

        "device_brand":
            getattr(
                ua.device,
                "brand",
                ""
            ),

        "device_model":
            getattr(
                ua.device,
                "model",
                ""
            ),

        "referrer":
            request.headers.get(
                "Referer",
                ""
            ),

        "page_url":
            request.url,

        "landing_page":
            request.path,

        **location,

        "is_returning":
            returning
    }

    conn = sqlite3.connect(DB)

    cursor = conn.execute("""

        INSERT INTO visitors (

            visit_time,
            session_id,

            ip,
            user_agent,

            browser,
            browser_version,

            os,
            os_version,

            device,
            device_brand,
            device_model,

            referrer,

            page_url,
            landing_page,

            country,
            country_code,
            region,
            city,
            postal_code,

            latitude,
            longitude,

            isp,
            organization,
            asn,

            timezone,

            is_returning

        )

        VALUES (

            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?

        )

    """, (

        visitor["visit_time"],
        visitor["session_id"],

        visitor["ip"],
        visitor["user_agent"],

        visitor["browser"],
        visitor["browser_version"],

        visitor["os"],
        visitor["os_version"],

        visitor["device"],
        visitor["device_brand"],
        visitor["device_model"],

        visitor["referrer"],

        visitor["page_url"],
        visitor["landing_page"],

        visitor["country"],
        visitor["country_code"],
        visitor["region"],
        visitor["city"],
        visitor["postal_code"],

        visitor["latitude"],
        visitor["longitude"],

        visitor["isp"],
        visitor["organization"],
        visitor["asn"],

        visitor["timezone"],

        visitor["is_returning"]

    ))

    visitor_id = cursor.lastrowid

    conn.commit()
    conn.close()

    response = render_template(
        "landing.html"
    )

    # Session cookie
    response = app.make_response(response)

    response.set_cookie(
        "analytics_session",
        session_id,
        max_age=60 * 60 * 24 * 365,
        httponly=True,
        samesite="Lax",
        secure=True
    )

    response.headers[
        "X-Visitor-ID"
    ] = str(visitor_id)

    return response


# =========================================================
# BROWSER INFORMATION API
# =========================================================

@app.route(
    "/api/browser-info",
    methods=["POST"]
)
def browser_info():

    data = request.get_json(
        silent=True
    ) or {}

    visitor_id = request.headers.get(
        "X-Visitor-ID"
    )

    # Better fallback
    if not visitor_id:

        visitor_id = request.args.get(
            "visitor_id"
        )

    if not visitor_id:

        return jsonify({
            "success": False,
            "error": "Missing visitor ID"
        }), 400

    allowed = {

        "language",
        "languages",

        "screen_width",
        "screen_height",

        "viewport_width",
        "viewport_height",

        "device_pixel_ratio",

        "color_scheme",

        "touch_support",

        "online_status",

        "connection_type",
        "connection_effective_type",

        "cookies_enabled",
        "java_enabled",

        "timezone",
        "timezone_offset",

        "traffic_source",

        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",

        "time_on_page",
        "scroll_depth",

        "gps_permission",

        "gps_latitude",
        "gps_longitude",
        "gps_accuracy"
    }

    clean = {
        k: data.get(k)
        for k in allowed
        if k in data
    }

    conn = sqlite3.connect(DB)

    if clean:

        fields = []
        values = []

        for key, value in clean.items():

            fields.append(
                f"{key} = ?"
            )

            if isinstance(value, (dict, list)):

                value = json.dumps(value)

            values.append(value)

        values.append(visitor_id)

        sql = f"""

            UPDATE visitors

            SET {", ".join(fields)}

            WHERE id = ?

        """

        conn.execute(
            sql,
            values
        )

        conn.commit()

    conn.close()

    return jsonify({
        "success": True
    })


# =========================================================
# DASHBOARD
# =========================================================

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


# =========================================================
# API: VISITOR DETAILS
# =========================================================

@app.route("/api/visitors")
def visitors_api():

    conn = sqlite3.connect(DB)

    conn.row_factory = sqlite3.Row

    visitors = conn.execute("""

        SELECT *

        FROM visitors

        ORDER BY id DESC

        LIMIT 500

    """).fetchall()

    conn.close()

    return jsonify([
        dict(v)
        for v in visitors
    ])


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

init_db()

ensure_columns()


# =========================================================
# LOCAL DEVELOPMENT
# =========================================================

if __name__ == "__main__":

    app.run(

        host="127.0.0.1",

        port=5000,

        debug=True
    )
