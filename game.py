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
MODES = ("human-ai", "human-human", "ai-ai")
DEFAULT_SIDE_SETTINGS = {
    "blue": {"depth": 3, "timeMs": 0},
    "orange": {"depth": 3, "timeMs": 0},
}


class HexoGame:
    def __init__(
        self,
        mode="human-ai",
        human_color="blue",
        first_color="blue",
        blue_depth=3,
        orange_depth=3,
        blue_time_ms=0,
        orange_time_ms=0,
        ponder=False,
    ):
        self.mode = mode if mode in MODES else "human-ai"
        self.human_color = human_color if human_color in COLORS else "blue"
        self.first_color = first_color if first_color in COLORS else "blue"
        self.ponder = bool(ponder)
        self.side_settings = {
            "blue": {
                "depth": self._clean_depth(blue_depth),
                "timeMs": self._clean_time_ms(blue_time_ms),
            },
            "orange": {
                "depth": self._clean_depth(orange_depth),
                "timeMs": self._clean_time_ms(orange_time_ms),
            },
        }
        self.search_stats = self.empty_search_stats()
        self.reset()

    def _clean_depth(self, depth):
        try:
            depth = int(depth)
        except (TypeError, ValueError):
            depth = 3
        return max(1, min(depth, 8))

    def _clean_time_ms(self, value):
        try:
            value = int(value)
        except (TypeError, ValueError):
            value = 0
        return max(0, min(value, 300000))

    def empty_search_stats(self):
        return {
            "running": False,
            "kind": "idle",
            "side": None,
            "depths": [],
            "nodes": 0,
            "pv": [],
            "candidates": [],
            "elapsedMs": 0,
            "moveApplied": False,
            "error": None,
        }

    def update_search_stats(self, stats):
        self.search_stats = {**self.empty_search_stats(), **self.search_stats, **stats}

    def reset(self):
        self.cellsplaced = new_board()
        self.ply = 0
        self.next_color = self.first_color
        self.history = []
        self.redo_stack = []
        self.winner = None
        self.game_over = False
        self.search_stats = self.empty_search_stats()
        self.bot = Reina0("0", "0", self.next_color, self.cellsplaced, self.side_settings[self.next_color]["depth"], telemetry_callback=self.update_search_stats)
        self.evaluate_winner()

    def configure(
        self,
        mode=None,
        human_color=None,
        first_color=None,
        blue_depth=None,
        orange_depth=None,
        blue_time_ms=None,
        orange_time_ms=None,
        ponder=None,
    ):
        if mode in MODES:
            self.mode = mode
        if human_color in COLORS:
            self.human_color = human_color
        if first_color in COLORS:
            self.first_color = first_color
        if blue_depth is not None:
            self.side_settings["blue"]["depth"] = self._clean_depth(blue_depth)
        if orange_depth is not None:
            self.side_settings["orange"]["depth"] = self._clean_depth(orange_depth)
        if blue_time_ms is not None:
            self.side_settings["blue"]["timeMs"] = self._clean_time_ms(blue_time_ms)
        if orange_time_ms is not None:
            self.side_settings["orange"]["timeMs"] = self._clean_time_ms(orange_time_ms)
        if ponder is not None:
            self.ponder = bool(ponder)

    def ai_sides(self):
        if self.mode == "ai-ai":
            return ["blue", "orange"]
        if self.mode == "human-ai":
            return [opposite_color(self.human_color)]
        return []

    def is_ai_turn(self):
        return self.next_color in self.ai_sides() and not self.game_over

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
        if self.is_ai_turn():
            raise ValueError("It is an AI turn.")
        actor = self.next_color
        if self.mode == "human-ai":
            actor = "you"
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

    def prepare_bot(self, side, kind):
        settings = self.side_settings[side]
        self.bot.color = side
        self.bot.movecheck = settings["depth"]
        self.bot.turnNum = str(self.ply + 1)
        self.bot.cellNum = "1"
        self.bot.themove = None
        self.search_stats = {
            **self.empty_search_stats(),
            "running": True,
            "kind": kind,
            "side": side,
        }
        return settings

    def run_search(self, side=None, kind="analysis"):
        side = side or self.next_color
        settings = self.prepare_bot(side, kind)
        self.bot.alphabetacalls(settings["depth"], settings["timeMs"])
        self.search_stats = {
            **self.search_stats,
            "running": False,
            "kind": kind,
            "side": side,
        }
        return self.bot.themove

    def bot_move(self):
        if not self.is_ai_turn():
            raise ValueError("It is not an AI turn.")
        side = self.next_color
        move = self.run_search(side, kind="move")
        try:
            pair = self._normalise_pair(move)
            if any(coord in self.occupied_coords() for coord in pair):
                pair = self.fallback_bot_move()
            if any(not self.is_coord_in_range(coord) for coord in pair):
                pair = self.fallback_bot_move()
        except (TypeError, ValueError):
            pair = self.fallback_bot_move()

        if pair is None:
            self.game_over = True
            return None
        move_record = self.place_pair(pair, side, actor=f"{side} ai")
        self.search_stats["moveApplied"] = True
        return move_record

    def analyze(self, side=None):
        if self.game_over:
            raise ValueError("The game is already over.")
        return self.run_search(side or self.next_color, kind="analysis")

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
        self.bot = Reina0("0", "0", self.next_color, self.cellsplaced, self.side_settings[self.next_color]["depth"], telemetry_callback=self.update_search_stats)
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
            "mode": self.mode,
            "nextColor": self.next_color,
            "humanColor": self.human_color,
            "firstColor": self.first_color,
            "aiSides": self.ai_sides(),
            "sideSettings": self.side_settings,
            "ponder": self.ponder,
            "botPending": self.is_ai_turn(),
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
SEARCH_THREAD = None


