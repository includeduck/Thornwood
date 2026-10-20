"""Thornwood Rescue: Team Ember's strategist.

Runs the four missions of Assignment 02 and prints the Owl Cipher report
(Scroll Box 5) and nothing else.

    Chapter 1  hill climbing, random restart, simulated annealing
    Chapter 2  genetic algorithm, checked by brute force
    Chapter 3  Stone Drop: full and depth-limited minimax
    Chapter 4  fail-soft alpha-beta: Stone Drop runs and Master Hyo's tree

Standard library only. All randomness comes from rng.random() on a
random.Random(seed) instance, in exactly the order the scroll boxes describe.
"""

import math
import random

INF = math.inf


# ===========================================================================
# Data, typed exactly from the scroll boxes
# ===========================================================================

# Scroll Box 1: safety map, SAFETY_MAP[row][col], row 0 is the top row.
SAFETY_MAP = [
    [52, 58, 52, 46, 40, 46, 53, 46],
    [58, 64, 58, 52, 46, 58, 60, 53],
    [64, 70, 64, 58, 53, 60, 67, 60],
    [58, 64, 58, 53, 60, 67, 74, 67],
    [52, 58, 53, 50, 67, 74, 81, 74],
    [46, 53, 60, 67, 74, 81, 88, 81],
    [53, 60, 67, 74, 81, 88, 95, 88],
    [46, 53, 60, 67, 74, 81, 88, 81],
]

# Direction numbers 0..3: up, right, down, left.
DIRECTIONS = [(-1, 0), (0, 1), (1, 0), (0, -1)]

RESTART_STARTS = [(0, 0), (4, 0), (7, 0), (0, 4)]
SA_SEED = 2
SA_T0 = 20.0
SA_COOLING = 0.97
SA_ITERATIONS = 200
SA_TARGET = 95

# Scroll Box 2: the tools as (name, load, volume, usefulness).
TOOLS = [
    ("Kunai set", 18, 9, 36),
    ("Wire spool", 11, 8, 9),
    ("Smoke bombs", 12, 5, 10),
    ("Paper bombs", 9, 3, 32),
    ("Energy pills", 5, 7, 31),
    ("Flash tags", 5, 6, 8),
    ("Messenger scroll", 11, 3, 33),
    ("Giant shuriken", 20, 6, 27),
    ("Spare rations", 13, 6, 5),
    ("Wind shuriken", 11, 2, 35),
    ("Twin blades", 14, 6, 21),
    ("Caltrops", 15, 9, 13),
    ("Medical kit", 8, 8, 26),
    ("Grappling hook", 10, 9, 19),
    ("Binding tags", 10, 7, 38),
]
LOAD_LIMIT = 86
VOLUME_LIMIT = 44

# Generation 0, positions 0..19, bit 0 first.
GENERATION_0 = [
    "110101101111101",
    "100010101111010",
    "010111011011001",
    "000010110111000",
    "010001001010000",
    "110111110111011",
    "000011100111110",
    "111100000010000",
    "111011111111111",
    "001111100111111",
    "011001010000111",
    "000110000001011",
    "111001000111110",
    "001001000011010",
    "011001110010001",
    "011000010011110",
    "111011001000011",
    "110110010001011",
    "000001000010100",
    "001000111111000",
]

GA_SEED = 12
GA_GENERATIONS = 50
GA_CROSSOVER_RATE = 0.9
GA_REPORT_GENERATIONS = [0, 10, 20, 30, 40, 50]

# Scroll Box 3: Stone Drop starting position, top row (row 4) first.
START_BOARD_ROWS = [
    ".....",
    ".O.X.",
    "XX.O.",
    "OXOO.",
    "OXXXO",
]
ROWS = 5
COLS = 5
EMPTY = "."
MAX_PLAYER = "X"
MIN_PLAYER = "O"
DEFAULT_ORDER = [0, 1, 2, 3, 4]
MIDDLE_FIRST_ORDER = [2, 1, 3, 0, 4]
DL_DEPTH = 4
DL_TERMINAL_SCALE = 1000

