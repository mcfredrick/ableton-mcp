"""sample_levels.py — sample track levels during playback and write aggregates to JSON."""
from __future__ import print_function

import argparse
import json
import math
import os
import socket
import sys
import time
from datetime import datetime


def cmd(s, ctype, params={}):
    s.sendall(json.dumps({'type': ctype, 'params': params}).encode())
    time.sleep(0.05)
    s.settimeout(5.0)
    chunks = []
    while True:
        try:
            chunk = s.recv(65536)
            if not chunk:
                break
            chunks.append(chunk)
            try:
                return json.loads(b''.join(chunks).decode())
            except json.JSONDecodeError:
                continue
        except socket.timeout:
            break
    return {}


def dbfs(linear):
    if linear <= 0:
        return -96.0
    return 20.0 * math.log10(linear)


BAND_KEYS = ["sub", "low", "lo_mid", "mud", "presence", "upper", "definition", "brilliance", "air"]


def aggregate_freq(freq_samples):
    """Compute per-band avg and peak from a list of {sample_index, bands} dicts."""
    if not freq_samples:
        return None, None

    avg = {}
    peak = {}
    for key in BAND_KEYS:
        values = [s["bands"][key] for s in freq_samples if s["bands"].get(key, -96.0) > -90.0]
        avg[key] = round(sum(values) / len(values), 2) if values else -96.0
        all_values = [s["bands"][key] for s in freq_samples]
        peak[key] = round(max(all_values), 2) if all_values else -96.0

    return avg, peak


def aggregate_track(index, name, samples, freq_samples):
    peak_max = max(samples) if samples else 0.0
    nonzero = [s for s in samples if s > 0.001]
    avg_nz = sum(nonzero) / len(nonzero) if nonzero else 0.0
    peak_max_db = dbfs(peak_max)
    avg_nz_db = dbfs(avg_nz)
    peak_sample_index = samples.index(max(samples)) if samples else 0

    freq_avg, freq_peak = aggregate_freq(freq_samples)

    return {
        "index": index,
        "name": name,
        "peak_max": round(peak_max, 6),
        "peak_max_dbfs": round(peak_max_db, 2),
        "avg_nonzero": round(avg_nz, 6),
        "avg_nonzero_dbfs": round(avg_nz_db, 2),
        "dynamic_range_db": round(peak_max_db - avg_nz_db, 2),
        "active_ratio": round(len(nonzero) / len(samples), 4) if samples else 0.0,
        "peak_sample_index": peak_sample_index,
        "samples": [round(s, 6) for s in samples],
        "freq_samples": freq_samples,
        "freq_avg": freq_avg,
        "freq_peak": freq_peak,
    }


