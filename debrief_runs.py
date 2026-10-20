"""Evidence for debrief.pdf (Chapter 5). Not part of the Owl Cipher.

Reuses thornwood.py. Wherever extra detail is needed (paths, populations,
traces), the instrumented re-run is asserted to match thornwood.py's own
result, so the evidence cannot drift from the submitted program.

Usage:  python debrief_runs.py > debrief/evidence.txt
"""

import itertools
import math
import random
import statistics

import thornwood as tw


def heading(title):
    """Print a section heading."""
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def table(rows, header):
    """Print rows as a fixed-width text table."""
    rows = [[str(x) for x in r] for r in [header] + rows]
    widths = [max(len(r[i]) for r in rows) for i in range(len(header))]
    for k, r in enumerate(rows):
        print("  ".join(x.rjust(w) for x, w in zip(r, widths)))
        if k == 0:
            print("  ".join("-" * w for w in widths))


# ===========================================================================
# Q1 Kaito: why hill climbing got stuck
# ===========================================================================

def hill_climb_path(start):
    """hill_climb, but returning every cell visited."""
    path = [start]
    while True:
        cur = path[-1]
        best_cell, best_value = None, tw.cell_value(cur)
        for d in range(4):
            n = tw.neighbour(cur, d)
            if n is not None and tw.cell_value(n) > best_value:
                best_cell, best_value = n, tw.cell_value(n)
        if best_cell is None:
            break
        path.append(best_cell)
    assert (path[-1], tw.cell_value(path[-1]), len(path) - 1) == tw.hill_climb(start)
    return path


def print_map(marks):
    """Print the safety map; marks maps cell -> one-character tag."""
    print("        " + "".join(f"{c:>5}" for c in range(8)))
    for r in range(8):
        cells = []
        for c in range(8):
            tag = marks.get((r, c), " ")
            cells.append(f"{tag}{tw.SAFETY_MAP[r][c]:>3} ")
        print(f"  row {r} " + "".join(cells))


def q1_kaito():
    """Path, neighbourhood of the stuck cell, and the four restart climbs."""
    heading("Q1 KAITO - why did hill climbing get stuck?")
    path = hill_climb_path((0, 0))
    print("Climb from (0,0): " + " -> ".join(f"{tw.fmt_cell(p)}={tw.cell_value(p)}" for p in path))
    stuck = path[-1]
    print(f"\nStuck at {tw.fmt_cell(stuck)} = {tw.cell_value(stuck)}. Its neighbours:")
    names = ["up", "right", "down", "left"]
    for d in range(4):
        n = tw.neighbour(stuck, d)
        print(f"  {names[d]:>5} {tw.fmt_cell(n)} = {tw.cell_value(n)}"
              f"  (delta {tw.cell_value(n) - tw.cell_value(stuck):+d})")
    peak = max(((r, c) for r in range(8) for c in range(8)), key=tw.cell_value)
    print(f"\nGlobal maximum: {tw.fmt_cell(peak)} = {tw.cell_value(peak)}")
    local_maxima = [(r, c) for r in range(8) for c in range(8)
                    if all(tw.neighbour((r, c), d) is None
                           or tw.cell_value(tw.neighbour((r, c), d)) < tw.cell_value((r, c))
                           for d in range(4))]
    print("Strict local maxima on the map: "
          + ", ".join(f"{tw.fmt_cell(m)}={tw.cell_value(m)}" for m in local_maxima))

    print("\nMap ('*' = Kaito's path, 'G' = global max):")
    marks = {p: "*" for p in path}
    marks[peak] = "G"
    print_map(marks)

    # Best path from the stuck cell to the peak that never goes below a level:
    # the highest "floor" any route to the summit must cross.
    best_floor = None
    for floor in sorted({v for row in tw.SAFETY_MAP for v in row}, reverse=True):
        seen, todo = {stuck}, [stuck]
        while todo:
            cur = todo.pop()
            for d in range(4):
                n = tw.neighbour(cur, d)
                if n and n not in seen and tw.cell_value(n) >= floor:
                    seen.add(n)
                    todo.append(n)
        if peak in seen:
            best_floor = floor
            break
    print(f"\nAny route from {tw.fmt_cell(stuck)} to {tw.fmt_cell(peak)} must drop to "
          f"{best_floor} or lower (a {tw.cell_value(stuck) - best_floor}-point descent).")

    print("\nRandom restart (Echo Split):")
    rows = []
    for start in tw.RESTART_STARTS:
        p = hill_climb_path(start)
        rows.append([tw.fmt_cell(start), tw.fmt_cell(p[-1]), tw.cell_value(p[-1]), len(p) - 1,
                     " -> ".join(tw.fmt_cell(x) for x in p)])
    table(rows, ["start", "final", "value", "steps", "path"])