def search_thread_running():
    return SEARCH_THREAD is not None and SEARCH_THREAD.is_alive()


def start_search_thread(kind):
    global SEARCH_THREAD
    if search_thread_running():
        return False

    side = GAME.next_color
    GAME.search_stats = {
        **GAME.empty_search_stats(),
        "running": True,
        "kind": kind,
        "side": side,
    }

    def worker():
        try:
            with GAME_LOCK:
                if kind == "move":
                    GAME.bot_move()
                else:
                    GAME.analyze(side)
        except Exception as exc:
            GAME.search_stats = {**GAME.empty_search_stats(), "running": False, "kind": kind, "side": side, "error": f"{type(exc).__name__}: {exc}"}

    SEARCH_THREAD = threading.Thread(target=worker, daemon=True)
    SEARCH_THREAD.start()
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
            self.send_json({**GAME.search_stats, "threadRunning": search_thread_running()})
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
                        mode=payload.get("mode", "human-ai"),
                        human_color=payload.get("humanColor", "blue"),
                        first_color=payload.get("firstColor", "blue"),
                        blue_depth=payload.get("blueDepth", 3),
                        orange_depth=payload.get("orangeDepth", 3),
                        blue_time_ms=payload.get("blueTimeMs", 0),
                        orange_time_ms=payload.get("orangeTimeMs", 0),
                        ponder=payload.get("ponder", False),
                    )
                    self.send_json(GAME.to_dict())
                    return

                if parsed.path == "/api/move":
                    GAME.player_move(payload.get("cells"))
                    self.send_json(GAME.to_dict())
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
                        mode=payload.get("mode"),
                        human_color=payload.get("humanColor"),
                        first_color=payload.get("firstColor"),
                        blue_depth=payload.get("blueDepth"),
                        orange_depth=payload.get("orangeDepth"),
                        blue_time_ms=payload.get("blueTimeMs"),
                        orange_time_ms=payload.get("orangeTimeMs"),
                        ponder=payload.get("ponder"),
                    )
                    self.send_json(GAME.to_dict())
                    return

            if parsed.path == "/api/bot/start":
                if not GAME.to_dict()["botPending"]:
                    raise ValueError("It is not an AI turn.")
                start_search_thread("move")
                self.send_json({**GAME.search_stats, "threadRunning": search_thread_running()})
                return

            if parsed.path == "/api/analyze/start":
                if GAME.to_dict()["gameOver"]:
                    raise ValueError("The game is already over.")
                start_search_thread("analysis")
                self.send_json({**GAME.search_stats, "threadRunning": search_thread_running()})
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
