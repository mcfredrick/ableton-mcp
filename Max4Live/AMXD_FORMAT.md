# .amxd Binary File Format

Reverse-engineered from working M4L devices (Max Audio Effect.amxd template, Verbotron.amxd).

## Header Structure (32 bytes)

```
Offset  Size  Content
------  ----  -------
0       4     b'ampf'           magic bytes
4       4     0x04000000        version (uint32 LE = 4)
8       4     b'aaaa'           chunk type marker
12      4     b'meta'           metadata chunk tag
16      4     0x04000000        meta chunk data length (uint32 LE = 4)
20      4     b'\x00\x00\x00\x00'  meta data (zeros)
24      4     b'ptch'           patch chunk tag
28      4     <json_length>     JSON byte length (uint32 LE)
32      N     {JSON bytes}      UTF-8 encoded patcher JSON
```

## Python write code

```python
import struct, json

json_bytes = json.dumps({"patcher": patch}, indent=2).encode("utf-8")
header = (
    b'ampf'
    + struct.pack('<I', 4)           # version
    + b'aaaa'
    + b'meta'
    + struct.pack('<I', 4)           # meta data length
    + b'\x00' * 4                   # meta data
    + b'ptch'
    + struct.pack('<I', len(json_bytes))
)
with open(path, "wb") as f:
    f.write(header + json_bytes)
```

## Patcher JSON structure

Start from the official Max Audio Effect template to get all required metadata fields.
Key fields: `classnamespace: "box"`, `devicewidth`, `subpatcher_template`, `project`, `latency`, `description`, `digest`, `tags`.

## live.numbox parameter registration

For Live to expose `live.numbox` objects via its device parameter API:

1. **`parameter_enable: 1`** at the box level (top-level attribute)
2. **`varname`** — unique string per box; becomes the parameter name Live reports
3. **`saved_attribute_attributes.valueof`** — flat key/value pairs (NOT nested `{"value": X}`):
   - `parameter_longname`, `parameter_shortname`, `parameter_mmin`, `parameter_mmax`
   - `parameter_type` (0=float), `parameter_unitstyle`, `parameter_mapping_index`
   - `parameter_initial`, `parameter_initial_enable`
4. **Top-level `"parameters"` dict** on the patcher:
   ```json
   {
     "obj-nb-0": ["Long Name", "Short", 0],
     "parameterbanks": {
       "0": {"index": 0, "name": "", "parameters": ["Short1", "Short2", ...]}
     }
   }
   ```
   Without this registry, Live only shows "Device On" regardless of live.numbox objects.

## Notes

- `varname` is what Live uses as the displayed parameter name (not `parameter_longname`)
- Parameters are sorted alphabetically by varname in `get_device_parameters`
- The wrong header format (e.g. with `mx@c` instead of `meta`) causes "error 6" in Live's GUI
- `classnamespace: "dsp.d"` causes parameters not to register (only "Device On" appears)
