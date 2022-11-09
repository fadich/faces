import asyncio
import json

import pika

import websockets

from db import File


def create_rabbitmq_connection():
    return pika.BlockingConnection(
        parameters=(
            pika.ConnectionParameters(
                host="192.168.50.43",
                port=5672,
                virtual_host="faces",
                credentials=pika.credentials.PlainCredentials(
                    username="faces",
                    password="31"
                )
            )
        )
    )


ws_connections = set()


async def register(websocket):
    print(f"New connection: {websocket}")
    ws_connections.add(websocket)
    try:
        await websocket.wait_closed()
    finally:
        ws_connections.remove(websocket)

    print(f"Connection closed: {websocket}")


async def main():
    async with websockets.serve(register, "192.168.50.43", 5001):
        await run_worker()


async def run_worker():
    channel = create_rabbitmq_connection().channel()

    try:
        while True:
            for meth, props, body in channel.consume(
                queue="faces-output",
                inactivity_timeout=0.01
            ):
                if body is not None:
                    body = json.loads(body)
                    send_status(*body[0])

                    channel.basic_ack(delivery_tag=meth.delivery_tag)

                await asyncio.sleep(0.1)
    except pika.exceptions.ConnectionClosedByBroker:
        pass


def send_status(image_id: int, input_hash: str):
    file = File.find_file_by_hash(input_hash)
    if file is None:
        print(f"No file found for hash '{input_hash}'")

        return

    msg = {
        "image_id": image_id,
        "status": None,
        "status_code": None,
        "result": None,
        "info": None,
    }

    if file.processed and file.failed:
        msg["status"] = "Failed"
        msg["status_code"] = 520
    elif file.processed and not file.failed:
        if image_id == file.image_id:
            msg["status"] = "Processed"
        else:
            msg["status"] = "Already processed"

        msg["status_code"] = 200

        faces = file.get_faces_found()
        if faces is not None:
            msg["info"] = f"Found {faces} face(s)"
        if int(faces):
            msg["result"] = file.result_url
    else:
        msg["status"] = "Processing"
        msg["status_code"] = 202

    websockets.broadcast(ws_connections, json.dumps(msg))


if __name__ == "__main__":
    print("Listening on ws://192.168.50.43:5001")
    print("Press [Ctrl+C] to stop")

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass