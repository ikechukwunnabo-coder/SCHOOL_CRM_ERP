from celery import shared_task


@shared_task(name="core.ping")
def celery_ping():
    return {"status": "ok"}
