import json
import os
import shutil

import cv2

from time import sleep

from celery import Celery

from db import File

celery_app = Celery("faces", broker="amqp://faces:31@192.168.50.43:5672/faces")
celery_app.conf.task_default_queue = 'default'
celery_app.conf.task_routes = {
    "*.process_image": {
        "queue": "faces-input",
    },
    "*.notify_status": {
        "queue": "faces-output",
    },
}


@celery_app.task
def process_image(image_id: int, input_hash: str):
    file = File.find_file_by_hash(input_hash)

    if image_id != file.image_id:  # The same file is being processed
        while not file.processed:
            sleep(0.25)
            file.refresh()
    else:
        notify_status.delay(image_id, input_hash)

        try:
            faces = _make_processing(file=file)
            file.meta = json.dumps({
                "faces": faces,
            })
        except Exception as e:
            file.failed = True
            file.meta = str(e)
        finally:
            file.processed = True
            file.save()

    notify_status.delay(image_id, input_hash)

    return f"Image #{image_id} has been processed..."


@celery_app.task
def notify_status(image_id, input_hash):
    return f"Image #{image_id}: HASH={input_hash}"


def _make_processing(file: File):
    input_path = f"rsc/uploads/{file.image_id}"

    # Process file
    output_dir = f"rsc/output/{file.image_id}"
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir, mode=0o775, exist_ok=True)

    img = cv2.imread(input_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    face_cascade = cv2.CascadeClassifier("clasifiers/haarcascade_frontalface_alt.xml")

    faces = face_cascade.detectMultiScale(gray, 1.1, 4)
    faces_amount = len(faces)

    for i, (x, y, w, h) in enumerate(faces):
        face = img[y:y + h, x:x + w]
        cv2.imwrite(os.path.join(output_dir, f"{i}.jpg"), face)

    return faces_amount
