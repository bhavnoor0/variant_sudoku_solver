# Variant Sudoku Solver

A recursive backtracking solver with constraint propagation, supporting arbitrary board sizes and multiple simultaneous constraint variants.

## Features

- **Arbitrary board sizes** — 4×4, 9×9, 16×16, or any perfect-square N×N grid
- **Standard rules** — rows, columns, and boxes
- **Anti-knight** — no two identical digits a chess knight's move apart
- **Anti-king** — no two identical digits diagonally adjacent
- **Kropki pairs** — white dots (consecutive values) and black dots (one value is double the other)
- **Constraint propagation** — candidate sets are pruned before every recursive call, so the solver rarely needs to backtrack
- **MRV heuristic** — the cell with the fewest remaining candidates is always chosen next, minimising the search tree

## Usage

```bash
# Standard 9×9
python main.py examples/standard_9x9.txt

# Anti-knight
python main.py examples/anti_knight_9x9.txt --anti-knight

# Anti-king
python main.py examples/standard_9x9.txt --anti-king

# Both
python main.py examples/anti_king_anti_knight_9x9.txt --anti-knight --anti-king

# Kropki dots defined in the file
python main.py examples/kropki_4x4.txt --kropki

# Kropki dots and anti-knight
python main.py examples/anti_knight_kropki_4x4.txt --anti-knight --kropki
```

## Puzzle file format

One row per line. Use `0` or `.` for empty cells. Values separated by spaces (or no spaces for single-digit boards).

```
# Standard 9×9 example
8 . . . . . . . .
. . 3 6 . . . . .
. 7 . . 9 . 2 . .
...
```

For Kropki dots, add a `KROPKI` section after the grid:

```
. . . .
. . . .
. . . .
. . . .

KROPKI
white 0 0 0 1    # (row=0,col=0) and (row=0,col=1) must be consecutive
black 1 0 2 0    # (row=1,col=0) and (row=2,col=0): one is double the other
```

## Python API

```python
from solver import Board, KropkiDot, solve

grid = [
    [8, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 3, 6, 0, 0, 0, 0, 0],
    # ...
]

board = Board(grid)

# Standard solve
solution = solve(board)

# With variants
solution = solve(
    board,
    anti_knight=True,
    anti_king=True,
    kropki=[
        KropkiDot(r1=0, c1=0, r2=0, c2=1, kind="white"),
        KropkiDot(r1=1, c1=2, r2=1, c2=3, kind="black"),
    ]
)

if solution:
    print(solution)
else:
    print("No solution exists.")
```

## How it works

### Constraint propagation

Before any recursive call, the solver maintains a *candidate set* for every cell — the set of values that could still legally go there. When a value is placed:

1. It is eliminated from the candidate sets of all peers (same row, column, box, and any active variant peers).
2. If a peer's candidate set is reduced to a single value (*naked single*), that value is immediately assigned and the process repeats.
3. For Kropki dots, candidate values that cannot be matched by any remaining candidate in the neighbouring cell are also eliminated.

This forward-checking step prunes the search space dramatically — many puzzles are solved by propagation alone, with zero backtracking.

### Backtracking search

When propagation stalls, the solver picks the unfilled cell with the fewest remaining candidates (**Minimum Remaining Values** heuristic) and tries each candidate in turn. Each branch gets its own copy of the candidate grid, so backtracking is a simple return.

### Supported constraints

| Constraint | Effect |
|---|---|
| Standard | Row, column, and box uniqueness |
| Anti-knight | Identical digits cannot be a chess knight's move apart |
| Anti-king | Identical digits cannot be diagonally adjacent |
| Kropki white | The two connected cells must have consecutive values (\|a−b\| = 1) |
| Kropki black | One connected cell must be exactly double the other (a = 2b or b = 2a) |

Multiple constraints are active simultaneously — the candidate grid enforces all of them at every propagation step.

## Running the tests

```bash
python tests.py
```

No external dependencies required — only the Python standard library.

## Performance

The "world's hardest" 9×9 puzzle (Arto Inkala, 2010) solves in under 0.05 seconds on a standard laptop.
