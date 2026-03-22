import pytest
from unittest.mock import MagicMock


def test_get_track_levels_returns_required_keys(ableton_script):
    result = ableton_script._get_track_levels()
    assert "tracks" in result
    assert "return_tracks" in result
    assert "master" in result


def test_get_track_levels_peak_is_max_of_left_right(ableton_script, mock_song):
    mock_song.tracks[0].output_meter_left = 0.3
    mock_song.tracks[0].output_meter_right = 0.5
    result = ableton_script._get_track_levels()
    assert result["tracks"][0]["output_meter_peak"] == 0.5


def test_get_track_levels_includes_all_tracks(ableton_script, mock_song):
    result = ableton_script._get_track_levels()
    assert len(result["tracks"]) == len(mock_song.tracks)


def test_get_device_parameters_returns_device_info(ableton_script, mock_song):
    result = ableton_script._get_device_parameters(0, 0)
    assert result["device_name"] == mock_song.tracks[0].devices[0].name
    assert result["class_name"] == mock_song.tracks[0].devices[0].class_name
    assert "parameters" in result


def test_get_device_parameters_returns_all_params(ableton_script, mock_song):
    result = ableton_script._get_device_parameters(0, 0)
    assert len(result["parameters"]) == len(mock_song.tracks[0].devices[0].parameters)


def test_get_device_parameters_invalid_track_raises(ableton_script):
    with pytest.raises(IndexError):
        ableton_script._get_device_parameters(999, 0)


def test_get_device_parameters_invalid_device_raises(ableton_script):
    with pytest.raises(IndexError):
        ableton_script._get_device_parameters(0, 999)


def test_set_device_parameter_sets_value(ableton_script, mock_song):
    param = mock_song.tracks[0].devices[0].parameters[0]
    ableton_script._set_device_parameter(0, 0, 0, 42.0)
    assert param.value == 42.0


def test_set_device_parameter_returns_updated_value(ableton_script, mock_song):
    mock_song.tracks[0].devices[0].parameters[1].value = 0.0
    result = ableton_script._set_device_parameter(0, 0, 1, 99.0)
    assert result["value"] == 99.0
    assert result["parameter_index"] == 1


def test_set_device_parameter_invalid_index_raises(ableton_script):
    with pytest.raises(IndexError):
        ableton_script._set_device_parameter(0, 0, 999, 1.0)


def test_get_device_parameters_master_track(ableton_script, mock_song):
    result = ableton_script._get_device_parameters(-1, 0)
    assert result["device_name"] == mock_song.master_track.devices[0].name
    assert result["class_name"] == mock_song.master_track.devices[0].class_name
    assert "parameters" in result


def test_set_device_parameter_master_track(ableton_script, mock_song):
    param = mock_song.master_track.devices[0].parameters[0]
    ableton_script._set_device_parameter(-1, 0, 0, 55.0)
    assert param.value == 55.0


def test_load_analyzer_device_raises_when_not_in_browser(ableton_script):
    with pytest.raises(RuntimeError, match="AbletonMCP Analyzer not found"):
        ableton_script.get_browser_items_at_path = lambda path: {"items": []}
        ableton_script._load_analyzer_device(0)


def test_load_analyzer_device_loads_correct_uri(ableton_script):
    from unittest.mock import patch
    items = [
        {"name": "AbletonMCP Analyzer", "uri": "query:AbletonMCP#Analyzer:FileId_999"},
    ]
    load_result = {"loaded": True, "item_name": "AbletonMCP Analyzer", "track_name": "1-MIDI", "uri": items[0]["uri"]}
    ableton_script.get_browser_items_at_path = lambda path: {"items": items}
    with patch.object(ableton_script, "_load_browser_item", return_value=load_result) as mock_load:
        result = ableton_script._load_analyzer_device(0)
        mock_load.assert_called_once_with(0, items[0]["uri"])
        assert result["device_name"] == "AbletonMCP Analyzer"


