# Plugin Library

One file per plugin. Each file contains the browser URI and parameter map for that plugin.

**CC: read the relevant file from this directory when working with a specific plugin. Do not load all files — only the ones needed for the current task.**

After a session where you discover or confirm a plugin's URI or parameters, update or create its file here. Do not write plugin parameter data into CLAUDE.md.

## Discovered plugins

<!-- CC: add a line here when a new plugin file is created -->

## File format

See any existing plugin file for the format. Key fields:
- `uri` — browser URI to load the plugin with `load_browser_item` or `load_device_and_get_parameters`
- `browser_path` — path for `get_browser_items_at_path` to find the plugin
- Parameter table — index, name, range, and notes for the parameters you use

## Notes on dynamic plugins

FabFilter Pro-Q 3 has dynamic bands — parameter indices shift as bands are added/removed. For these, always call `get_device_parameters` live rather than relying on a stored map. Only store the URI and general notes.
