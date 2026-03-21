#!/usr/bin/env python3
"""
AbletonMCP setup script — installs the Remote Script, M4L analyzer, and MCP server config.

Run once on a new machine:
    python install.py
"""
import glob
import json
import os
import platform
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).parent.resolve()
REMOTE_SCRIPT_SRC = REPO_ROOT / "AbletonMCP_Remote_Script"
ANALYZER_SRC = REPO_ROOT / "Max4Live" / "AbletonMCP_Analyzer.amxd"
MCP_CONFIG = Path.home() / ".claude" / "mcp.json"

IS_WINDOWS = platform.system() == "Windows"


def find_remote_scripts_dir():
    if IS_WINDOWS:
        candidates = [Path.home() / "Documents" / "Ableton" / "User Library" / "Remote Scripts"]
    else:
        candidates = [Path.home() / "Music" / "Ableton" / "User Library" / "Remote Scripts"]
        # Fallback: glob for versioned prefs dirs, pick the highest version
        versioned = sorted(
            glob.glob(str(Path.home() / "Library" / "Preferences" / "Ableton" / "Live *" / "User Remote Scripts"))
        )
        candidates.extend(Path(p) for p in reversed(versioned))

    for path in candidates:
        if path.exists():
            return path
    return candidates[0]  # Return the primary candidate even if it doesn't exist


def find_m4l_presets_dir():
    if IS_WINDOWS:
        return (
            Path.home()
            / "Documents"
            / "Ableton"
            / "User Library"
            / "Presets"
            / "Audio Effects"
            / "Max Audio Effect"
        )
    return (
        Path.home()
        / "Music"
        / "Ableton"
        / "User Library"
        / "Presets"
        / "Audio Effects"
        / "Max Audio Effect"
    )


def step1_install_remote_script():
    print("\n[Step 1] Installing Remote Script...")
    scripts_dir = find_remote_scripts_dir()
    dst = scripts_dir / "AbletonMCP"

    if not scripts_dir.exists():
        print(f"  WARNING: Remote Scripts directory not found at {scripts_dir}")
        print("  Create it manually, then re-run this script or copy the folder yourself:")
        print(f"    {REMOTE_SCRIPT_SRC}  →  {dst}")
        return

    try:
        shutil.copytree(str(REMOTE_SCRIPT_SRC), str(dst), dirs_exist_ok=True)
        print(f"  Copied: {REMOTE_SCRIPT_SRC}")
        print(f"      to: {dst}")
    except Exception as e:
        print(f"  ERROR copying Remote Script: {e}")


def step2_install_analyzer():
    print("\n[Step 2] Installing M4L Analyzer...")
    if not ANALYZER_SRC.exists():
        print(f"  WARNING: Analyzer not found at {ANALYZER_SRC} — skipping.")
        return

    dst_dir = find_m4l_presets_dir()
    try:
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst = dst_dir / ANALYZER_SRC.name
        shutil.copy2(str(ANALYZER_SRC), str(dst))
        print(f"  Copied: {ANALYZER_SRC}")
        print(f"      to: {dst}")
    except Exception as e:
        print(f"  ERROR copying M4L Analyzer: {e}")


def step3_configure_mcp():
    print("\n[Step 3] Configuring MCP server...")
    config = {"mcpServers": {}}

    if MCP_CONFIG.exists():
        try:
            with open(MCP_CONFIG) as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            print(f"  WARNING: {MCP_CONFIG} contains invalid JSON: {e}")
            snippet = json.dumps(
                {
                    "AbletonMCP": {
                        "command": "uv",
                        "args": ["--directory", str(REPO_ROOT), "run", "ableton-mcp"],
                    }
                },
                indent=2,
            )
            print("  Add this to the 'mcpServers' object in mcp.json manually:")
            print(snippet)
            return

    servers = config.setdefault("mcpServers", {})

    if "AbletonMCP" in servers:
        print("  MCP server already configured — skipping.")
        return

    servers["AbletonMCP"] = {
        "command": "uv",
        "args": ["--directory", str(REPO_ROOT), "run", "ableton-mcp"],
    }

    MCP_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(MCP_CONFIG, "w") as f:
            json.dump(config, f, indent=2)
            f.write("\n")
        print(f"  Added AbletonMCP server to {MCP_CONFIG}")
        print(f"  Repo path: {REPO_ROOT}")
    except Exception as e:
        print(f"  ERROR writing mcp.json: {e}")


def step4_next_steps():
    print(
        """
Setup complete. Next steps:
  1. Restart Ableton Live (or reload the AbletonMCP control surface in Settings)
  2. In Ableton: Settings → Link, Tempo & MIDI → Control Surface → AbletonMCP
  3. Restart Claude Code to pick up the new MCP server
  4. Load the analyzer: tell Claude "load the AbletonMCP Analyzer on track 0"
"""
    )


if __name__ == "__main__":
    print(f"AbletonMCP Installer — repo: {REPO_ROOT}")
    step1_install_remote_script()
    step2_install_analyzer()
    step3_configure_mcp()
    step4_next_steps()
