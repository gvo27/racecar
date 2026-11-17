"""Design rules of one board: the tuning file that the board tools and the mill checks read.

File: `design_rules.toml` in the board directory. A board without that file uses `design_rules.toml` of the lab
directory (the mill profile). Each value has `value`, `unit`, `status` (`assumed` or `confirmed`) and `source`,
like the lab file. Change a value, then run `make pcb-all BOARD=<board>`.

Stdlib only (no pcbnew): `load()` returns a `Rules` object. `python3 rules.py [file]` prints the rules.
"""
import os
import sys
import tomllib
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lab  # noqa: E402
import paths  # noqa: E402

FILE_NAME = "design_rules.toml"
# key -> (minimum, maximum) in mm. A value outside the range is a typing error, not a design choice.
SCALARS = {
    "horizontal_error": (0.0, 1.0),
    "cut_spacing_min": (0.0, 10.0),
    "clearance": (0.1, 5.0),
    "track_min": (0.1, 10.0),
    "zone_min_width": (0.1, 10.0),
    "zone_clearance": (0.1, 5.0),
    "component_gap": (0.0, 20.0),
    "module_gap": (0.0, 20.0),
    "edge_clearance": (0.1, 10.0),
    "edge_band": (0.0, 10.0),
    "annular_min": (0.1, 5.0),
    "annular_target": (0.1, 5.0),
}
CLASS_ORDER = ("Default", "HighCurrent", "Power3A", "Power5A")


@dataclass
class Exception_:
    ref: str
    clearance: float
    reason: str
    zones: bool = False  # True: the lower clearance is also valid for zone fill (planned zones at the part)
    own_pads: bool = False  # True: the lower clearance is valid only between two pads of this part


@dataclass
class Rules:
    path: str
    horizontal_error: float
    cut_spacing_min: float
    clearance: float
    track_min: float
    zone_min_width: float
    zone_clearance: float
    component_gap: float
    module_gap: float
    edge_clearance: float
    edge_band: float
    annular_min: float
    annular_target: float
    track_width: dict = field(default_factory=dict)   # net class -> width mm
    exceptions: list = field(default_factory=list)
    exclude: tuple = ()
    footprint: dict = field(default_factory=dict)     # ref -> footprint of this board (not the footprint of the base schematic)
    status: dict = field(default_factory=dict)        # key -> assumed|confirmed

    @property
    def copper_target(self):
        """Width of copper between two isolation gaps that keeps the gaps cut_spacing_min apart (center to center)."""
        return max(self.track_min, self.cut_spacing_min - self.clearance)

    def gap_min(self, cut_width):
        """Smallest copper gap that the mill can cut with a horizontal error on each side."""
        return cut_width + 2.0 * self.horizontal_error

    def exception_for(self, ref):
        return next((e for e in self.exceptions if e.ref == ref), None)

    def assumed(self):
        return sorted(k for k, s in self.status.items() if s == "assumed")


def rules_file(board_dir=None):
    own = os.path.join(board_dir or paths.board_dir(), FILE_NAME)
    return own if os.path.isfile(own) else os.path.join(lab.lab_dir(), FILE_NAME)


def _entry(raw, key, where):
    t = raw.get(key)
    if not isinstance(t, dict):
        raise ValueError("%s: key [%s] is missing" % (where, key))
    if t.get("status") not in ("assumed", "confirmed") or not t.get("source"):
        raise ValueError("%s: [%s] needs status (assumed|confirmed) and source" % (where, key))
    return t


