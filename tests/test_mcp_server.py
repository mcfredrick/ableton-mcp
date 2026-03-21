import json
import pytest
from unittest.mock import MagicMock, patch


def _make_mock_ableton(return_value=None):
    mock_conn = MagicMock()
    mock_conn.send_command.return_value = return_value or {"status": "ok"}
    return mock_conn


def test_get_track_levels_sends_correct_command():
    mock_conn = _make_mock_ableton({"tracks": [], "return_tracks": [], "master": {}})
    with patch('MCP_Server.server.get_ableton_connection', return_value=mock_conn):
        from MCP_Server.server import get_track_levels
        get_track_levels(MagicMock())
        mock_conn.send_command.assert_called_once_with("get_track_levels")


def test_get_track_levels_returns_json():
    payload = {"tracks": [{"index": 0, "output_meter_peak": 0.5}], "return_tracks": [], "master": {}}
    mock_conn = _make_mock_ableton(payload)
    with patch('MCP_Server.server.get_ableton_connection', return_value=mock_conn):
        from MCP_Server.server import get_track_levels
        result = get_track_levels(MagicMock())
        parsed = json.loads(result)
        assert "tracks" in parsed
        assert parsed["tracks"][0]["output_meter_peak"] == 0.5


def test_get_device_parameters_sends_correct_params():
    mock_conn = _make_mock_ableton({"device_name": "EQ Eight", "class_name": "PluginDevice", "parameters": []})
    with patch('MCP_Server.server.get_ableton_connection', return_value=mock_conn):
        from MCP_Server.server import get_device_parameters
        get_device_parameters(MagicMock(), track_index=2, device_index=1)
        mock_conn.send_command.assert_called_once_with(
            "get_device_parameters",
            {"track_index": 2, "device_index": 1},
        )


def test_set_device_parameter_sends_all_params():
    mock_conn = _make_mock_ableton({"value": 42.0})
    with patch('MCP_Server.server.get_ableton_connection', return_value=mock_conn):
        from MCP_Server.server import set_device_parameter
        set_device_parameter(MagicMock(), track_index=1, device_index=0, parameter_index=2, value=42.0)
        mock_conn.send_command.assert_called_once_with(
            "set_device_parameter",
            {"track_index": 1, "device_index": 0, "parameter_index": 2, "value": 42.0},
        )


def test_get_track_levels_returns_error_string_on_failure():
    mock_conn = MagicMock()
    mock_conn.send_command.side_effect = Exception("connection refused")
    with patch('MCP_Server.server.get_ableton_connection', return_value=mock_conn):
        from MCP_Server.server import get_track_levels
        result = get_track_levels(MagicMock())
        assert isinstance(result, str)
        assert result.startswith("Error")


def test_set_device_parameter_returns_error_string_on_failure():
    mock_conn = MagicMock()
    mock_conn.send_command.side_effect = Exception("timeout")
    with patch('MCP_Server.server.get_ableton_connection', return_value=mock_conn):
        from MCP_Server.server import set_device_parameter
        result = set_device_parameter(MagicMock(), track_index=0, device_index=0, parameter_index=0, value=1.0)
        assert isinstance(result, str)
        assert result.startswith("Error")


def test_load_analyzer_device_sends_correct_command():
    payload = {"loaded": True, "device_name": "AbletonMCP Analyzer", "track_name": "Track 1", "uri": "query:test"}
    mock_conn = _make_mock_ableton(payload)
    with patch('MCP_Server.server.get_ableton_connection', return_value=mock_conn):
        from MCP_Server.server import load_analyzer_device
        result = load_analyzer_device(MagicMock(), track_index=3)
        mock_conn.send_command.assert_called_once_with("load_analyzer_device", {"track_index": 3})
        parsed = json.loads(result)
        assert parsed["loaded"] is True


def test_load_analyzer_device_returns_error_string_on_failure():
    mock_conn = MagicMock()
    mock_conn.send_command.side_effect = Exception("AbletonMCP Analyzer not found in browser")
    with patch('MCP_Server.server.get_ableton_connection', return_value=mock_conn):
        from MCP_Server.server import load_analyzer_device
        result = load_analyzer_device(MagicMock(), track_index=0)
        assert isinstance(result, str)
        assert result.startswith("Error")


def test_load_device_and_get_parameters_sends_correct_commands():
    mock_conn = MagicMock()
    mock_conn.send_command.side_effect = [
        {"loaded": True},
        {"devices": [{"index": 0, "name": "Pro-Q 3"}]},
        {"device_name": "Pro-Q 3", "parameters": []},
    ]
    with patch('MCP_Server.server.get_ableton_connection', return_value=mock_conn):
        from MCP_Server.server import load_device_and_get_parameters
        result = load_device_and_get_parameters(MagicMock(), track_index=1, item_uri="query:AudioFx#Pro-Q%203")
        parsed = json.loads(result)
        assert "device_name" in parsed
        assert parsed["device_name"] == "Pro-Q 3"


def test_get_track_volumes_sends_correct_command():
    mock_conn = _make_mock_ableton({"tracks": [], "return_tracks": [], "master": {}})
    with patch('MCP_Server.server.get_ableton_connection', return_value=mock_conn):
        from MCP_Server.server import get_track_volumes
        get_track_volumes(MagicMock())
        mock_conn.send_command.assert_called_once_with("get_track_volumes")


def test_set_track_volume_sends_correct_params():
    mock_conn = _make_mock_ableton({"track_index": 2, "volume": 0.8})
    with patch('MCP_Server.server.get_ableton_connection', return_value=mock_conn):
        from MCP_Server.server import set_track_volume
        set_track_volume(MagicMock(), track_index=2, volume=0.8)
        mock_conn.send_command.assert_called_once_with(
            "set_track_volume",
            {"track_index": 2, "volume": 0.8},
        )


def test_toggle_device_sends_correct_params():
    mock_conn = _make_mock_ableton({"track_index": 1, "device_index": 0, "enabled": False})
    with patch('MCP_Server.server.get_ableton_connection', return_value=mock_conn):
        from MCP_Server.server import toggle_device
        toggle_device(MagicMock(), track_index=1, device_index=0, enabled=False)
        mock_conn.send_command.assert_called_once_with(
            "toggle_device",
            {"track_index": 1, "device_index": 0, "enabled": False},
        )


def test_capture_session_snapshot_creates_file():
    import io
    mock_conn = MagicMock()
    mock_conn.send_command.side_effect = [
        {"track_count": 1, "tempo": 120.0},   # get_session_info
        {"tracks": [], "return_tracks": [], "master": {}},  # get_track_levels
        {"tracks": [], "return_tracks": [], "master": {}},  # get_track_volumes
        {"name": "Bass", "devices": []},       # get_track_info for track 0
    ]
    mock_open = MagicMock(return_value=io.StringIO())
    with patch('MCP_Server.server.get_ableton_connection', return_value=mock_conn), \
         patch('os.makedirs'), \
         patch('builtins.open', mock_open):
        from MCP_Server.server import capture_session_snapshot
        result = capture_session_snapshot(MagicMock(), label="pre-mix")
        assert "Snapshot saved" in result
