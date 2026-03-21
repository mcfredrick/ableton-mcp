Start a CC mastering session on the current Ableton Live project.

Follow the CC Mastering Session workflow from CLAUDE.md exactly, in order:

1. Set up mastering chain — check what's already on the master track (track_index=-1), load any missing devices (EQ Eight → Multiband Dynamics → Glue Compressor → Limiter → AbletonMCP Analyzer) in signal-chain order. If FabFilter Pro-Q 3, Pro-L 2, or Pro-C 2 are available in the browser, prefer them over built-in devices for the mastering chain. Check with get_browser_items_at_path first.
2. Set up reference track — create an audio track named "Reference", load AbletonMCP Analyzer on it, then ask me to drop the reference audio file into the first clip slot and wait for confirmation before continuing
3. Match loudness — read peak levels on reference and mix, adjust until matched within 2 dB
4. Build frequency profiles — read AbletonMCP Analyzer on both tracks, display a comparison table with deltas
5. Apply EQ corrections — for any band delta > 2 dB, propose a correction and apply it to master EQ Eight after I confirm
6. Set dynamics — read current Glue Compressor and Limiter parameters, set to the mastering standard values from CLAUDE.md
7. Verify — re-read analyzers and levels, present the mastering sign-off checklist

Start immediately with Step 1. Report findings at each step before moving to the next. For Step 2, pause and wait for me to confirm the reference file is in place before reading levels.
