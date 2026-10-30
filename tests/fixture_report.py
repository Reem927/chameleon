"""Quality report for resize() across every fixture and target.

Usage: python -m tests.fixture_report [out_dir]

For each fixture x target it records the winning layout strategy, whether
the output passes the hard rules, the smallest text size, the worst text
overflow, and how many content units newly overlap compared to the source.
Every output is rendered to a PNG in out_dir (a new temporary directory
when omitted) so the numbers can be checked by eye.
"""

from __future__ import annotations

import logging
import sys
import tempfile
from itertools import combinations
from pathlib import Path

from engine.constraints import validate_candidate
from engine.decision_policy import suggest_policies
from engine.geometry import element_bounds, group_bounds, overlap_area
from engine.layouts import generate_candidates
from engine.resize import resize
from engine.text_fit import text_overflow
from renderer.converter.convert import render_design_to_png
from tests.test_fixtures import FIXTURE_NAMES, load_fixture, target_label, targets_for


ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = ROOT / "brand_kit" / "assets"
# Units overlapping by more than this share of the smaller one count as touching.
OVERLAP_THRESHOLD = 0.01
OVERFLOW_LIMIT = 0.02
READABLE_FONT = 7.0
ILLEGIBLE_FONT = 4.0


def winning_strategy(source, target, output):
    candidates = generate_candidates(source, target, suggest_policies(source, target))
    for name, candidate in candidates:
        if candidate == output:
            if validate_candidate(source, target, candidate):
                return f"{name}(fallback)"
            return name
    return "unmatched"


def is_backdrop(element, canvas):
    """Full-canvas backgrounds and faint decorative shapes."""
    if element["type"] == "shape" and element.get("opacity", 1) <= 0.3:
        return True
    bounds = element_bounds(element)
    return (
        bounds.left <= 0
        and bounds.top <= 0
        and bounds.right >= canvas["width"]
        and bounds.bottom >= canvas["height"]
    )


def content_units(source):
    """Groups as one unit each, plus every ungrouped element that is not backdrop."""
    units = {}
    for element in source["elements"]:
        group_id = element.get("group_id")
        if group_id:
            units.setdefault(f"group:{group_id}", []).append(element["id"])
        elif not is_backdrop(element, source["canvas"]):
            units[element["id"]] = [element["id"]]
    return list(units.values())


def overlap_ratio(first, second):
    smaller = min(first.width * first.height, second.width * second.height)
    if smaller <= 0:
        return 0.0
    return overlap_area(first, second) / smaller


def new_overlaps(source, output):
    source_by_id = {element["id"]: element for element in source["elements"]}
    output_by_id = {element["id"]: element for element in output["elements"]}
    count = 0
    for first, second in combinations(content_units(source), 2):
        before = overlap_ratio(
            group_bounds(source_by_id[i] for i in first),
            group_bounds(source_by_id[i] for i in second),
        )
        after = overlap_ratio(
            group_bounds(output_by_id[i] for i in first),
            group_bounds(output_by_id[i] for i in second),
        )
        if after > OVERLAP_THRESHOLD and after > before + OVERLAP_THRESHOLD:
            count += 1
    return count


def measure(name, source, target, out_dir):
    row = {"fixture": name, "target": target_label(target)}
    try:
        output = resize(source, target)
    except Exception as error:  # noqa: BLE001 - the report must cover every case
        row.update(strategy=f"raised {type(error).__name__}", valid=False, min_font=None,
                   max_overflow=None, new_overlaps=None, png="")
        return row
    texts = [element for element in output["elements"] if element["type"] == "text"]
    row["strategy"] = winning_strategy(source, target, output)
    row["valid"] = not validate_candidate(source, target, output)
    row["min_font"] = min((element["font_size"] for element in texts), default=None)
    row["max_overflow"] = max((text_overflow(element) for element in texts), default=0.0)
    row["new_overlaps"] = new_overlaps(source, output)
    png = Path(out_dir) / f"{name}__{row['target']}.png"
    try:
        render_design_to_png(output, ASSETS_DIR, png)
        row["png"] = png.name
    except Exception as error:  # noqa: BLE001
        row["png"] = f"render failed: {type(error).__name__}"
    return row


def format_number(value, digits):
    return "-" if value is None else f"{value:.{digits}f}"


def print_table(rows):
    header = (
        f"{'fixture':<14} {'target':<10} {'strategy':<26} {'valid':<5} "
        f"{'min_font':>8} {'overflow':>8} {'new_ovl':>7}  png"
    )
    print(header)
    print("-" * len(header))
    for row in rows:
        print(
            f"{row['fixture']:<14} {row['target']:<10} {row['strategy']:<26} "
            f"{'yes' if row['valid'] else 'NO':<5} "
            f"{format_number(row['min_font'], 2):>8} "
            f"{format_number(row['max_overflow'], 3):>8} "
            f"{'-' if row['new_overlaps'] is None else row['new_overlaps']:>7}  {row['png']}"
        )


def print_summary(rows, out_dir):
    fonts = [row["min_font"] for row in rows if row["min_font"] is not None]
    overflows = [row["max_overflow"] for row in rows if row["max_overflow"] is not None]
    print()
    print("Summary")
    print(f"  cases:                {len(rows)}")
    print(f"  invalid:              {sum(not row['valid'] for row in rows)}")
    print(f"  overflow > {OVERFLOW_LIMIT}:      {sum(value > OVERFLOW_LIMIT for value in overflows)}")
    print(f"  min font < {READABLE_FONT:g}:         {sum(value < READABLE_FONT for value in fonts)}")
    print(f"  min font < {ILLEGIBLE_FONT:g}:         {sum(value < ILLEGIBLE_FONT for value in fonts)}")
    print(f"  cases with new overlaps: {sum(bool(row['new_overlaps']) for row in rows)}")
    print(f"  PNGs in:              {out_dir}")


def main(argv):
    # The renderer logs every font fallback; unknown_font.json makes that noisy.
    logging.getLogger("cr_renderer").setLevel(logging.ERROR)
    out_dir = Path(argv[0]) if argv else Path(tempfile.mkdtemp(prefix="fixture_report_"))
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for name in FIXTURE_NAMES:
        source = load_fixture(name)
        for target in targets_for(source):
            rows.append(measure(name, source, target, out_dir))
    print_table(rows)
    print_summary(rows, out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
