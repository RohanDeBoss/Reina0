import argparse
import json
import mimetypes
import threading
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from mybot import COLORS, Reina0, add_to_index, cell, mark_dirty_multiple, new_board, opposite_color


PLACEMENT_RANGE = 8


class HexoGame:
    def __init__(self, human_color="blue", first_color="blue", bot_depth=3, bot_enabled=True):
        self.human_color = human_color if human_color in COLORS else "blue"
        self.bot_color = opposite_color(self.human_color)
        self.first_color = first_color if first_color in COLORS else "blue"
        self.bot_depth = self._clean_depth(bot_depth)
        self.bot_enabled = bool(bot_enabled)
        self.search_stats = self.empty_search_stats()
        self.reset()

    def empty_search_stats(self):
        return {
            "running": False,
            "depths": [],
            "nodes": 0,
            "pv": [],
            "candidates": [],
            "elapsedMs": 0,
            "moveApplied": False,
            "error": None,
        }

    def update_search_stats(self, stats):
        self.search_stats = {**self.empty_search_stats(), **stats}

    def _clean_depth(self, depth):
        try:
            depth = int(depth)
        except (TypeError, ValueError):
            depth = 3
        return max(1, min(depth, 8))

    def reset(self):
        self.cellsplaced = new_board()
        self.ply = 0
        self.next_color = self.first_color
        self.history = []
        self.redo_stack = []
        self.winner = None
        self.game_over = False
        self.search_stats = self.empty_search_stats()
        self.bot = Reina0("0", "0", self.bot_color, self.cellsplaced, self.bot_depth, telemetry_callback=self.update_search_stats)
        self.evaluate_winner()

    def configure(self, human_color=None, first_color=None, bot_depth=None, bot_enabled=None):
        if human_color in COLORS:
            self.human_color = human_color
            self.bot_color = opposite_color(human_color)
        if first_color in COLORS:
            self.first_color = first_color
        if bot_depth is not None:
            self.bot_depth = self._clean_depth(bot_depth)
        if bot_enabled is not None:
            self.bot_enabled = bool(bot_enabled)
        self.bot.color = self.bot_color
        self.bot.movecheck = self.bot_depth

    def occupied_coords(self):
        return {(c.x, c.y) for c in self.cellsplaced.values()}

    def hex_distance(self, a, b):
        dx = a[0] - b[0]
        dy = a[1] - b[1]
        dz = dx - dy
        return max(abs(dx), abs(dy), abs(dz))

    def is_coord_in_range(self, coord, anchors=None):
        anchors = anchors or self.occupied_coords()
        return any(self.hex_distance(coord, anchor) <= PLACEMENT_RANGE for anchor in anchors)

    def legal_frontier(self):
        occupied = self.occupied_coords()
        frontier = set()
        for ax, ay in occupied:
            for x in range(ax - PLACEMENT_RANGE, ax + PLACEMENT_RANGE + 1):
                for y in range(ay - PLACEMENT_RANGE, ay + PLACEMENT_RANGE + 1):
                    coord = (x, y)
                    if coord not in occupied and self.hex_distance(coord, (ax, ay)) <= PLACEMENT_RANGE:
                        frontier.add(coord)
        return frontier

    def _normalise_pair(self, coords):
        if not isinstance(coords, (list, tuple)) or len(coords) != 2:
            raise ValueError("Place exactly two cells.")

        pair = []
        for coord in coords:
            if isinstance(coord, dict):
                x = coord.get("x")
                y = coord.get("y")
            else:
                x, y = coord
            pair.append((int(x), int(y)))

        if pair[0] == pair[1]:
            raise ValueError("Choose two different cells.")
        return pair

    def place_pair(self, coords, color, actor="player", record=True):
        if self.game_over:
            raise ValueError("The game is already over.")
        if color != self.next_color:
            raise ValueError(f"{self.next_color.title()} is next to move.")

        pair = self._normalise_pair(coords)
        occupied = self.occupied_coords()
        blocked = [coord for coord in pair if coord in occupied]
        if blocked:
            x, y = blocked[0]
            raise ValueError(f"Cell ({x}, {y}) is already occupied.")

        illegal = [coord for coord in pair if not self.is_coord_in_range(coord, occupied)]
        if illegal:
            x, y = illegal[0]
            raise ValueError(f"Cell ({x}, {y}) is more than {PLACEMENT_RANGE} hexes from the current position.")

        self.ply += 1
        placed = []
        for index, (x, y) in enumerate(pair, start=1):
            key = f"{actor}:{self.ply:03d}:{index}"
            placed_cell = cell(x, y, color)
            self.cellsplaced[key] = placed_cell
            add_to_index(self.bot, placed_cell, key)
            placed.append(placed_cell)

        mark_dirty_multiple(self.bot, placed, self.bot.by_x, self.bot.by_y, self.bot.by_z)
        move = {
            "actor": actor,
            "color": color,
            "cells": [{"x": x, "y": y} for x, y in pair],
            "ply": self.ply,
        }

        if record:
            self.history.append(move)
            self.redo_stack.clear()

        self.evaluate_winner()
        if not self.game_over:
            self.next_color = opposite_color(self.next_color)
        return move

    def player_move(self, coords):
        if self.bot_enabled and self.next_color != self.human_color:
            raise ValueError("It is the bot's turn.")
        actor = "you" if self.bot_enabled else "player"
        return self.place_pair(coords, self.next_color, actor=actor)

    def fallback_bot_move(self):
        occupied = self.occupied_coords()
        self.bot.legalMoves()
        legal = [coord for coord in self.bot.legalcoords if coord not in occupied]
        legal = [coord for coord in legal if self.is_coord_in_range(coord, occupied)]
        if len(legal) >= 2:
            return tuple(legal[:2])

        anchor_cells = list(self.cellsplaced.values()) or [cell(0, 0, "orange")]
        seen = set(occupied)
        fallback = []
        for radius in range(1, PLACEMENT_RANGE + 1):
            for anchor in anchor_cells:
                for x in range(anchor.x - radius, anchor.x + radius + 1):
                    for y in range(anchor.y - radius, anchor.y + radius + 1):
                        if (x, y) not in seen and self.hex_distance((x, y), (anchor.x, anchor.y)) <= PLACEMENT_RANGE:
                            fallback.append((x, y))
                            seen.add((x, y))
                            if len(fallback) == 2:
                                return tuple(fallback)
        return None

    def bot_move(self):
        if not self.bot_enabled:
            raise ValueError("Bot play is disabled.")
        if self.next_color != self.bot_color:
            raise ValueError("It is not the bot's turn.")
        if self.game_over:
            raise ValueError("The game is already over.")

        self.bot.color = self.bot_color
        self.bot.movecheck = self.bot_depth
        self.bot.turnNum = str(self.ply + 1)
        self.bot.cellNum = "1"
        self.bot.themove = None
        self.search_stats = self.empty_search_stats()
        self.bot.alphabetacalls(self.bot_depth)

        move = self.bot.themove
        try:
            pair = self._normalise_pair(move)
            if any(coord in self.occupied_coords() for coord in pair):
                pair = self.fallback_bot_move()
        except (TypeError, ValueError):
            pair = self.fallback_bot_move()

        if pair is None:
            self.game_over = True
            return None
        move = self.place_pair(pair, self.bot_color, actor="bot")
        self.search_stats["moveApplied"] = True
        return move

    def evaluate_winner(self):
        self.winner = None
        for placed_cell in self.cellsplaced.values():
            placed_cell.checkcells(self.bot.by_x, self.bot.by_y, self.bot.by_z)
            if placed_cell.sixinarow:
                self.winner = placed_cell.color
                self.game_over = True
                return self.winner
        self.game_over = False
        return None

    def undo(self, steps=1):
        steps = max(1, int(steps))
        for _ in range(min(steps, len(self.history))):
            self.redo_stack.append(self.history.pop())
        self._rebuild_from_history()

    def redo(self):
        if not self.redo_stack:
            return
        move = self.redo_stack.pop()
        self.place_pair(move["cells"], move["color"], actor=move["actor"], record=False)
        self.history.append(move)

    def _rebuild_from_history(self):
        history = list(self.history)
        redo_stack = list(self.redo_stack)
        self.cellsplaced = new_board()
        self.ply = 0
        self.next_color = self.first_color
        self.winner = None
        self.game_over = False
        self.search_stats = self.empty_search_stats()
        self.bot = Reina0("0", "0", self.bot_color, self.cellsplaced, self.bot_depth, telemetry_callback=self.update_search_stats)
        for move in history:
            self.place_pair(move["cells"], move["color"], actor=move["actor"], record=False)
        self.history = history
        self.redo_stack = redo_stack

    def to_dict(self):
        self.evaluate_winner()
        cells = []
        for key, placed_cell in self.cellsplaced.items():
            placed_cell.checkcells(self.bot.by_x, self.bot.by_y, self.bot.by_z)
            cells.append({
                "key": key,
                "x": placed_cell.x,
                "y": placed_cell.y,
                "z": placed_cell.z,
                "color": placed_cell.color,
                "eval": placed_cell.eval,
                "threatcount": placed_cell.threatcount,
                "sixinarow": placed_cell.sixinarow,
                "line": max(placed_cell.preempx, placed_cell.preempy, placed_cell.preempz),
            })

        xs = [item["x"] for item in cells]
        ys = [item["y"] for item in cells]
        frontier = [{"x": x, "y": y} for x, y in sorted(self.legal_frontier())]
        return {
            "cells": cells,
            "bounds": {
                "minX": min(xs),
                "maxX": max(xs),
                "minY": min(ys),
                "maxY": max(ys),
            },
            "nextColor": self.next_color,
            "humanColor": self.human_color,
            "firstColor": self.first_color,
            "botColor": self.bot_color,
            "botDepth": self.bot_depth,
            "botEnabled": self.bot_enabled,
            "botPending": self.bot_enabled and self.next_color == self.bot_color and not self.game_over,
            "gameOver": self.game_over,
            "winner": self.winner,
            "history": list(self.history),
            "canUndo": bool(self.history),
            "canRedo": bool(self.redo_stack),
            "occupied": len(cells),
            "turn": self.ply + 1,
            "lastScore": self.bot.last_score,
            "placementRange": PLACEMENT_RANGE,
            "frontier": frontier,
            "search": dict(self.search_stats),
        }


