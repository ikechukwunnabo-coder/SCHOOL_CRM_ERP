from django.core.cache import cache
from django.db import connections
from django.db.utils import OperationalError
from redis.exceptions import RedisError
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    db_ok = True
    try:
        with connections["default"].cursor():
            pass
    except OperationalError:
        db_ok = False

    cache_key = "health-check"
    cache_ok = True
    try:
        cache.set(cache_key, "ok", timeout=5)
        cache_ok = cache.get(cache_key) == "ok"
        cache.delete(cache_key)
    except RedisError:
        cache_ok = False

    status = "ok" if db_ok and cache_ok else "degraded"
    return Response(
        {
            "status": status,
            "database": "ok" if db_ok else "unavailable",
            "cache": "ok" if cache_ok else "unavailable",
        }
    )
