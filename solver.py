"""
Variant Sudoku Solver
=====================
Recursive backtracking solver with constraint propagation.
Supports arbitrary board sizes and the following constraint variants:
  - Standard (rows, columns, boxes)
  - Anti-knight
  - Anti-king
  - Kropki pairs (consecutive and double)
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Optional


# ---------------------------------------------------------------------------
# Board
# ---------------------------------------------------------------------------

class Board:
    """
    Represents a sudoku grid of arbitrary size N×N where N must be a perfect
    square (4, 9, 16, 25, …).

    Cells are indexed as (row, col) with 0-based coordinates.
    A value of 0 means the cell is empty.
    """

    def __init__(self, grid: list[list[int]]):
        self.n = len(grid)
        self.box = int(math.isqrt(self.n))
        if self.box * self.box != self.n:
            raise ValueError(f"Board size {self.n} is not a perfect square.")
        if any(len(row) != self.n for row in grid):
            raise ValueError("Grid must be square.")
        # Store as flat list for speed; index = row*n + col
        self._cells: list[int] = [v for row in grid for v in row]
        self._n = self.n

    # ------------------------------------------------------------------
    # Access helpers
    # ------------------------------------------------------------------

    def get(self, r: int, c: int) -> int:
        return self._cells[r * self._n + c]

    def set(self, r: int, c: int, v: int) -> None:
        self._cells[r * self._n + c] = v

    def copy(self) -> "Board":
        b = Board.__new__(Board)
        b.n = self.n
        b.box = self.box
        b._n = self._n
        b._cells = self._cells[:]
        return b

    def to_grid(self) -> list[list[int]]:
        return [self._cells[r * self._n:(r + 1) * self._n] for r in range(self._n)]

    def empty_cells(self) -> list[tuple[int, int]]:
        n = self._n
        return [(i // n, i % n) for i, v in enumerate(self._cells) if v == 0]

    def __str__(self) -> str:
        n = self._n
        box = self.box
        lines = []
        for r in range(n):
            if r > 0 and r % box == 0:
                lines.append("-" * (n * 2 + box - 1))
            row_str = ""
            for c in range(n):
                if c > 0 and c % box == 0:
                    row_str += "|"
                v = self.get(r, c)
                row_str += ("." if v == 0 else str(v)).rjust(2 if n > 9 else 1)
            lines.append(row_str)
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Kropki constraint definition
# ---------------------------------------------------------------------------

@dataclass
class KropkiDot:
    """
    A Kropki dot between two adjacent cells.
      kind='white'  → the two values are consecutive  (|a-b| == 1)
      kind='black'  → one value is double the other   (a==2b or b==2a)
    """
    r1: int
    c1: int
    r2: int
    c2: int
    kind: str  # 'white' or 'black'

    def satisfied(self, a: int, b: int) -> bool:
        if a == 0 or b == 0:
            return True          # unknown — not violated yet
        if self.kind == "white":
            return abs(a - b) == 1
        else:  # black
            return a == 2 * b or b == 2 * a


# ---------------------------------------------------------------------------
# Constraint checker (pure functions, called during propagation & placement)
# ---------------------------------------------------------------------------

# Knight moves (chess)
_KNIGHT_DELTAS = [(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)]
# King moves (chess, excluding orthogonal/same — we only care about diagonals
# since orthogonal peers are already covered by row/col constraints)
_KING_DELTAS   = [(-1,-1),(-1,1),(1,-1),(1,1)]


def _peers_standard(r: int, c: int, n: int, box: int) -> list[tuple[int,int]]:
    """All cells that must differ from (r,c) under standard rules."""
    peers = set()
    for cc in range(n):
        peers.add((r, cc))
    for rr in range(n):
        peers.add((rr, c))
    br, bc = (r // box) * box, (c // box) * box
    for dr in range(box):
        for dc in range(box):
            peers.add((br + dr, bc + dc))
    peers.discard((r, c))
    return list(peers)


def _extra_peers(r: int, c: int, n: int,
                 anti_knight: bool, anti_king: bool) -> list[tuple[int,int]]:
    """Additional peers added by variant constraints."""
    extra = []
    deltas = []
    if anti_knight:
        deltas += _KNIGHT_DELTAS
    if anti_king:
        deltas += _KING_DELTAS
    for dr, dc in deltas:
        nr, nc = r + dr, c + dc
        if 0 <= nr < n and 0 <= nc < n:
            extra.append((nr, nc))
    return extra


# ---------------------------------------------------------------------------
# Candidate sets (the "propagation" state)
# ---------------------------------------------------------------------------

class CandidateGrid:
    """
    Maintains a set of possible values for every cell.
    Propagation removes values that are provably impossible.
    """

    def __init__(self, board: Board, anti_knight: bool, anti_king: bool,
                 kropki: list[KropkiDot]):
        self.n = board.n
        self.box = board.box
        self.anti_knight = anti_knight
        self.anti_king = anti_king
        self.kropki = kropki

        # Build peer lists once (expensive to recompute)
        n, box = self.n, self.box
        self._std_peers: list[list[tuple[int,int]]] = [
            _peers_standard(r, c, n, box)
            for r in range(n) for c in range(n)
        ]
        self._all_peers: list[list[tuple[int,int]]] = [
            self._std_peers[r * n + c] + _extra_peers(r, c, n, anti_knight, anti_king)
            for r in range(n) for c in range(n)
        ]

        # Kropki lookup: cell → list of (neighbour_index, dot)
        self._kropki_map: list[list[tuple[int, KropkiDot]]] = [[] for _ in range(n * n)]
        for dot in kropki:
            i1 = dot.r1 * n + dot.c1
            i2 = dot.r2 * n + dot.c2
            self._kropki_map[i1].append((i2, dot))
            self._kropki_map[i2].append((i1, dot))

        # Initialise candidate sets
        full = set(range(1, n + 1))
        self._cands: list[set[int]] = [full.copy() for _ in range(n * n)]

        # Seed from given clues
        for r in range(n):
            for c in range(n):
                v = board.get(r, c)
                if v != 0:
                    if not self._assign(r, c, v):
                        raise ValueError("Puzzle is immediately contradictory.")

    # ------------------------------------------------------------------
    # Core propagation
    # ------------------------------------------------------------------

    def candidates(self, r: int, c: int) -> set[int]:
        return self._cands[r * self.n + c]

    def _assign(self, r: int, c: int, v: int) -> bool:
        """
        Assign value v to (r,c) and propagate: eliminate v from all peers.
        Returns False if a contradiction is found.
        """
        idx = r * self.n + c
        cands = self._cands[idx]
        if v not in cands:
            return False
        # Eliminate every other candidate from this cell
        for other in list(cands):
            if other != v:
                if not self._eliminate(r, c, other):
                    return False
        return True

    def _eliminate(self, r: int, c: int, v: int) -> bool:
        """
        Remove v from (r,c)'s candidates and propagate consequences.
        Returns False on contradiction.
        """
        idx = r * self.n + c
        cands = self._cands[idx]
        if v not in cands:
            return True   # already eliminated, nothing to do
        cands.discard(v)
        if len(cands) == 0:
            return False  # contradiction: no candidates left
        if len(cands) == 1:
            # Naked single → propagate to peers
            (sole,) = cands
            for (pr, pc) in self._all_peers[idx]:
                if not self._eliminate(pr, pc, sole):
                    return False
        # Propagate Kropki constraints involving this cell
        for (nidx, dot) in self._kropki_map[idx]:
            nr, nc = nidx // self.n, nidx % self.n
            # For each remaining candidate of the neighbour, check it is still
            # satisfiable given our updated candidate set.
            for nv in list(self._cands[nidx]):
                if not any(dot.satisfied(cv, nv) for cv in cands):
                    if not self._eliminate(nr, nc, nv):
                        return False
        return True

    def copy(self) -> "CandidateGrid":
        cg = CandidateGrid.__new__(CandidateGrid)
        cg.n = self.n
        cg.box = self.box
        cg.anti_knight = self.anti_knight
        cg.anti_king = self.anti_king
        cg.kropki = self.kropki
        cg._std_peers = self._std_peers        # immutable, share reference
        cg._all_peers = self._all_peers        # immutable, share reference
        cg._kropki_map = self._kropki_map      # immutable, share reference
        cg._cands = [s.copy() for s in self._cands]
        return cg

    def place(self, r: int, c: int, v: int) -> Optional["CandidateGrid"]:
        """
        Return a new CandidateGrid with (r,c)=v propagated, or None on contradiction.
        """
        new_cg = self.copy()
        if not new_cg._assign(r, c, v):
            return None
        return new_cg

    def choose_cell(self) -> Optional[tuple[int, int]]:
        """
        MRV heuristic: pick the unfilled cell with the fewest candidates.
        Returns None if all cells are filled (solution found).
        """
        best_r, best_c, best_n = -1, -1, self.n + 1
        for r in range(self.n):
            for c in range(self.n):
                idx = r * self.n + c
                nc = len(self._cands[idx])
                if nc == 1:
                    # Already determined — skip
                    # (value == the single candidate, cell is "filled" for search)
                    pass
                # We detect "empty" as >1 candidates OR ==1 with board value==0
                # easier: track separately? No — let's check board consistency.
                # Actually CandidateGrid doesn't hold a board copy.
                # We track: a cell is solved iff exactly 1 candidate exists.
                # Unfilled means we haven't committed yet — but after propagation
                # a cell with 1 candidate is effectively decided.
                # So "choose" among cells with >1 candidates:
                if nc > 1 and nc < best_n:
                    best_r, best_c, best_n = r, c, nc
        if best_r == -1:
            return None   # all cells have exactly 1 candidate → solved
        return (best_r, best_c)

    def extract_board(self) -> list[list[int]]:
        n = self.n
        grid = []
        for r in range(n):
            row = []
            for c in range(n):
                cands = self._cands[r * n + c]
                if len(cands) == 1:
                    (v,) = cands
                    row.append(v)
                else:
                    row.append(0)
            grid.append(row)
        return grid


# ---------------------------------------------------------------------------
# Solver
# ---------------------------------------------------------------------------

def solve(board: Board,
          anti_knight: bool = False,
          anti_king: bool = False,
          kropki: list[KropkiDot] | None = None,
          ) -> Optional[Board]:
    """
    Solve a variant sudoku puzzle.

    Parameters
    ----------
    board       : Board with 0 representing empty cells.
    anti_knight : No two identical values may be a chess knight's move apart.
    anti_king   : No two identical values may be a chess king's move apart
                  (diagonally adjacent).
    kropki      : List of KropkiDot constraints between adjacent cells.

    Returns
    -------
    A solved Board, or None if no solution exists.
    """
    if kropki is None:
        kropki = []

    try:
        cg = CandidateGrid(board, anti_knight, anti_king, kropki)
    except ValueError:
        return None

    result = _backtrack(cg)
    if result is None:
        return None

    return Board(result.extract_board())


def _backtrack(cg: CandidateGrid) -> Optional[CandidateGrid]:
    cell = cg.choose_cell()
    if cell is None:
        return cg   # solved

    r, c = cell
    for v in sorted(cg.candidates(r, c)):
        new_cg = cg.place(r, c, v)
        if new_cg is None:
            continue
        result = _backtrack(new_cg)
        if result is not None:
            return result

    return None  # no value worked → backtrack