# Scroll Box 4: Master Hyo's trial tree. An internal node is
# (name, [children]) and a leaf is (name, utility). Children are left to right.
HYO_TREE = ("R", [
    ("A", [
        ("A1", [
            ("A1a", [("L1", 4), ("L2", -27), ("L3", -22)]),
            ("A1b", [("L4", -28), ("L5", 16), ("L6", 13)]),
            ("A1c", [("L7", 2), ("L8", -20), ("L9", 10)]),
            ("A1d", [("L10", -15), ("L11", 17), ("L12", -4)]),
        ]),
        ("A2", [
            ("A2a", [("L13", 24), ("L14", -29), ("L15", 12)]),
            ("A2b", [("L16", -21), ("L17", -22)]),
            ("A2c", [("L18", 8), ("L19", 0)]),
        ]),
        ("A3", [
            ("A3a", [("L20", -15), ("L21", 22), ("L22", 7)]),
            ("A3b", [("L23", -29), ("L24", 17)]),
            ("A3c", [("L25", 24), ("L26", 4), ("L27", 4)]),
            ("A3d", [("L28", 2), ("L29", -28)]),
        ]),
    ]),
    ("B", [
        ("B1", [
            ("B1a", [("L30", 12), ("L31", 5), ("L32", -10)]),
            ("B1b", [("L33", 24), ("L34", 12), ("L35", -3)]),
            ("B1c", [("L36", 24), ("L37", 14), ("L38", -18)]),
            ("B1d", [("L39", 26), ("L40", 30)]),
        ]),
        ("B2", [
            ("B2a", [("L41", 30), ("L42", 9)]),
            ("B2b", [("L43", 25), ("L44", -3), ("L45", 8)]),
            ("B2c", [("L46", -21), ("L47", -27), ("L48", -24)]),
        ]),
    ]),
    ("C", [
        ("C1", [
            ("C1a", [("L49", 5), ("L50", 15), ("L51", 19)]),
            ("C1b", [("L52", -27), ("L53", -4)]),
            ("C1c", [("L54", -7), ("L55", 8)]),
        ]),
        ("C2", [
            ("C2a", [("L56", -10), ("L57", -24), ("L58", -4)]),
            ("C2b", [("L59", 30), ("L60", -4)]),
        ]),
    ]),
])
TREE_WINDOW_NODE = "B2"


# ===========================================================================
# Chapter 1: The False Summit (local search)
# ===========================================================================

def cell_value(cell):
    """Return the safety value of cell (row, col)."""
    r, c = cell
    return SAFETY_MAP[r][c]


def neighbour(cell, d):
    """Return the neighbour of cell in direction d (0 up, 1 right, 2 down,
    3 left), or None if it lies outside the map."""
    r, c = cell
    dr, dc = DIRECTIONS[d]
    nr, nc = r + dr, c + dc
    if 0 <= nr < len(SAFETY_MAP) and 0 <= nc < len(SAFETY_MAP[0]):
        return (nr, nc)
    return None


def hill_climb(start):
    """Steepest-ascent hill climbing (Scroll Box 1, Part A).

    From the current cell, move to the highest neighbour if it is strictly
    higher than the current cell. Neighbours are checked up, right, down,
    left, and a strict comparison means the first one wins a tie. Each move
    is one step. Stop when no neighbour is higher.

    Returns (final_cell, final_value, steps).
    """
    current = start
    steps = 0
    while True:
        best_cell, best_value = None, cell_value(current)
        for d in range(4):
            n = neighbour(current, d)
            if n is not None and cell_value(n) > best_value:
                best_cell, best_value = n, cell_value(n)
        if best_cell is None:
            return current, cell_value(current), steps
        current = best_cell
        steps += 1


def random_restart(starts):
    """Random-restart hill climbing (Scroll Box 1, Part B, Echo Split).

    Run hill_climb from each start cell in the given order. The best final
    value is credited to the first climb that reached it.

    Returns (best_value, best_start, total_steps).
    """
    best_value, best_start, total_steps = None, None, 0
    for start in starts:
        _, value, steps = hill_climb(start)
        total_steps += steps
        if best_value is None or value > best_value:
            best_value, best_start = value, start
    return best_value, best_start, total_steps


def simulated_annealing(seed, t0=SA_T0, cooling=SA_COOLING,
                        iterations=SA_ITERATIONS, start=(0, 0)):
    """Simulated annealing on the safety map (Scroll Box 1, Part C).

    Random draws per iteration, in order:
      1. d = int(rng.random() * 4) picks a direction.
      2. Only if the neighbour exists and delta < 0: r = rng.random(), and
         the move is accepted when r < exp(delta / T).
    A move with delta >= 0 is always accepted. Every accepted move adds 1
    to the accepted count and may raise the best value. T is multiplied by
    the cooling rate every iteration, including off-map ones.

    Returns (final_cell, final_value, best_value, accepted).
    """
    rng = random.Random(seed)
    current = start
    t = t0
    best = cell_value(current)
    accepted = 0
    for _ in range(iterations):
        d = int(rng.random() * 4)
        n = neighbour(current, d)
        if n is not None:
            delta = cell_value(n) - cell_value(current)
            if delta >= 0:
                move = True
            else:
                move = rng.random() < math.exp(delta / t)
            if move:
                current = n
                accepted += 1
                if cell_value(current) > best:
                    best = cell_value(current)
        t *= cooling
    return current, cell_value(current), best, accepted