# ===========================================================================
# Q2 Gennai: starting heat and cooling
# ===========================================================================

def sa_trace(seed, t0=tw.SA_T0, cooling=tw.SA_COOLING, iterations=tw.SA_ITERATIONS):
    """simulated_annealing with a record of what happened. Same draws."""
    rng = random.Random(seed)
    cur, t = (0, 0), t0
    best, accepted = tw.cell_value(cur), 0
    downhill_taken = 0
    first_95 = last_95_exit = last_downhill = None
    for it in range(iterations):
        d = int(rng.random() * 4)
        n = tw.neighbour(cur, d)
        if n is not None:
            delta = tw.cell_value(n) - tw.cell_value(cur)
            move = delta >= 0 or rng.random() < math.exp(delta / t)
            if move:
                if delta < 0:
                    downhill_taken += 1
                    last_downhill = it
                    if tw.cell_value(cur) == 95:
                        last_95_exit = it
                cur = n
                accepted += 1
                best = max(best, tw.cell_value(cur))
                if tw.cell_value(cur) == 95 and first_95 is None:
                    first_95 = it
        t *= cooling
    result = (cur, tw.cell_value(cur), best, accepted)
    assert result == tw.simulated_annealing(seed, t0=t0, cooling=cooling, iterations=iterations)
    return {"final": cur, "value": tw.cell_value(cur), "best": best, "accepted": accepted,
            "downhill": downhill_taken, "first_95": first_95,
            "left_95": last_95_exit, "last_downhill": last_downhill}


def freeze_iteration(t0, cooling, delta=-7, p=0.01):
    """First iteration whose acceptance chance for delta drops below p."""
    t, it = t0, 0
    while math.exp(delta / t) >= p:
        t *= cooling
        it += 1
    return it


def q2_gennai():
    """Per-seed runs at T0=20 and T0=40, the schedule, and a sensitivity sweep."""
    heading("Q2 GENNAI - starting heat and cooling rate")
    for t0 in (20.0, 40.0):
        print(f"\nT0 = {t0:g}, cooling 0.97, 200 iterations")
        rows, ok = [], 0
        for seed in range(1, 21):
            r = sa_trace(seed, t0=t0)
            ok += r["value"] == 95
            rows.append([seed, tw.fmt_cell(r["final"]), r["value"], r["best"], r["accepted"],
                         r["downhill"], r["first_95"] if r["first_95"] is not None else "-",
                         r["left_95"] if r["left_95"] is not None else "-",
                         r["last_downhill"] if r["last_downhill"] is not None else "-",
                         "yes" if r["value"] == 95 else ""])
        table(rows, ["seed", "final", "value", "best", "acc", "downhill", "first@95",
                     "last_left95", "last_downhill", "success"])
        print(f"Successes (final value 95): {ok}/20")

    print("\nTemperature schedule T_n = T0 * 0.97^n and P(accept) = exp(delta/T):")
    rows = []
    for it in (0, 25, 50, 75, 100, 125, 150, 199):
        row = [it]
        for t0 in (20.0, 40.0):
            t = t0 * 0.97 ** it
            row += [f"{t:.2f}"] + [f"{math.exp(dl / t):.3f}" for dl in (-6, -7, -14)]
        rows.append(row)
    table(rows, ["iter", "T(20)", "p-6", "p-7", "p-14", "T(40)", "p-6", "p-7", "p-14"])
    for t0 in (20.0, 40.0):
        t1 = math.ceil(math.log(1 / t0) / math.log(0.97))
        print(f"T0={t0:g}: T < 1 from iteration {t1}; "
              f"P(accept delta=-7) < 1% from iteration {freeze_iteration(t0, 0.97)}")

    print("\nSensitivity: successes out of seeds 1..20 (final value 95)")
    t0s = (5.0, 10.0, 20.0, 30.0, 40.0, 60.0, 80.0)
    rows = []
    for cooling in (0.95, 0.97, 0.98, 0.99):
        rows.append([cooling] + [sum(sa_trace(s, t0, cooling)["value"] == 95 for s in range(1, 21))
                                 for t0 in t0s])
    table(rows, ["cooling"] + [f"T0={t:g}" for t in t0s])


