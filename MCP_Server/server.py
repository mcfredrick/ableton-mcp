# ableton_mcp_server.py
from mcp.server.fastmcp import FastMCP, Context
import socket
import json
import logging
from dataclasses import dataclass
from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict, Any, List, Union

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AbletonMCPServer")

@dataclass
class AbletonConnection:
    host: str
    port: int
    sock: socket.socket = None
    
    def connect(self) -> bool:
        """Connect to the Ableton Remote Script socket server"""
        if self.sock:
            return True
            
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            logger.info(f"Connected to Ableton at {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Ableton: {str(e)}")
            self.sock = None
            return False
    
    def disconnect(self):
        """Disconnect from the Ableton Remote Script"""
        if self.sock:
            try:
                self.sock.close()
            except Exception as e:
                logger.error(f"Error disconnecting from Ableton: {str(e)}")
            finally:
                self.sock = None

    def receive_full_response(self, sock, buffer_size=8192):
        """Receive the complete response, potentially in multiple chunks"""
        chunks = []
        sock.settimeout(15.0)  # Increased timeout for operations that might take longer
        
        try:
            while True:
                try:
                    chunk = sock.recv(buffer_size)
                    if not chunk:
                        if not chunks:
                            raise Exception("Connection closed before receiving any data")
                        break
                    
                    chunks.append(chunk)
                    
                    # Check if we've received a complete JSON object
                    try:
                        data = b''.join(chunks)
                        json.loads(data.decode('utf-8'))
                        logger.info(f"Received complete response ({len(data)} bytes)")
                        return data
                    except json.JSONDecodeError:
                        # Incomplete JSON, continue receiving
                        continue
                except socket.timeout:
                    logger.warning("Socket timeout during chunked receive")
                    break
                except (ConnectionError, BrokenPipeError, ConnectionResetError) as e:
                    logger.error(f"Socket connection error during receive: {str(e)}")
                    raise
        except Exception as e:
            logger.error(f"Error during receive: {str(e)}")
            raise
            
        # If we get here, we either timed out or broke out of the loop
        if chunks:
            data = b''.join(chunks)
            logger.info(f"Returning data after receive completion ({len(data)} bytes)")
            try:
                json.loads(data.decode('utf-8'))
                return data
            except json.JSONDecodeError:
                raise Exception("Incomplete JSON response received")
        else:
            raise Exception("No data received")

    def send_command(self, command_type: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send a command to Ableton and return the response"""
        if not self.sock and not self.connect():
            raise ConnectionError("Not connected to Ableton")
        
        command = {
            "type": command_type,
            "params": params or {}
        }
        
        # Check if this is a state-modifying command
        is_modifying_command = command_type in [
            "create_midi_track", "set_track_name",
            "create_clip", "add_notes_to_clip", "set_clip_name",
            "set_tempo", "fire_clip", "stop_clip", "set_device_parameter",
            "start_playback", "stop_playback", "load_instrument_or_effect",
            "load_analyzer_device", "load_browser_item",
            "set_track_volume", "set_track_pan", "set_track_mute",
            "set_track_solo", "set_track_arm", "toggle_device",
            "create_scene", "fire_scene", "set_scene_name",
            "set_rack_device_parameter",
        ]
        
        try:
            logger.info(f"Sending command: {command_type} with params: {params}")
            
            # Send the command
            self.sock.sendall(json.dumps(command).encode('utf-8'))
            logger.info(f"Command sent, waiting for response...")
            
            # For state-modifying commands, add a small delay to give Ableton time to process
            if is_modifying_command:
                import time
                time.sleep(0.1)  # 100ms delay
            
            # Set timeout based on command type
            timeout = 15.0 if is_modifying_command else 10.0
            self.sock.settimeout(timeout)
            
            # Receive the response
            response_data = self.receive_full_response(self.sock)
            logger.info(f"Received {len(response_data)} bytes of data")
            
            # Parse the response
            response = json.loads(response_data.decode('utf-8'))
            logger.info(f"Response parsed, status: {response.get('status', 'unknown')}")
            
            if response.get("status") == "error":
                logger.error(f"Ableton error: {response.get('message')}")
                raise Exception(response.get("message", "Unknown error from Ableton"))
            
            # For state-modifying commands, add another small delay after receiving response
            if is_modifying_command:
                import time
                time.sleep(0.1)  # 100ms delay
            
            return response.get("result", {})
        except socket.timeout:
            logger.error("Socket timeout while waiting for response from Ableton")
            self.sock = None
            raise Exception("Timeout waiting for Ableton response")
        except (ConnectionError, BrokenPipeError, ConnectionResetError) as e:
            logger.error(f"Socket connection error: {str(e)}")
            self.sock = None
            raise Exception(f"Connection to Ableton lost: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response from Ableton: {str(e)}")
            if 'response_data' in locals() and response_data:
                logger.error(f"Raw response (first 200 bytes): {response_data[:200]}")
            self.sock = None
            raise Exception(f"Invalid response from Ableton: {str(e)}")
        except Exception as e:
            logger.error(f"Error communicating with Ableton: {str(e)}")
            self.sock = None
            raise Exception(f"Communication error with Ableton: {str(e)}")

@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    """Manage server startup and shutdown lifecycle"""
    try:
        logger.info("AbletonMCP server starting up")
        
        try:
            ableton = get_ableton_connection()
            logger.info("Successfully connected to Ableton on startup")
        except Exception as e:
            logger.warning(f"Could not connect to Ableton on startup: {str(e)}")
            logger.warning("Make sure the Ableton Remote Script is running")
        
        yield {}
    finally:
        global _ableton_connection
        if _ableton_connection:
            logger.info("Disconnecting from Ableton on shutdown")
            _ableton_connection.disconnect()
            _ableton_connection = None
        logger.info("AbletonMCP server shut down")

# Create the MCP server with lifespan support
mcp = FastMCP(
    "AbletonMCP",
    lifespan=server_lifespan
)

# Global connection for resources
_ableton_connection = None

def get_ableton_connection():
    """Get or create a persistent Ableton connection"""
    global _ableton_connection
    
    if _ableton_connection is not None:
        try:
            # Test the connection with a simple ping
            # We'll try to send an empty message, which should fail if the connection is dead
            # but won't affect Ableton if it's alive
            _ableton_connection.sock.settimeout(1.0)
            _ableton_connection.sock.sendall(b'')
            return _ableton_connection
        except Exception as e:
            logger.warning(f"Existing connection is no longer valid: {str(e)}")
            try:
                _ableton_connection.disconnect()
            except:
                pass
            _ableton_connection = None
    
    # Connection doesn't exist or is invalid, create a new one
    if _ableton_connection is None:
        # Try to connect up to 3 times with a short delay between attempts
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(f"Connecting to Ableton (attempt {attempt}/{max_attempts})...")
                _ableton_connection = AbletonConnection(host="localhost", port=9877)
                if _ableton_connection.connect():
                    logger.info("Created new persistent connection to Ableton")
                    
                    # Validate connection with a simple command
                    try:
                        # Get session info as a test
                        _ableton_connection.send_command("get_session_info")
                        logger.info("Connection validated successfully")
                        return _ableton_connection
                    except Exception as e:
                        logger.error(f"Connection validation failed: {str(e)}")
                        _ableton_connection.disconnect()
                        _ableton_connection = None
                        # Continue to next attempt
                else:
                    _ableton_connection = None
            except Exception as e:
                logger.error(f"Connection attempt {attempt} failed: {str(e)}")
                if _ableton_connection:
                    _ableton_connection.disconnect()
                    _ableton_connection = None
            
            # Wait before trying again, but only if we have more attempts left
            if attempt < max_attempts:
                import time
                time.sleep(1.0)
        
        # If we get here, all connection attempts failed
        if _ableton_connection is None:
            logger.error("Failed to connect to Ableton after multiple attempts")
            raise Exception("Could not connect to Ableton. Make sure the Remote Script is running.")
    
    return _ableton_connection


# Core Tool endpoints

@mcp.tool()
def get_session_info(ctx: Context) -> str:
    """Get detailed information about the current Ableton session"""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_session_info")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting session info from Ableton: {str(e)}")
        return f"Error getting session info: {str(e)}"

@mcp.tool()
def get_track_info(ctx: Context, track_index: int) -> str:
    """
    Get detailed information about a specific track in Ableton.

    Track index convention: 0+ = regular/group tracks, -1 = master, -2 = return A, -3 = return B, etc.
    Master and return tracks omit clip_slots and arm. Master additionally omits mute and solo.
    Response includes track_type ("audio", "midi", "group", "return", or "master") and is_group_track.
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_track_info", {"track_index": track_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting track info from Ableton: {str(e)}")
        return f"Error getting track info: {str(e)}"