def fate_test(seeds, target=SA_TARGET, t0=SA_T0):
    """Fate test (Scroll Box 1, Part D).

    Run simulated_annealing once per seed and count the runs whose final
    value (not best value) equals target.
    """
    return sum(1 for seed in seeds
               if simulated_annealing(seed, t0=t0)[1] == target)


# ===========================================================================
# Chapter 2: Rin's Seedcraft (genetic algorithm)
# ===========================================================================

def parse_chromosome(text):
    """Turn a bit string (bit 0 first) into a list of ints."""
    return [int(ch) for ch in text]


def chromosome_str(bits):
    """Turn a chromosome into its 15-character string, bit 0 first."""
    return "".join(str(b) for b in bits)


def fitness(bits):
    """Total usefulness of the packed tools if both the load and volume
    limits hold, otherwise 0."""
    load = volume = useful = 0
    for packed, (_, l, v, u) in zip(bits, TOOLS):
        if packed:
            load += l
            volume += v
            useful += u
    if load <= LOAD_LIMIT and volume <= VOLUME_LIMIT:
        return useful
    return 0


def rank_population(fits):
    """Return population positions ordered best-first by fitness.

    Python's sort is stable, so equal fitness keeps the lower position first.
    """
    return sorted(range(len(fits)), key=lambda i: -fits[i])


def tournament(population, fits, rng):
    """Tournament selection of size three.

    Draw three positions with int(rng.random() * size), repeats allowed.
    The highest fitness wins, and a strict comparison gives ties to the
    one drawn first. Returns the winning chromosome (not a copy).
    """
    size = len(population)
    winner = int(rng.random() * size)
    for _ in range(2):
        challenger = int(rng.random() * size)
        if fits[challenger] > fits[winner]:
            winner = challenger
    return population[winner]


def crossover(parent1, parent2, rng, rate=GA_CROSSOVER_RATE):
    """One-point crossover.

    Draw rng.random(). If it is below rate, draw cut = int(rng.random() * 14)
    + 1, and the children swap tails at the cut. Otherwise the children are
    copies of the parents and no cut is drawn. Always returns two new lists.
    """
    if rng.random() < rate:
        cut = int(rng.random() * (len(parent1) - 1)) + 1
        return (parent1[:cut] + parent2[cut:],
                parent2[:cut] + parent1[cut:])
    return parent1[:], parent2[:]


def mutate(child, rng):
    """Bit-flip mutation, in place.

    For bits 0 to 14 in order, draw rng.random() and flip the bit if the
    draw is below 1/15. One draw is made for every bit.
    """
    rate = 1 / len(child)
    for k in range(len(child)):
        if rng.random() < rate:
            child[k] = 1 - child[k]


def genetic_algorithm(generation0, seed=GA_SEED, generations=GA_GENERATIONS):
    """Genetic algorithm for the tool pouch (Scroll Box 2).

    Each generation: rank and record stats, stop after recording the last
    generation, copy ranks 1 and 2 as elites, then fill the population two
    children at a time with tournament, tournament, crossover, then mutation
    of child 1 and child 2.

    Returns a list with one (best_fitness, fitness_sum, top_chromosome)
    entry per generation 0..generations.
    """
    rng = random.Random(seed)
    population = [parse_chromosome(s) for s in generation0]
    size = len(population)
    history = []
    for gen in range(generations + 1):
        fits = [fitness(c) for c in population]
        ranked = rank_population(fits)
        history.append((fits[ranked[0]], sum(fits), population[ranked[0]][:]))
        if gen == generations:
            break
        nxt = [population[ranked[0]][:], population[ranked[1]][:]]
        while len(nxt) < size:
            parent1 = tournament(population, fits, rng)
            parent2 = tournament(population, fits, rng)
            child1, child2 = crossover(parent1, parent2, rng)
            mutate(child1, rng)
            nxt.append(child1)
            mutate(child2, rng)
            nxt.append(child2)
        population = nxt
    return history