# ===========================================================================
# Q3 Rin: why the GA stopped at 234
# ===========================================================================

def hamming(a, b):
    """Number of differing bits."""
    return sum(x != y for x, y in zip(a, b))


def totals(bits):
    """(load, volume, usefulness) of a chromosome, ignoring the limits."""
    return tuple(sum(t[i] for b, t in zip(bits, tw.TOOLS) if b) for i in (1, 2, 3))


def ga_run(seed=tw.GA_SEED, generations=tw.GA_GENERATIONS, mutation_rate=None,
           score=tw.fitness, repair=None):
    """genetic_algorithm with pluggable mutation rate, fitness and repair,
    also recording population diversity. With the defaults it reproduces
    thornwood.genetic_algorithm exactly (asserted in main)."""
    rng = random.Random(seed)
    pop = [tw.parse_chromosome(s) for s in tw.GENERATION_0]
    rate = mutation_rate if mutation_rate is not None else 1 / 15
    history = []
    for gen in range(generations + 1):
        fits = [score(c) for c in pop]
        ranked = tw.rank_population(fits)
        pairs = list(itertools.combinations(pop, 2))
        history.append({
            "best": fits[ranked[0]], "sum": sum(fits), "top": pop[ranked[0]][:],
            "true_top": tw.fitness(pop[ranked[0]]),
            "true_best": max(tw.fitness(c) for c in pop),
            "unique": len({tuple(c) for c in pop}),
            "diversity": sum(hamming(a, b) for a, b in pairs) / len(pairs),
            "pop": [c[:] for c in pop],
        })
        if gen == generations:
            break
        nxt = [pop[ranked[0]][:], pop[ranked[1]][:]]
        while len(nxt) < len(pop):
            p1 = tw.tournament(pop, fits, rng)
            p2 = tw.tournament(pop, fits, rng)
            c1, c2 = tw.crossover(p1, p2, rng)
            for child in (c1, c2):
                for k in range(len(child)):
                    if rng.random() < rate:
                        child[k] = 1 - child[k]
                if repair:
                    repair(child)
                nxt.append(child)
        pop = nxt
    return history


def penalty_fitness(bits, weight=3):
    """Usefulness minus weight x (load overflow + volume overflow)."""
    load, vol, use = totals(bits)
    return use - weight * (max(0, load - tw.LOAD_LIMIT) + max(0, vol - tw.VOLUME_LIMIT))


def greedy_repair(bits):
    """Drop packed tools with the worst usefulness per unit of (scaled) size
    until both limits hold. Deterministic."""
    def density(k):
        _, load, vol, use = tw.TOOLS[k]
        return use / (load / tw.LOAD_LIMIT + vol / tw.VOLUME_LIMIT)
    while True:
        load, vol, _ = totals(bits)
        if load <= tw.LOAD_LIMIT and vol <= tw.VOLUME_LIMIT:
            return
        worst = min((k for k in range(15) if bits[k]), key=lambda k: (density(k), k))
        bits[worst] = 0