@mcp.tool()
def create_midi_track(ctx: Context, index: int = -1) -> str:
    """
    Create a new MIDI track in the Ableton session.
    
    Parameters:
    - index: The index to insert the track at (-1 = end of list)
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("create_midi_track", {"index": index})
        return f"Created new MIDI track: {result.get('name', 'unknown')}"
    except Exception as e:
        logger.error(f"Error creating MIDI track: {str(e)}")
        return f"Error creating MIDI track: {str(e)}"


@mcp.tool()
def set_track_name(ctx: Context, track_index: int, name: str) -> str:
    """
    Set the name of a track.
    
    Parameters:
    - track_index: The index of the track to rename
    - name: The new name for the track
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_track_name", {"track_index": track_index, "name": name})
        return f"Renamed track to: {result.get('name', name)}"
    except Exception as e:
        logger.error(f"Error setting track name: {str(e)}")
        return f"Error setting track name: {str(e)}"

@mcp.tool()
def create_clip(ctx: Context, track_index: int, clip_index: int, length: float = 4.0) -> str:
    """
    Create a new MIDI clip in the specified track and clip slot.
    
    Parameters:
    - track_index: The index of the track to create the clip in
    - clip_index: The index of the clip slot to create the clip in
    - length: The length of the clip in beats (default: 4.0)
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("create_clip", {
            "track_index": track_index, 
            "clip_index": clip_index, 
            "length": length
        })
        return f"Created new clip at track {track_index}, slot {clip_index} with length {length} beats"
    except Exception as e:
        logger.error(f"Error creating clip: {str(e)}")
        return f"Error creating clip: {str(e)}"

@mcp.tool()
def add_notes_to_clip(
    ctx: Context, 
    track_index: int, 
    clip_index: int, 
    notes: List[Dict[str, Union[int, float, bool]]]
) -> str:
    """
    Add MIDI notes to a clip.
    
    Parameters:
    - track_index: The index of the track containing the clip
    - clip_index: The index of the clip slot containing the clip
    - notes: List of note dictionaries, each with pitch, start_time, duration, velocity, and mute
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("add_notes_to_clip", {
            "track_index": track_index,
            "clip_index": clip_index,
            "notes": notes
        })
        return f"Added {len(notes)} notes to clip at track {track_index}, slot {clip_index}"
    except Exception as e:
        logger.error(f"Error adding notes to clip: {str(e)}")
        return f"Error adding notes to clip: {str(e)}"