def brute_force_optimum():
    """Exact optimum of the tool pouch by checking all 2^15 pouches.

    Mask m packs tool k when bit k of m is set. The first mask (in increasing
    order) with the highest fitness is kept.

    Returns (best_fitness, best_chromosome, number_of_optimal_pouches).
    """
    n = len(TOOLS)
    best_fit, best_bits, count = -1, None, 0
    for mask in range(1 << n):
        bits = [(mask >> k) & 1 for k in range(n)]
        f = fitness(bits)
        if f > best_fit:
            best_fit, best_bits, count = f, bits, 1
        elif f == best_fit:
            count += 1
    return best_fit, best_bits, count


# ===========================================================================
# Chapter 3: Stone Drop (minimax)
# ===========================================================================

def build_windows():
    """All four-cell lines on the 5x5 board (horizontal, vertical and both
    diagonals) as lists of (row, col). There are 28."""
    windows = []
    for r in range(ROWS):
        for c in range(COLS):
            for dr, dc in ((0, 1), (1, 0), (1, 1), (1, -1)):
                cells = [(r + i * dr, c + i * dc) for i in range(4)]
                if all(0 <= rr < ROWS and 0 <= cc < COLS for rr, cc in cells):
                    windows.append(cells)
    return windows


WINDOWS = build_windows()


class Board:
    """A Stone Drop board. grid[row][col] with row 0 at the bottom."""

    def __init__(self, rows_top_first):
        """Build the board from rows given top row first."""
        self.grid = [list(row) for row in reversed(rows_top_first)]
        self.heights = [sum(1 for r in range(ROWS) if self.grid[r][c] != EMPTY)
                        for c in range(COLS)]
        self.empty = sum(row.count(EMPTY) for row in self.grid)

    def play(self, col, player):
        """Drop player's stone into col."""
        self.grid[self.heights[col]][col] = player
        self.heights[col] += 1
        self.empty -= 1

    def undo(self, col):
        """Remove the top stone of col."""
        self.heights[col] -= 1
        self.grid[self.heights[col]][col] = EMPTY
        self.empty += 1

    def moves(self, order):
        """Columns that are not full, in the given order."""
        return [c for c in order if self.heights[c] < ROWS]

    def winner(self):
        """The player who owns a full window, or None."""
        g = self.grid
        for w in WINDOWS:
            a = g[w[0][0]][w[0][1]]
            if (a != EMPTY and a == g[w[1][0]][w[1][1]]
                    == g[w[2][0]][w[2][1]] == g[w[3][0]][w[3][1]]):
                return a
        return None

    def __str__(self):
        """The board as text, top row first."""
        return "\n".join("".join(row) for row in reversed(self.grid))


def other(player):
    """The opponent of player."""
    return MIN_PLAYER if player == MAX_PLAYER else MAX_PLAYER


def terminal_utility(board):
    """Utility of a finished game, or None if the game is not over.

    X completes four: 1 + E. O completes four: -(1 + E). Full board with
    no line of four: 0. E is the number of empty cells.
    """
    w = board.winner()
    if w == MAX_PLAYER:
        return 1 + board.empty
    if w == MIN_PLAYER:
        return -(1 + board.empty)
    if board.empty == 0:
        return 0
    return None


def evaluate(board):
    """Heuristic for unfinished positions (Scroll Box 3, Part B).

    For each of the 28 windows: k >= 1 X stones and no O adds k^2, k >= 1
    O stones and no X subtracts k^2, and anything else adds 0.
    """
    g = board.grid
    score = 0
    for w in WINDOWS:
        x = o = 0
        for r, c in w:
            if g[r][c] == MAX_PLAYER:
                x += 1
            elif g[r][c] == MIN_PLAYER:
                o += 1
        if x and not o:
            score += x * x
        elif o and not x:
            score -= o * o
    return score


def leaf_value(board, depth, stats):
    """Shared game-over and cutoff test for minimax and alpha-beta.

    A finished game counts as a leaf and returns its utility (times 1000 in
    depth-limited search). An unfinished position at depth 0 returns
    evaluate(). Otherwise returns None and the caller expands the node.
    """
    u = terminal_utility(board)
    if u is not None:
        stats["leaves"] += 1
        return u if depth is None else u * DL_TERMINAL_SCALE
    if depth == 0:
        return evaluate(board)
    return None


