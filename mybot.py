import bisect
import random
import time
from collections import defaultdict
class cell():
    def __init__(self, x, y, color):
        # Assigned parameters, not variable to change
        self.x = x
        self.y = y
        self.z = x-y
        self.color = color
        # States of the cell, variable to change
        # States in axes (open, closed, etc.)
        self.statex = 2
        self.statey = 2
        self.statez = 2
        # Limits for search
        self.posx = 6
        self.negx = -6
        self.posy = 6
        self.negy = -6
        self.posz = 6
        self.negz = -6
        # For detection of preemptives, and gaps in preemptives
        self.preemparrayx = []
        self.preemparrayy = []
        self.preemparrayz = []
        self.gapx = 0
        self.gapy = 0
        self.gapz = 0
        self.k = -7
        # Preemptives in axes
        self.preempx = 1
        self.preempy = 1
        self.preempz = 1
        self.preempstatex = 2
        self.preempstatey = 2
        self.preempstatez = 2
        # Win condition
        self.sixinarow = False
        # Evaluation and Cleanup
        self.eval = 0
        self.dirty = True
    # Raytracing function
    def checkcells(self, by_x, by_y, by_z):
        # Evaluation
        if self.dirty == False:
            pass
        else:
            self.preemparrayx = []
            self.preemparrayy = []
            self.preemparrayz = []
            self.preemparray = []
            self.preempx = 1
            self.preempy = 1
            self.preempz = 1
            # Y axis
            for c in by_x.get(self.x, []):
                valy = c.y - self.y
                # Enemy detection
                if c.color != self.color:
                    if valy < self.posy and valy > self.negy:
                        # Reduces vision
                        if valy < 0:
                            self.negy = valy
                        elif valy > 0:
                            self.posy = valy
                        # Checks if this hex is open, closed, or dead 
                        if self.posy < 3 or self.negy > -3:
                            self.statey = 1
                        if self.posy - self.negy < 6:
                            self.statey = 0 
                # Friendly cell detection
                if c.color == self.color:
                    if valy < self.posy and valy > self.negy:
                        bisect.insort(self.preemparrayy, valy)
            # X axis
            for c in by_y.get(self.y, []):
                valxz = c.x - self.x
                if c.color != self.color:
                    if valxz < self.posx and valxz > self.negx:
                        if valxz < 0:
                            self.negx = valxz
                        elif valxz > 0:
                            self.posx = valxz
                        if self.posx < 3 or self.negx > -3:
                            self.statex = 1
                        if self.posx - self.negx < 6:
                            self.statex = 0 
                if c.color == self.color:
                    if valxz < self.posx and valxz > self.negx:
                        bisect.insort(self.preemparrayx, valxz)
            # Z axis
            for c in by_z.get(self.z, []):
                valxz = c.x - self.x
                if c.color != self.color:
                    if valxz < self.posz and valxz > self.negz:
                        if valxz < 0:
                            self.negz = valxz
                        elif valxz > 0:
                            self.posz = valxz
                        if self.posz < 3 or self.negz > -3:
                            self.statez = 1
                        if self.posz - self.negz < 6:
                            self.statez = 0
                if c.color == self.color:
                    if valxz < self.posz and valxz > self.negz:
                        bisect.insort(self.preemparrayz, valxz)
            # Detects preemptives, threats and wins
            self.threatcount = 0
            # X axis
            for i in range(-5, 1): # Evaluates the 6 absolute windows overlapping this cell
                self.preemparray = []
                if i > self.negx and i + 6 <= self.posx:
                    left = bisect.bisect_left(self.preemparrayx, i)
                    right = bisect.bisect_left(self.preemparrayx, i + 6)
                    self.preemparray = self.preemparrayx[left:right]
                    k = len(self.preemparray)
                    
                    if k > 0:
                        # Recalculate gaps for the pieces in this specific window
                        self.gapx = 0
                        k_prev = -7
                        for j in self.preemparray:
                            if k_prev != -7:
                                self.gapx += j - k_prev - 1
                            k_prev = j
                            
                        # The threat level inherits the line's open/closed state
                        if self.gapx <= abs(4-k):
                            left_bound = min(self.preemparray)
                            right_bound = max(self.preemparray)

                            # If its closed on one side:
                            if self.negx > -6 and left_bound - 2 <= self.negx: 
                                self.preempstatex = 1
                            # And on the other:
                            if self.posx < 6 and right_bound + 2 >= self.posx: 
                                self.preempstatex = 1
                        else:
                            self.preempstatex = 1
                        if k > self.preempx:
                            self.preempx = k
            # Win detection                
            if self.preempx == 6:
                if self.gapx == 0:
                    self.sixinarow = True
                    self.preempstatex = 1000000
            
            # Y axis
            for i in range(-5, 1):
                self.preemparray = []
                if i > self.negy and i + 6 <= self.posy:
                    # Window creation
                    left = bisect.bisect_left(self.preemparrayy, i)
                    right = bisect.bisect_left(self.preemparrayy, i + 6)
                    self.preemparray = self.preemparrayy[left:right]
                    k = len(self.preemparray)
                    
                    if k > 0:
                        self.gapy = 0
                        k_prev = -7
                        for j in self.preemparray:
                            if k_prev != -7:
                                self.gapy += j - k_prev - 1
                            k_prev = j
                            
                        if self.gapy <= abs(4-k):
                            left_bound = min(self.preemparray)
                            right_bound = max(self.preemparray)

                            if self.negy > -6 and left_bound - 2 <= self.negy: 
                                self.preempstatey = 1
                            if self.posy < 6 and right_bound + 2 >= self.posy: 
                                self.preempstatey = 1
                        else:
                            self.preempstatey = 1

                        if k > self.preempy:
                            self.preempy = k
                            
            if self.preempy == 6:
                if self.gapy == 0:
                    self.sixinarow = True
                    self.preempstatey = 1000000

            # Z axis
            for i in range(-5, 1):
                self.preemparray = []
                if i > self.negz and i + 6 <= self.posz:
                    left = bisect.bisect_left(self.preemparrayz, i)
                    right = bisect.bisect_left(self.preemparrayz, i + 6)
                    self.preemparray = self.preemparrayz[left:right]
                    k = len(self.preemparray)
                    
                    if k > 0:
                        self.gapz = 0
                        k_prev = -7
                        for j in self.preemparray:
                            if k_prev != -7:
                                self.gapz += j - k_prev - 1
                            k_prev = j
                            
                        if self.gapz <= abs(4-k):
                            left_bound = min(self.preemparray)
                            right_bound = max(self.preemparray)

                            if self.negz > -6 and left_bound - 2 <= self.negz: 
                                self.preempstatez = 1
                            if self.posz < 6 and right_bound + 2 >= self.posz: 
                                self.preempstatez = 1
                        else:
                            self.preempstatez = 1

                        if k > self.preempz:
                            self.preempz = k
                            
            if self.preempz == 6:
                if self.gapz == 0:
                    self.sixinarow = True
                    self.preempstatez = 1000000
            # Total threat count and eval for the cell
            self.threatcount = (self.preempstatex if self.preempx >= 4 else 0) + (self.preempstatey if self.preempy >= 4 else 0) + (self.preempstatez if self.preempz >= 4 else 0)
            self.eval = ((self.statex*self.preempx*(self.preempstatex/2) + self.statey*self.preempy*(self.preempstatey/2) + self.statez*self.preempz*(self.preempstatez/2))/6)
            self.dirty = False
        return self.eval
