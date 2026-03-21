import pytest
from Max4Live.generate_analyzer_patch import biquad_bandpass_coeffs, generate, BANDS


def test_bandpass_coeffs_returns_five_values():
    coeffs = biquad_bandpass_coeffs(1000, 1.5)
    assert len(coeffs) == 5


def test_bandpass_coeffs_normalized():
    # Bandpass filter: b0 + b1 + b2 == 0 (no DC component)
    # Return order: (a1/a0, a2/a0, b0/a0, 0.0, -b0/a0)
    coeffs = biquad_bandpass_coeffs(1000, 1.5)
    b_sum = coeffs[2] + coeffs[3] + coeffs[4]  # b0/a0 + 0.0 + (-b0/a0)
    assert abs(b_sum) < 1e-10


def test_all_bands_have_distinct_coefficients():
    all_coeffs = [biquad_bandpass_coeffs(b["fc"], b["q"]) for b in BANDS]
    assert len(set(all_coeffs)) == len(BANDS)


def test_generate_returns_patcher_structure():
    patch = generate()
    assert "boxes" in patch
    assert "lines" in patch


def test_generate_correct_box_count():
    # 3 static (plugin~, plugout~, title comment) + 6 bands × 5 objects = 33
    patch = generate()
    assert len(patch["boxes"]) == 33


def test_generate_correct_line_count():
    # 2 pass-through (plugin→plugout L+R) + 6 bands × 4 connections = 26
    patch = generate()
    assert len(patch["lines"]) == 26


def test_all_parameters_have_correct_range():
    patch = generate()
    numboxes = [
        b["box"] for b in patch["boxes"]
        if b.get("box", {}).get("maxclass") == "live.numbox"
    ]
    assert len(numboxes) == 6
    for nb in numboxes:
        saved = nb["saved_attribute_attributes"]["valueof"]
        assert saved["parameter_mmin"]["value"] == -70.0
        assert saved["parameter_mmax"]["value"] == 0.0
        assert saved["parameter_enable"]["value"] == 1


def test_band_names_match_canonical_list():
    patch = generate()
    numboxes = [
        b["box"] for b in patch["boxes"]
        if b.get("box", {}).get("maxclass") == "live.numbox"
    ]
    long_names = [nb["saved_attribute_attributes"]["valueof"]["parameter_longname"]["value"] for nb in numboxes]
    expected = ["Sub Level", "Low Level", "LoMid Level", "Mid Level", "HiMid Level", "Hi Level"]
    assert long_names == expected
