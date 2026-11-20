from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        # Normalize error payload shape (extend as API design matures)
        response.data = {"errors": response.data}
    return response
