import sys
from unittest.mock import MagicMock

# Must happen before any import of the Remote Script or MCP Server.
# _Framework is only available inside Ableton Live — stub it out entirely.
_framework_mock = MagicMock()
# Make ControlSurface a real class so AbletonMCP can be instantiated with __new__.
class _FakeControlSurface:
    def __init__(self, c_instance=None):
        pass
    def log_message(self, msg):
        pass
    def show_message(self, msg):
        pass
    def song(self):
        return None

_framework_cs_module = MagicMock()
_framework_cs_module.ControlSurface = _FakeControlSurface
sys.modules.setdefault('_Framework', _framework_mock)
sys.modules.setdefault('_Framework.ControlSurface', _framework_cs_module)

# Stub the mcp package so @mcp.tool() is a transparent no-op decorator.
# This ensures the real function bodies remain callable in tests.
class _FakeContext:
    pass

def _identity_decorator(*args, **kwargs):
    """Returns the decorated function unchanged."""
    def decorator(fn):
        return fn
    # Support both @mcp.tool() and @mcp.tool
    if len(args) == 1 and callable(args[0]):
        return args[0]
    return decorator

_fake_fastmcp_instance = MagicMock()
_fake_fastmcp_instance.tool = _identity_decorator

class _FakeFastMCP:
    def __init__(self, *args, **kwargs):
        pass
    tool = staticmethod(_identity_decorator)

_mcp_fastmcp_module = MagicMock()
_mcp_fastmcp_module.FastMCP = _FakeFastMCP
_mcp_fastmcp_module.Context = _FakeContext

_mcp_server_module = MagicMock()
_mcp_server_module.fastmcp = _mcp_fastmcp_module

_mcp_module = MagicMock()
_mcp_module.server = _mcp_server_module

sys.modules['mcp'] = _mcp_module
sys.modules['mcp.server'] = _mcp_server_module
sys.modules['mcp.server.fastmcp'] = _mcp_fastmcp_module

# Evict any previously cached MCP_Server modules so they re-import
# with the stubbed mcp above (relevant when pytest re-uses a process).
for _key in list(sys.modules):
    if _key.startswith('MCP_Server'):
        del sys.modules[_key]

import pytest
from unittest.mock import patch


def _make_param(name, value=0.0, min_val=0.0, max_val=1.0, is_quantized=False):
    p = MagicMock()
    p.name = name
    p.value = value
    p.min = min_val
    p.max = max_val
    p.is_quantized = is_quantized
    return p


def _make_device(name, class_name, params):
    d = MagicMock()
    d.name = name
    d.class_name = class_name
    d.parameters = params
    return d


def _make_track(name, left=0.5, right=0.6, devices=None):
    t = MagicMock()
    t.name = name
    t.output_meter_left = left
    t.output_meter_right = right
    t.devices = devices or []
    return t


@pytest.fixture
def mock_song():
    params0 = [
        _make_param("Gain", 0.5, -70.0, 6.0),
        _make_param("Frequency", 1000.0, 20.0, 20000.0),
        _make_param("Q", 1.0, 0.1, 10.0),
    ]
    device0 = _make_device("EQ Eight", "PluginDevice", params0)

    track0 = _make_track("Bass", left=0.3, right=0.5, devices=[device0])
    track1 = _make_track("Lead", left=0.4, right=0.4, devices=[device0])

    return_params = [
        _make_param("Return Gain", 0.8, 0.0, 1.0),
        _make_param("Return Pan", 0.0, -1.0, 1.0),
        _make_param("Return Mute", 0.0, 0.0, 1.0),
    ]
    return_device = _make_device("Reverb", "Reverb", return_params)
    return_track = _make_track("Reverb A", left=0.2, right=0.2, devices=[return_device])

    master_params = [
        _make_param("Gain", 0.0, -70.0, 6.0),
        _make_param("Volume", 1.0, 0.0, 1.0),
    ]
    master_device = _make_device("Glue Compressor", "GlueCompressor", master_params)

    master = MagicMock()
    master.output_meter_left = 0.7
    master.output_meter_right = 0.75
    master.devices = [master_device]

    song = MagicMock()
    song.tracks = [track0, track1]
    song.return_tracks = [return_track]
    song.master_track = master
    return song


@pytest.fixture
def ableton_script(mock_song):
    with patch('AbletonMCP_Remote_Script.__init__.socket'), \
         patch('AbletonMCP_Remote_Script.__init__.threading'):
        from AbletonMCP_Remote_Script.__init__ import AbletonMCP
        script = AbletonMCP.__new__(AbletonMCP)
        script._song = mock_song
        script.running = False
        # Provide a no-op log_message so methods don't fail
        script.log_message = MagicMock()
        return script
