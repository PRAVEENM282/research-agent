from celery import Celery
from celery.schedules import schedule
from celery.signals import setup_logging

from src.config.logging_config import configure_logging
from src.config.settings import settings

celery_app = Celery(
    "handoff",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["src.worker.tasks"],
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
    task_time_limit=300,
    task_soft_time_limit=270,
    broker_connection_retry_on_startup=True,
    result_expires=86400,
    beat_schedule={
        "dispatch-pending-outbox": {
            "task": "src.worker.tasks.dispatch_pending_outbox",
            "schedule": schedule(run_every=2.0),
        }
    },
)


@setup_logging.connect
def configure_celery_logging(**kwargs: object) -> None:
    configure_logging(settings.log_level)