def test_get_track_volumes_returns_required_keys(ableton_script):
    result = ableton_script._get_track_volumes()
    assert "tracks" in result
    assert "return_tracks" in result
    assert "master" in result


def test_get_track_volumes_track_has_mixer_fields(ableton_script, mock_song):
    result = ableton_script._get_track_volumes()
    track = result["tracks"][0]
    assert "volume" in track
    assert "pan" in track
    assert "mute" in track
    assert "solo" in track
    assert "arm" in track


def test_set_track_volume_sets_value(ableton_script, mock_song):
    ableton_script._set_track_volume(0, 0.75)
    assert mock_song.tracks[0].mixer_device.volume.value == 0.75


def test_set_track_mute_sets_mute(ableton_script, mock_song):
    ableton_script._set_track_mute(0, True)
    assert mock_song.tracks[0].mute is True


def test_set_track_arm_raises_when_cannot_be_armed(ableton_script, mock_song):
    mock_song.tracks[0].can_be_armed = False
    with pytest.raises(RuntimeError, match="cannot be armed"):
        ableton_script._set_track_arm(0, True)


def test_get_rack_devices_returns_chains(ableton_script, mock_song):
    from tests.conftest import _make_param, _make_rack_device
    params = [_make_param("Gain", 0.5, -70.0, 6.0)]
    rack = _make_rack_device("My Rack", "Chain A", "Pro-Q 3", params)
    mock_song.tracks[0].devices = [rack]
    result = ableton_script._get_rack_devices(0, 0)
    assert result["rack_name"] == "My Rack"
    assert len(result["chains"]) == 1
    assert result["chains"][0]["name"] == "Chain A"
    assert result["chains"][0]["devices"][0]["name"] == "Pro-Q 3"
    assert len(result["chains"][0]["devices"][0]["parameters"]) == 1


def test_get_rack_devices_raises_when_not_rack(ableton_script, mock_song):
    mock_song.tracks[0].devices[0].can_have_chains = False
    with pytest.raises(ValueError, match="does not support chains"):
        ableton_script._get_rack_devices(0, 0)


def test_set_rack_device_parameter_sets_value(ableton_script, mock_song):
    from tests.conftest import _make_param, _make_rack_device
    params = [_make_param("Gain", 0.0, -70.0, 6.0)]
    rack = _make_rack_device("My Rack", "Chain A", "Pro-Q 3", params)
    mock_song.tracks[0].devices = [rack]
    ableton_script._set_rack_device_parameter(0, 0, 0, 0, 0, 3.5)
    assert rack.chains[0].devices[0].parameters[0].value == 3.5


def test_set_rack_device_parameter_invalid_chain_raises(ableton_script, mock_song):
    from tests.conftest import _make_param, _make_rack_device
    rack = _make_rack_device("My Rack", "Chain A", "Pro-Q 3", [_make_param("X")])
    mock_song.tracks[0].devices = [rack]
    with pytest.raises(IndexError):
        ableton_script._set_rack_device_parameter(0, 0, 99, 0, 0, 1.0)


def test_get_clip_notes_returns_notes(ableton_script, mock_song):
    slot = MagicMock()
    slot.has_clip = True
    clip = MagicMock()
    clip.is_midi_clip = True
    clip.name = "Pattern"
    clip.length = 4.0
    clip.get_notes.return_value = [
        (60, 0.0, 0.5, 100, False),
        (64, 0.5, 0.5, 90, False),
    ]
    slot.clip = clip
    mock_song.tracks[0].clip_slots = [slot]
    result = ableton_script._get_clip_notes(0, 0)
    assert "notes" in result
    assert len(result["notes"]) == 2
    assert result["notes"][0]["pitch"] == 60
    assert result["length"] == 4.0


# --- get_all_analyzer_levels ---

ANALYZER_BAND_NAMES = [
    "Sub Level", "Low Level", "LoMid Level", "Mud Level",
    "Presence Level", "Upper Level", "Definition Level",
    "Brilliance Level", "Air Level",
]


