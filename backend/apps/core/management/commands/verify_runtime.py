from django.core.cache import cache
from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from django.db.utils import OperationalError
from redis.exceptions import RedisError

from apps.core.tasks import celery_ping
from config.celery import app as celery_app


class Command(BaseCommand):
    def handle(self, *args, **options):
        results = {}

        try:
            with connections["default"].cursor():
                results["database"] = "ok"
        except OperationalError as exc:
            results["database"] = str(exc)

        cache_key = "runtime-verification"
        try:
            cache.set(cache_key, "ok", timeout=10)
            results["cache"] = "ok" if cache.get(cache_key) == "ok" else "unexpected value"
            cache.delete(cache_key)
        except RedisError as exc:
            results["cache"] = str(exc)

        connection = celery_app.connection()
        try:
            connection.ensure_connection(max_retries=1)
            results["broker"] = "ok"
        except Exception as exc:
            results["broker"] = str(exc)
        finally:
            connection.release()

        try:
            results["result_backend"] = "ok" if celery_app.backend.client.ping() else "unavailable"
        except Exception as exc:
            results["result_backend"] = str(exc)

        try:
            result = celery_ping.apply(throw=True)
            task_ok = result.successful() and result.get() == {"status": "ok"}
            results["task"] = "ok" if task_ok else "unexpected result"
        except Exception as exc:
            results["task"] = str(exc)

        for name, status in results.items():
            style = self.style.SUCCESS if status == "ok" else self.style.ERROR
            self.stdout.write(style(f"{name}: {status}"))

        failed = [name for name, status in results.items() if status != "ok"]
        if failed:
            raise CommandError(f"Runtime verification failed: {', '.join(failed)}")

        self.stdout.write(self.style.SUCCESS("Runtime verification passed"))