@mcp.tool()
def set_clip_name(ctx: Context, track_index: int, clip_index: int, name: str) -> str:
    """
    Set the name of a clip.
    
    Parameters:
    - track_index: The index of the track containing the clip
    - clip_index: The index of the clip slot containing the clip
    - name: The new name for the clip
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_clip_name", {
            "track_index": track_index,
            "clip_index": clip_index,
            "name": name
        })
        return f"Renamed clip at track {track_index}, slot {clip_index} to '{name}'"
    except Exception as e:
        logger.error(f"Error setting clip name: {str(e)}")
        return f"Error setting clip name: {str(e)}"

@mcp.tool()
def set_tempo(ctx: Context, tempo: float) -> str:
    """
    Set the tempo of the Ableton session.
    
    Parameters:
    - tempo: The new tempo in BPM
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_tempo", {"tempo": tempo})
        return f"Set tempo to {tempo} BPM"
    except Exception as e:
        logger.error(f"Error setting tempo: {str(e)}")
        return f"Error setting tempo: {str(e)}"


@mcp.tool()
def load_instrument_or_effect(ctx: Context, track_index: int, uri: str) -> str:
    """
    Load an instrument or effect onto a track using its URI.
    
    Parameters:
    - track_index: 0+ = regular/group tracks, -1 = master, -2 = return A, -3 = return B, etc.
    - uri: The URI of the instrument or effect to load (e.g., 'query:Synths#Instrument%20Rack:Bass:FileId_5116')
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("load_browser_item", {
            "track_index": track_index,
            "item_uri": uri
        })
        
        # Check if the instrument was loaded successfully
        if result.get("loaded", False):
            new_devices = result.get("new_devices", [])
            if new_devices:
                return f"Loaded instrument with URI '{uri}' on track {track_index}. New devices: {', '.join(new_devices)}"
            else:
                devices = result.get("devices_after", [])
                return f"Loaded instrument with URI '{uri}' on track {track_index}. Devices on track: {', '.join(devices)}"
        else:
            return f"Failed to load instrument with URI '{uri}'"
    except Exception as e:
        logger.error(f"Error loading instrument by URI: {str(e)}")
        return f"Error loading instrument by URI: {str(e)}"

@mcp.tool()
def fire_clip(ctx: Context, track_index: int, clip_index: int) -> str:
    """
    Start playing a clip.
    
    Parameters:
    - track_index: The index of the track containing the clip
    - clip_index: The index of the clip slot containing the clip
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("fire_clip", {
            "track_index": track_index,
            "clip_index": clip_index
        })
        return f"Started playing clip at track {track_index}, slot {clip_index}"
    except Exception as e:
        logger.error(f"Error firing clip: {str(e)}")
        return f"Error firing clip: {str(e)}"

