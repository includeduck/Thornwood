"""Tests for thornwood.py: data entry, algorithm rules, cross-checks, report format."""

import ast
import pathlib
import re
import shutil
import subprocess
import sys
import time

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import thornwood as tw  # noqa: E402

SOURCE = (ROOT / "thornwood.py").read_text(encoding="utf-8")

REPORT_KEYS = [
    "HC_FINAL", "HC_VALUE", "HC_STEPS", "RR_BEST_VALUE", "RR_BEST_START",
    "RR_TOTAL_STEPS", "SA_FINAL", "SA_FINAL_VALUE", "SA_BEST_VALUE",
    "SA_ACCEPTED", "SA_SUCCESS_1_TO_20", "GA_GEN_BEST", "GA_BEST_CHROMOSOME",
    "GA_BEST_FITNESS", "GA_FIRST_GEN", "GA_FINAL_AVG", "OPT_FITNESS",
    "OPT_CHROMOSOME", "MM_VALUE", "MM_MOVE", "MM_NODES", "MM_LEAVES",
    "DL_VALUE", "DL_MOVE", "DL_NODES", "AB1", "AB2", "AB3", "TREE_VALUE",
    "TREE_MOVE", "TREE_LR_LEAVES", "TREE_LR_LIST", "TREE_B2_WINDOW",
    "TREE_RL_LEAVES", "MISSION_STATUS",
]

VALUE_PATTERNS = {
    "HC_FINAL": r"\(\d,\d\)", "RR_BEST_START": r"\(\d,\d\)", "SA_FINAL": r"\(\d,\d\)",
    "GA_GEN_BEST": r"\d+(,\d+){5}",
    "GA_BEST_CHROMOSOME": r"[01]{15}", "OPT_CHROMOSOME": r"[01]{15}",
    "GA_FINAL_AVG": r"\d+\.\d{2}",
    "MM_MOVE": r"[0-4]", "DL_MOVE": r"[0-4]",
    "AB1": r"-?\d+,[0-4],\d+", "AB2": r"-?\d+,[0-4],\d+", "AB3": r"-?\d+,[0-4],\d+",
    "TREE_MOVE": r"[ABC]",
    "TREE_LR_LIST": r"L\d+(,L\d+)*",
    "TREE_B2_WINDOW": r"\((-inf|-?\d+),(inf|-?\d+)\)",
    "MISSION_STATUS": r"SUCCESS|FAILED",
}


@pytest.fixture(scope="module")
def report():
    return tw.build_report()


@pytest.fixture(scope="module")
def values(report):
    return dict(line.split(": ", 1) for line in report[1:])


class ScriptedRng:
    """Stand-in for random.Random that returns preset draws and counts them."""

    def __init__(self, draws):
        self.draws = list(draws)
        self.calls = 0

    def random(self):
        self.calls += 1
        return self.draws.pop(0)


class CountingRandom(tw.random.Random):
    """random.Random that counts calls to random()."""

    def __init__(self, seed):
        super().__init__(seed)
        self.calls = 0

    def random(self):
        self.calls += 1
        return super().random()


# --------------------------------------------------------------------------
# Report format and determinism
# --------------------------------------------------------------------------

def test_main_prints_exactly_the_report(capsys):
    tw.main()
    out = capsys.readouterr().out
    lines = out.split("\n")
    assert lines[-1] == ""            # one trailing newline from print
    lines = lines[:-1]
    assert len(lines) == 36
    assert lines[0] == "=== OWL CIPHER ==="
    assert [l.split(": ", 1)[0] for l in lines[1:]] == REPORT_KEYS
    for line in lines:
        assert line == line.rstrip()
        assert "\r" not in line
    for line in lines[1:]:
        key, value = line.split(": ", 1)
        assert not value.startswith(" ")
        assert " " not in value, line
        pattern = VALUE_PATTERNS.get(key, r"-?\d+")
        assert re.fullmatch(pattern, value), line


def test_report_is_deterministic(report):
    assert tw.build_report() == report


def test_script_runs_fast_and_matches_build_report(report):
    start = time.perf_counter()
    result = subprocess.run([sys.executable, str(ROOT / "thornwood.py")],
                            capture_output=True, text=True, check=True)
    assert time.perf_counter() - start < 60
    assert result.stderr == ""
    assert result.stdout.splitlines() == report


# --------------------------------------------------------------------------
# Assignment rules on the source itself
# --------------------------------------------------------------------------

