from flask import Flask, request, render_template, jsonify
from user_agents import parse
import requests
import sqlite3
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
            gps_accuracy REAL
        )
    """)

    conn.commit()
    conn.close()


# =========================================================
# IP ADDRESS
# =========================================================

def get_ip():

    forwarded = request.headers.get(
        "X-Forwarded-For"
    )

    if forwarded:

        return forwarded.split(",")[0].strip()

    return request.remote_addr


# =========================================================
# IP GEOLOCATION
# =========================================================

def get_ip_location(ip):

    result = {

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
        return result

    if (
        ip.startswith("127.")
        or ip.startswith("10.")
        or ip.startswith("192.168.")
        or ip == "::1"
    ):
        return result

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

            result.update({

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
            })

    except Exception as e:

        print(
            "IP geolocation error:",
            e
        )

    return result


# =========================================================
# HOME PAGE
# =========================================================

@app.route("/")
def landing():

    ip = get_ip()

    user_agent = request.headers.get(
        "User-Agent",
        ""
    )

    ua = parse(user_agent)

    location = get_ip_location(ip)


    # -----------------------------------------------------
    # SESSION
    # -----------------------------------------------------

    session_id = request.cookies.get(
        "analytics_session"
    )

    is_returning = 1 if session_id else 0

    if not session_id:

        session_id = str(
            uuid.uuid4()
        )


    # -----------------------------------------------------
    # INSERT VISITOR
    # -----------------------------------------------------

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

            ?, ?,

            ?, ?,

            ?, ?,

            ?, ?,

            ?, ?, ?,

            ?, ?, ?,

            ?, ?, ?, ?, ?,

            ?, ?,

            ?, ?, ?,

            ?,

            ?

        )

    """, (

        # 1
        datetime.now(
            timezone.utc
        ).isoformat(),

        # 2
        session_id,

        # 3
        ip,

        # 4
        user_agent,

        # 5
        ua.browser.family,

        # 6
        ua.browser.version_string,

        # 7
        ua.os.family,

        # 8
        ua.os.version_string,

        # 9
        ua.device.family,

        # 10
        getattr(
            ua.device,
            "brand",
            ""
        ),

        # 11
        getattr(
            ua.device,
            "model",
            ""
        ),

        # 12
        request.headers.get(
            "Referer",
            ""
        ),

        # 13
        request.url,

        # 14
        request.path,

        # 15
        location["country"],

        # 16
        location["country_code"],

        # 17
        location["region"],

        # 18
        location["city"],

        # 19
        location["postal_code"],

        # 20
        location["latitude"],

        # 21
        location["longitude"],

        # 22
        location["isp"],

        # 23
        location["organization"],

        # 24
        location["asn"],

        # 25
        location["timezone"],

        # 26
        is_returning
    ))


    visitor_id = cursor.lastrowid

    conn.commit()
    conn.close()


    # -----------------------------------------------------
    # RENDER PAGE
    # -----------------------------------------------------

    html = render_template(

        "landing.html",

        visitor_id=visitor_id
    )


    response = app.make_response(
        html
    )


    response.set_cookie(

        "analytics_session",

        session_id,

        max_age=60 * 60 * 24 * 365,

        httponly=True,

        samesite="Lax",

        secure=True
    )


    return response


# =========================================================
# BROWSER INFORMATION
# =========================================================

@app.route(
    "/api/browser-info",
    methods=["POST"]
)
def browser_info():

    data = request.get_json(
        silent=True
    ) or {}


    visitor_id = data.get(
        "visitor_id"
    )


    if not visitor_id:

        return jsonify({

            "success": False,

            "error":
                "Missing visitor_id"

        }), 400


    allowed_fields = [

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
    ]


    updates = []

    values = []


    for field in allowed_fields:

        if field in data:

            updates.append(
                f"{field} = ?"
            )

            value = data[field]


            if isinstance(
                value,
                list
            ):

                value = ",".join(
                    str(x)
                    for x in value
                )


            values.append(value)


    if updates:

        values.append(
            visitor_id
        )


        conn = sqlite3.connect(DB)


        conn.execute(

            f"""
            UPDATE visitors

            SET {", ".join(updates)}

            WHERE id = ?
            """,

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
# JSON API
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

        dict(visitor)

        for visitor in visitors

    ])


# =========================================================
# INITIALIZE DATABASE
# =========================================================

init_db()


# =========================================================
# LOCAL DEVELOPMENT
# =========================================================

if __name__ == "__main__":

    app.run(

        host="127.0.0.1",

        port=5000,

        debug=True
    )
