"""Canonical content-free errors with server-generated correlation identifiers."""
import re
import uuid
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

DEFAULTS = {
    400: ("BAD_REQUEST", "The request is malformed."),
    401: ("UNAUTHENTICATED", "An active authentication session is required."),
    403: ("FORBIDDEN", "This operation is not permitted."),
    404: ("NOT_FOUND", "The resource was not found."),
    409: ("CONFLICT", "The request conflicts with the current resource state."),
    422: ("VALIDATION_ERROR", "The request failed validation."),
    429: ("RATE_LIMITED", "Too many requests. Try again later."),
    503: ("DEPENDENCY_UNAVAILABLE", "A required capability is unavailable."),
}


def envelope(request, status, code=None, fields=None):
    default_code, message = DEFAULTS.get(status, ("INTERNAL_ERROR", "The request could not be completed."))
    error = {"code": code or default_code, "message": message, "request_id": request.state.request_id}
    if fields:
        error["field_errors"] = fields
    return {"error": error}


def install_errors(app):
    @app.middleware("http")
    async def correlate(request, call_next):
        request.state.request_id = str(uuid.uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @app.exception_handler(HTTPException)
    async def http_error(request, exception):
        code = None
        if isinstance(exception.detail, str):
            # Only a bounded machine-code prefix; never free text or input values.
            candidate = exception.detail.split(":", 1)[0]
            if re.fullmatch(r"[A-Z][A-Z0-9_]{1,79}", candidate):
                code = candidate
        return JSONResponse(status_code=exception.status_code,
            content=envelope(request, exception.status_code, code), headers=exception.headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exception):
        fields = [{"field": ".".join(str(part) for part in error["loc"]), "code": error["type"]}
            for error in exception.errors()]
        return JSONResponse(status_code=422, content=envelope(request, 422, fields=fields))
