from __future__ import annotations

from inspect import signature
from typing import get_type_hints

from fastapi.routing import APIRoute
from starlette.responses import Response

from app.main import app


def test_every_json_api_route_declares_a_response_model() -> None:
    missing: list[str] = []

    for route in app.routes:
        if not isinstance(route, APIRoute) or not route.path.startswith("/api/v1/"):
            continue

        return_type = get_type_hints(route.endpoint).get(
            "return", signature(route.endpoint).return_annotation
        )
        returns_raw_response = isinstance(return_type, type) and issubclass(return_type, Response)
        if route.response_model is None and not returns_raw_response:
            methods = ",".join(sorted(route.methods or []))
            missing.append(f"{methods} {route.path}")

    assert missing == [], "JSON routes without response models: " + ", ".join(missing)


def test_openapi_json_success_responses_reference_schemas() -> None:
    document = app.openapi()
    missing: list[str] = []

    for path, operations in document["paths"].items():
        for method, operation in operations.items():
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            success_responses = [
                response
                for status_code, response in operation.get("responses", {}).items()
                if status_code.startswith("2")
            ]
            for response in success_responses:
                json_schema = response.get("content", {}).get("application/json", {}).get("schema")
                if json_schema == {}:
                    missing.append(f"{method.upper()} {path}")

    assert missing == [], "JSON success responses with empty schemas: " + ", ".join(missing)
