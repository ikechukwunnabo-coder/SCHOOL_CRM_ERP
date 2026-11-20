from django.db import connections
from django.db.utils import OperationalError
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    db_ok = True
    try:
        connections["default"].cursor()
    except OperationalError:
        db_ok = False
    status = "ok" if db_ok else "degraded"
    return Response({"status": status, "database": "ok" if db_ok else "unavailable"})
