# Thornwood Rescue — Implementation Plan

Deliverables: **`thornwood.py`** (prints the 36-line Owl Cipher report and nothing else) and **`debrief.pdf`** (≤ 4 pages, answers the five Chapter 5 questions using program output as evidence).

Course mapping: Chapter 1 uses Lecture 07 (hill climbing, random restart, simulated annealing). Chapter 2 uses Lecture 08 (GA: tournament selection, elitism, one-point crossover, bit-flip mutation). Chapters 3 and 4 use Lecture 10 (minimax, cutoff test with an evaluation function, α–β pruning, move ordering).

---

## 0. Hard constraints (from Scroll Box 0 and 5). Check these before every commit.

| # | Constraint | How we honour it |
|---|---|---|
| 1 | Python ≥ 3.10, stdlib only | Import only `math`, `random`, `itertools`. No `sys`, no `numpy`. No 3.11+ syntax. |
| 2 | No hard-coded answers | Every report value comes from a function call. The data tables are typed in exactly. |
| 3 | RNG discipline | `rng = random.Random(seed)`. Only ever call `rng.random()`. Integers via `int(rng.random() * k)`. |
| 4 | Draw order is exact | Each algorithm's draw sequence is written in its docstring and tested (see §6). |
| 5 | Tie-breaks exact | Strict `>` comparisons everywhere that say "first wins". Stable sorting for GA ranking. |
| 6 | One function per algorithm, each with a docstring | See the module layout in §1. |
| 7 | < 5 min runtime | Expected to take seconds (the estimate is in §4.6). |
| 8 | Output exact | 36 lines, `KEY: value`, one space after the colon, no trailing spaces, no other prints. |

---

## 1. Module layout of `thornwood.py`

```
# ---------- DATA (typed exactly from the scroll boxes) ----------
SAFETY_MAP            8x8 list of lists, row 0 = top
DIRECTIONS            [(-1,0), (0,1), (1,0), (0,-1)]   # up, right, down, left = 0..3
TOOLS                 list of (name, load, volume, usefulness), indices 0..14
LOAD_LIMIT = 86, VOLUME_LIMIT = 44
GENERATION_0          list of 20 bit-strings, positions 0..19
START_BOARD_ROWS      ["....." , ".O.X.", "XX.O.", "OXOO.", "OXXXO"]  # top row first
HYO_TREE              nested structure (§5.1)

# ---------- Chapter 1: local search ----------
neighbour(cell, d)                    -> cell | None
hill_climb(start)                     -> (final_cell, value, steps)
random_restart(starts)                -> (best_value, best_start, total_steps)
simulated_annealing(seed, t0=20.0, cooling=0.97, iterations=200)
                                      -> (final_cell, final_value, best_value, accepted)
fate_test(seeds, target=95, t0=20.0)  -> count

# ---------- Chapter 2: GA + exact check ----------
parse_chromosome(s) / chromosome_str(bits)
fitness(bits)
rank_population(pop, fits)            -> indices ordered best-first (stable)
tournament(pop, fits, rng)            -> parent (the list object; never mutated)
crossover(p1, p2, rng)                -> (c1, c2) new lists
mutate(child, rng)                    -> in-place on the child (child is already a fresh list)
genetic_algorithm(gen0, seed=12, generations=50) -> history[gen] = (best, avg_sum, top_bits)
brute_force_optimum()                 -> (best_fitness, bits)

# ---------- Chapter 3: Stone Drop + minimax ----------
WINDOWS               generated programmatically; assert len == 28
parse_board(rows)     -> board[row][col], row 0 = bottom
winner(board)         -> 'X' | 'O' | None
empty_count(board), legal_moves(board, order)
play(board, col, p) / undo(board, col)
terminal_value(board) -> utility or None (game not over)
evaluate(board)       -> Σ k² over X-only windows − Σ k² over O-only windows
minimax(board, player, order, stats, depth=None) -> (value, best_move)

# ---------- Chapter 4: alpha-beta ----------
alphabeta(board, player, alpha, beta, order, stats, depth=None) -> (value, best_move)
tree_alphabeta(node, is_max, alpha, beta, reverse, log) -> (value, best_child_name)

# ---------- Report ----------
format helpers: fmt_cell, fmt_inf, fmt_avg
build_report() -> list[str] (36 lines)
main(): print("\n".join(build_report()))
if __name__ == "__main__": main()
```

