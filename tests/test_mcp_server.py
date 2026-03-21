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
