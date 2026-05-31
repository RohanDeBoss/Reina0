# Reina0
HeXO bot with a local browser UI.

Run it with:

```bash
python game.py
```

`game.py` starts a local server and opens the playable UI in your browser. Choose your side, choose who moves first, press Play Game, then click two empty hexes to place your move; the bot replies automatically by default.

The board only shows legal frontier cells. A new cell must be within 8 hexes of the position as it existed before your turn. Hover the engine board in the lower-right of the canvas to see eval, depth timing, nodes, and PV while Reina0 searches.

In VS Code or a similar editor, open `game.py` and press Run/Play.

Project layout:

- `game.py` - web app launcher, local API, and game-state wrapper.
- `mybot.py` - Reina0 bot/search logic.
- `web/` - canvas UI, controls, and styling.
- `hexo.py` / `server.py` - compatibility launchers that forward to `game.py`.