@mcp.tool()
def stop_clip(ctx: Context, track_index: int, clip_index: int) -> str:
    """
    Stop playing a clip.
    
    Parameters:
    - track_index: The index of the track containing the clip
    - clip_index: The index of the clip slot containing the clip
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("stop_clip", {
            "track_index": track_index,
            "clip_index": clip_index
        })
        return f"Stopped clip at track {track_index}, slot {clip_index}"
    except Exception as e:
        logger.error(f"Error stopping clip: {str(e)}")
        return f"Error stopping clip: {str(e)}"

@mcp.tool()
def start_playback(ctx: Context) -> str:
    """Start playing the Ableton session."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("start_playback")
        return "Started playback"
    except Exception as e:
        logger.error(f"Error starting playback: {str(e)}")
        return f"Error starting playback: {str(e)}"

@mcp.tool()
def stop_playback(ctx: Context) -> str:
    """Stop playing the Ableton session."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("stop_playback")
        return "Stopped playback"
    except Exception as e:
        logger.error(f"Error stopping playback: {str(e)}")
        return f"Error stopping playback: {str(e)}"

@mcp.tool()
def get_browser_tree(ctx: Context, category_type: str = "all") -> str:
    """
    Get a hierarchical tree of browser categories from Ableton.
    
    Parameters:
    - category_type: Type of categories to get ('all', 'instruments', 'sounds', 'drums', 'audio_effects', 'midi_effects')
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_browser_tree", {
            "category_type": category_type
        })
        
        # Check if we got any categories
        if "available_categories" in result and len(result.get("categories", [])) == 0:
            available_cats = result.get("available_categories", [])
            return (f"No categories found for '{category_type}'. "
                   f"Available browser categories: {', '.join(available_cats)}")
        
        # Format the tree in a more readable way
        total_folders = result.get("total_folders", 0)
        formatted_output = f"Browser tree for '{category_type}' (showing {total_folders} folders):\n\n"
        
        def format_tree(item, indent=0):
            output = ""
            if item:
                prefix = "  " * indent
                name = item.get("name", "Unknown")
                path = item.get("path", "")
                has_more = item.get("has_more", False)
                
                # Add this item
                output += f"{prefix}• {name}"
                if path:
                    output += f" (path: {path})"
                if has_more:
                    output += " [...]"
                output += "\n"
                
                # Add children
                for child in item.get("children", []):
                    output += format_tree(child, indent + 1)
            return output
        
        # Format each category
        for category in result.get("categories", []):
            formatted_output += format_tree(category)
            formatted_output += "\n"
        
        return formatted_output
    except Exception as e:
        error_msg = str(e)
        if "Browser is not available" in error_msg:
            logger.error(f"Browser is not available in Ableton: {error_msg}")
            return f"Error: The Ableton browser is not available. Make sure Ableton Live is fully loaded and try again."
        elif "Could not access Live application" in error_msg:
            logger.error(f"Could not access Live application: {error_msg}")
            return f"Error: Could not access the Ableton Live application. Make sure Ableton Live is running and the Remote Script is loaded."
        else:
            logger.error(f"Error getting browser tree: {error_msg}")
            return f"Error getting browser tree: {error_msg}"

