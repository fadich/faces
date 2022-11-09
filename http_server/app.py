import hashlib
import os

from flask import (
    Flask,
    request,
    Response,
    render_template,
    abort,
    send_from_directory,
)

from db import File
from tasks import process_image

app = Flask(__name__, template_folder="templates")

app.config["MAX_CONTENT_LENGTH"] = 256 * 1024 * 1024 * 1024  # 256Mb
app.config["UPLOAD_FOLDER"] = "rsc/uploads"  # 256Mb

if not os.path.isdir(app.config["UPLOAD_FOLDER"]):
    os.makedirs(app.config["UPLOAD_FOLDER"], mode=0o775, exist_ok=True)


@app.route("/")
def render_form():
    return render_template("upload-form.html")


@app.route("/", methods=["POST"])
def upload_file():
    if "image_id" not in request.form:
        return "No ID", 400

    image_id = request.form.get("image_id")

    if not image_id.isdigit():
        return "Invalid ID", 400

    image_id = int(image_id)
    if File.find_file_by_id(image_id) is not None:
        return "Invalid ID", 400

    if "file" not in request.files:
        return "Not found", 400

    file = request.files.get("file")

    if file.filename == "":
        return "No selected file", 400

    if not file.mimetype.startswith("image"):
        return "Invalid type", 400

    sha256_hash = hashlib.sha256()
    for byte_block in iter(lambda: file.stream.read(4096), b""):
        sha256_hash.update(byte_block)

    file.stream.seek(0)
    filehash = sha256_hash.hexdigest()

    model = File.find_file_by_hash(filehash)
    if model is not None:
        if not model.processed:
            process_image.delay(image_id, model.input_hash)
            return Response("Processing", status=303)

        res = Response("Already processed", status=303)
        faces = model.get_faces_found()

        if faces is not None:
            res.headers["X-FACES-INFO"] = f"Found {faces} face(s)"
        if int(faces):
            res.headers["X-FACES-RESULT-URL"] = model.result_url

        return res

    input_path = os.path.join(app.config["UPLOAD_FOLDER"], f"{image_id}")
    file.save(input_path)

    model = File(
        image_id=image_id,
        input_hash=filehash
    )

    model.save()

    try:
        process_image.delay(image_id, model.input_hash)
    except Exception:
        model.delete()

        return "Failed", 503

    return "In queue", 201


@app.route("/output/", defaults={"req_path": ""})
@app.route("/output/<path:req_path>")
def dir_listing(req_path):
    abs_path = os.path.abspath(os.path.join("rsc/output", req_path))

    if not os.path.exists(abs_path):
        return abort(404)

    # Check if path is a file and serve
    if os.path.isfile(abs_path):
        return send_from_directory(
            directory=os.path.dirname(abs_path),
            path=os.path.basename(abs_path),
            # as_attachment=True,
        )

    # Show directory contents
    files = os.listdir(abs_path)
    return render_template("files.html", files=files)