def main():
    parser = argparse.ArgumentParser(description="Sample Ableton track levels during playback")
    parser.add_argument("--duration", type=int, default=0, help="Sampling duration in seconds (0 = auto-detect from song length)")
    parser.add_argument("--interval", type=int, default=200, help="Sampling interval in ms (default: 200)")
    parser.add_argument("--freq-interval", type=float, default=2.0,
                        help="Frequency sampling interval in seconds (default: 2.0)")
    parser.add_argument("--output", type=str, default="", help="Output file path (default: sessions/levels-{timestamp}.json)")
    args = parser.parse_args()

    freq_interval_s = args.freq_interval

    if not args.output:
        os.makedirs("sessions", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        output_path = "sessions/levels-{}.json".format(timestamp)
    else:
        output_path = args.output

    print("Connecting to Ableton on localhost:9877...")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect(('localhost', 9877))
    except Exception as e:
        print("ERROR: Could not connect to Ableton: {}".format(e))
        sys.exit(1)

    info_resp = cmd(s, "get_session_info")
    info = info_resp.get("result", {})
    tempo = info.get("tempo", "unknown")
    print("Session tempo: {}".format(tempo))

    # Auto-detect song length if no duration given
    duration = args.duration
    if not duration:
        song_secs = info.get("arrangement_length_seconds", 0)
        if song_secs:
            duration = int(song_secs) + 2  # 2s tail buffer
            print("Song length: {}s (auto-detected)".format(int(song_secs)))
        else:
            duration = 120
            print("Could not detect song length, defaulting to {}s".format(duration))

    interval_s = args.interval / 1000.0
    num_samples = int(duration / interval_s)
    freq_interval_s = args.freq_interval

    print("Resetting playhead to bar 1...")
    cmd(s, "set_song_position", {"position_beats": 0.0})
    time.sleep(0.3)
    print("Starting playback...")
    cmd(s, "start_playback")
    time.sleep(0.3)

    # Collect initial level response to discover track names/count
    first_resp = cmd(s, "get_track_levels")
    first_result = first_resp.get("result", {})

    track_names = {t["index"]: t["name"] for t in first_result.get("tracks", [])}
    return_names = {t["index"]: t["name"] for t in first_result.get("return_tracks", [])}

    # Per-track sample lists keyed by index
    track_samples = {i: [] for i in track_names}
    return_samples = {i: [] for i in return_names}
    master_samples = []

    # Freq samples: keyed by (kind, index) -> list of {sample_index, bands}
    track_freq_samples = {i: [] for i in track_names}
    return_freq_samples = {i: [] for i in return_names}

    def record_level_sample(result, sample_idx):
        for t in result.get("tracks", []):
            idx = t["index"]
            if idx in track_samples:
                track_samples[idx].append(t.get("output_meter_peak", 0.0))
        for t in result.get("return_tracks", []):
            idx = t["index"]
            if idx in return_samples:
                return_samples[idx].append(t.get("output_meter_peak", 0.0))
        m = result.get("master", {})
        master_samples.append(m.get("output_meter_peak", 0.0))

    def record_freq_sample(sample_idx):
        resp = cmd(s, "get_all_analyzer_levels")
        result = resp.get("result", {})
        for t in result.get("tracks", []):
            idx = t["index"]
            if idx in track_freq_samples:
                track_freq_samples[idx].append({"sample_index": sample_idx, "bands": t["bands"]})
        for t in result.get("return_tracks", []):
            idx = t["index"]
            if idx in return_freq_samples:
                return_freq_samples[idx].append({"sample_index": sample_idx, "bands": t["bands"]})

    record_level_sample(first_result, 0)

    print("Sampling for {} seconds ({} samples at {}ms intervals, freq every {}s)...".format(
        args.duration, num_samples, args.interval, freq_interval_s))

    start_time = time.time()
    last_freq_time = start_time

    # Take initial freq sample
    record_freq_sample(0)
    last_freq_time = time.time()

    arrangement_end_beats = info.get("arrangement_length_beats", None)

    for i in range(num_samples - 1):
        time.sleep(interval_s)
        resp = cmd(s, "get_track_levels")
        result = resp.get("result", {})
        record_level_sample(result, i + 1)

        # Stop once the playhead passes the last beat of the arrangement
        if arrangement_end_beats is not None:
            song_time = result.get("current_song_time")
            if song_time is not None and song_time >= arrangement_end_beats:
                print("\nReached end of arrangement at beat {:.1f}.".format(song_time))
                break

        now = time.time()
        if now - last_freq_time >= freq_interval_s:
            record_freq_sample(i + 1)
            last_freq_time = now

        if (i + 1) % 10 == 0:
            print(".", end="", flush=True)

    print()
    print("Stopping playback...")
    cmd(s, "stop_playback")
    s.close()

    tracks_out = [
        aggregate_track(i, track_names[i], track_samples[i], track_freq_samples.get(i, []))
        for i in sorted(track_samples)
    ]
    returns_out = [
        aggregate_track(i, return_names[i], return_samples[i], return_freq_samples.get(i, []))
        for i in sorted(return_samples)
    ]
    master_out = aggregate_track(-1, "Master", master_samples, [])

    output = {
        "timestamp": datetime.now().isoformat(),
        "tempo": tempo,
        "duration_s": args.duration,
        "interval_ms": args.interval,
        "freq_interval_s": freq_interval_s,
        "sample_count": len(master_samples),
        "tracks": tracks_out,
        "return_tracks": returns_out,
        "master": master_out,
    }

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True) if os.path.dirname(output_path) else None
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print("Written to: {}".format(output_path))
    print("Tracks sampled: {}".format(len(tracks_out)))
    if tracks_out:
        hottest = max(tracks_out, key=lambda t: t["peak_max_dbfs"])
        print("Hottest track: {} ({} dBFS)".format(hottest["name"], hottest["peak_max_dbfs"]))


if __name__ == "__main__":
    main()