COLORS = ("orange", "blue")


def opposite_color(color):
    return "blue" if color == "orange" else "orange"


def new_board():
    return {"t01": cell(0, 0, "orange")}


# Defaults are kept for the original terminal game. The web UI creates its own
# HexoGame instance instead of relying on these globals.
color = "orange"
player = 2
cellsplaced = new_board()
# Turn functions
    # Adds cells so that the eval detects them
def add_to_index(bot, cell, key):
    bot.by_x.setdefault(cell.x, []).append(cell)
    bot.by_y.setdefault(cell.y, []).append(cell)
    bot.by_z.setdefault(cell.z, []).append(cell)
    bot.cell_to_key[id(cell)] = key
def remove_from_index(bot, cell):
    bot.by_x.setdefault(cell.x, []).remove(cell)
    bot.by_y.setdefault(cell.y, []).remove(cell)
    bot.by_z.setdefault(cell.z, []).remove(cell)
    del bot.cell_to_key[id(cell)]
    # Player's turn
def turn(x1, y1, x2, y2, turnNum,cellNum, bot):
    if player == 1:
        coloring = "orange" 
    else:
        coloring = "blue"
    notation = "t" + turnNum + cellNum
    c1 = cell(x1, y1, coloring)
    c2 = cell(x2, y2, coloring)
    cellsplaced.update({notation:c1})
    add_to_index(bot, c1, notation)
    cellNum = str(int(cellNum) + 1)
    notation = "t" + turnNum + cellNum
    cellsplaced.update({notation:c2})
    add_to_index(bot, c2, notation)
    mark_dirty_multiple(bot, [c1, c2], bot.by_x, bot.by_y, bot.by_z)
    # Marks cells for re-evaluation
