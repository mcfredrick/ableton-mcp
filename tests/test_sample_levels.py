"""Tests for sample_levels.py freq aggregation logic."""
import sys
import os

# Ensure the repo root is on sys.path so sample_levels can be imported.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sample_levels import aggregate_freq, aggregate_track, BAND_KEYS


def _make_freq_sample(sample_index, **band_overrides):
    bands = {k: -30.0 for k in BAND_KEYS}
    bands.update(band_overrides)
    return {"sample_index": sample_index, "bands": bands}


def test_aggregate_freq_returns_none_for_empty():
    avg, peak = aggregate_freq([])
    assert avg is None
    assert peak is None


def test_aggregate_freq_computes_avg_and_peak():
    samples = [
        _make_freq_sample(0, sub=-40.0, low=-20.0),
        _make_freq_sample(5, sub=-30.0, low=-10.0),
    ]
    avg, peak = aggregate_freq(samples)
    assert avg["sub"] == -35.0
    assert avg["low"] == -15.0
    assert peak["sub"] == -30.0
    assert peak["low"] == -10.0


def test_aggregate_freq_avg_excludes_silence():
    # Values at or below -90 dB are treated as silence and excluded from avg.
    samples = [
        _make_freq_sample(0, sub=-91.0),
        _make_freq_sample(1, sub=-30.0),
    ]
    avg, peak = aggregate_freq(samples)
    # Only the -30.0 sample contributes to avg
    assert avg["sub"] == -30.0


def test_aggregate_freq_avg_all_silent_returns_minus96():
    samples = [_make_freq_sample(0, sub=-95.0), _make_freq_sample(1, sub=-92.0)]
    avg, peak = aggregate_freq(samples)
    assert avg["sub"] == -96.0


def test_aggregate_freq_peak_includes_all_values():
    # Peak should reflect the least-negative value regardless of -90 threshold.
    samples = [
        _make_freq_sample(0, air=-91.0),
        _make_freq_sample(1, air=-50.0),
    ]
    avg, peak = aggregate_freq(samples)
    assert peak["air"] == -50.0


def test_aggregate_track_no_freq_samples():
    result = aggregate_track(0, "Bass", [0.5, 0.3], [])
    assert result["freq_samples"] == []
    assert result["freq_avg"] is None
    assert result["freq_peak"] is None


def test_aggregate_track_includes_freq_data():
    freq_samples = [_make_freq_sample(0, sub=-40.0), _make_freq_sample(1, sub=-20.0)]
    result = aggregate_track(0, "Bass", [0.5, 0.3], freq_samples)
    assert result["freq_samples"] == freq_samples
    assert result["freq_avg"]["sub"] == -30.0
    assert result["freq_peak"]["sub"] == -20.0


def test_aggregate_track_freq_samples_preserved_verbatim():
    freq_samples = [_make_freq_sample(3, mud=-25.5)]
    result = aggregate_track(1, "Lead", [0.1], freq_samples)
    assert result["freq_samples"][0]["sample_index"] == 3
    assert result["freq_samples"][0]["bands"]["mud"] == -25.5
