"""Setuptools backend with explicit control over bundling Ghostty."""
from contextvars import ContextVar
from functools import wraps
from inspect import signature

from setuptools import build_meta as _setuptools

_bundle = ContextVar("bundle", default=True)


def bundle_library():
    return _bundle.get()


def _bundle_setting(config_settings):
    value = (config_settings or {}).get("bundle", "true")
    if isinstance(value, list) and len(value) == 1:
        value = value[0]
    if not isinstance(value, str) or value.lower() not in ("true", "false"):
        raise ValueError("bundle must be 'true' or 'false'")
    return value.lower() == "true"


def _configured(hook):
    @wraps(hook)
    def configured(*args, **kwargs):
        settings = signature(hook).bind(*args, **kwargs).arguments.get("config_settings")
        token = _bundle.set(_bundle_setting(settings))
        try:
            return hook(*args, **kwargs)
        finally:
            _bundle.reset(token)
    return configured


get_requires_for_build_wheel = _configured(_setuptools.get_requires_for_build_wheel)
get_requires_for_build_sdist = _configured(_setuptools.get_requires_for_build_sdist)
get_requires_for_build_editable = _configured(_setuptools.get_requires_for_build_editable)
prepare_metadata_for_build_wheel = _configured(_setuptools.prepare_metadata_for_build_wheel)
prepare_metadata_for_build_editable = _configured(_setuptools.prepare_metadata_for_build_editable)
build_wheel = _configured(_setuptools.build_wheel)
build_sdist = _configured(_setuptools.build_sdist)
build_editable = _configured(_setuptools.build_editable)
