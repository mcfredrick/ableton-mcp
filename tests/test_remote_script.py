import pytest


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


def test_get_clip_notes_returns_notes(ableton_script, mock_song):
    from unittest.mock import MagicMock
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