@mcp.tool()
def get_browser_items_at_path(ctx: Context, path: str) -> str:
    """
    Get browser items at a specific path in Ableton's browser.
    
    Parameters:
    - path: Path in the format "category/folder/subfolder"
            where category is one of the available browser categories in Ableton
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_browser_items_at_path", {
            "path": path
        })
        
        # Check if there was an error with available categories
        if "error" in result and "available_categories" in result:
            error = result.get("error", "")
            available_cats = result.get("available_categories", [])
            return (f"Error: {error}\n"
                   f"Available browser categories: {', '.join(available_cats)}")
        
        return json.dumps(result, indent=2)
    except Exception as e:
        error_msg = str(e)
        if "Browser is not available" in error_msg:
            logger.error(f"Browser is not available in Ableton: {error_msg}")
            return f"Error: The Ableton browser is not available. Make sure Ableton Live is fully loaded and try again."
        elif "Could not access Live application" in error_msg:
            logger.error(f"Could not access Live application: {error_msg}")
            return f"Error: Could not access the Ableton Live application. Make sure Ableton Live is running and the Remote Script is loaded."
        elif "Unknown or unavailable category" in error_msg:
            logger.error(f"Invalid browser category: {error_msg}")
            return f"Error: {error_msg}. Please check the available categories using get_browser_tree."
        elif "Path part" in error_msg and "not found" in error_msg:
            logger.error(f"Path not found: {error_msg}")
            return f"Error: {error_msg}. Please check the path and try again."
        else:
            logger.error(f"Error getting browser items at path: {error_msg}")
            return f"Error getting browser items at path: {error_msg}"

@mcp.tool()
def get_track_levels(ctx: Context) -> str:
    """
    Get real-time output meter levels for all tracks, return tracks, and master.

    Returns peak meter values (0.0–1.0) for left, right, and combined peak per track.
    Use this to audit gain staging across the session.
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_track_levels")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting track levels: {str(e)}")
        return f"Error getting track levels: {str(e)}"


@mcp.tool()
def get_device_parameters(ctx: Context, track_index: int, device_index: int) -> str:
    """
    Get all parameters for a device on a track.

    Parameters:
    - track_index: 0+ = regular/group tracks, -1 = master, -2 = return A, -3 = return B, etc.
    - device_index: The index of the device on that track

    Returns each parameter's index, name, current value, min, max, and whether it is quantized.
    Use this to read EQ Eight band settings, compressor gain reduction, Utility gain/width, etc.
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_device_parameters", {
            "track_index": track_index,
            "device_index": device_index,
        })
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting device parameters: {str(e)}")
        return f"Error getting device parameters: {str(e)}"


@mcp.tool()
def set_device_parameter(
    ctx: Context,
    track_index: int,
    device_index: int,
    parameter_index: int,
    value: float,
) -> str:
    """
    Set a parameter value on a device.

    Parameters:
    - track_index: 0+ = regular/group tracks, -1 = master, -2 = return A, -3 = return B, etc.
    - device_index: The index of the device on that track
    - parameter_index: The index of the parameter (from get_device_parameters)
    - value: The new value (must be within the parameter's min/max range)
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_device_parameter", {
            "track_index": track_index,
            "device_index": device_index,
            "parameter_index": parameter_index,
            "value": value,
        })
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error setting device parameter: {str(e)}")
        return f"Error setting device parameter: {str(e)}"


