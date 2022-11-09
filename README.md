# Faces

## Getting started

Install requirements
```shell
pip install -r ./requirements.txt
```

Run RabbitMQ broker
```shell
sudo rabbitmq-server -detached
```

Start Flask HTTP-server
```shell
flask --app http_server.app --debug run --host=192.168.50.43
```

Run Celery worker for faces-input queue
```shell
celery -A tasks worker --loglevel=INFO -Q faces-input --pool=threads -n worker-input-1
```

Run WS server / notification worker for faces-output queue
```shell
python -m ws_notification_worker.app
```

### Usage

Web server is up on [192.168.50.43:5000](http://192.168.50.43:5000/).

RabbitMQ Client is up on [192.168.50.43:15672](http://192.168.50.43:15672/).
