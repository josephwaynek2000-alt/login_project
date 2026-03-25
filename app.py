import os
import base64
import requests
import psycopg2
from urllib.parse import urlparse
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from PIL import Image
import cloudinary
import cloudinary.uploader
import cloudinary.api

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-secret")

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
UPLOAD_FOLDER = os.path.join("static", "uploads")

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    return psycopg2.connect(os.environ["DATABASE_URL"])

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS songs (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            artist TEXT NOT NULL,
            spotify_link TEXT NOT NULL,
            embed_link TEXT NOT NULL
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

app.config["SESSION_COOKIE_SECURE"] = not app.debug
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

init_db()

def extract_track_id(spotify_link):
    spotify_link = spotify_link.strip().split("?")[0]

    if "/track/" not in spotify_link:
        return None

    return spotify_link.split("/track/")[1].split("/")[0]


def get_spotify_access_token():
    client_id = os.environ.get("SPOTIFY_CLIENT_ID")
    client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise ValueError("Missing Spotify API credentials.")

    auth_string = f"{client_id}:{client_secret}"
    auth_bytes = auth_string.encode("utf-8")
    auth_b64 = base64.b64encode(auth_bytes).decode("utf-8")

    response = requests.post(
        "https://accounts.spotify.com/api/token",
        headers={
            "Authorization": f"Basic {auth_b64}",
            "Content-Type": "application/x-www-form-urlencoded"
        },
        data={"grant_type": "client_credentials"},
        timeout=15
    )

    response.raise_for_status()
    return response.json()["access_token"]


def get_track_details(track_id):
    token = get_spotify_access_token()

    response = requests.get(
        f"https://api.spotify.com/v1/tracks/{track_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=15
    )

    response.raise_for_status()
    data = response.json()

    title = data["name"]
    artist = ", ".join(artist["name"] for artist in data["artists"])
    spotify_link = data["external_urls"]["spotify"]
    embed_link = f"https://open.spotify.com/embed/track/{track_id}"

    return {
        "title": title,
        "artist": artist,
        "spotify_link": spotify_link,
        "embed_link": embed_link
    }

cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
    secure=True
)

USERNAME = "Iva_Jansen"
PASSWORD_HASH = generate_password_hash("Honey")

print("RUNNING THIS APP FILE NOW")


@app.route("/")
def home():
    if "user" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        print("TYPED USERNAME:", repr(username))
        print("TYPED PASSWORD:", repr(password))
        print("EXPECTED USERNAME:", repr(USERNAME))
        print("EXPECTED PASSWORD:", repr(PASSWORD_HASH))

        if username == USERNAME and check_password_hash(PASSWORD_HASH, password):
            session["user"] = username
            return redirect(url_for("dashboard"))
        else:
            error = "Invalid username or password."

    return render_template("login.html", error=error)

@app.route("/add-song", methods=["POST"])
def add_song():
    if "user" not in session:
        return redirect(url_for("login"))

    spotify_link = request.form.get("spotify_link", "").strip()

    if not spotify_link:
        flash("Please paste a Spotify track link.")
        return redirect(url_for("dashboard"))

    track_id = extract_track_id(spotify_link)
    if not track_id:
        flash("Please use a Spotify track link.")
        return redirect(url_for("dashboard"))

    try:
        song = get_track_details(track_id)

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO songs (title, artist, spotify_link, embed_link)
            VALUES (%s, %s, %s, %s)
        """, (
            song["title"],
            song["artist"],
            song["spotify_link"],
            song["embed_link"]
        ))
        conn.commit()
        cur.close()
        conn.close()

        flash("Song added successfully.")
    except Exception as e:
        print("SPOTIFY ERROR:", e)
        flash("Could not fetch song info from Spotify.")

    return redirect(url_for("dashboard"))

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, title, artist, spotify_link, embed_link
        FROM songs
        ORDER BY id DESC
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    songs = [
        {
            "id": row[0],
            "title": row[1],
            "artist": row[2],
            "spotify_link": row[3],
            "embed_link": row[4],
        }
        for row in rows
    ]

    return render_template(
        "dashboard.html",
        username=session["user"],
        songs=songs,
        page="dashboard"
    )


@app.route("/letters")
def letters():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("letters.html", username=session["user"], page="letters")

@app.route("/memories")
def memories():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("memories.html", username=session["user"], page="memories")

@app.route("/photos", methods=["GET", "POST"])
def photos():
    if "user" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        if "photo" not in request.files:
            flash("No photo uploaded.")
            return redirect(url_for("photos"))

        file = request.files["photo"]

        if file.filename == "":
            flash("No photo selected.")
            return redirect(url_for("photos"))

        if file and allowed_file(file.filename):
            try:
                result = cloudinary.uploader.upload(
                    file,
                    folder="login_project_photos",
                    resource_type="image"
                )
                flash("Photo uploaded successfully.")
            except Exception as e:
                flash(f"Upload failed: {str(e)}")

            return redirect(url_for("photos"))

    images = []

    try:
        result = cloudinary.api.resources(
            type="upload",
            prefix="login_project_photos/",
            resource_type="image",
            max_results=100
        )

        for resource in result.get("resources", []):
            images.append({
                "url": resource["secure_url"],
                "public_id": resource["public_id"]
            })

    except Exception as e:
        flash(f"Could not load photos: {str(e)}")

    return render_template(
        "photos.html",
        username=session["user"],
        page="photos",
        images=images
    )

@app.route("/delete-photo", methods=["POST"])
def delete_photo():
    if "user" not in session:
        return redirect(url_for("login"))

    public_id = request.form.get("public_id")

    if not public_id:
        flash("Missing photo ID.")
        return redirect(url_for("photos"))

    try:
        cloudinary.uploader.destroy(public_id, resource_type="image")
        flash("Photo deleted.")
    except Exception as e:
        flash(f"Delete failed: {str(e)}")

    return redirect(url_for("photos"))

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)