Design choices:
- **Parameterise everything** (seed, `t0`, column order, depth, reverse). The debrief's extra runs then reuse the same functions without touching the report.
- **Counters live in a small `stats` dict** (`{"nodes": 0, "leaves": 0}`) passed by reference. No globals, so repeated runs don't leak counts into each other.
- **Debrief extras go in a separate helper script `debrief_runs.py`.** It does `import thornwood` and prints tables. This keeps `thornwood.py`'s output pure. It is not part of the submission, but the debrief should say how the extra numbers were produced.

---

## 2. Chapter 1: The False Summit

### 2.1 Grid helpers
- `value(r,c) = SAFETY_MAP[r][c]`. Cells are `(row, col)` with row 0 at the top.
- `neighbour(cell, d)` applies `DIRECTIONS[d]`. It returns `None` when the result is outside 0..7.

### 2.2 `hill_climb(start)`: Part A (steepest ascent)
```
cur = start; steps = 0
loop:
    best_cell, best_val = None, value(cur)
    for d in 0..3:
        n = neighbour(cur, d)
        if n and value(n) > best_val:      # strict: first in order wins ties
            best_cell, best_val = n, value(n)
    if best_cell is None: break
    cur = best_cell; steps += 1
return cur, value(cur), steps
```
- The tie rule falls out of using strict `>` against the running best, which starts at the *current* cell's value. A neighbour must beat the current cell and every earlier neighbour.
- Hand oracle: from (0,0) the path is (0,0) → (0,1) [right beats down on the tie] → (1,1) → (2,1)=70. That's 3 steps. All four neighbours of (2,1) are 64, a strict local maximum. Use this as the unit test and as the Q1 debrief evidence.

### 2.3 `random_restart(starts)`: Part B
- `starts = [(0,0), (4,0), (7,0), (0,4)]` in that order.
- Track `best_value` with strict `>`, so the *first* climb that reaches the max keeps the credit. Sum the steps across all four climbs.

### 2.4 `simulated_annealing(seed, t0, cooling, iterations)`: Part C
```
rng = random.Random(seed); cur = (0,0); T = t0
best = value(cur); accepted = 0
repeat iterations times:
    d = int(rng.random() * 4)
    n = neighbour(cur, d)
    if n is not None:
        delta = value(n) - value(cur)
        if delta >= 0: move = True
        else:          move = rng.random() < math.exp(delta / T)   # draw ONLY when delta < 0
        if move:
            cur = n; accepted += 1
            if value(cur) > best: best = value(cur)
    T *= cooling                       # every iteration, including off-map ones
return cur, value(cur), best, accepted
```
Pitfalls:
- Moves with Δ = 0 are accepted and **do** count toward `accepted`.
- No `r` draw happens for Δ ≥ 0 or for off-map neighbours.
- `math.exp` of a large negative number returns 0.0 and is safe. T never reaches 0 (20·0.97²⁰⁰ ≈ 0.045).
- "best" is updated only after a move. "final" is where the walk ends, which may be below "best".

### 2.5 `fate_test`: Part D
Run SA for seeds 1..20 inclusive and count runs whose **final value** (not best value) == 95.

### 2.6 Report lines
`HC_FINAL, HC_VALUE, HC_STEPS, RR_BEST_VALUE, RR_BEST_START, RR_TOTAL_STEPS, SA_FINAL, SA_FINAL_VALUE, SA_BEST_VALUE, SA_ACCEPTED, SA_SUCCESS_1_TO_20`. Cells are formatted `(r,c)` with no space.

---

## 3. Chapter 2: Rin's Seedcraft (GA + exact optimum)

