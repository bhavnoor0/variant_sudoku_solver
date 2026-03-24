"""
Command-line interface for the Variant Sudoku Solver.

Usage examples
--------------
Solve a standard 9×9 puzzle from a file:
    python main.py examples/standard_9x9.txt

Solve with anti-knight and anti-king constraints:
    python main.py examples/standard_9x9.txt --anti-knight --anti-king

Solve with Kropki dots defined in the puzzle file:
    python main.py examples/kropki_9x9.txt --kropki

Solve a 4×4 puzzle:
    python main.py examples/standard_4x4.txt

Puzzle file format
------------------
One row per line. Use 0 or '.' for empty cells.
Values separated by whitespace (or nothing for single-digit boards).

For Kropki dots, add a section after the grid:
    KROPKI
    white 0 1 0 2    # white dot between (row=0,col=1) and (row=0,col=2)
    black 3 3 3 4    # black dot between (row=3,col=3) and (row=3,col=4)
"""

import argparse
import sys
import time

from solver import Board, KropkiDot, solve


def parse_puzzle_file(path: str) -> tuple[Board, list[KropkiDot]]:
    with open(path) as f:
        lines = [l.rstrip() for l in f if l.strip() and not l.startswith("#")]

    kropki_dots: list[KropkiDot] = []
    grid_lines: list[str] = []
    in_kropki = False

    for line in lines:
        if line.strip().upper() == "KROPKI":
            in_kropki = True
            continue
        if in_kropki:
            parts = line.split()
            if len(parts) != 5:
                raise ValueError(f"Bad Kropki line: {line!r}")
            kind, r1, c1, r2, c2 = parts[0], int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4])
            if kind not in ("white", "black"):
                raise ValueError(f"Kropki kind must be 'white' or 'black', got {kind!r}")
            kropki_dots.append(KropkiDot(r1, c1, r2, c2, kind))
        else:
            grid_lines.append(line)

    grid: list[list[int]] = []
    for line in grid_lines:
        # Support both spaced ("1 2 3") and compact ("123") formats
        if " " in line or "\t" in line:
            tokens = line.split()
        else:
            tokens = list(line)
        row: list[int] = []
        for t in tokens:
            if t in (".", "0"):
                row.append(0)
            else:
                row.append(int(t))
        grid.append(row)

    return Board(grid), kropki_dots


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Variant Sudoku Solver — recursive backtracking with constraint propagation"
    )
    parser.add_argument("puzzle", help="Path to puzzle file")
    parser.add_argument("--anti-knight", action="store_true",
                        help="Apply anti-knight constraint")
    parser.add_argument("--anti-king", action="store_true",
                        help="Apply anti-king (diagonal) constraint")
    parser.add_argument("--kropki", action="store_true",
                        help="Read Kropki dots from puzzle file")
    args = parser.parse_args()

    try:
        board, kropki_dots = parse_puzzle_file(args.puzzle)
    except (ValueError, FileNotFoundError) as e:
        print(f"Error reading puzzle: {e}", file=sys.stderr)
        sys.exit(1)

    if not args.kropki:
        kropki_dots = []

    print("Puzzle:")
    print(board)
    print()

    t0 = time.perf_counter()
    solution = solve(
        board,
        anti_knight=args.anti_knight,
        anti_king=args.anti_king,
        kropki=kropki_dots,
    )
    elapsed = time.perf_counter() - t0

    if solution is None:
        print("No solution found.")
    else:
        print("Solution:")
        print(solution)
        print(f"\nSolved in {elapsed:.4f}s")


if __name__ == "__main__":
    main()