def _make_analyzer_device(band_values):
    """Build a mock AbletonMCP Analyzer device with the 9 band parameters."""
    from tests.conftest import _make_param, _make_device
    params = [_make_param(name, value) for name, value in zip(ANALYZER_BAND_NAMES, band_values)]
    return _make_device("AbletonMCP Analyzer", "MaxDevice", params)


def test_get_all_analyzer_levels_returns_required_keys(ableton_script, mock_song):
    analyzer = _make_analyzer_device([-45.0] * 9)
    mock_song.tracks[0].devices = [analyzer]
    mock_song.tracks[1].devices = []
    result = ableton_script._get_all_analyzer_levels()
    assert "tracks" in result
    assert "return_tracks" in result


def test_get_all_analyzer_levels_only_includes_tracks_with_analyzer(ableton_script, mock_song):
    analyzer = _make_analyzer_device([-45.0] * 9)
    mock_song.tracks[0].devices = [analyzer]
    mock_song.tracks[1].devices = []  # no analyzer
    result = ableton_script._get_all_analyzer_levels()
    assert len(result["tracks"]) == 1
    assert result["tracks"][0]["index"] == 0
    assert result["tracks"][0]["name"] == mock_song.tracks[0].name


def test_get_all_analyzer_levels_band_values(ableton_script, mock_song):
    band_values = [-45.0, -22.0, -18.0, -30.0, -25.0, -20.0, -15.0, -12.0, -28.0]
    analyzer = _make_analyzer_device(band_values)
    mock_song.tracks[0].devices = [analyzer]
    mock_song.tracks[1].devices = []
    result = ableton_script._get_all_analyzer_levels()
    bands = result["tracks"][0]["bands"]
    assert bands["sub"] == -45.0
    assert bands["low"] == -22.0
    assert bands["lo_mid"] == -18.0
    assert bands["mud"] == -30.0
    assert bands["presence"] == -25.0
    assert bands["upper"] == -20.0
    assert bands["definition"] == -15.0
    assert bands["brilliance"] == -12.0
    assert bands["air"] == -28.0


def test_get_all_analyzer_levels_missing_band_defaults_to_minus96(ableton_script, mock_song):
    from tests.conftest import _make_param, _make_device
    # Only provide 3 of 9 bands
    params = [
        _make_param("Sub Level", -40.0),
        _make_param("Low Level", -20.0),
        _make_param("Mud Level", -15.0),
    ]
    analyzer = _make_device("AbletonMCP Analyzer", "MaxDevice", params)
    mock_song.tracks[0].devices = [analyzer]
    mock_song.tracks[1].devices = []
    result = ableton_script._get_all_analyzer_levels()
    bands = result["tracks"][0]["bands"]
    assert bands["lo_mid"] == -96.0
    assert bands["presence"] == -96.0
    assert bands["air"] == -96.0
    assert bands["sub"] == -40.0
    assert bands["mud"] == -15.0


def test_get_all_analyzer_levels_detects_by_class_name(ableton_script, mock_song):
    from tests.conftest import _make_param, _make_device
    params = [_make_param(name, -30.0) for name in ANALYZER_BAND_NAMES]
    # Name does NOT contain AbletonMCP, but class_name contains MaxDevice
    analyzer = _make_device("Some M4L Device", "MaxDevice", params)
    mock_song.tracks[0].devices = [analyzer]
    mock_song.tracks[1].devices = []
    result = ableton_script._get_all_analyzer_levels()
    assert len(result["tracks"]) == 1


def test_get_all_analyzer_levels_reports_correct_device_index(ableton_script, mock_song):
    from tests.conftest import _make_param, _make_device
    eq = _make_device("EQ Eight", "PluginDevice", [_make_param("Gain")])
    analyzer = _make_analyzer_device([-50.0] * 9)
    mock_song.tracks[0].devices = [eq, analyzer]
    mock_song.tracks[1].devices = []
    result = ableton_script._get_all_analyzer_levels()
    assert result["tracks"][0]["analyzer_device_index"] == 1