### 3.1 Representation and fitness
- A chromosome is a `list[int]` of 15 bits, bit 0 = tool 0. It is printed bit 0 first: `"".join(map(str, bits))`.
- `fitness(bits)` sums load, volume and usefulness over the packed tools. It returns the usefulness if `load <= 86 and volume <= 44`, else `0`.
- Generation 0 is parsed from the 20 strings exactly. No draws.

### 3.2 Ranking
`ranked = sorted(range(20), key=lambda i: -fits[i])`. Python's sort is stable, so ties go to the lower position. Rank 1 = `ranked[0]`.

### 3.3 One generation (the exact draw order is critical)
```
history = []
pop = gen0
for g in 0..50:
    fits = [fitness(c) for c in pop]
    ranked = rank_population(pop, fits)
    history.append((fits[ranked[0]], sum(fits), pop[ranked[0]][:]))
    if g == 50: break                       # no draws after evaluating gen 50
    nxt = [pop[ranked[0]][:], pop[ranked[1]][:]]     # elitism: copies
    while len(nxt) < 20:                    # 9 rounds
        p1 = tournament(pop, fits, rng)     # 3 draws
        p2 = tournament(pop, fits, rng)     # 3 draws
        c1, c2 = crossover(p1, p2, rng)     # 1 draw, +1 cut draw if < 0.9
        mutate(c1, rng); nxt.append(c1)     # 15 draws
        mutate(c2, rng); nxt.append(c2)     # 15 draws
    pop = nxt
```
- **Tournament:** 3 draws `int(rng.random()*20)`, repeats allowed. Positions index the *current population in its stored order*, not the ranked order. The winner uses strict `>` (the first drawn wins ties).
- **Crossover:** `if rng.random() < 0.9: cut = int(rng.random()*14) + 1; c1 = p1[:cut] + p2[cut:]; c2 = p2[:cut] + p1[cut:]` else `c1, c2 = p1[:], p2[:]`.
- **Mutation:** for bit 0..14, draw and flip if `< 1/15`. Draw for **every** bit, even when no flip happens.
- **Aliasing:** elites, parents and children must be independent lists. Slicing (`[:]`) handles this. Add a unit test that mutating a child leaves the old population unchanged.
- One generation uses exactly 9 × (6 + 1 or 2 + 30) draws. A test can count draws with a wrapper RNG to confirm the sequence.

### 3.4 Report values from `history`
- `GA_GEN_BEST` = best at gens 0, 10, 20, 30, 40, 50 (comma-joined).
- `GA_BEST_CHROMOSOME`, `GA_BEST_FITNESS` = top-ranked at gen 50.
- `GA_FIRST_GEN` = smallest g with `history[g].best == GA_BEST_FITNESS`.
- `GA_FINAL_AVG` = gen-50 sum / 20, printed with 2 decimals. Since `sum/20` is a multiple of 0.05, `f"{s/20:.2f}"` is exact. A pure-integer alternative is `f"{s*5//100}.{s*5%100:02d}"`.

### 3.5 `brute_force_optimum()`: Tomo's check
- Enumerate `mask` in `range(2**15)` with `bits[k] = (mask >> k) & 1` and keep the max fitness under strict `>`.
- Also **count how many masks reach the max**. The spec assumes a unique optimum. If it isn't unique, document which tie-break we used (first in mask order) in a docstring and in the debrief.
- Optional cross-check: a 2-D 0/1 knapsack DP (load × volume). Check it agrees on the value. This goes in tests only.
- Story sanity check: the GA should land on 234 and the optimum should be 241. If our numbers differ, re-audit the draw order before anything else.

---

## 4. Chapter 3: Stone Drop (minimax)

### 4.1 Board
- `board[row][col]` holds `'X'`, `'O'` or `'.'`, with row 0 = **bottom**. Parse `START_BOARD_ROWS` by reversing (the given rows are top-first).
- Keep `heights[col]` (the next free row) for O(1) drop and undo. Mutate in place and undo after the recursive call. This is not memoization and is allowed.
- Assertions at start-up: 7 X, 7 O, 11 empty, no winner, X to move.

