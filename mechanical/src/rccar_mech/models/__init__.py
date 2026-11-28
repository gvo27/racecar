"""Model registry. A model module has:

- `build(cfg) -> Compound`: the assembly. Printed parts have a plain label. Reference envelopes (not printed:
  boards, battery, chassis posts) have a label that starts with `ref_`.
- `acceptance(asm, cfg) -> list[Finding]`: the model-specific acceptance criteria.
- `STL_TOLERANCE`: the STL chord tolerance (mm).
The design parameters are in mechanical/config/<model>.toml.
"""

import importlib
import pkgutil

from rccar_mech import params

REF_PREFIX = "ref_"


def names() -> list[str]:
    return sorted(m.name for m in pkgutil.iter_modules(__path__) if not m.name.startswith("_"))


def module(name: str):
    if name not in names():
        raise KeyError(f"unknown model {name}: {', '.join(names())}")
    return importlib.import_module(f"{__name__}.{name}")


def config(name: str, overrides: dict | None = None) -> dict:
    return params.load_design(params.config_path(f"{name}.toml"), overrides)


def build(name: str, overrides: dict | None = None):
    mod = module(name)
    cfg = config(name, overrides)
    return mod.build(cfg), cfg


def acceptance(name: str, asm, cfg) -> list:
    return module(name).acceptance(asm, cfg)


def is_ref(part) -> bool:
    return (part.label or "").startswith(REF_PREFIX)