ROOT = Path(__file__).resolve().parent
STATIC_ROOT = ROOT / "web"
GAME = HexoGame()
GAME_LOCK = threading.Lock()
BOT_THREAD = None


def bot_thread_running():
    return BOT_THREAD is not None and BOT_THREAD.is_alive()


def start_bot_thread():
    global BOT_THREAD
    if bot_thread_running():
        return False
    GAME.search_stats = {**GAME.empty_search_stats(), "running": True}

    def worker():
        try:
            with GAME_LOCK:
                GAME.bot_move()
        except Exception as exc:
            GAME.search_stats = {**GAME.empty_search_stats(), "running": False, "error": f"{type(exc).__name__}: {exc}"}

    BOT_THREAD = threading.Thread(target=worker, daemon=True)
    BOT_THREAD.start()
    return True


class HexoRequestHandler(SimpleHTTPRequestHandler):
    server_version = "HexoLocal/1.0"

    def log_message(self, format, *args):
        print(f"{self.address_string()} - {format % args}")

    def send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length == 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/state":
            with GAME_LOCK:
                self.send_json(GAME.to_dict())
            return
        if parsed.path == "/api/search":
            self.send_json({**GAME.search_stats, "threadRunning": bot_thread_running()})
            return

        path = parsed.path if parsed.path != "/" else "/index.html"
        self.serve_static(path)

    def do_POST(self):
        global GAME
        parsed = urlparse(self.path)

        try:
            payload = self.read_json()
            with GAME_LOCK:
                if parsed.path == "/api/new":
                    GAME = HexoGame(
                        human_color=payload.get("humanColor", "blue"),
                        first_color=payload.get("firstColor", "blue"),
                        bot_depth=payload.get("botDepth", 3),
                        bot_enabled=payload.get("botEnabled", True),
                    )
                    if payload.get("autoBot", True) and GAME.to_dict()["botPending"]:
                        GAME.bot_move()
                    self.send_json(GAME.to_dict())
                    return

                if parsed.path == "/api/move":
                    GAME.player_move(payload.get("cells"))
                    if payload.get("autoBot", True) and GAME.to_dict()["botPending"]:
                        GAME.bot_move()
                    self.send_json(GAME.to_dict())
                    return

                if parsed.path == "/api/bot":
                    GAME.bot_move()
                    self.send_json(GAME.to_dict())
                    return

                if parsed.path == "/api/bot/start":
                    if not GAME.to_dict()["botPending"]:
                        raise ValueError("It is not the bot's turn.")
                    start_bot_thread()
                    self.send_json({**GAME.search_stats, "threadRunning": bot_thread_running()})
                    return

                if parsed.path == "/api/undo":
                    GAME.undo(payload.get("steps", 1))
                    self.send_json(GAME.to_dict())
                    return

                if parsed.path == "/api/redo":
                    GAME.redo()
                    self.send_json(GAME.to_dict())
                    return

                if parsed.path == "/api/options":
                    GAME.configure(
                        human_color=payload.get("humanColor"),
                        first_color=payload.get("firstColor"),
                        bot_depth=payload.get("botDepth"),
                        bot_enabled=payload.get("botEnabled"),
                    )
                    self.send_json(GAME.to_dict())
                    return

            self.send_json({"error": "Unknown endpoint."}, status=404)
        except ValueError as exc:
            self.send_json({"error": str(exc)}, status=400)
        except json.JSONDecodeError:
            self.send_json({"error": "Invalid JSON."}, status=400)
        except Exception as exc:
            self.send_json({"error": f"{type(exc).__name__}: {exc}"}, status=500)

    def serve_static(self, path):
        requested = (STATIC_ROOT / unquote(path).lstrip("/")).resolve()
        try:
            requested.relative_to(STATIC_ROOT.resolve())
        except ValueError:
            self.send_error(404)
            return

        if requested.is_dir():
            requested = requested / "index.html"
        if not requested.exists() or not requested.is_file():
            self.send_error(404)
            return

        content_type = mimetypes.guess_type(requested.name)[0] or "application/octet-stream"
        body = requested.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run(host, port, open_browser=True):
    selected_port = port
    while True:
        try:
            httpd = ThreadingHTTPServer((host, selected_port), HexoRequestHandler)
            break
        except OSError:
            selected_port += 1
            if selected_port > port + 20:
                raise

    url = f"http://{host}:{selected_port}"
    print(f"HeXO local UI running at {url}")
    if open_browser:
        threading.Timer(0.6, webbrowser.open, args=(url,)).start()
    print("Press Ctrl+C to stop.")
    httpd.serve_forever()


def main():
    parser = argparse.ArgumentParser(description="Run the local HeXO browser UI.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-open", action="store_true", help="Start the server without opening a browser.")
    args = parser.parse_args()
    run(args.host, args.port, open_browser=not args.no_open)


if __name__ == "__main__":
    main()