def q3_rin():
    """Bit-by-bit comparison, neighbourhood of 234, diversity, and fixes."""
    heading("Q3 RIN - why did the seeds stop at 234?")
    hist = ga_run()
    ref = tw.genetic_algorithm(tw.GENERATION_0)
    assert [(h["best"], h["sum"], h["top"]) for h in hist] == ref
    ga = hist[-1]["top"]
    opt_fit, opt, _ = tw.brute_force_optimum()

    rows = []
    for k, (name, load, vol, use) in enumerate(tw.TOOLS):
        diff = "<--" if ga[k] != opt[k] else ""
        rows.append([k, name, load, vol, use, ga[k], opt[k], diff])
    table(rows, ["bit", "tool", "load", "vol", "use", "GA", "OPT", ""])
    for label, bits in (("GA ", ga), ("OPT", opt)):
        load, vol, use = totals(bits)
        print(f"{label} {tw.chromosome_str(bits)}  load {load}/{tw.LOAD_LIMIT}  "
              f"volume {vol}/{tw.VOLUME_LIMIT}  usefulness {use}")
    print(f"Hamming distance GA -> OPT: {hamming(ga, opt)}")

    print("\nEvery feasible pouch better than 234, by Hamming distance from the GA pouch:")
    by_dist = {}
    for mask in range(1 << 15):
        bits = [(mask >> k) & 1 for k in range(15)]
        f = tw.fitness(bits)
        if f > tw.fitness(ga):
            by_dist.setdefault(hamming(bits, ga), []).append((f, tw.chromosome_str(bits)))
    for dist in sorted(by_dist):
        items = sorted(by_dist[dist], reverse=True)
        print(f"  distance {dist}: {len(items)} pouch(es), best {items[0][0]} "
              f"({', '.join(s for _, s in items[:4])}{'...' if len(items) > 4 else ''})")
    single = []
    for k in range(15):
        b = ga[:]
        b[k] = 1 - b[k]
        single.append(f"bit{k}->{tw.fitness(b)}")
    print("  single-bit flips of the GA pouch: " + ", ".join(single))

    print("\nPopulation over the generations:")
    rows = [[g, hist[g]["best"], f"{hist[g]['sum'] / 20:.2f}", hist[g]["unique"],
             f"{hist[g]['diversity']:.2f}", sum(1 for c in hist[g]["pop"] if tw.fitness(c) == 0)]
            for g in (0, 5, 10, 15, 20, 30, 40, 50)]
    table(rows, ["gen", "best", "avg", "unique", "mean_hamming", "infeasible"])
    final_pop = hist[-1]["pop"]
    freq = [sum(c[k] for c in final_pop) for k in range(15)]
    print("\nGen 50: how many of the 20 chromosomes have each bit set (OPT bit in brackets):")
    print("  " + "  ".join(f"b{k}:{freq[k]}[{opt[k]}]" for k in range(15)))

    print("\nFixes: how often the GA finds 241, seeds 1..30")
    print("(metric: best feasible pouch in the last generation, scored by true fitness)")
    variants = [
        ("baseline (as specified)", {}),
        ("100 generations", {"generations": 100}),
        ("mutation 2/15", {"mutation_rate": 2 / 15}),
        ("mutation 3/15", {"mutation_rate": 3 / 15}),
        ("penalty fitness (w=3)", {"score": penalty_fitness}),
        ("penalty fitness (w=10)", {"score": lambda b: penalty_fitness(b, 10)}),
        ("greedy repair", {"repair": greedy_repair}),
        ("repair + mutation 2/15", {"repair": greedy_repair, "mutation_rate": 2 / 15}),
    ]
    rows = []
    for label, kw in variants:
        finals = [ga_run(seed=s, **kw)[-1] for s in range(1, 31)]
        hits = sum(f["true_best"] == opt_fit for f in finals)
        mean = statistics.mean(f["true_best"] for f in finals)
        rows.append([label, f"{hits}/30", f"{mean:.1f}", min(f["true_best"] for f in finals)])
    table(rows, ["variant", "found 241", "mean best", "worst"])
    print("(seed 12 baseline is the Owl Cipher run; the other rows are extra experiments)")


# ===========================================================================
# Q4 Vesper: how each losing move loses
# ===========================================================================

def principal_variation(board, player, order=tw.DEFAULT_ORDER):
    """Best play for both sides from board until the game ends.
    Returns the list of (player, column)."""
    line = []
    while tw.terminal_utility(board) is None:
        _, move = tw.minimax(board, player, order, tw.new_stats())
        line.append((player, move))
        board.play(move, player)
        player = tw.other(player)
    return line


def q4_vesper():
    """Root move values and the forced line after each move."""
    heading("Q4 VESPER - how every losing move loses")
    print("Starting position (top row first), X to move:")
    print("\n".join("  " + r for r in tw.START_BOARD_ROWS))
    for col in tw.DEFAULT_ORDER:
        board = tw.Board(tw.START_BOARD_ROWS)
        board.play(col, tw.MAX_PLAYER)
        value, _ = tw.minimax(board, tw.MIN_PLAYER, tw.DEFAULT_ORDER, tw.new_stats())
        line = [(tw.MAX_PLAYER, col)] + principal_variation(board, tw.MIN_PLAYER)
        verdict = "WIN for X" if value > 0 else ("LOSS for X" if value < 0 else "draw")
        print(f"\nX plays column {col}: value {value:+d} ({verdict})")
        print("  best play: " + " ".join(f"{p}{c}" for p, c in line))
        w = board.winner()
        print(f"  ends: {w + ' completes four' if w else 'board full, no line'} "
              f"with {board.empty} empty cells, utility {tw.terminal_utility(board):+d}")
        for r in str(board).split("\n"):
            print("    " + r)

    # Immediate threats: which O replies win at once after each X move?
    print("\nImmediate O wins available after each X move:")
    for col in tw.DEFAULT_ORDER:
        board = tw.Board(tw.START_BOARD_ROWS)
        board.play(col, tw.MAX_PLAYER)
        wins = []
        for reply in board.moves(tw.DEFAULT_ORDER):
            board.play(reply, tw.MIN_PLAYER)
            if board.winner() == tw.MIN_PLAYER:
                wins.append(reply)
            board.undo(reply)
        print(f"  after X{col}: O wins at once in column(s) {wins if wins else 'none'}")