def mark_dirty_multiple(bot, cells, by_x, by_y, by_z):
    seen = set()
    for new_cell in cells:
        for c in by_x.get(new_cell.x, []):
            if id(c) not in seen:
                c.dirty = True
                seen.add(id(c))
        for c in by_y.get(new_cell.y, []):
            if id(c) not in seen:
                c.dirty = True
                seen.add(id(c))
        for c in by_z.get(new_cell.z, []):
            if id(c) not in seen:
                c.dirty = True
                seen.add(id(c))
# Bot
class Reina0():
    def __init__ (self, turnNum, cellNum, color, position, depth, verbose=False, telemetry_callback=None):
        # Turn keys
        self.turnNum = turnNum
        self.cellNum = cellNum
        # Position
        self.hypocellsplaced = position
        self.by_x = {}
        self.by_y = {}
        self.by_z = {}
        self.cell_to_key = {}
        for key, placed_cell in position.items():
            add_to_index(self, placed_cell, key)
        # Alpha-beta tools
        self.legalcoords = []
        self.color = color
        self.themove = []
        self.last_score = None
        self.search_stats = {
            "running": False,
            "depths": [],
            "nodes": 0,
            "pv": [],
            "candidates": [],
            "elapsedMs": 0,
        }
        self.telemetry_callback = telemetry_callback
        self.verbose = verbose
        self.depth = {}
        self.movecheck = depth
        # Pre-generated cell pool
        self.cell_pool = [cell(0, 0, "") for _ in range(2000)]
        # Transposition Table
        self.transposition_table = {}
            # Zobrist Table
        self.zobrist_table = defaultdict(lambda: random.getrandbits(64))
        # Running memory of the board
        self.current_hash = 0
    # Get cells from cell pool
    def acquire_cell(self, x, y, color):
        c = self.cell_pool.pop()
        c.x = x
        c.y = y
        c.z = x - y
        c.color = color
        
        # Factory Reset of structural variables
        c.eval = 0
        c.threatcount = 0
        c.sixinarow = False
        c.dirty = True
        
        c.posx, c.negx, c.posy, c.negy, c.posz, c.negz = 6, -6, 6, -6, 6, -6
        c.statex, c.statey, c.statez = 2, 2, 2
        c.preempstatex, c.preempstatey, c.preempstatez = 2, 2, 2
        c.preempx, c.preempy, c.preempz = 1, 1, 1
        
        return c
    # Return cells to cell pool
    def release_cells(self, cells):
        for c in cells:
            self.cell_pool.append(c)
    # Legal moves
    def legalMoves(self):
        self.legalcoords = []
        seen = set()
        occupied = {(c.x, c.y) for c in self.hypocellsplaced.values()}
        
        # Last 16 pieces placed (8 turns)
        focus_cells = list(self.hypocellsplaced.values())[-16:]
        
        # Pieces in threes or higher
        for c in self.hypocellsplaced.values():
            c.checkcells(self.by_x, self.by_y, self.by_z)
            if (c.threatcount > 0 or c.preempx >= 3 or c.preempy >= 3 or c.preempz >= 3) and c not in focus_cells:
                focus_cells.append(c)
                
        # Generates 5x5 on highly relevant pieces
        for c in focus_cells:
            for x in range(c.x - 2, c.x + 3):
                for y in range(c.y - 2, c.y + 3):
                    if (x, y) not in seen and (x, y) not in occupied:
                        self.legalcoords.append((x, y))
                        seen.add((x, y))
    # Sees which cells are affected by the new cwlls placed
    def affected_cells(self, i, j):
        affected = set()
        for cell in (i, j):
            for c in self.by_x.get(cell.x, []):
                if c is not i and c is not j and id(c) in self.cell_to_key:
                    affected.add(self.cell_to_key[id(c)])
            for c in self.by_y.get(cell.y, []):
                if c is not i and c is not j and id(c) in self.cell_to_key:
                    affected.add(self.cell_to_key[id(c)])
            for c in self.by_z.get(cell.z, []):
                if c is not i and c is not j and id(c) in self.cell_to_key:
                    affected.add(self.cell_to_key[id(c)])
        return affected
    # Saves previous states
    def snapshots(self, board, affected):
        snapshot = {}
        for k in affected:
            c = board[k]
            snapshot[k] = (c.statex, c.statey, c.statez, c.posx, c.negx, c.posy, c.negy, c.posz, c.negz, c.eval, c.dirty, c.preempstatex, c.preempstatey, c.preempstatez, c.preempx, c.preempy, c.preempz, c.sixinarow, c.gapx, c.gapy, c.gapz, c.threatcount)
        return snapshot
    # Gets previous states
    def retrieve_snapshot(self, board, snapshot):
        for k, state in snapshot.items():
            c = board[k]
            (c.statex, c.statey, c.statez, c.posx, c.negx, c.posy, c.negy, c.posz, c.negz, c.eval, c.dirty, c.preempstatex, c.preempstatey, c.preempstatez, c.preempx, c.preempy, c.preempz, c.sixinarow, c.gapx, c.gapy, c.gapz, c.threatcount) = state
    # Depth 0 evaluation for tree()
    def prescore(self, i, j, board, base_eval, base_total, affected, maxplayer, base_threat_count):
        evaluation = base_total
        
        # Updates evaluations for affected cells
        for k in affected:
            evaluation -= base_eval.get(k, 0)
            board[k].checkcells(self.by_x, self.by_y, self.by_z)
            if board[k].color == self.color:
                evaluation += board[k].eval
            else:
                evaluation -= board[k].eval
                
        i.checkcells(self.by_x, self.by_y, self.by_z)
        j.checkcells(self.by_x, self.by_y, self.by_z)

        # Instant win intercept
        if i.sixinarow or j.sixinarow:
            return 10000000 if maxplayer else -10000000
        
        # Checks for enemy threats
        global_threatcount = 0
        for c in board.values():
            if c.color != i.color: # Only check enemy cells for threats
                global_threatcount = max(global_threatcount, c.threatcount)

        threatcount = min(global_threatcount, base_threat_count)
        
        # Nothing special, continue with regular evaluation
        if threatcount == 0:
            if maxplayer:
                evaluation += i.eval + j.eval
            else:
                evaluation -= (i.eval + j.eval)
            return evaluation
        else:
            # The enemy still has an active threat, prune this move
            return None
    # Branching function
    def tree(self, maxplayer, board, base_eval, base_threats, cached_keys, move_width, is_qs):
        prescores = []
        cached_moves = [] 
        
        cached_set = set(cached_keys) if cached_keys else set()
        # Currrent color it's branching with
        playercolor = "blue" if self.color == "orange" else "orange"
        current_color = self.color if maxplayer else playercolor
        
        self.legalMoves()
        # Quiescence Reactivation
        if is_qs and base_threats == 0:
            active_coords = []
            friendly_coords = []
            for c in board.values():
                if c.color == current_color:
                    if ((c.preempx >= 2 and c.statex == 2) or
                        (c.preempy >= 2 and c.statey == 2) or
                        (c.preempz >= 2 and c.statez == 2)):
                        friendly_coords.append((c.x, c.y))
            
            for lx, ly in self.legalcoords: 
                if any(abs(lx - fx) <= 2 and abs(ly - fy) <= 2 for fx, fy in friendly_coords):
                    active_coords.append((lx, ly))
        else:
            active_coords = self.legalcoords 

        base_total = sum(base_eval.values())

        # Generates threat set
        threat_threshold = 4 if is_qs else 3
        threatsx, threatsy, threatsz = set(), set(), set()
        bot_threatsx, bot_threatsy, bot_threatsz = set(), set(), set()
        
        active_enemy_color = playercolor if maxplayer else self.color
        # Tracks enemy and friendly threats
        for k, c in board.items():
            if c.color == active_enemy_color:
                if c.preempx >= threat_threshold: threatsx.add(c)
                elif c.preempy >= threat_threshold: threatsy.add(c)
                elif c.preempz >= threat_threshold: threatsz.add(c)
            elif c.color == current_color:
                if c.preempx >= 4: bot_threatsx.add(c)
                elif c.preempy >= 4: bot_threatsy.add(c)
                elif c.preempz >= 4: bot_threatsz.add(c)
        lethal_x = [t for t in threatsx if t.preempx >= 4]
        lethal_y = [t for t in threatsy if t.preempy >= 4]
        lethal_z = [t for t in threatsz if t.preempz >= 4]
        has_lethal = bool(lethal_x or lethal_y or lethal_z)
        threat_y_lines = {t.y for t in threatsx}
        threat_x_lines = {t.x for t in threatsy}
        threat_z_lines = {t.z for t in threatsz}
        
        bot_off_y_lines = {t.y for t in bot_threatsx}
        bot_off_x_lines = {t.x for t in bot_threatsy}
        bot_off_z_lines = {t.z for t in bot_threatsz}

        # Loop
        for idx, i in enumerate(active_coords):
            for j in active_coords[idx+1:]:
                fingerprint = tuple(sorted((i, j)))

                if fingerprint in cached_set:
                    cached_moves.append((0, fingerprint))
                    continue

                # Heuristic prune
                (x1, y1), (x2, y2) = fingerprint
                
                # Checks defensive and ofensive threats
                is_defensive = (y1 in threat_y_lines or y2 in threat_y_lines) or \
                               (x1 in threat_x_lines or x2 in threat_x_lines) or \
                               ((x1-y1) in threat_z_lines or (x2-y2) in threat_z_lines)
                               
                is_offensive = (y1 in bot_off_y_lines or y2 in bot_off_y_lines) or \
                               (x1 in bot_off_x_lines or x2 in bot_off_x_lines) or \
                               ((x1-y1) in bot_off_z_lines or (x2-y2) in bot_off_z_lines)

                if has_lethal and not (is_defensive or is_offensive):
                    continue

                # Normal path, evaluates cells with depth 0
                i_cell = self.acquire_cell(x1, y1, current_color)
                j_cell = self.acquire_cell(x2, y2, current_color)
                
                affected = self.affected_cells(i_cell, j_cell)
                snapshot = self.snapshots(board, affected)
                board["hypo1"] = i_cell
                board["hypo2"] = j_cell
                add_to_index(self, i_cell, "hypo1")
                add_to_index(self, j_cell, "hypo2")
                self.current_hash ^= self.zobrist_table[(i_cell.x, i_cell.y, i_cell.color)]
                self.current_hash ^= self.zobrist_table[(j_cell.x, j_cell.y, j_cell.color)]
                mark_dirty_multiple(self, [i_cell, j_cell], self.by_x, self.by_y, self.by_z)
                
                evaluation = self.prescore(i_cell, j_cell, board, base_eval, base_total, affected, maxplayer, base_threats)
                
                if evaluation is not None:
                    is_forcing = (i_cell.threatcount >= 2 or j_cell.threatcount >= 2)
                    # We pass the is_defensive flag into the tuple so we don't have to calculate it again!
                    prescores.append((evaluation, fingerprint, is_forcing, is_defensive))
                    
                remove_from_index(self, i_cell)
                remove_from_index(self, j_cell)
                del board["hypo1"]
                del board["hypo2"]
                self.retrieve_snapshot(board, snapshot)
                self.current_hash ^= self.zobrist_table[(j_cell.x, j_cell.y, j_cell.color)]
                self.current_hash ^= self.zobrist_table[(i_cell.x, i_cell.y, i_cell.color)]
                self.release_cells([i_cell, j_cell])

        # Sorting and merging
        priority = []
        forcing = []
        normal = []
        
        for score, fingerprint, is_forcing, is_defensive in prescores:
            if is_defensive:
                priority.append((score, fingerprint))
            elif is_forcing:
                forcing.append((score, fingerprint))
            else:
                normal.append((score, fingerprint))
                
        priority.sort(key=lambda x: x[0], reverse=maxplayer)
        forcing.sort(key=lambda x: x[0], reverse=maxplayer)
        normal.sort(key=lambda x: x[0], reverse=maxplayer)

        if is_qs:
            # Quiescence limited moveset
            top_moves = cached_moves + priority + forcing
        else:
            # Normal move distribution
            slots_remaining = move_width
            
            defense_cap = int(move_width * 0.5)
            take_defense = min(len(priority), defense_cap, slots_remaining)
            top_priority = priority[:take_defense]
            slots_remaining -= take_defense

            forcing_cap = int(slots_remaining * 0.5)
            take_forcing = min(len(forcing), forcing_cap, slots_remaining)
            top_forcing = forcing[:take_forcing]
            slots_remaining -= take_forcing

            top_normal = normal[:slots_remaining]
            # List of top moves
            top_moves = cached_moves + top_priority + top_forcing + top_normal

        childupdated = {}
        for score, pair_tuple in top_moves:
            childupdated[pair_tuple] = score
        # Returns list of top moves
        return childupdated
    # Alpha-beta pruning
    def alphabetaupdated(self, bot, depth, alpha, beta, on_pv=False):
        self.search_stats["nodes"] = self.search_stats.get("nodes", 0) + 1
        cached_ordered_keys = []
        state = (self.current_hash, bot)
        
        # Zobrist cache unpaching
        if state in self.transposition_table:
            stored = self.transposition_table[state]
            stored_depth = stored[0]
            stored_result = stored[1]
            stored_ordered = stored[2] if len(stored) > 2 else []

            if stored_depth >= depth:
                if self.movecheck != depth:  
                    return [stored_ordered, stored_result]
            else:
                if stored_ordered:
                    cached_ordered_keys = [item for score, item in stored_ordered]
        statictotaleval = 0
        Ordered = []
        base_eval = {}
        base_threats = 0
        forced_win = None
        # Depth 0 evaluation, quiescence search
        for i in self.hypocellsplaced:
            c = self.hypocellsplaced[i]
            c.checkcells(self.by_x, self.by_y, self.by_z)
            forced_win = None
            # Detects unblocked threats
            if c.sixinarow:
                forced_win = 10000000 if self.color == c.color else -10000000
                break
            # Evaluation
            staticeval = c.eval
            staticthreats = c.threatcount
            if self.color == c.color:
                statictotaleval += staticeval
                base_eval[i] = staticeval
            else:
                statictotaleval -= staticeval
                base_eval[i] = -staticeval
            if bot:
                if c.color != self.color:
                    base_threats = max(base_threats, staticthreats)
            else:
                if c.color == self.color:
                    base_threats = max(base_threats, staticthreats)
        if forced_win is not None:
                self.transposition_table[state] = (depth, forced_win, list(Ordered))
                return [Ordered, forced_win]
        in_quiescence = (depth <= 0)
        # Quiescence (and Stand Pat)
        if in_quiescence:
            # Hard limit to prevent infinite loops in Check Wars
            if depth < -2:
                self.transposition_table[state] = (depth, statictotaleval, list(Ordered))
                return [Ordered, statictotaleval]
                
            # If the board is quiet, we "Stand Pat" (take the static score as our baseline safety net)
            if base_threats == 0:
                Ordered.append([statictotaleval, "StandPat"])
                
                # Alpha-Beta Pruning: If our static score is already good enough to cause a cutoff, 
                # we don't even need to waste time looking for forcing moves!
                if bot:
                    if statictotaleval >= beta:
                        return [Ordered, statictotaleval]
                    alpha = max(alpha, statictotaleval)
                else:
                    if statictotaleval <= alpha:
                        return [Ordered, statictotaleval]
                    beta = min(beta, statictotaleval)
        if len(self.hypocellsplaced) == 1:
            opening_moves = [((0, -1), (1, 1)), ((-1, -1), (1, 1)), ((1, 1), (2, 2)), ((-2, 0), (1, 1)), ((-1, 1), (1, -1)), ((0, -1), (1, 0)), ((0, -1), (2, 1)), ((1, 2), (2, 2)), ((-1, 2), (0, 2)), ((2, 0), (2, 2)), ((-2, 1), (-1, 2)), ((-2, 2), (-1, 2)), ((1, 1), (2, 1)), ((2, 1), (3, 1)), ((1, -1), (2, 1)), ((-1, 1), (2, 1)), ((2, 1), (4, 2)), ((8, 0), (8, 1)), ((8, 0), (1, 1))]
            self.themove = random.choice(opening_moves)
            self.last_score = 0
            self.search_stats["pv"] = [self.format_move(self.themove)]
            self.search_stats["candidates"] = [{"score": 0, "move": self.format_move(self.themove)}]
            return
        else: 
            # Dynamic move width
            dynamic_width = max(4, int(512 / (2 ** max(1, depth))))
            # Deciding the iteration order...
            iteration_keys = []
            if cached_ordered_keys:
                if bot:
                    childupdated = self.tree(True, self.hypocellsplaced, base_eval, base_threats, cached_ordered_keys, dynamic_width, in_quiescence)
                else:
                    childupdated = self.tree(False, self.hypocellsplaced, base_eval, base_threats, cached_ordered_keys, dynamic_width, in_quiescence)
                
                # Puts cached moves first
                for k in cached_ordered_keys:
                    if k in childupdated:
                        iteration_keys.append(k)
                        
                # Appends the rest of the generated moves
                for k in childupdated.keys():
                    if k not in iteration_keys:
                        iteration_keys.append(k)
            else:
                # No cache available, use tree() instead
                if bot:
                    childupdated = self.tree(True, self.hypocellsplaced, base_eval, base_threats, None, dynamic_width, in_quiescence)
                else:
                    childupdated = self.tree(False, self.hypocellsplaced, base_eval, base_threats, None, dynamic_width, in_quiescence)
                iteration_keys = list(childupdated.keys())
        if childupdated != {}:
            if bot:
                best_item = max(childupdated, key=childupdated.get)
            else:
                best_item = None
            for move_index, item in enumerate(iteration_keys):
                (x1, y1), (x2, y2) = item
                
                # Lazy Instantiation
                current_color = self.color if bot else ( "blue" if self.color == "orange" else "orange" )
                c1 = self.acquire_cell(x1, y1, current_color)
                c2 = self.acquire_cell(x2, y2, current_color)
                snapshot = self.snapshots(self.hypocellsplaced, self.affected_cells(c1, c2))
                
                string1 = "hypo1eval" + str(depth)
                self.hypocellsplaced.update({string1: c1})
                add_to_index(self, c1, string1)
                
                string2 = "hypo2eval" + str(depth)
                self.hypocellsplaced.update({string2: c2})
                add_to_index(self, c2, string2)
                
                mark_dirty_multiple(self, [c1, c2], self.by_x, self.by_y, self.by_z)
                should_cache = on_pv and (not bot or item == best_item)
                # LMR logic
                reduction = 0
                if depth >= 4 and move_index >= 5 and not should_cache:
                    reduction = 2
                # Alpha-beta pruning
                if bot:
                    returneval = self.alphabetaupdated(False, depth - 1 - reduction, alpha, beta, on_pv=should_cache)[1]
                    if reduction > 0 and returneval > alpha:
                        returneval = self.alphabetaupdated(False, depth - 1, alpha, beta, on_pv=should_cache)[1]
                        
                    Ordered.append([returneval, item])
                    alpha = max(alpha, returneval)
                else:
                    returneval = self.alphabetaupdated(True, depth - 1 - reduction, alpha, beta, on_pv=should_cache)[1]
                    if reduction > 0 and returneval < beta:
                        returneval = self.alphabetaupdated(True, depth - 1, alpha, beta, on_pv=should_cache)[1]
                        
                    Ordered.append([returneval, item])
                    beta = min(beta, returneval)

                # Cleanup and release
                del self.hypocellsplaced[string1]
                remove_from_index(self, c1)
                del self.hypocellsplaced[string2]
                remove_from_index(self, c2)
                self.retrieve_snapshot(self.hypocellsplaced, snapshot)
                self.release_cells([c1, c2])
                # Alpha-beta cutoffs
                if beta <= alpha:
                    break
        elif in_quiescence and base_threats == 0:
            # No forcing moves found past the horizon
            pass
        # Triple threats
        elif bot:
            statictotaleval = -5000000
            self.themove = None
            return [Ordered, statictotaleval]
        else:
            statictotaleval = 5000000
            return [Ordered, statictotaleval]
                
        # Sorting
        if Ordered:
            Ordered.sort(key=lambda x: x[0], reverse=bot)
        
        # Assigning the bot's move and updating the TT
        if self.movecheck == depth:
            best_score = Ordered[0][0]
            best_key = Ordered[0][1]
            self.last_score = best_score
            self.search_stats["pv"] = [self.format_move(best_key)]
            self.search_stats["candidates"] = [
                {"score": score, "move": self.format_move(move)}
                for score, move in Ordered[:5]
            ]
            if self.verbose:
                print(best_score)
            
            self.transposition_table[state] = (depth, best_score, list(Ordered))
            self.themove = best_key 
            return self.themove
        else:
            best_score = Ordered[0][0]
            self.transposition_table[state] = (depth, best_score, list(Ordered))
            return [Ordered, best_score]
    def format_move(self, move):
        if move == "StandPat":
            return "Stand Pat"
        try:
            (x1, y1), (x2, y2) = move
            return f"({x1},{y1}) ({x2},{y2})"
        except (TypeError, ValueError):
            return str(move)

    def emit_telemetry(self):
        if self.telemetry_callback:
            self.telemetry_callback(dict(self.search_stats))

    # Calling Alphabetaupdated()
    def alphabetacalls(self, depth):
        started = time.perf_counter()
        self.search_stats = {
            "running": True,
            "depths": [],
            "nodes": 0,
            "pv": [],
            "candidates": [],
            "elapsedMs": 0,
        }
        self.emit_telemetry()
        self.current_hash = 0
        for c in self.hypocellsplaced.values():
            # State is defined by its X, Y, and Color
            state_tuple = (c.x, c.y, c.color)
            self.current_hash ^= self.zobrist_table[state_tuple]
        for i in range(depth):
            dturn = i + 1
            depth_started = time.perf_counter()
            nodes_before = self.search_stats["nodes"]
            self.alphabetaupdated(True, dturn, float("-inf"), float("inf"))
            depth_time = time.perf_counter() - depth_started
            self.search_stats["elapsedMs"] = int((time.perf_counter() - started) * 1000)
            self.search_stats["depths"].append({
                "depth": dturn,
                "timeMs": int(depth_time * 1000),
                "nodes": self.search_stats["nodes"] - nodes_before,
                "score": self.last_score,
                "pv": list(self.search_stats.get("pv", [])),
            })
            self.emit_telemetry()
        self.search_stats["running"] = False
        self.search_stats["elapsedMs"] = int((time.perf_counter() - started) * 1000)
        self.emit_telemetry()
    # The bot's turn
    def boturn(self):
        notation = "bot: " + self.turnNum + self.cellNum
        c1 = cell(self.themove[0][0], self.themove[0][1], self.color)
        c2 = cell(self.themove[1][0], self.themove[1][1], self.color)
        self.hypocellsplaced.update({notation:c1})
        add_to_index(self, c1, notation)
        self.cellNum = str(int(self.cellNum) + 1)
        notation = "bot: " + self.turnNum + self.cellNum
        self.hypocellsplaced.update({notation:c2})
        add_to_index(self, c2, notation)
        if self.verbose:
            print(self.themove[0][0], self.themove[0][1], self.themove[1][0], self.themove[1][1])
        mark_dirty_multiple(self, [c1, c2], self.by_x, self.by_y, self.by_z)

