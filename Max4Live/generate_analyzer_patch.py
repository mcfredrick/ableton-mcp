"""
Generate AbletonMCP_Analyzer.amxd — a 6-band RMS analyzer M4L audio effect device.

.amxd files are Max patches with a different extension. No Max/MSP required.

Run: python Max4Live/generate_analyzer_patch.py
"""

import json
import math
import os


BANDS = [
    {"short": "Sub",   "long": "Sub Level",   "fc": 40,    "q": 0.5},
    {"short": "Low",   "long": "Low Level",   "fc": 110,   "q": 1.5},
    {"short": "LoMid", "long": "LoMid Level", "fc": 316,   "q": 1.5},
    {"short": "Mid",   "long": "Mid Level",   "fc": 1000,  "q": 1.5},
    {"short": "HiMid", "long": "HiMid Level", "fc": 4000,  "q": 1.5},
    {"short": "Hi",    "long": "Hi Level",    "fc": 12000, "q": 0.7},
]

SAMPLE_RATE = 44100
COL_WIDTH = 140
COL_START_X = 50
ROW_Y = {"biquad": 80, "peakamp": 130, "atodb": 180, "numbox": 230, "label": 280}


def biquad_bandpass_coeffs(fc, q):
    """Audio EQ Cookbook bandpass (constant skirt gain), normalized by a0."""
    w0 = 2 * math.pi * fc / SAMPLE_RATE
    alpha = math.sin(w0) / (2 * q)
    b0 = math.sin(w0) / 2
    a0 = 1 + alpha
    a1 = -2 * math.cos(w0)
    a2 = 1 - alpha
    # Max biquad~ arg order: a1/a0, a2/a0, b0/a0, 0.0, -b0/a0
    return a1 / a0, a2 / a0, b0 / a0, 0.0, -(b0 / a0)


def rect(x, y, w, h):
    return [x, y, w, h]


def make_box(id_, maxclass, text, x, y, w, h, extra=None):
    box = {
        "id": id_,
        "maxclass": maxclass,
        "text": text,
        "patching_rect": rect(x, y, w, h),
        "numinlets": 0,
        "numoutlets": 0,
        "outlettype": [],
    }
    if extra:
        box.update(extra)
    return {"box": box}


def make_newobj(id_, text, x, y, w, h, numinlets, numoutlets, outlettype, extra=None):
    return make_box(
        id_, "newobj", text, x, y, w, h,
        extra=dict(numinlets=numinlets, numoutlets=numoutlets, outlettype=outlettype, **(extra or {}))
    )


def make_comment(id_, text, x, y, w, h):
    box = {
        "id": id_,
        "maxclass": "comment",
        "text": text,
        "patching_rect": rect(x, y, w, h),
        "numinlets": 1,
        "numoutlets": 0,
        "outlettype": [],
    }
    return {"box": box}


def make_live_numbox(id_, band, x, y):
    saved_attrs = {
        "valueof": {
            "parameter_enable": {"value": 1},
            "parameter_longname": {"value": band["long"]},
            "parameter_shortname": {"value": band["short"]},
            "parameter_mmin": {"value": -70.0},
            "parameter_mmax": {"value": 0.0},
            "parameter_type": {"value": 0},
            "parameter_unitstyle": {"value": 2},
            "parameter_initial": {"value": [-70.0]},
            "parameter_initial_enable": {"value": 1},
        }
    }
    box = {
        "id": id_,
        "maxclass": "live.numbox",
        "patching_rect": rect(x, y, 120, 40),
        "numinlets": 1,
        "numoutlets": 2,
        "outlettype": ["", "bang"],
        "parameter_enable": 1,
        "saved_attribute_attributes": saved_attrs,
    }
    return {"box": box}


def make_line(src_id, src_outlet, dst_id, dst_inlet):
    return {
        "patchline": {
            "source": [src_id, src_outlet],
            "destination": [dst_id, dst_inlet],
        }
    }


