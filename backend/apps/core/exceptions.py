from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler


class ConflictError(APIException):
    status_code = 409
    default_detail = "The request conflicts with the current resource state."


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        # Normalize error payload shape (extend as API design matures)
        response.data = {"errors": response.data}
    return response
