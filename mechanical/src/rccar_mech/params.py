"""Load the TOML files of mechanical/config.

Fact files (hardware.toml, print.toml): each table has `status` ("confirmed" or "assumed") and a non-empty `source`.
Design files (<model>.toml): parameters that the designer sets. They have no status.
"""

import tomllib
from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"
STATUSES = ("confirmed", "assumed")


class ParamError(ValueError):
    """A config file breaks the rules of this module."""


def config_path(name: str) -> Path:
    return CONFIG_DIR / name


def _read(path) -> dict:
    with open(path, "rb") as fh:
        return tomllib.load(fh)


def load_facts(path) -> dict:
    data = _read(path)
    for name, table in data.items():
        if not isinstance(table, dict):
            raise ParamError(f"{path}: key {name} is outside a table")
        if table.get("status") not in STATUSES:
            raise ParamError(f"{path}: table [{name}] needs status = confirmed or assumed")
        if not str(table.get("source", "")).strip():
            raise ParamError(f"{path}: table [{name}] needs a source")
    return data


def _convert(path, key, old, value):
    if isinstance(old, bool):
        v = str(value).strip().lower()
        if v not in ("true", "false"):
            raise ParamError(f"{path}: {key} needs true or false, not {value}")
        return v == "true"
    try:
        return type(old)(value)
    except ValueError as e:
        raise ParamError(f"{path}: {key} = {value}: {e}") from e


def load_design(path, overrides: dict | None = None) -> dict:
    data = _read(path)
    for key, value in (overrides or {}).items():
        if key not in data:
            raise ParamError(f"{path}: unknown parameter {key}")
        data[key] = _convert(path, key, data[key], value)
    return data


def assumed(facts: dict) -> list[str]:
    return [name for name, table in facts.items() if table["status"] == "assumed"]