### 4.2 Windows (28)
Generate them; don't type them: for every cell and each direction in {(0,1), (1,0), (1,1), (1,−1)}, keep the 4-cell run if it stays on the board. That gives 10 horizontal + 10 vertical + 4 + 4 diagonal = 28. Assert `len(WINDOWS) == 28`.

### 4.3 Game-over test and utility
```
terminal_value(board):
    if X owns a full window: return  1 + E
    if O owns a full window: return -(1 + E)
    if E == 0:               return 0
    return None
```
E = number of empty cells at that moment. Only the player who just moved can have a new line, but scanning all 28 windows is simplest and fast enough. An optional optimisation is a per-cell window index that checks only windows through the last stone.

### 4.4 `minimax(board, player, order, stats, depth=None)`: one function for Parts A and B
```
stats["nodes"] += 1                          # every call is a node
u = terminal_value(board)
if u is not None:
    stats["leaves"] += 1
    return (u if depth is None else u * 1000), None
if depth == 0: return evaluate(board), None
best_val, best_move = None, None
for col in legal_moves(board, order):        # order, skipping full columns
    play(board, col, player)
    v, _ = minimax(board, other(player), order, stats, None if depth is None else depth-1)
    undo(board, col)
    if best_move is None or (player=='X' and v > best_val) or (player=='O' and v < best_val):
        best_val, best_move = v, col         # strict improvement = "first column strictly better"
return best_val, best_move
```
- The game-over test comes **before** the depth check, so a finished game at depth 0 still returns utility × 1000.
- Part A: `depth=None`, order `[0,1,2,3,4]`. Report value, move, nodes, leaves.
- Part B: `depth=4`, same order. Report value, move, nodes.
- Returning `best_move` from every node also gives the principal variation, which the Vesper debrief question needs.

### 4.5 `evaluate(board)` (Part B)
For each of the 28 windows: `x = count('X')`, `o = count('O')`. If `x ≥ 1 and o == 0` add `x²`. If `o ≥ 1 and x == 0` subtract `o²`. Otherwise add 0.

### 4.6 Feasibility
The empty cells per column are 2, 1, 3, 1, 4. The number of complete move orderings is 11!/(2!·1!·3!·1!·4!) = 138,600, and early wins cut many games short. So the full tree is at most a few hundred thousand nodes, which takes seconds in Python. No optimisation is needed beyond in-place play and undo.

### 4.7 Report lines
`MM_VALUE, MM_MOVE, MM_NODES, MM_LEAVES, DL_VALUE, DL_MOVE, DL_NODES`. Then `MISSION_STATUS = SUCCESS if MM_VALUE > 0 else FAILED`.

---

## 5. Chapter 4: Alpha-beta

### 5.1 `alphabeta(...)` for Stone Drop (fail-soft, exactly as in Scroll Box 4)
```
stats["nodes"] += 1
terminal / depth-0 handling identical to minimax
if player == 'X':                       # MAX
    v = -inf; best = None
    for col in legal_moves(board, order):
        play; cv, _ = alphabeta(child, 'O', alpha, beta, ...); undo
        if best is None or cv > v: v, best = cv, col      # v = max(v, cv) + strict best-move
        if v >= beta: return v, best                       # fail-soft: return v, not beta
        alpha = max(alpha, v)
    return v, best
else:                                   # MIN, mirror image with v <= alpha
```
- The root is an ordinary MAX node with α = −∞, β = +∞. Since β = +∞ it never cuts, so it tries every column. Any child value ≤ α is an upper bound and can never be "strictly better", so the best-move rule stays correct under fail-soft.
- Runs: AB1 = full depth, order 0..4. AB2 = full depth, order `[2,1,3,0,4]` at every node. AB3 = depth 4 with eval, order 0..4.
- Built-in invariants (tests): `AB1.value == AB2.value == MM_VALUE`, `AB3.value == DL_VALUE`, and AB node counts ≤ the minimax counts.