# ===========================================================================
# Q5 Jun: node counts and move ordering
# ===========================================================================

def root_breakdown(search, order):
    """Nodes spent under each root column, and the value it returned."""
    board = tw.Board(tw.START_BOARD_ROWS)
    out = {}
    alpha = -tw.INF
    for col in board.moves(order):
        board.play(col, tw.MAX_PLAYER)
        stats = tw.new_stats()
        if search == "ab":
            v, _ = tw.alphabeta(board, tw.MIN_PLAYER, alpha, tw.INF, order, stats)
            alpha = max(alpha, v)
        else:
            v, _ = tw.minimax(board, tw.MIN_PLAYER, order, stats)
        board.undo(col)
        out[col] = (v, stats["nodes"])
    return out


def trace_tree(node, is_max, alpha, beta, reverse, depth, lines, leaves):
    """tree_alphabeta with a printed trace (same rules, same leaf order)."""
    name, body = node
    pad = "  " * depth
    if not isinstance(body, list):
        leaves.append(name)
        lines.append(f"{pad}{name} = {body}")
        return body
    kind = "MAX" if is_max else "MIN"
    lines.append(f"{pad}{name} ({kind}) window ({tw.fmt_bound(alpha)},{tw.fmt_bound(beta)})")
    children = list(reversed(body)) if reverse else body
    v = -tw.INF if is_max else tw.INF
    for i, child in enumerate(children):
        cv = trace_tree(child, not is_max, alpha, beta, reverse, depth + 1, lines, leaves)
        v = max(v, cv) if is_max else min(v, cv)
        if (is_max and v >= beta) or (not is_max and v <= alpha):
            pruned = [c[0] for c in children[i + 1:]]
            test = "v>=beta" if is_max else "v<=alpha"
            if pruned:
                lines.append(f"{pad}  -> {name} = {v}, CUT ({test}), skips {','.join(pruned)}")
            else:
                lines.append(f"{pad}  -> {name} = {v} ({test} on the last child, nothing pruned)")
            return v
        if is_max:
            alpha = max(alpha, v)
        else:
            beta = min(beta, v)
    lines.append(f"{pad}  -> {name} = {v}")
    return v


def subtree_names(node):
    """Leaf names under node."""
    name, body = node
    if not isinstance(body, list):
        return [name]
    return [n for c in body for n in subtree_names(c)]