def minimax(board, player, order, stats, depth=None):
    """Minimax search on Stone Drop (Scroll Box 3).

    depth=None searches to the end of the game (Part A). An integer depth
    gives depth-limited search with evaluate() at depth 0 (Part B). Every
    call counts as one node. No memoization.

    Returns (value, best_move). best_move is the first column whose value
    is strictly better for the player to move than every column before it,
    or None at a leaf.
    """
    stats["nodes"] += 1
    v = leaf_value(board, depth, stats)
    if v is not None:
        return v, None
    child_depth = None if depth is None else depth - 1
    best_value, best_move = None, None
    for col in board.moves(order):
        board.play(col, player)
        value, _ = minimax(board, other(player), order, stats, child_depth)
        board.undo(col)
        if (best_move is None
                or (player == MAX_PLAYER and value > best_value)
                or (player == MIN_PLAYER and value < best_value)):
            best_value, best_move = value, col
    return best_value, best_move


# ===========================================================================
# Chapter 4: Running on Empty (alpha-beta)
# ===========================================================================

def alphabeta(board, player, alpha, beta, order, stats, depth=None):
    """Fail-soft alpha-beta search on Stone Drop (Scroll Box 4).

    MAX: v = -inf, then for each child v = max(v, child). Return v as soon
    as v >= beta, otherwise alpha = max(alpha, v). MIN is the mirror image
    with v <= alpha and beta = min(beta, v). Pruning returns v itself.
    Nodes, leaves, depth and best move follow minimax().

    Returns (value, best_move).
    """
    stats["nodes"] += 1
    v = leaf_value(board, depth, stats)
    if v is not None:
        return v, None
    child_depth = None if depth is None else depth - 1
    best_move = None
    if player == MAX_PLAYER:
        v = -INF
        for col in board.moves(order):
            board.play(col, player)
            value, _ = alphabeta(board, MIN_PLAYER, alpha, beta, order,
                                 stats, child_depth)
            board.undo(col)
            if value > v:
                v, best_move = value, col
            if v >= beta:
                return v, best_move
            alpha = max(alpha, v)
    else:
        v = INF
        for col in board.moves(order):
            board.play(col, player)
            value, _ = alphabeta(board, MAX_PLAYER, alpha, beta, order,
                                 stats, child_depth)
            board.undo(col)
            if value < v:
                v, best_move = value, col
            if v <= alpha:
                return v, best_move
            beta = min(beta, v)
    return v, best_move


def tree_alphabeta(node, is_max, alpha, beta, reverse, log):
    """Fail-soft alpha-beta on Master Hyo's tree (Scroll Box 4, Part B).

    node is (name, children) or (name, utility). Leaves are appended to
    log["leaves"] in the order they are evaluated. The (alpha, beta) window
    that TREE_WINDOW_NODE receives is stored in log["window"]. With
    reverse=True, children are visited right to left at every node.

    Returns (value, best_child_name), where best_child_name follows the
    strict-improvement best-move rule.
    """
    name, body = node
    if name == TREE_WINDOW_NODE:
        log["window"] = (alpha, beta)
    if not isinstance(body, list):
        log["leaves"].append(name)
        return body, None
    children = list(reversed(body)) if reverse else body
    best = None
    if is_max:
        v = -INF
        for child in children:
            value, _ = tree_alphabeta(child, False, alpha, beta, reverse, log)
            if value > v:
                v, best = value, child[0]
            if v >= beta:
                return v, best
            alpha = max(alpha, v)
    else:
        v = INF
        for child in children:
            value, _ = tree_alphabeta(child, True, alpha, beta, reverse, log)
            if value < v:
                v, best = value, child[0]
            if v <= alpha:
                return v, best
            beta = min(beta, v)
    return v, best


# ===========================================================================
# Owl Cipher report
# ===========================================================================

def fmt_cell(cell):
    """Format a cell as (r,c)."""
    return f"({cell[0]},{cell[1]})"


def fmt_bound(x):
    """Format an alpha or beta bound, writing infinities as -inf and inf."""
    if x == INF:
        return "inf"
    if x == -INF:
        return "-inf"
    return str(int(x))


def fmt_average(total, count):
    """Format total / count with two decimals."""
    return f"{total / count:.2f}"


def new_stats():
    """Fresh node and leaf counters."""
    return {"nodes": 0, "leaves": 0}


