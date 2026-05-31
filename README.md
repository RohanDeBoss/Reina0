# Reina0
HeXO bot with a local browser UI.

Run it with:

```bash
python game.py
```

`game.py` starts a local server and opens the playable UI in your browser. The launch dialog lets you choose Human vs Human, Human vs AI, or AI vs AI, pick who moves first, and set depth/time controls for each side.

The board only shows legal frontier cells. A new cell must be within 8 hexes of the position as it existed before your turn. Engine eval, nodes, per-depth timing, and PV are shown live in the right-side engine panel while Reina0 searches.

In VS Code or a similar editor, open `game.py` and press Run/Play.

Project layout:

- `game.py` - web app launcher, local API, and game-state wrapper.
- `mybot.py` - Reina0 bot/search logic.
- `web/` - canvas UI, controls, and styling.
- `hexo.py` / `server.py` - compatibility launchers that forward to `game.py`.
