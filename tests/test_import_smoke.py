"""Smoke tests for public API imports and model schema generation."""

from __future__ import annotations

import inspect

import pytest
from pydantic import BaseModel

import models as fdd

PUBLIC_MODEL_NAMES = sorted(
    name
    for name in fdd.__all__
    if inspect.isclass(getattr(fdd, name)) and issubclass(getattr(fdd, name), BaseModel)
)


def test_top_level_api_imports_are_available() -> None:
    """Top-level package exports should remain importable."""

    for name in fdd.__all__:
        assert hasattr(fdd, name), f"missing export: {name}"


@pytest.mark.parametrize("model_name", PUBLIC_MODEL_NAMES)
def test_public_models_generate_json_schema(model_name: str) -> None:
    """
    Public Pydantic models should build JSON schema without raising.

    This is a light smoke test for model definitions and references.
    """

    model_cls = getattr(fdd, model_name)
    schema = model_cls.model_json_schema()

    assert schema.get("type") == "object"
    assert "properties" in schema