def load(path=None):
    path = path or rules_file()
    with open(path, "rb") as fh:
        raw = tomllib.load(fh)
    known = set(SCALARS) | {"netclass", "exception", "parts"}
    extra = sorted(set(raw) - known)
    if extra:
        raise ValueError("%s: unknown keys: %s" % (path, ", ".join(extra)))
    vals, status = {}, {}
    for key, (lo, hi) in SCALARS.items():
        t = _entry(raw, key, path)
        v = float(t["value"])
        if not lo <= v <= hi:
            raise ValueError("%s: [%s] value %s is not in the range %s to %s mm" % (path, key, v, lo, hi))
        vals[key], status[key] = v, t["status"]
    classes = raw.get("netclass", {})
    missing = [c for c in CLASS_ORDER if c not in classes]
    if missing or set(classes) - set(CLASS_ORDER):
        raise ValueError("%s: [netclass.*] must be exactly: %s" % (path, ", ".join(CLASS_ORDER)))
    widths = {}
    for name in CLASS_ORDER:
        t = _entry(classes, name, path + " netclass")
        widths[name] = float(t["track_width"])
        status["netclass." + name] = t["status"]
        if widths[name] < vals["track_min"] - 1e-9:
            raise ValueError("%s: netclass %s track_width %.2f is below track_min %.2f" % (path, name, widths[name], vals["track_min"]))
    exc = []
    for e in raw.get("exception", []):
        refs = [e["ref"]] if e.get("ref") else list(e.get("refs", []))  # one part, or a list of parts with the same values
        for k in ("clearance", "reason"):
            if not e.get(k):
                raise ValueError("%s: exception %r: missing field %s" % (path, e, k))
        if not refs or (e.get("ref") and e.get("refs")):
            raise ValueError("%s: exception %r: needs ref or refs" % (path, e))
        if set(e) - {"ref", "refs", "clearance", "reason", "zones", "own_pads"}:
            raise ValueError("%s: exception %s: unknown field" % (path, refs))
        if e.get("zones") and e.get("own_pads"):  # the DRU rule and the pad clearance of build_pcb would disagree
            raise ValueError("%s: exception %s: use zones or own_pads, not both" % (path, refs))
        for ref in refs:
            exc.append(Exception_(ref, float(e["clearance"]), e["reason"], bool(e.get("zones", False)), bool(e.get("own_pads", False))))
    parts = raw.get("parts", {})
    if set(parts) - {"exclude", "reason", "footprint", "footprint_reason"}:
        raise ValueError("%s: [parts] has unknown keys" % path)
    r = Rules(path=path, track_width=widths, exceptions=exc, exclude=tuple(parts.get("exclude", [])), footprint=dict(parts.get("footprint", {})), status=status, **vals)
    if r.annular_target < r.annular_min - 1e-9:
        raise ValueError("%s: annular_target %.2f is below annular_min %.2f" % (path, r.annular_target, r.annular_min))
    if r.zone_clearance < r.clearance - 1e-9:
        raise ValueError("%s: zone_clearance %.2f is below clearance %.2f" % (path, r.zone_clearance, r.clearance))
    return r


def check_against_lab(r, lim_raw):
    """The design rules must not go below the lab limits (milling.toml). Returns a list of problems."""
    out = []
    for key, lab_key in (("track_min", "track_min"), ("edge_clearance", "edge_clearance"), ("annular_min", "annular_min")):
        if getattr(r, key) < lim_raw[lab_key]["value"] - 1e-9:
            out.append("%s %.2f mm is below the lab limit %s %.2f mm" % (key, getattr(r, key), lab_key, lim_raw[lab_key]["value"]))
    return out


def main(argv=None):
    r = load(argv[0] if argv else None)
    print("design rules: %s" % r.path)
    for key in SCALARS:
        print("  %-18s %6.3f mm  (%s)" % (key, getattr(r, key), r.status[key]))
    for name in CLASS_ORDER:
        print("  track %-12s %6.3f mm  (%s)" % (name, r.track_width[name], r.status["netclass." + name]))
    print("  %-18s %6.3f mm  (derived: cut_spacing_min - clearance, at least track_min)" % ("copper_target", r.copper_target))
    for e in r.exceptions:
        print("  exception %-8s clearance %.2f mm: %s" % (e.ref, e.clearance, e.reason))
    if r.exclude:
        print("  parts not on this board: %s" % ", ".join(r.exclude))
    for ref, fp in sorted(r.footprint.items()):
        print("  footprint %-5s %s" % (ref, fp))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
