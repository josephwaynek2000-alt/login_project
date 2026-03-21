import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
from PIL import Image
from werkzeug.security import generate_password_hash, check_password_hash

import os
from flask import Flask

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-secret")

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

UPLOAD_FOLDER = os.path.join("static", "Uploads")


app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

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
            return redirect(url_for("photos"))

        file = request.files["photo"]

        if file.filename == "":
            flash("Photo uploaded!")
            return redirect(url_for("photos"))

        if file and allowed_file(file.filename):
            import time

            filename = f"{int(time.time())}_{secure_filename(file.filename)}"
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            image = Image.open(file)
            # Resize to max width/height
            image.thumbnail((800, 800))  # keeps aspect ratio
            image.save(save_path)
            return redirect(url_for("photos"))

    images = []

    if os.path.exists(app.config["UPLOAD_FOLDER"]):
        for filename in os.listdir(app.config["UPLOAD_FOLDER"]):
            if allowed_file(filename):
                images.append(filename)

    images.sort(reverse=True)

    return render_template(
        "photos.html",
        username=session["user"],
        page="photos",
        images=images
    )

@app.route("/delete-photo/<filename>", methods=["POST"])
def delete_photo(filename):
    if "user" not in session:
        return redirect(url_for("login"))

    safe_name = secure_filename(filename)
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], safe_name)

    if os.path.exists(file_path):
        os.remove(file_path)

    return redirect(url_for("photos"))

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))


if __name__ == "__main__":
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    app.run(debug=True)