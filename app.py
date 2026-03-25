import os
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

app.config["SESSION_COOKIE_SECURE"] = not app.debug
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
    secure=True
)

USERNAME = "Iva_Jansen"
PASSWORD_HASH = generate_password_hash("Honey")

print("RUNNING THIS APP FILE NOW")
print("CURRENT USERNAME:", repr(USERNAME))
print("CURRENT PASSWORD:", repr(PASSWORD_HASH))

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

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html", username=session["user"], page="dashboard")

@app.route("/add-song", methods=["POST"])
def add_song():
    if "user" not in session:
        return redirect(url_for("login"))

    title = request.form.get("title", "").strip()
    artist = request.form.get("artist", "").strip()
    spotify_link = request.form.get("spotify_link", "").strip()

    if title and artist and spotify_link:
        songs.append({
            "title": title,
            "artist": artist,
            "spotify_link": spotify_link
        })
        flash("Song added successfully.")
    else:
        flash("Please fill out all song fields.")
        
    return redirect(url_for("dashboard"))

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