def generate():
    boxes = []
    lines = []

    # --- Static objects ---
    total_width = COL_START_X * 2 + len(BANDS) * COL_WIDTH
    center_x = total_width // 2

    boxes.append(make_comment(
        "obj-title",
        "AbletonMCP Analyzer — 6-band RMS level meter",
        10, 8, 500, 20,
    ))

    boxes.append(make_newobj(
        "obj-plugin", "plugin~",
        center_x - 80, 30, 80, 22,
        numinlets=0, numoutlets=2,
        outlettype=["signal", "signal"],
    ))

    boxes.append(make_newobj(
        "obj-plugout", "plugout~",
        center_x + 10, 30, 80, 22,
        numinlets=2, numoutlets=0,
        outlettype=[],
    ))

    # Pass-through: left and right channels straight to plugout~
    lines.append(make_line("obj-plugin", 0, "obj-plugout", 0))
    lines.append(make_line("obj-plugin", 1, "obj-plugout", 1))

    # --- Per-band signal chain ---
    for i, band in enumerate(BANDS):
        x = COL_START_X + i * COL_WIDTH
        coeffs = biquad_bandpass_coeffs(band["fc"], band["q"])
        coeff_str = " ".join(f"{c:.8f}" for c in coeffs)
        bq_text = f"biquad~ {coeff_str}"

        bq_id  = f"obj-bq-{i}"
        pa_id  = f"obj-pa-{i}"
        db_id  = f"obj-db-{i}"
        nb_id  = f"obj-nb-{i}"
        lbl_id = f"obj-lbl-{i}"

        boxes.append(make_newobj(
            bq_id, bq_text,
            x, ROW_Y["biquad"], 130, 22,
            numinlets=2, numoutlets=1, outlettype=["signal"],
        ))
        boxes.append(make_newobj(
            pa_id, "peakamp~ 1024",
            x, ROW_Y["peakamp"], 100, 22,
            numinlets=1, numoutlets=1, outlettype=[""],
        ))
        boxes.append(make_newobj(
            db_id, "atodb",
            x, ROW_Y["atodb"], 60, 22,
            numinlets=1, numoutlets=1, outlettype=[""],
        ))
        boxes.append(make_live_numbox(nb_id, band, x, ROW_Y["numbox"]))
        boxes.append(make_comment(
            lbl_id,
            f"{band['short']} ({band['fc']} Hz)",
            x, ROW_Y["label"], 130, 20,
        ))

        # Signal chain wiring
        lines.append(make_line("obj-plugin", 0, bq_id, 0))
        lines.append(make_line(bq_id, 0, pa_id, 0))
        lines.append(make_line(pa_id, 0, db_id, 0))
        lines.append(make_line(db_id, 0, nb_id, 0))

    patch = {
        "fileversion": 1,
        "appversion": {
            "major": 8,
            "minor": 6,
            "revision": 0,
            "architecture": "x64",
            "modernui": 1,
        },
        "classnamespace": "dsp.devicepreprocessor",
        "rect": [100, 100, COL_START_X * 2 + len(BANDS) * COL_WIDTH + 20, 340],
        "bglocked": 0,
        "openinpresentation": 0,
        "default_fontsize": 12.0,
        "default_fontface": 0,
        "default_fontname": "Arial",
        "gridonopen": 1,
        "gridsize": [15.0, 15.0],
        "gridsnaponopen": 1,
        "objectsnaponopen": 1,
        "statusbarvisible": 2,
        "toolbarvisible": 1,
        "boxes": boxes,
        "lines": lines,
        "dependency_cache": [],
        "autosave": 0,
    }

    return patch


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(script_dir, "AbletonMCP_Analyzer.amxd")

    patch = generate()

    with open(out_path, "w") as f:
        json.dump({"patcher": patch}, f, indent=2)

    box_count = len(patch["boxes"])
    line_count = len(patch["lines"])

    print(f"Written: {out_path}")
    print(f"Bands  : {len(BANDS)}")
    print(f"Boxes  : {box_count}")
    print(f"Lines  : {line_count}")
    print()
    print("Next steps:")
    print("  1. Open Ableton Live (no Max/MSP needed)")
    print("  2. Drag Max4Live/AbletonMCP_Analyzer.amxd onto a track as an audio effect")
    print("  3. Use get_device_parameters MCP command to read band levels")
    print("  4. Parameters: Sub Level, Low Level, LoMid Level, Mid Level, HiMid Level, Hi Level")


if __name__ == "__main__":
    main()
