"""
Shared Flask API helpers — error responses and Pydantic JSON parsing.
"""

from __future__ import annotations

from typing import Any, Type, TypeVar

from flask import jsonify, request
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


class ApiHTTPError(Exception):
    """Raised inside views/helpers; convert via api_error()."""

    def __init__(self, status_code: int, detail: Any):
        self.status_code = status_code
        self.detail = detail
        super().__init__(str(detail))


def api_error(status: int, detail: Any):
    """Return JSON `{"detail": ...}` with the given HTTP status."""
    return jsonify({"detail": detail}), status


def validation_error_response(exc: ValidationError):
    """FastAPI-like 422 body from Pydantic ValidationError.errors()."""
    return jsonify({"detail": exc.errors()}), 422


def parse_json_model(model_cls: Type[T]) -> T:
    """Validate request JSON with a Pydantic model; raises ValidationError on failure."""
    return model_cls.model_validate(request.get_json(silent=True) or {})