### 5.2 Master Hyo's tree
Representation: a nested tuple `(name, children)` for internal nodes and `(name, value)` for leaves, typed in left-to-right order:
```
HYO_TREE = ("R", [
  ("A", [("A1", [("A1a", [("L1",4),("L2",-27),("L3",-22)]), ...]), ...]),
  ("B", [...]), ("C", [...])])
```
Add a check that there are exactly 60 leaves, L1..L60 in left-to-right order.

`tree_alphabeta(node, is_max, alpha, beta, reverse, log)`:
- Leaf: `log["leaves"].append(name)` and return the value.
- If `name == "B2"`, record `log["b2_window"] = (alpha, beta)` *on entry*.
- Children are iterated `reversed(children)` when `reverse=True`.
- The same fail-soft MAX/MIN rules as above. The root tracks the best child name with the strict rule.

Outputs:
- LR run: `TREE_VALUE`, `TREE_MOVE` (A/B/C), `TREE_LR_LEAVES = len(list)`, `TREE_LR_LIST = ",".join(list)`, `TREE_B2_WINDOW`.
- RL run: `TREE_RL_LEAVES` only.
- Formatting: `fmt_inf(x)` gives `"-inf"` / `"inf"` for infinities and `str(int(x))` otherwise. That yields e.g. `(3,inf)` or `(-inf,12)` with no spaces.
- Verification: compute plain minimax on the tree and assert it equals `TREE_VALUE`. Then **trace the LR run by hand** (the spec asks for this and the debrief explains it) and diff it against the program's leaf list.

---

## 6. Testing and verification (`test_thornwood.py`, not submitted)

