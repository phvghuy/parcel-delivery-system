from celery import Celery

from smart_delivery_routing.config import REDIS_URL

celery_app = Celery(
    "smart_delivery_routing",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["smart_delivery_routing.application.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    result_expires=86400,
)
