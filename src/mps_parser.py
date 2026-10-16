"""Parser minimalista de arquivos MPS (formato fixo/livre) sem dependencias.

Suporta os cartoes usados nas instancias MIPLIB: NAME, ROWS, COLUMNS, RHS,
RANGES (opcional), BOUNDS. Retorna um dicionario com objetivo, restricoes,
coeficientes e bounds, alem de metadados (sentinela *ROWS:, *COLUMNS: etc.).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class MPSModel:
    name: str = ""
    sense: str = "min"
    obj_name: str = ""
    obj_coeffs: dict[str, float] = field(default_factory=dict)
    row_types: dict[str, str] = field(default_factory=dict)
    rhs: dict[str, float] = field(default_factory=dict)
    ranges: dict[str, float] = field(default_factory=dict)
    col_coeffs: dict[str, dict[str, float]] = field(default_factory=dict)
    bounds: dict[str, tuple[float, float]] = field(default_factory=dict)
    integer_cols: list[str] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)

    @property
    def columns(self) -> list[str]:
        return list(self.col_coeffs.keys())

    @property
    def rows(self) -> list[str]:
        return list(self.row_types.keys())


def _parse_header_comments(lines: list[str]) -> dict[str, str]:
    meta: dict[str, str] = {}
    for line in lines:
        m = re.match(r"\*([A-Z ]+):\s*(.*)", line)
        if m:
            meta[m.group(1).strip()] = m.group(2).strip()
    return meta


def parse_mps(path: str) -> MPSModel:
    with open(path, "r") as fh:
        raw_lines = fh.readlines()

    model = MPSModel()
    model.metadata = _parse_header_comments(raw_lines)

    section = None
    current_col = None
    current_int = False
    in_integer_marker = False

    def tokens(line: str) -> list[str]:
        return line.split()

    for line in raw_lines:
        if not line.strip():
            continue
        if line.lstrip().startswith("*"):
            continue

        tok = tokens(line)
        head = tok[0].upper()

        if head in ("NAME", "ROWS", "COLUMNS", "RHS", "RANGES", "BOUNDS", "ENDATA",
                    "OBJSENSE", "OBJSENS"):
            if head == "NAME":
                section = "NAME"
                model.name = tok[1] if len(tok) > 1 else ""
                continue
            if head == "ENDATA":
                break
            if head == "OBJSENSE":
                section = "OBJSENSE"
                continue
            if head == "OBJSENS":
                model.sense = "max" if len(tok) > 1 and tok[1].upper().startswith("MAX") else "min"
                section = None
                continue
            section = head
            continue

        if section == "OBJSENSE":
            model.sense = "max" if tok[0].upper().startswith("MAX") else "min"
            continue

        if section == "ROWS":
            rtype, rname = tok[0].upper(), tok[1]
            model.row_types[rname] = rtype
            if rtype == "N":
                model.obj_name = rname
            continue

        if section == "COLUMNS":
            if "'MARKER'" in line or "MARKER" in line:
                if "INTORG" in line.upper():
                    in_integer_marker = True
                elif "INTEND" in line.upper():
                    in_integer_marker = False
                continue

            col = tok[0]
            if current_col != col:
                current_col = col
                current_int = in_integer_marker
                if current_int and col not in model.integer_cols:
                    model.integer_cols.append(col)
                model.col_coeffs.setdefault(col, {})

            pairs = tok[1:]
            for i in range(0, len(pairs) - 1, 2):
                rname = pairs[i]
                try:
                    val = float(pairs[i + 1])
                except ValueError:
                    continue
                if rname == model.obj_name:
                    model.obj_coeffs[col] = model.obj_coeffs.get(col, 0.0) + val
                else:
                    model.col_coeffs[col][rname] = model.col_coeffs[col].get(rname, 0.0) + val
            continue

        if section == "RHS":
            pairs = tok[1:]
            for i in range(0, len(pairs) - 1, 2):
                rname, val = pairs[i], float(pairs[i + 1])
                model.rhs[rname] = val
            continue

        if section == "RANGES":
            pairs = tok[1:]
            for i in range(0, len(pairs) - 1, 2):
                rname, val = pairs[i], float(pairs[i + 1])
                model.ranges[rname] = val
            continue

        if section == "BOUNDS":
            btype, bname = tok[0].upper(), tok[1]
            col = tok[2]
            val = float(tok[3]) if len(tok) > 3 else 0.0
            lo, hi = model.bounds.get(col, (0.0, float("inf")))
            if btype == "UP":
                hi = val
            elif btype == "LO":
                lo = val
            elif btype == "FX":
                lo = hi = val
            elif btype == "FR":
                lo, hi = float("-inf"), float("inf")
            elif btype == "MI":
                lo = float("-inf")
            elif btype == "PL":
                hi = float("inf")
            elif btype == "BV":
                lo, hi = 0.0, 1.0
                if col not in model.integer_cols:
                    model.integer_cols.append(col)
            elif btype == "LI":
                lo = val
                if col not in model.integer_cols:
                    model.integer_cols.append(col)
            elif btype == "UI":
                hi = val
                if col not in model.integer_cols:
                    model.integer_cols.append(col)
            model.bounds[col] = (lo, hi)
            continue

    for col in model.col_coeffs:
        if col not in model.bounds:
            model.bounds[col] = (0.0, float("inf"))

    return model


if __name__ == "__main__":
    import sys

    m = parse_mps(sys.argv[1])
    print("metadata:", m.metadata)
    print("name:", m.name, "sense:", m.sense, "obj:", m.obj_name)
    print("n cols:", len(m.columns), "n rows:", len(m.rows))
    print("n integer:", len(m.integer_cols))
    print("row types:", {t: sum(1 for v in m.row_types.values() if v == t) for t in set(m.row_types.values())})
    print("obj coeffs:", m.obj_coeffs)
    print("bounds sample:", list(m.bounds.items())[:5])
