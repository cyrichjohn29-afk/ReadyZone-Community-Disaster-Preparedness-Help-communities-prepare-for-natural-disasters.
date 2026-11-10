import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, g, abort

app = Flask(__name__)
BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.environ.get("DB_PATH", os.path.join(BASE, "readyzone.db"))
TABLES = {"announcements", "centers", "supplies", "relief"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS announcements(id INTEGER PRIMARY KEY, title TEXT, body TEXT, level TEXT, created TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS centers(id INTEGER PRIMARY KEY, name TEXT, address TEXT, capacity INTEGER, occupied INTEGER DEFAULT 0, contact TEXT);
CREATE TABLE IF NOT EXISTS supplies(id INTEGER PRIMARY KEY, item TEXT, qty INTEGER, min_qty INTEGER, unit TEXT, location TEXT);
CREATE TABLE IF NOT EXISTS relief(id INTEGER PRIMARY KEY, kind TEXT, title TEXT, details TEXT, contact TEXT, status TEXT DEFAULT 'open', created TEXT DEFAULT CURRENT_TIMESTAMP);
"""

CHECKLISTS = {
    "Before the disaster": [
        "Make a family emergency plan and meeting point",
        "Pack a go-bag: water, food, flashlight, radio, first aid",
        "Keep copies of IDs and documents in a waterproof bag",
        "Save emergency numbers on paper and on your phone",
        "Know your nearest evacuation center and route",
        "Charge power banks and keep spare batteries",
    ],
    "During the disaster": [
        "Follow official announcements and evacuation orders",
        "Turn off gas, power and water if told to",
        "Move to higher ground or a safe room",
        "Keep children, elderly and pets with you",
        "Avoid floodwater and fallen power lines",
    ],
    "After the disaster": [
        "Check family members for injuries",
        "Report damage and needs to your barangay or relief team",
        "Boil or treat water before drinking",
        "Do not enter damaged buildings until cleared",
        "Help neighbors who need assistance",
    ],
}


def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_):
    d = g.pop("db", None)
    if d:
        d.close()


def q(sql, args=()):
    return db().execute(sql, args).fetchall()


def run(sql, args=()):
    db().execute(sql, args)
    db().commit()


def f(name):
    return request.form.get(name, "").strip()


def num(name, default=0):
    try:
        return max(0, int(request.form.get(name, default)))
    except ValueError:
        return default


def init_db():
    con = sqlite3.connect(DB)
    con.executescript(SCHEMA)
    if not con.execute("SELECT 1 FROM centers LIMIT 1").fetchone():
        con.executemany("INSERT INTO announcements(title,body,level) VALUES(?,?,?)", [
            ("Welcome to ReadyZone", "Post alerts, find shelters, track supplies and coordinate relief here.", "info"),
            ("Typhoon watch", "Prepare your go-bag and monitor official weather bulletins.", "warning"),
        ])
        con.executemany("INSERT INTO centers(name,address,capacity,occupied,contact) VALUES(?,?,?,?,?)", [
            ("Barangay Gymnasium", "Main Street, Poblacion", 300, 40, "0917-000-0001"),
            ("Central Elementary School", "School Road", 500, 120, "0917-000-0002"),
        ])
        con.executemany("INSERT INTO supplies(item,qty,min_qty,unit,location) VALUES(?,?,?,?,?)", [
            ("Drinking water", 120, 200, "liters", "Barangay Hall"),
            ("Rice", 300, 150, "kg", "Barangay Hall"),
            ("First aid kits", 25, 20, "kits", "Health Center"),
        ])
        con.executemany("INSERT INTO relief(kind,title,details,contact) VALUES(?,?,?,?)", [
            ("need", "Food packs for 40 families", "Sitio Riverside, flooded access road", "0917-000-0003"),
            ("offer", "Boat and 2 volunteers", "Available for rescue and delivery", "0917-000-0004"),
        ])
    con.commit()
    con.close()


init_db()


@app.route("/")
def index():
    stats = {
        "alerts": q("SELECT COUNT(*) c FROM announcements")[0]["c"],
        "free": q("SELECT COALESCE(SUM(capacity-occupied),0) c FROM centers")[0]["c"],
        "low": q("SELECT COUNT(*) c FROM supplies WHERE qty < min_qty")[0]["c"],
        "open": q("SELECT COUNT(*) c FROM relief WHERE status!='done'")[0]["c"],
    }
    latest = q("SELECT * FROM announcements ORDER BY id DESC LIMIT 3")
    return render_template("index.html", stats=stats, latest=latest)


@app.route("/announcements", methods=["GET", "POST"])
def announcements():
    if request.method == "POST" and f("title"):
        level = f("level") if f("level") in ("info", "warning", "danger") else "info"
        run("INSERT INTO announcements(title,body,level) VALUES(?,?,?)", (f("title"), f("body"), level))
        return redirect(url_for("announcements"))
    return render_template("announcements.html", rows=q("SELECT * FROM announcements ORDER BY id DESC"))


@app.route("/centers", methods=["GET", "POST"])
def centers():
    if request.method == "POST" and f("name"):
        run("INSERT INTO centers(name,address,capacity,occupied,contact) VALUES(?,?,?,?,?)",
            (f("name"), f("address"), num("capacity"), 0, f("contact")))
        return redirect(url_for("centers"))
    return render_template("centers.html", rows=q("SELECT * FROM centers ORDER BY name"))


@app.post("/centers/<int:i>/occupied")
def centers_occupied(i):
    run("UPDATE centers SET occupied=MIN(capacity,?) WHERE id=?", (num("occupied"), i))
    return redirect(url_for("centers"))


@app.route("/supplies", methods=["GET", "POST"])
def supplies():
    if request.method == "POST" and f("item"):
        run("INSERT INTO supplies(item,qty,min_qty,unit,location) VALUES(?,?,?,?,?)",
            (f("item"), num("qty"), num("min_qty"), f("unit"), f("location")))
        return redirect(url_for("supplies"))
    return render_template("supplies.html", rows=q("SELECT * FROM supplies ORDER BY (qty<min_qty) DESC, item"))


@app.post("/supplies/<int:i>/adjust")
def supplies_adjust(i):
    delta = request.form.get("delta", "0")
    try:
        delta = int(delta)
    except ValueError:
        delta = 0
    run("UPDATE supplies SET qty=MAX(0,qty+?) WHERE id=?", (delta, i))
    return redirect(url_for("supplies"))


@app.route("/checklists")
def checklists():
    return render_template("checklists.html", lists=CHECKLISTS)


@app.route("/relief", methods=["GET", "POST"])
def relief():
    if request.method == "POST" and f("title"):
        kind = "offer" if f("kind") == "offer" else "need"
        run("INSERT INTO relief(kind,title,details,contact) VALUES(?,?,?,?)", (kind, f("title"), f("details"), f("contact")))
        return redirect(url_for("relief"))
    return render_template("relief.html", rows=q("SELECT * FROM relief ORDER BY (status='done'), id DESC"))


@app.post("/relief/<int:i>/status")
def relief_status(i):
    s = f("status")
    if s in ("open", "in progress", "done"):
        run("UPDATE relief SET status=? WHERE id=?", (s, i))
    return redirect(url_for("relief"))


@app.post("/delete/<table>/<int:i>")
def delete(table, i):
    if table not in TABLES:
        abort(404)
    run(f"DELETE FROM {table} WHERE id=?", (i,))
    return redirect(request.referrer or url_for("index"))


@app.get("/health")
def health():
    return "ok"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=bool(os.environ.get("DEBUG")))
