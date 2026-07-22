"""Configuration loading with parameter provenance preserved."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
import tomllib


@dataclass(frozen=True)
class Parameter:
    """A scalar configuration value together with its provenance."""

    value: Any
    unit: str | None
    source: str
    ref: str


def load_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    with config_path.open("rb") as stream:
        config = tomllib.load(stream)
    config["_config_path"] = str(config_path.resolve())
    return config


def parameter(config: Mapping[str, Any], *keys: str) -> Parameter:
    node: Any = config
    for key in keys:
        node = node[key]
    if not isinstance(node, Mapping) or "value" not in node:
        dotted = ".".join(keys)
        raise TypeError(f"{dotted} is not a provenance-tagged parameter")
    return Parameter(
        value=node["value"],
        unit=node.get("unit"),
        source=str(node.get("source", "TBD")),
        ref=str(node.get("ref", "TBD")),
    )


def value(config: Mapping[str, Any], *keys: str) -> Any:
    return parameter(config, *keys).value