@mcp.tool()
def load_analyzer_device(ctx: Context, track_index: int) -> str:
    """
    Load the AbletonMCP Analyzer M4L device onto a track.

    The device must be installed first (run install.py). It will be placed
    at the end of the track's device chain. Use get_track_info to find the
    device index after loading, then get_device_parameters to read band levels.

    Parameters:
    - track_index: 0+ = regular/group tracks, -1 = master, -2 = return A, -3 = return B, etc.
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("load_analyzer_device", {"track_index": track_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error loading analyzer device: {str(e)}")
        return f"Error loading analyzer device: {str(e)}"


@mcp.tool()
def get_track_volumes(ctx: Context) -> str:
    """Get volume, pan, mute, solo, and arm state for all tracks, return tracks, and master."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_track_volumes")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting track volumes: {str(e)}")
        return f"Error getting track volumes: {str(e)}"


@mcp.tool()
def set_track_volume(ctx: Context, track_index: int, volume: float) -> str:
    """
    Set the volume of a track.
    Track index convention: 0+ = regular/group tracks, -1 = master, -2 = return A, -3 = return B, etc.
    Volume range: 0.0 (silence) to 1.0 (unity gain, 0 dB). Values above 1.0 boost up to +6 dB.
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_track_volume", {"track_index": track_index, "volume": volume})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error setting track volume: {str(e)}")
        return f"Error setting track volume: {str(e)}"


@mcp.tool()
def set_track_pan(ctx: Context, track_index: int, pan: float) -> str:
    """
    Set the panning of a track.
    Track index convention: 0+ = regular/group tracks, -1 = master, -2 = return A, -3 = return B, etc.
    Pan range: -1.0 (full left) to 1.0 (full right). 0.0 is center.
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_track_pan", {"track_index": track_index, "pan": pan})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error setting track pan: {str(e)}")
        return f"Error setting track pan: {str(e)}"


@mcp.tool()
def set_track_mute(ctx: Context, track_index: int, muted: bool) -> str:
    """Mute or unmute a track. muted=True silences the track. Supports regular, group, and return tracks (not master). Track index convention: 0+ = regular/group, -2 = return A, -3 = return B, etc."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_track_mute", {"track_index": track_index, "muted": muted})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error setting track mute: {str(e)}")
        return f"Error setting track mute: {str(e)}"


@mcp.tool()
def set_track_solo(ctx: Context, track_index: int, soloed: bool) -> str:
    """Solo or unsolo a track. Supports regular, group, and return tracks (not master). Track index convention: 0+ = regular/group, -2 = return A, -3 = return B, etc."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_track_solo", {"track_index": track_index, "soloed": soloed})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error setting track solo: {str(e)}")
        return f"Error setting track solo: {str(e)}"


@mcp.tool()
def set_track_arm(ctx: Context, track_index: int, armed: bool) -> str:
    """Arm or disarm a track for recording. Only valid on tracks that can be armed."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_track_arm", {"track_index": track_index, "armed": armed})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error setting track arm: {str(e)}")
        return f"Error setting track arm: {str(e)}"


@mcp.tool()
def toggle_device(ctx: Context, track_index: int, device_index: int, enabled: bool) -> str:
    """
    Enable or bypass a device on a track.
    Track index convention: 0+ = regular/group tracks, -1 = master, -2 = return A, -3 = return B, etc.
    enabled=True turns the device on; enabled=False bypasses it.
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("toggle_device", {
            "track_index": track_index,
            "device_index": device_index,
            "enabled": enabled,
        })
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error toggling device: {str(e)}")
        return f"Error toggling device: {str(e)}"


@mcp.tool()
def get_clip_notes(ctx: Context, track_index: int, clip_index: int) -> str:
    """
    Read all MIDI notes from a clip.
    Returns pitch, start_time, duration, velocity, and mute for each note.
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_clip_notes", {
            "track_index": track_index,
            "clip_index": clip_index,
        })
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting clip notes: {str(e)}")
        return f"Error getting clip notes: {str(e)}"


@mcp.tool()
def create_scene(ctx: Context, index: int = -1) -> str:
    """Create a new scene. index=-1 appends at the end."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("create_scene", {"index": index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error creating scene: {str(e)}")
        return f"Error creating scene: {str(e)}"