def test_only_allowed_imports():
    tree = ast.parse(SOURCE)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module.split(".")[0])
    assert imported <= {"math", "random", "itertools"}


def test_rng_usage_is_restricted():
    tree = ast.parse(SOURCE)
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if node.value.id == "random":
                assert node.attr == "Random", f"random.{node.attr} used"
        if isinstance(node, ast.Attribute) and node.attr in {
                "randint", "choice", "shuffle", "sample", "uniform",
                "randrange", "choices", "gauss"}:
            pytest.fail(f".{node.attr} used")


def test_every_function_has_a_docstring():
    tree = ast.parse(SOURCE)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            assert ast.get_docstring(node), node.name


@pytest.mark.skipif(shutil.which("vermin") is None
                    and not (ROOT / ".thornwood_env" / "Scripts" / "vermin.exe").exists(),
                    reason="vermin not installed")
def test_compatible_with_python_3_10():
    exe = shutil.which("vermin") or str(ROOT / ".thornwood_env" / "Scripts" / "vermin.exe")
    result = subprocess.run([exe, "-t=3.10-", "--no-tips", "--violations",
                             str(ROOT / "thornwood.py")],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


# --------------------------------------------------------------------------
# Data entry
# --------------------------------------------------------------------------

def test_data_shapes():
    assert len(tw.SAFETY_MAP) == 8 and all(len(r) == 8 for r in tw.SAFETY_MAP)
    assert len(tw.TOOLS) == 15
    assert len(tw.GENERATION_0) == 20
    assert all(re.fullmatch(r"[01]{15}", c) for c in tw.GENERATION_0)
    assert len(tw.WINDOWS) == 28


def test_start_board():
    board = tw.Board(tw.START_BOARD_ROWS)
    flat = [cell for row in board.grid for cell in row]
    assert flat.count("X") == 7 and flat.count("O") == 7 and board.empty == 11
    assert board.winner() is None
    assert board.grid[0] == list("OXXXO")          # row 0 is the bottom
    assert board.heights == [3, 4, 2, 4, 1]
    for c in range(tw.COLS):                       # stones obey gravity
        column = [board.grid[r][c] for r in range(tw.ROWS)]
        assert column == sorted(column, key=lambda s: s == tw.EMPTY)


def tree_leaves(node):
    name, body = node
    if not isinstance(body, list):
        return [(name, body)]
    return [leaf for child in body for leaf in tree_leaves(child)]


def test_hyo_tree_leaves_are_l1_to_l60_in_order():
    assert [n for n, _ in tree_leaves(tw.HYO_TREE)] == [f"L{i}" for i in range(1, 61)]


# --------------------------------------------------------------------------
# Chapter 1
# --------------------------------------------------------------------------

def test_hill_climb_hand_trace():
    # (0,0) -> (0,1) [right wins the tie with down] -> (1,1) -> (2,1)
    assert tw.hill_climb((0, 0)) == ((2, 1), 70, 3)
    assert all(tw.cell_value(tw.neighbour((2, 1), d)) == 64 for d in range(4))


def test_neighbour_off_map():
    assert tw.neighbour((0, 0), 0) is None and tw.neighbour((0, 0), 3) is None
    assert tw.neighbour((7, 7), 1) is None and tw.neighbour((7, 7), 2) is None


def test_random_restart_credits_first_climb_to_best():
    results = [tw.hill_climb(s) for s in tw.RESTART_STARTS]
    best, start, total = tw.random_restart(tw.RESTART_STARTS)
    assert best == max(v for _, v, _ in results)
    first = next(i for i, (_, v, _) in enumerate(results) if v == best)
    assert start == tw.RESTART_STARTS[first]
    assert total == sum(s for _, _, s in results)


def test_sa_draw_count(monkeypatch):
    """One direction draw per iteration, plus one r draw per downhill on-map try."""
    made = []
    monkeypatch.setattr(tw.random, "Random", lambda seed: made.append(CountingRandom(seed)) or made[-1])
    tw.simulated_annealing(tw.SA_SEED)
    # Replay with an independent loop to count downhill attempts.
    real = CountingRandom(tw.SA_SEED)
    cur, t, downhill = (0, 0), tw.SA_T0, 0
    for _ in range(tw.SA_ITERATIONS):
        n = tw.neighbour(cur, int(real.random() * 4))
        if n is not None:
            delta = tw.cell_value(n) - tw.cell_value(cur)
            if delta >= 0 or real.random() < tw.math.exp(delta / t):
                cur = n
            if delta < 0:
                downhill += 1
        t *= tw.SA_COOLING
    assert made[0].calls == tw.SA_ITERATIONS + downhill == real.calls
    assert tw.simulated_annealing(tw.SA_SEED)[0] == cur


def test_sa_skipped_iterations_make_no_r_draw(monkeypatch):
    # Draw 0.0 always: direction 0 (up) from (0,0) is off the map every time.
    rng = ScriptedRng([0.0] * tw.SA_ITERATIONS)
    monkeypatch.setattr(tw.random, "Random", lambda seed: rng)
    assert tw.simulated_annealing(1) == ((0, 0), 52, 52, 0)
    assert rng.calls == tw.SA_ITERATIONS


def test_fate_test_counts_final_value():
    expected = sum(1 for s in range(1, 21) if tw.simulated_annealing(s)[1] == 95)
    assert tw.fate_test(range(1, 21)) == expected


# --------------------------------------------------------------------------
# Chapter 2
# --------------------------------------------------------------------------

def test_fitness_limits():
    assert tw.fitness([0] * 15) == 0
    assert tw.fitness([1] * 15) == 0               # over both limits
    one = [0] * 15
    one[14] = 1
    assert tw.fitness(one) == 38


def test_rank_ties_go_to_lower_position():
    assert tw.rank_population([5, 9, 9, 1, 5]) == [1, 2, 0, 4, 3]


def test_tournament_draws_three_and_first_drawn_wins_ties():
    pop = [[i] for i in range(20)]
    fits = [0] * 20
    fits[5] = fits[10] = 7
    rng = ScriptedRng([10 / 20, 5 / 20, 3 / 20])
    assert tw.tournament(pop, fits, rng) is pop[10]
    assert rng.calls == 3


def test_crossover_with_cut():
    p1, p2 = [1] * 15, [0] * 15
    rng = ScriptedRng([0.5, 3 / 14])               # crossover, cut = 3 + 1 = 4
    c1, c2 = tw.crossover(p1, p2, rng)
    assert c1 == [1] * 4 + [0] * 11 and c2 == [0] * 4 + [1] * 11
    assert rng.calls == 2
    c1[0] = 9
    assert p1 == [1] * 15


def test_crossover_without_cut_copies_parents():
    p1, p2 = [1] * 15, [0] * 15
    rng = ScriptedRng([0.9])                       # not below 0.9: no cut drawn
    c1, c2 = tw.crossover(p1, p2, rng)
    assert c1 == p1 and c2 == p2 and c1 is not p1 and c2 is not p2
    assert rng.calls == 1


def test_mutation_draws_once_per_bit():
    child = [0] * 15
    draws = [0.5] * 15
    draws[2] = 0.01
    draws[14] = 1 / 15                             # not below 1/15: no flip
    rng = ScriptedRng(draws)
    tw.mutate(child, rng)
    assert child == [0, 0, 1] + [0] * 12
    assert rng.calls == 15


def test_ga_draw_budget(monkeypatch):
    made = []
    monkeypatch.setattr(tw.random, "Random", lambda seed: made.append(CountingRandom(seed)) or made[-1])
    tw.genetic_algorithm(tw.GENERATION_0)
    rounds = tw.GA_GENERATIONS * 9
    assert rounds * 37 <= made[0].calls <= rounds * 38


def test_ga_history_is_monotone_with_elitism():
    history = tw.genetic_algorithm(tw.GENERATION_0)
    assert len(history) == tw.GA_GENERATIONS + 1
    bests = [h[0] for h in history]
    assert bests == sorted(bests)
    assert history[0][0] == max(tw.fitness(tw.parse_chromosome(c)) for c in tw.GENERATION_0)
    for best, _, bits in history:
        assert tw.fitness(bits) == best


def knapsack_dp():
    """2-D 0/1 knapsack over (load, volume), independent of brute force."""
    table = [[0] * (tw.VOLUME_LIMIT + 1) for _ in range(tw.LOAD_LIMIT + 1)]
    for _, load, vol, use in tw.TOOLS:
        for l in range(tw.LOAD_LIMIT, load - 1, -1):
            for v in range(tw.VOLUME_LIMIT, vol - 1, -1):
                table[l][v] = max(table[l][v], table[l - load][v - vol] + use)
    return table[tw.LOAD_LIMIT][tw.VOLUME_LIMIT]


def test_brute_force_matches_dp_and_is_unique():
    best, bits, count = tw.brute_force_optimum()
    assert best == knapsack_dp()
    assert tw.fitness(bits) == best
    assert count == 1


def test_story_numbers(values):
    # Chapter 2 panels: the seeds stop at 234 while 241 is possible.
    assert values["GA_BEST_FITNESS"] == "234"
    assert values["OPT_FITNESS"] == "241"


# --------------------------------------------------------------------------
# Chapters 3 and 4
# --------------------------------------------------------------------------

def test_terminal_utility_and_evaluation():
    board = tw.Board(["....."] * 4 + ["XXXX."])
    assert tw.terminal_utility(board) == 1 + 21
    board = tw.Board(["....."] * 5)
    assert tw.terminal_utility(board) is None and tw.evaluate(board) == 0
    board = tw.Board(["....."] * 4 + ["X...."])
    # X at (0,0) sits in 3 windows: horizontal, vertical, diagonal.
    assert tw.evaluate(board) == 3


def test_play_undo_restores_board():
    board = tw.Board(tw.START_BOARD_ROWS)
    before = str(board), list(board.heights), board.empty
    board.play(4, "X")
    board.undo(4)
    assert (str(board), board.heights, board.empty) == before


def test_four_of_five_moves_lose(values):
    root_values = []
    for col in tw.DEFAULT_ORDER:
        board = tw.Board(tw.START_BOARD_ROWS)
        board.play(col, tw.MAX_PLAYER)
        value, _ = tw.minimax(board, tw.MIN_PLAYER, tw.DEFAULT_ORDER, tw.new_stats())
        root_values.append(value)
    assert sum(v > 0 for v in root_values) == 1
    assert sum(v < 0 for v in root_values) == 4
    assert root_values.index(max(root_values)) == int(values["MM_MOVE"])


def test_alphabeta_agrees_with_minimax(values):
    mm = (int(values["MM_VALUE"]), int(values["MM_MOVE"]))
    dl = (int(values["DL_VALUE"]), int(values["DL_MOVE"]))
    ab1, ab2, ab3 = (tuple(map(int, values[k].split(","))) for k in ("AB1", "AB2", "AB3"))
    assert ab1[:2] == mm and ab2[:2] == mm and ab3[:2] == dl
    assert ab1[2] < int(values["MM_NODES"]) and ab2[2] < int(values["MM_NODES"])
    assert ab3[2] < int(values["DL_NODES"])
    assert values["MISSION_STATUS"] == ("SUCCESS" if mm[0] > 0 else "FAILED")


def test_middle_first_order_also_matches_minimax():
    value, _, _ = tw.run_stone_drop(tw.minimax, tw.MIDDLE_FIRST_ORDER)
    assert value == int(tw.run_stone_drop(tw.minimax, tw.DEFAULT_ORDER)[0])


def tree_minimax(node, is_max):
    name, body = node
    if not isinstance(body, list):
        return body
    vals = [tree_minimax(child, not is_max) for child in body]
    return max(vals) if is_max else min(vals)


def test_tree_alphabeta_agrees_with_plain_minimax(values):
    assert int(values["TREE_VALUE"]) == tree_minimax(tw.HYO_TREE, True)
    root_children = {c[0]: tree_minimax(c, False) for c in tw.HYO_TREE[1]}
    assert values["TREE_MOVE"] == max(root_children, key=root_children.get)
    rl_value, _, _ = tw.run_tree(reverse=True)
    assert rl_value == int(values["TREE_VALUE"])


def test_tree_lr_hand_trace(values):
    # Hand trace of the left-to-right run (see PLAN.md / debrief).
    assert values["TREE_LR_LIST"] == ",".join(
        f"L{i}" for i in [1, 2, 3, 4, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17,
                          18, 19, 20, 21, 22, 30, 31, 32, 33, 34, 35, 36, 37,
                          38, 39, 40, 41, 42, 43, 44, 46, 49, 52, 54])
    assert values["TREE_B2_WINDOW"] == "(-15,26)"
    assert values["TREE_VALUE"] == "9" and values["TREE_MOVE"] == "B"
    assert values["TREE_LR_LEAVES"] == "39"


def test_bound_formatting():
    assert tw.fmt_bound(-tw.INF) == "-inf" and tw.fmt_bound(tw.INF) == "inf"
    assert tw.fmt_bound(-15) == "-15"
    assert tw.fmt_average(2964, 20) == "148.20"
