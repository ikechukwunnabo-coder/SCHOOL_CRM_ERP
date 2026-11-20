import threading

_audit_context = threading.local()


class AuditContextMiddleware:
    """Attach request/user context for audit logging services."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _audit_context.request = request
        _audit_context.user = getattr(request, "user", None)
        try:
            response = self.get_response(request)
            # refresh user post-auth if needed
            _audit_context.user = getattr(request, "user", _audit_context.user)
            return response
        finally:
            _audit_context.request = None
            _audit_context.user = None


def get_current_request():
    return getattr(_audit_context, "request", None)


def get_current_user():
    user = getattr(_audit_context, "user", None)
    if user and getattr(user, "is_authenticated", False):
        return user
    return None