def run_stone_drop(search, order, depth=None):
    """Run search (minimax or alphabeta) from the starting position, X to
    move. Returns (value, move, stats)."""
    board = Board(START_BOARD_ROWS)
    stats = new_stats()
    if search is alphabeta:
        value, move = alphabeta(board, MAX_PLAYER, -INF, INF, order, stats, depth)
    else:
        value, move = minimax(board, MAX_PLAYER, order, stats, depth)
    return value, move, stats


def run_tree(reverse):
    """Run alpha-beta on Master Hyo's tree. Returns (value, move, log)."""
    log = {"leaves": [], "window": None}
    value, move = tree_alphabeta(HYO_TREE, True, -INF, INF, reverse, log)
    return value, move, log


def build_report():
    """Compute every mission and return the 36 Owl Cipher lines."""
    hc_cell, hc_value, hc_steps = hill_climb((0, 0))
    rr_value, rr_start, rr_steps = random_restart(RESTART_STARTS)
    sa_cell, sa_value, sa_best, sa_accepted = simulated_annealing(SA_SEED)
    sa_success = fate_test(range(1, 21))

    history = genetic_algorithm(GENERATION_0)
    ga_best, ga_sum, ga_bits = history[-1]
    ga_first = next(g for g, h in enumerate(history) if h[0] == ga_best)
    opt_fit, opt_bits, _ = brute_force_optimum()

    mm_value, mm_move, mm_stats = run_stone_drop(minimax, DEFAULT_ORDER)
    dl_value, dl_move, dl_stats = run_stone_drop(minimax, DEFAULT_ORDER, DL_DEPTH)
    ab_runs = [
        run_stone_drop(alphabeta, DEFAULT_ORDER),
        run_stone_drop(alphabeta, MIDDLE_FIRST_ORDER),
        run_stone_drop(alphabeta, DEFAULT_ORDER, DL_DEPTH),
    ]

    tree_value, tree_move, lr_log = run_tree(reverse=False)
    _, _, rl_log = run_tree(reverse=True)
    alpha, beta = lr_log["window"]

    lines = [
        "=== OWL CIPHER ===",
        f"HC_FINAL: {fmt_cell(hc_cell)}",
        f"HC_VALUE: {hc_value}",
        f"HC_STEPS: {hc_steps}",
        f"RR_BEST_VALUE: {rr_value}",
        f"RR_BEST_START: {fmt_cell(rr_start)}",
        f"RR_TOTAL_STEPS: {rr_steps}",
        f"SA_FINAL: {fmt_cell(sa_cell)}",
        f"SA_FINAL_VALUE: {sa_value}",
        f"SA_BEST_VALUE: {sa_best}",
        f"SA_ACCEPTED: {sa_accepted}",
        f"SA_SUCCESS_1_TO_20: {sa_success}",
        "GA_GEN_BEST: " + ",".join(str(history[g][0]) for g in GA_REPORT_GENERATIONS),
        f"GA_BEST_CHROMOSOME: {chromosome_str(ga_bits)}",
        f"GA_BEST_FITNESS: {ga_best}",
        f"GA_FIRST_GEN: {ga_first}",
        f"GA_FINAL_AVG: {fmt_average(ga_sum, len(GENERATION_0))}",
        f"OPT_FITNESS: {opt_fit}",
        f"OPT_CHROMOSOME: {chromosome_str(opt_bits)}",
        f"MM_VALUE: {mm_value}",
        f"MM_MOVE: {mm_move}",
        f"MM_NODES: {mm_stats['nodes']}",
        f"MM_LEAVES: {mm_stats['leaves']}",
        f"DL_VALUE: {dl_value}",
        f"DL_MOVE: {dl_move}",
        f"DL_NODES: {dl_stats['nodes']}",
    ]
    for label, (value, move, stats) in zip(("AB1", "AB2", "AB3"), ab_runs):
        lines.append(f"{label}: {value},{move},{stats['nodes']}")
    lines += [
        f"TREE_VALUE: {tree_value}",
        f"TREE_MOVE: {tree_move}",
        f"TREE_LR_LEAVES: {len(lr_log['leaves'])}",
        "TREE_LR_LIST: " + ",".join(lr_log["leaves"]),
        f"TREE_B2_WINDOW: ({fmt_bound(alpha)},{fmt_bound(beta)})",
        f"TREE_RL_LEAVES: {len(rl_log['leaves'])}",
        "MISSION_STATUS: " + ("SUCCESS" if mm_value > 0 else "FAILED"),
    ]
    return lines


def main():
    """Print the Owl Cipher report."""
    print("\n".join(build_report()))


if __name__ == "__main__":
    main()
