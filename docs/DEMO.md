# Recording a demo

A short screen capture is the best thing to attach to a social post. Two easy
options.

## Option A: terminal cast (asciinema)

Records the tool sequence running against the real archives. Fast, tiny,
embeddable.

```bash
pip install asciinema
asciinema rec astrodata-demo.cast \
  -c "python examples/demo.py 'HD 122563'"
# upload / share:
asciinema upload astrodata-demo.cast
```

`examples/demo.py` runs the canonical flow: resolve a target via SIMBAD, pull
the nearest Gaia DR3 source (with its J2016.0 epoch), list Keck HIRES frames,
and show the provenance + citation attached to every result.

## Option B: the real client (screen recording)

Shows what users actually see. Connect the server to an MCP client (see the
README), then screen-record a single natural-language prompt:

> "Resolve HD 122563, then show the nearest Gaia DR3 source and any Keck HIRES
> data, and give me the citations."

Keep it to ~30 seconds: one prompt, the client calling `simbad_resolve` ->
`gaia_cone_search` / `koa_query`, and the answer with acknowledgements. On
macOS use QuickTime or `Cmd+Shift+5`; any screen recorder works.