@mcp.tool()
def fire_scene(ctx: Context, scene_index: int) -> str:
    """Launch all clips in a scene."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("fire_scene", {"scene_index": scene_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error firing scene: {str(e)}")
        return f"Error firing scene: {str(e)}"


@mcp.tool()
def set_scene_name(ctx: Context, scene_index: int, name: str) -> str:
    """Set the name of a scene."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_scene_name", {"scene_index": scene_index, "name": name})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error setting scene name: {str(e)}")
        return f"Error setting scene name: {str(e)}"


@mcp.tool()
def get_rack_devices(ctx: Context, track_index: int, device_index: int) -> str:
    """
    Get all chains and their sub-devices (with full parameter lists) for a rack device.

    Use this to inspect instruments or effects racks that contain nested device chains,
    such as a Rack wrapping FabFilter Pro-Q 3 or other plugins.

    Parameters:
    - track_index: 0+ = regular/group tracks, -1 = master, -2 = return A, -3 = return B, etc.
    - device_index: The index of the rack device on that track.

    Returns rack_name, and for each chain: its index, name, and list of devices with parameters.
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_rack_devices", {
            "track_index": track_index,
            "device_index": device_index,
        })
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting rack devices: {str(e)}")
        return f"Error getting rack devices: {str(e)}"


@mcp.tool()
def set_rack_device_parameter(
    ctx: Context,
    track_index: int,
    device_index: int,
    chain_index: int,
    chain_device_index: int,
    parameter_index: int,
    value: float,
) -> str:
    """
    Set a parameter on a device nested inside a rack chain.

    Use get_rack_devices first to discover chain_index, chain_device_index,
    and parameter_index values.

    Parameters:
    - track_index: 0+ = regular/group tracks, -1 = master, -2 = return A, -3 = return B, etc.
    - device_index: The index of the rack device on that track.
    - chain_index: The index of the chain inside the rack.
    - chain_device_index: The index of the device within that chain.
    - parameter_index: The index of the parameter on that device.
    - value: The new value (must be within the parameter's min/max range).
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_rack_device_parameter", {
            "track_index": track_index,
            "device_index": device_index,
            "chain_index": chain_index,
            "chain_device_index": chain_device_index,
            "parameter_index": parameter_index,
            "value": value,
        })
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error setting rack device parameter: {str(e)}")
        return f"Error setting rack device parameter: {str(e)}"


@mcp.tool()
def capture_session_snapshot(ctx: Context, label: str = "") -> str:
    """
    Capture a full snapshot of the session state: track levels, volumes, pans,
    mute/solo states, and all device parameters. Saves to sessions/ directory.

    Call this at the start of a mixing or mastering session to create a benchmark.
    After the session, the snapshot shows exactly what changed.

    Parameters:
    - label: optional label to include in the filename (e.g., "pre-mix", "pre-master")
    """
    import os
    from datetime import datetime

    try:
        ableton = get_ableton_connection()

        session_info = ableton.send_command("get_session_info")
        levels = ableton.send_command("get_track_levels")
        volumes = ableton.send_command("get_track_volumes")
        track_count = session_info.get("track_count", 0)

        tracks_snapshot = []
        for i in range(track_count):
            track_info = ableton.send_command("get_track_info", {"track_index": i})
            devices_snapshot = []
            for device in track_info.get("devices", []):
                try:
                    params = ableton.send_command("get_device_parameters", {
                        "track_index": i,
                        "device_index": device["index"],
                    })
                    devices_snapshot.append(params)
                except Exception:
                    devices_snapshot.append({"device_index": device["index"], "error": "could not read"})
            tracks_snapshot.append({
                "index": i,
                "name": track_info.get("name"),
                "devices": devices_snapshot,
            })

        timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
        suffix = f"-{label}" if label else ""
        filename = f"snapshot-{timestamp}{suffix}.json"

        sessions_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sessions")
        os.makedirs(sessions_dir, exist_ok=True)
        filepath = os.path.join(sessions_dir, filename)

        snapshot = {
            "timestamp": timestamp,
            "label": label,
            "session_info": session_info,
            "levels": levels,
            "volumes": volumes,
            "tracks": tracks_snapshot,
        }

        with open(filepath, "w") as f:
            json.dump(snapshot, f, indent=2)

        return f"Snapshot saved: {filepath} ({track_count} tracks, {sum(len(t['devices']) for t in tracks_snapshot)} devices)"
    except Exception as e:
        logger.error(f"Error capturing session snapshot: {str(e)}")
        return f"Error capturing session snapshot: {str(e)}"