1. **Format test:** run `main()` with stdout captured. Expect exactly 36 lines, the key order matching Scroll Box 5, a per-line regex (`^[A-Z0-9_]+: \S.*\S$|^=== OWL CIPHER ===$`), no trailing whitespace, and nothing else printed.
2. **Determinism:** run twice and get byte-identical output.
3. **Hand oracles:** `hill_climb((0,0)) == ((2,1), 70, 3)`. The window count is 28. The starting board counts are 7/7/11.
4. **RNG audit:** wrap `random.Random` in a counting subclass. Check SA draws = 200 + (#iterations with on-map Δ<0). Check GA per-round draws = 6 + (1 or 2) + 30. Grep the source for any forbidden call (`randint`, `choice`, `shuffle`, `random.random(`).
5. **Cross-checks:** the knapsack brute force agrees with the DP. Alpha-beta values agree with minimax. The tree alpha-beta agrees with tree minimax. Root child values should show "four of five moves lose" (exactly one positive child), which the story implies.
6. **Aliasing:** mutating a GA child never changes a parent or elite.
7. **Timing:** total runtime well under 5 min. Expect < 30 s even on a slow lab PC.
8. **Python 3.10:** run under 3.10 if available (e.g. `py -3.10 thornwood.py`) and confirm the only imports are math, random and itertools.

---

## 7. Debrief helper runs (`debrief_runs.py`) → evidence for `debrief.pdf`

| Q | Who | What to compute / show |
|---|---|---|
| 1 | Kaito | The HC path from (0,0) with values. The 3×3 neighbourhood around the stuck cell (all neighbours 64 < 70). Where the global max 95 is. The low "valley" (columns 3–4, values 40–53) separating the left hill from the right ridge. Which restarts escape it and why. |
| 2 | Gennai | A table of seeds 1–20 at T₀=20 and at **T₀=40**: final cell, final value, best value, accepted count, success yes/no. The temperature schedule Tₙ = T₀·0.97ⁿ. The acceptance probability e^{Δ/T} for typical downhill steps (Δ ≈ −5…−17) at iterations 0, 25, 50, 100. The "freeze" point where T < 1 (≈ iteration 98 for T₀=20, ≈ 121 for T₀=40). Explain the trade-off: hotter means more exploration but also a chance of wandering off the summit late. Note why final ≠ best for some seeds. |
| 3 | Rin | A seed-by-seed (bit-by-bit) table of the GA's 234 pouch vs the 241 optimum, showing each tool's load, volume and usefulness, plus totals against the 86/44 limits. The Hamming distance between them, and whether any 1- or 2-bit move from 234 is feasible and better (local optimum in bit space). Population diversity per generation (unique chromosomes, per-bit allele frequency at gen 50) to show premature convergence. The fitness cliff, where infeasible = 0. **One concrete fix** with a demonstration run, e.g. a penalty or repair fitness instead of 0, a higher mutation rate, more generations or a larger population, multiple restarts, or smaller tournaments. Label demo runs as outside the Owl Cipher. |
| 4 | Vesper | The value of each of the five root columns (full minimax). For each of the four losing columns, O's winning reply line (the principal variation, from the `best_move` chain) with small board diagrams of the final position. The winning column's line for contrast. |
| 5 | Jun | A node-count table: MM, DL, AB1, AB2, AB3 with % saved vs the matching minimax. **Why middle-first barely helped:** give per-root-child node counts under both orders. Points to back with data: columns 1 and 3 have only one empty cell, so branching collapses fast. Many lines end in forced or immediate wins. The decisive moves aren't concentrated in the middle for this position. **Tree:** LR vs RL leaf counts, plus the hand trace of the LR run (α, β at each node, which subtrees were cut and why). The expected explanation, to be confirmed against the actual trace: RL meets strong values early, so it gets tight α/β bounds sooner and cuts more siblings, while LR only discovers good bounds late. |

Page budget: Q1 ½ page, Q2 ¾, Q3 ¾, Q4 1, Q5 1. Use compact tables and tiny ASCII boards. Paste the Owl Cipher output as an appendix only if space allows (4-page limit).

---

## 8. Build order / milestones

1. **Skeleton and data entry.** Constants typed from the scroll boxes, plus start-up assertions (map 8×8, 15 tools, 20 chromosomes of length 15, board counts, 60 tree leaves). Re-read each number against the PDF once. A wrong digit here silently poisons everything.
2. **Chapter 1.** HC, RR, SA, fate test, and the hand-oracle test.
3. **Chapter 2.** Fitness, brute force first (it gives the target), then the GA with draw-count tests.
4. **Chapter 3.** Board, windows, terminal test, minimax full, then depth-limited.
5. **Chapter 4.** Alpha-beta on Stone Drop (check its invariants against Chapter 3), then the Hyo tree plus a hand trace.
6. **Report.** `build_report()`, the formatters, and the format and determinism tests.
7. **Hardening.** Docstrings on every algorithm function (each states its tie-break and draw order). Remove all debug prints. Time it. Test on Python 3.10.
8. **Debrief.** `debrief_runs.py`, then write and export `debrief.pdf` (≤ 4 pages).

## 9. Known traps checklist

- [ ] GA ranking: sort the *indices* with key `-fitness` (stable, so ties go to the lower position). Never sort the population list itself.
- [ ] Tournament indexes the population in its stored order (elites at 0,1, then children), not the ranked order.
- [ ] No RNG draws after evaluating generation 50.
- [ ] SA cools on off-map iterations too. It draws `r` only for Δ < 0.
- [ ] `SA_SUCCESS` counts the **final** value = 95, not the best value.
- [ ] RR credits the **first** climb to reach the best value.
- [ ] The board is printed top-first but stored bottom-first.
- [ ] The terminal test comes before the depth-0 test. The DL utility is ×1000. E counts empties at the terminal moment.
- [ ] Node count includes the root and every terminal. Leaves = terminal positions only.
- [ ] Fail-soft returns `v`, never α/β. `-inf`/`inf` are printed as text, not `-inf.0`.
- [ ] B2's window is captured on entry, in the LR run only.
- [ ] No memoization or transposition table anywhere.
- [ ] `thornwood.py` prints exactly 36 lines. Debrief extras live in a separate script.