def q5_jun():
    """Node table, move-order analysis and the trial-tree traces."""
    heading("Q5 JUN - the ki (node counts) of every method")
    mm = tw.run_stone_drop(tw.minimax, tw.DEFAULT_ORDER)
    dl = tw.run_stone_drop(tw.minimax, tw.DEFAULT_ORDER, tw.DL_DEPTH)
    ab1 = tw.run_stone_drop(tw.alphabeta, tw.DEFAULT_ORDER)
    ab2 = tw.run_stone_drop(tw.alphabeta, tw.MIDDLE_FIRST_ORDER)
    ab3 = tw.run_stone_drop(tw.alphabeta, tw.DEFAULT_ORDER, tw.DL_DEPTH)
    rows = [
        ["MM  full minimax, 01234", mm[0], mm[1], mm[2]["nodes"], mm[2]["leaves"], "-"],
        ["DL  minimax depth 4, 01234", dl[0], dl[1], dl[2]["nodes"], dl[2]["leaves"], "-"],
        ["AB1 alpha-beta full, 01234", ab1[0], ab1[1], ab1[2]["nodes"], ab1[2]["leaves"],
         f"{100 * (1 - ab1[2]['nodes'] / mm[2]['nodes']):.1f}% vs MM"],
        ["AB2 alpha-beta full, 21304", ab2[0], ab2[1], ab2[2]["nodes"], ab2[2]["leaves"],
         f"{100 * (1 - ab2[2]['nodes'] / mm[2]['nodes']):.1f}% vs MM"],
        ["AB3 alpha-beta depth 4, 01234", ab3[0], ab3[1], ab3[2]["nodes"], ab3[2]["leaves"],
         f"{100 * (1 - ab3[2]['nodes'] / dl[2]['nodes']):.1f}% vs DL"],
    ]
    table(rows, ["run", "value", "move", "nodes", "leaves", "saved"])
    print(f"AB2 vs AB1: {ab1[2]['nodes'] - ab2[2]['nodes']} fewer nodes "
          f"({100 * (1 - ab2[2]['nodes'] / ab1[2]['nodes']):.1f}%)")

    board = tw.Board(tw.START_BOARD_ROWS)
    print(f"\nEmpty cells per column at the root: "
          f"{[tw.ROWS - h for h in board.heights]} (columns 0..4)")

    print("\nNodes under each root column (value in brackets):")
    rows = []
    for col in range(5):
        row = [col]
        for search, order in (("mm", tw.DEFAULT_ORDER), ("ab", tw.DEFAULT_ORDER),
                              ("ab", tw.MIDDLE_FIRST_ORDER)):
            v, n = root_breakdown(search, order)[col]
            row.append(f"{n} [{v:+d}]")
        rows.append(row)
    table(rows, ["root col", "minimax", "AB 01234", "AB 21304"])
    print("(alpha-beta values for non-best columns are fail-soft bounds, not exact)")

    print("\nFull-depth alpha-beta under all 120 column orders:")
    counts = {}
    for order in itertools.permutations(range(5)):
        _, _, stats = tw.run_stone_drop(tw.alphabeta, list(order))
        counts[order] = stats["nodes"]
    ranked = sorted(counts.values())
    print(f"  min {ranked[0]}, median {statistics.median(ranked):.0f}, max {ranked[-1]}")
    for order in ((0, 1, 2, 3, 4), (2, 1, 3, 0, 4)):
        rank = 1 + sum(1 for c in counts.values() if c < counts[order])
        print(f"  order {''.join(map(str, order))}: {counts[order]} nodes, rank {rank}/120")
    best = sorted(counts, key=lambda o: (counts[o], o))[:5]
    print("  five cheapest orders: " + ", ".join(f"{''.join(map(str, o))}={counts[o]}" for o in best))

    heading("Q5 JUN - Master Hyo's tree: left-to-right vs right-to-left")
    for reverse in (False, True):
        lines, leaves = [], []
        value = trace_tree(tw.HYO_TREE, True, -tw.INF, tw.INF, reverse, 0, lines, leaves)
        tw_value, _, log = tw.run_tree(reverse)
        assert (value, leaves) == (tw_value, log["leaves"])
        label = "RIGHT TO LEFT" if reverse else "LEFT TO RIGHT"
        print(f"\n{label}: value {value}, {len(leaves)} leaves")
        per = {c[0]: sum(1 for n in leaves if n in set(subtree_names(c))) for c in tw.HYO_TREE[1]}
        total = {c[0]: len(subtree_names(c)) for c in tw.HYO_TREE[1]}
        print("  leaves read per root subtree: "
              + ", ".join(f"{k} {per[k]}/{total[k]}" for k in per))
        print("  " + ",".join(leaves))
        print()
        print("\n".join("  " + l for l in lines))
    root_vals = {c[0]: min_child_value(c) for c in tw.HYO_TREE[1]}
    print("\nExact minimax values of the root's children: "
          + ", ".join(f"{k}={v}" for k, v in root_vals.items()))


def min_child_value(node, is_max=False):
    """Plain minimax value of a tree node."""
    name, body = node
    if not isinstance(body, list):
        return body
    vals = [min_child_value(c, not is_max) for c in body]
    return max(vals) if is_max else min(vals)


def main():
    """Print all debrief evidence."""
    print("Thornwood debrief evidence (generated by debrief_runs.py)")
    q1_kaito()
    q2_gennai()
    q3_rin()
    q4_vesper()
    q5_jun()


if __name__ == "__main__":
    main()
