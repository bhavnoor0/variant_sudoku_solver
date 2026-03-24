"""
Tests for the Variant Sudoku Solver.
Run with: python tests.py
"""

import sys
import time
from solver import Board, KropkiDot, solve


def grid_from_str(s):
    lines = [l.strip() for l in s.strip().splitlines() if l.strip() and not l.strip().startswith("#")]
    return [[int(c) if c not in ".0" else 0 for c in line.split()] for line in lines]


def is_valid_solution(board, anti_knight=False, anti_king=False, kropki=None):
    n = board.n
    vals = set(range(1, n + 1))
    for r in range(n):
        if {board.get(r, c) for c in range(n)} != vals:
            return False
    for c in range(n):
        if {board.get(r, c) for r in range(n)} != vals:
            return False
    box = board.box
    for br in range(box):
        for bc in range(box):
            cells = {board.get(br*box+dr, bc*box+dc) for dr in range(box) for dc in range(box)}
            if cells != vals:
                return False
    if anti_knight:
        for r in range(n):
            for c in range(n):
                v = board.get(r, c)
                for dr, dc in [(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)]:
                    nr, nc = r+dr, c+dc
                    if 0 <= nr < n and 0 <= nc < n and board.get(nr, nc) == v:
                        return False
    if anti_king:
        for r in range(n):
            for c in range(n):
                v = board.get(r, c)
                for dr, dc in [(-1,-1),(-1,1),(1,-1),(1,1)]:
                    nr, nc = r+dr, c+dc
                    if 0 <= nr < n and 0 <= nc < n and board.get(nr, nc) == v:
                        return False
    if kropki:
        for dot in kropki:
            a, b = board.get(dot.r1, dot.c1), board.get(dot.r2, dot.c2)
            if not dot.satisfied(a, b):
                return False
    return True


PASS = FAIL = 0

def check(name, condition):
    global PASS, FAIL
    if condition:
        print(f"  ✓ {name}"); PASS += 1
    else:
        print(f"  ✗ FAIL: {name}"); FAIL += 1

def raises(name, fn):
    global PASS, FAIL
    try:
        fn(); print(f"  ✗ FAIL: {name} (expected exception)"); FAIL += 1
    except Exception:
        print(f"  ✓ {name}"); PASS += 1


print("Standard Sudoku")
g = grid_from_str("1 . . .\n. . 3 .\n. 2 . .\n. . . 4")
sol = solve(Board(g)); check("4x4 easy", sol is not None and is_valid_solution(sol))

g = grid_from_str("""
5 3 . . 7 . . . .
6 . . 1 9 5 . . .
. 9 8 . . . . 6 .
8 . . . 6 . . . 3
4 . . 8 . 3 . . 1
7 . . . 2 . . . 6
. 6 . . . . 2 8 .
. . . 4 1 9 . . 5
. . . . 8 . . 7 9
""")
sol = solve(Board(g)); check("9x9 medium", sol is not None and is_valid_solution(sol))

g = grid_from_str("""
8 . . . . . . . .
. . 3 6 . . . . .
. 7 . . 9 . 2 . .
. 5 . . . 7 . . .
. . . . 4 5 7 . .
. . . 1 . . . 3 .
. . 1 . . . . 6 8
. . 8 5 . . . 1 .
. 9 . . . . 4 . .
""")
t = time.perf_counter(); sol = solve(Board(g)); elapsed = time.perf_counter()-t
check(f"9x9 hard (Inkala) in {elapsed:.3f}s", sol is not None and is_valid_solution(sol))

check("contradiction → None", solve(Board(grid_from_str("1 1 . .\n. . . .\n. . . .\n. . . ."))) is None)
raises("invalid size raises", lambda: Board([[1,2,3],[4,5,6],[7,8,9]]))

print("\nAnti-Knight")
sol = solve(Board([[0]*4 for _ in range(4)]), anti_knight=True)
check("4x4 empty", sol is not None and is_valid_solution(sol, anti_knight=True))

print("\nAnti-King")
# 4x4 anti-king has no solution (mathematically impossible) — verify solver returns None
sol = solve(Board([[0]*4 for _ in range(4)]), anti_king=True)
check("4x4 empty correctly unsolvable", sol is None)
# 9x9 anti-king is solvable
sol = solve(Board([[0]*9 for _ in range(9)]), anti_king=True)
check("9x9 empty", sol is not None and is_valid_solution(sol, anti_king=True))

print("\nKropki")
dots = [KropkiDot(0,0,0,1,"white")]
sol = solve(Board([[0]*4 for _ in range(4)]), kropki=dots)
check("white dot correct", sol is not None and abs(sol.get(0,0)-sol.get(0,1))==1)
check("white dot valid", sol is not None and is_valid_solution(sol, kropki=dots))

dots = [KropkiDot(0,0,0,1,"black")]
sol = solve(Board([[0]*4 for _ in range(4)]), kropki=dots)
a,b = sol.get(0,0), sol.get(0,1)
check("black dot correct", a==2*b or b==2*a)
check("black dot valid", is_valid_solution(sol, kropki=dots))

print("\nBoard utils")
g = [[1,2,3,4],[3,4,1,2],[2,1,4,3],[4,3,2,1]]
b = Board(g); b2 = b.copy(); b2.set(0,0,9)
check("copy independence", b.get(0,0)==1)
check("empty_cells full board", b.empty_cells()==[])
check("empty_cells finds hole", (0,1) in Board([[1,0,3,4],[3,4,1,2],[2,1,4,3],[4,3,2,1]]).empty_cells())

print(f"\n{'='*40}")
print(f"Results: {PASS} passed, {FAIL} failed")
if FAIL:
    sys.exit(1)