@mcp.tool()
def load_device_and_get_parameters(ctx: Context, track_index: int, item_uri: str) -> str:
    """
    Load a device onto a track by URI and immediately return all its parameters.

    Use this to discover a third-party plugin's parameter names and indices in one step.
    After calling this, use set_device_parameter with the returned parameter indices to
    control the plugin. Use get_track_info to find the device index after loading.

    Parameters:
    - track_index: 0+ = regular/group tracks, -1 = master, -2 = return A, -3 = return B, etc.
    - item_uri: The browser URI of the device to load

    Returns the device name, class name, and full parameter list with indices, names,
    current values, and min/max ranges.
    """
    try:
        ableton = get_ableton_connection()
        load_result = ableton.send_command("load_browser_item", {
            "track_index": track_index,
            "item_uri": item_uri,
        })
        if not load_result.get("loaded", False):
            return f"Failed to load device with URI '{item_uri}'"
        track_info = ableton.send_command("get_track_info", {"track_index": track_index})
        devices = track_info.get("devices", [])
        if not devices:
            return "Device loaded but could not find it on track"
        device_index = len(devices) - 1
        params_result = ableton.send_command("get_device_parameters", {
            "track_index": track_index,
            "device_index": device_index,
        })
        params_result["device_index"] = device_index
        return json.dumps(params_result, indent=2)
    except Exception as e:
        logger.error(f"Error loading device and getting parameters: {str(e)}")
        return f"Error loading device and getting parameters: {str(e)}"


@mcp.tool()
def load_drum_kit(ctx: Context, track_index: int, rack_uri: str, kit_path: str) -> str:
    """
    Load a drum rack and then load a specific drum kit into it.
    
    Parameters:
    - track_index: The index of the track to load on
    - rack_uri: The URI of the drum rack to load (e.g., 'Drums/Drum Rack')
    - kit_path: Path to the drum kit inside the browser (e.g., 'drums/acoustic/kit1')
    """
    try:
        ableton = get_ableton_connection()
        
        # Step 1: Load the drum rack
        result = ableton.send_command("load_browser_item", {
            "track_index": track_index,
            "item_uri": rack_uri
        })
        
        if not result.get("loaded", False):
            return f"Failed to load drum rack with URI '{rack_uri}'"
        
        # Step 2: Get the drum kit items at the specified path
        kit_result = ableton.send_command("get_browser_items_at_path", {
            "path": kit_path
        })
        
        if "error" in kit_result:
            return f"Loaded drum rack but failed to find drum kit: {kit_result.get('error')}"
        
        # Step 3: Find a loadable drum kit
        kit_items = kit_result.get("items", [])
        loadable_kits = [item for item in kit_items if item.get("is_loadable", False)]
        
        if not loadable_kits:
            return f"Loaded drum rack but no loadable drum kits found at '{kit_path}'"
        
        # Step 4: Load the first loadable kit
        kit_uri = loadable_kits[0].get("uri")
        load_result = ableton.send_command("load_browser_item", {
            "track_index": track_index,
            "item_uri": kit_uri
        })
        
        return f"Loaded drum rack and kit '{loadable_kits[0].get('name')}' on track {track_index}"
    except Exception as e:
        logger.error(f"Error loading drum kit: {str(e)}")
        return f"Error loading drum kit: {str(e)}"

# Main execution
def main():
    """Run the MCP server"""
    mcp.run()

if __name__ == "__main__":
    main()