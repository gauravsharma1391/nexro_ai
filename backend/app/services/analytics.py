"""Deterministic data analytics with pandas. No user-supplied code is ever executed."""
import io
import json
import re
import uuid
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from ..core import db
from ..core.config import settings
from ..core.errors import AppError

ID_RE = re.compile(r"^[a-f0-9]{32}$")
AGGS = {"sum", "mean", "median", "min", "max", "count"}


# ---------- storage ----------
def safe_name(name: str | None) -> str:
    base = Path((name or "upload").replace("\\", "/")).name
    return re.sub(r"[^A-Za-z0-9._ -]", "_", base)[:100] or "upload"


def _path(did: str) -> Path:
    if not ID_RE.match(did or ""):
        raise AppError(400, "invalid_dataset_id", "Invalid dataset id.")
    return settings.upload_dir / f"{did}.csv"


def load(did: str) -> pd.DataFrame:
    p = _path(did)
    if not p.is_file():
        raise AppError(404, "dataset_not_found", "Dataset not found. It may have been deleted or expired.")
    return pd.read_csv(p)


def save_new(df: pd.DataFrame, filename: str, parent: str | None = None) -> str:
    did = uuid.uuid4().hex
    df.to_csv(_path(did), index=False)
    db.record_dataset(did, filename, len(df), len(df.columns), parent)
    return did


def parse_upload(filename: str, content: bytes) -> pd.DataFrame:
    ext = Path(filename or "").suffix.lower()
    if ext not in {".csv", ".xlsx"}:
        raise AppError(415, "unsupported_file", "Only .csv and .xlsx files are supported.")
    if not content:
        raise AppError(400, "empty_file", "The uploaded file is empty.")
    try:
        if ext == ".csv":
            try:
                df = pd.read_csv(io.BytesIO(content))
            except UnicodeDecodeError:
                df = pd.read_csv(io.BytesIO(content), encoding="latin-1")
        else:
            df = pd.read_excel(io.BytesIO(content), engine="openpyxl")
    except ImportError:
        raise AppError(415, "missing_dependency", "Reading .xlsx files needs openpyxl (pip install openpyxl).")
    except Exception:
        raise AppError(400, "unreadable_file", "The file could not be read as a valid table.")
    if df.shape[1] == 0 or len(df) == 0:
        raise AppError(400, "no_data", "The file contains no data rows.")
    if len(df) > settings.max_rows or df.shape[1] > 500:
        raise AppError(413, "too_large", f"Limit is {settings.max_rows} rows and 500 columns.")
    seen: dict[str, int] = {}
    names = []
    for i, c in enumerate(df.columns):
        n = str(c).strip() or f"column_{i + 1}"
        if n in seen:
            seen[n] += 1
            n = f"{n}_{seen[n]}"
        else:
            seen[n] = 0
        names.append(n)
    df.columns = names
    return df


# ---------- helpers ----------
def _py(v):
    if isinstance(v, np.bool_):
        return bool(v)
    if isinstance(v, np.integer):
        return int(v)
    if isinstance(v, (np.floating, float)):
        f = float(v)
        return None if (np.isnan(f) or np.isinf(f)) else round(f, 6)
    if v is None:
        return None
    if isinstance(v, (str, int, bool)):
        return v
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    return str(v)


def records(df: pd.DataFrame) -> list[dict]:
    return json.loads(df.to_json(orient="records", date_format="iso"))


def col_type(s: pd.Series) -> str:
    if pd.api.types.is_bool_dtype(s):
        return "boolean"
    if pd.api.types.is_numeric_dtype(s):
        return "numeric"
    if pd.api.types.is_datetime64_any_dtype(s):
        return "datetime"
    nn = s.dropna()
    if nn.empty:
        return "categorical"
    sample = nn.astype(str).head(200)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        parsed = pd.to_datetime(sample, errors="coerce")
    if parsed.notna().mean() > 0.9 and sample.str.contains(r"[-/:]").mean() > 0.9:
        return "datetime"
    return "categorical" if nn.nunique() <= max(50, 0.5 * len(nn)) else "text"


def _col(df, name, kind=None) -> pd.Series:
    if not name or name not in df.columns:
        raise AppError(400, "invalid_column", f"Column '{name}' does not exist.")
    if kind == "numeric" and not pd.api.types.is_numeric_dtype(df[name]):
        raise AppError(400, "invalid_column_type", f"Column '{name}' must be numeric.")
    return df[name]


def overview(df: pd.DataFrame) -> dict:
    return {"rows": len(df), "cols": len(df.columns), "missing_cells": int(df.isna().sum().sum()),
            "duplicate_rows": int(df.duplicated().sum())}


def _outliers(s: pd.Series) -> dict:
    v = s.dropna()
    if v.empty:
        return {"method": "IQR", "count": 0, "lower": None, "upper": None}
    q1, q3 = v.quantile(0.25), v.quantile(0.75)
    iqr = q3 - q1
    lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    return {"method": "IQR (1.5 x IQR rule)", "count": int(((v < lo) | (v > hi)).sum()),
            "lower": _py(lo), "upper": _py(hi)}


def correlations(df: pd.DataFrame) -> dict:
    num = [c for c in df.columns if col_type(df[c]) == "numeric"]
    if len(num) < 2:
        return {"columns": num, "matrix": [], "top_pairs": []}
    m = df[num].corr()
    pairs = []
    for i, a in enumerate(num):
        for b in num[i + 1:]:
            v = m.loc[a, b]
            if not np.isnan(v):
                pairs.append({"a": a, "b": b, "r": round(float(v), 4)})
    pairs.sort(key=lambda p: abs(p["r"]), reverse=True)
    return {"columns": num, "matrix": [[_py(x) for x in row] for row in m.values.tolist()], "top_pairs": pairs[:5],
            "note": "Correlation does not imply causation."}


def summary(df: pd.DataFrame) -> dict:
    n = len(df)
    cols = []
    for c in df.columns:
        s, t = df[c], col_type(df[c])
        info = {"name": c, "type": t, "missing": int(s.isna().sum()),
                "missing_pct": round(100 * s.isna().sum() / n, 2) if n else 0, "unique": int(s.nunique())}
        if t == "numeric":
            mode = s.mode()
            info.update(mean=_py(s.mean()), median=_py(s.median()), mode=_py(mode.iloc[0]) if len(mode) else None,
                        std=_py(s.std()), min=_py(s.min()), max=_py(s.max()), outliers=_outliers(s))
        else:
            vc = s.value_counts().head(5)
            info["top_values"] = [{"value": str(k), "count": int(v)} for k, v in vc.items()]
        cols.append(info)
    return {"overview": overview(df), "columns": cols, "correlations": correlations(df)}


def preview(df, page=1, page_size=25, search=None, sort=None, desc=False,
            filter_col=None, minv=None, maxv=None) -> dict:
    d = df
    if filter_col:
        num = pd.to_numeric(_col(d, filter_col, "numeric"), errors="coerce")
        mask = pd.Series(True, index=d.index)
        if minv is not None:
            mask &= num >= minv
        if maxv is not None:
            mask &= num <= maxv
        d = d[mask]
    if search:
        mask = d.astype(str).apply(lambda c: c.str.contains(search, case=False, regex=False, na=False)).any(axis=1)
        d = d[mask]
    if sort:
        _col(d, sort)
        d = d.sort_values(sort, ascending=not desc, na_position="last")
    page_size, page = max(1, min(page_size, 100)), max(1, page)
    chunk = d.iloc[(page - 1) * page_size: page * page_size]
    return {"columns": list(df.columns), "rows": records(chunk), "total": len(d), "page": page,
            "page_size": page_size}


def groupby(df, by: str, column: str, agg: str) -> dict:
    if agg not in AGGS:
        raise AppError(400, "invalid_aggregation", f"Aggregation must be one of {sorted(AGGS)}.")
    _col(df, by)
    _col(df, column, None if agg == "count" else "numeric")
    g = df.groupby(by, dropna=True)[column].agg(agg).sort_values(ascending=False).head(100)
    return {"rows": [{by: str(k), f"{agg}_{column}": _py(v)} for k, v in g.items()]}


# ---------- charts ----------
def _box(v: pd.Series, name: str) -> dict:
    q1, med, q3 = (float(x) for x in v.quantile([0.25, 0.5, 0.75]))
    iqr = q3 - q1
    inside = v[(v >= q1 - 1.5 * iqr) & (v <= q3 + 1.5 * iqr)]
    return {"name": name, "min": _py(inside.min()), "q1": _py(q1), "median": _py(med), "q3": _py(q3),
            "max": _py(inside.max()), "outliers": int(len(v) - len(inside))}


def chart(df: pd.DataFrame, spec: dict) -> dict:
    t, x, y = spec["type"], spec.get("x"), spec.get("y")
    agg = spec.get("agg") or "sum"
    if agg not in AGGS:
        raise AppError(400, "invalid_aggregation", f"Aggregation must be one of {sorted(AGGS)}.")
    if t == "bar":
        _col(df, x)
        if y:
            _col(df, y, None if agg == "count" else "numeric")
            g = df.groupby(x, dropna=True)[y].agg(agg).sort_values(ascending=False).head(30)
        else:
            g = df[x].value_counts().head(30)
        data = [{"x": str(k), "y": _py(v)} for k, v in g.items()]
    elif t == "line":
        _col(df, x)
        _col(df, y, "numeric")
        d = df[[x, y]].dropna().copy()
        if col_type(d[x]) == "datetime":
            d[x] = pd.to_datetime(d[x], errors="coerce")
            d = d.dropna()
        g = d.groupby(x)[y].agg(agg).sort_index().head(500)
        data = [{"x": k.strftime("%Y-%m-%d") if hasattr(k, "strftime") else _py(k), "y": _py(v)}
                for k, v in g.items()]
    elif t == "histogram":
        v = pd.to_numeric(_col(df, x, "numeric"), errors="coerce").dropna()
        if v.empty:
            raise AppError(400, "no_data", "The column has no numeric values.")
        counts, edges = np.histogram(v, bins=max(2, min(int(spec.get("bins") or 10), 100)))
        data = [{"bin": f"{edges[i]:.4g} to {edges[i + 1]:.4g}", "count": int(c)} for i, c in enumerate(counts)]
    elif t == "scatter":
        _col(df, x, "numeric")
        _col(df, y, "numeric")
        d = df[[x, y]].dropna()
        if len(d) > 1000:
            d = d.sample(1000, random_state=0)
        data = [{"x": _py(a), "y": _py(b)} for a, b in d.values]
    elif t == "pie":
        _col(df, x)
        vc = df[x].value_counts()
        data = [{"name": str(k), "value": int(v)} for k, v in vc.head(8).items()]
        if len(vc) > 8:
            data.append({"name": "Other", "value": int(vc.iloc[8:].sum())})
    elif t == "box":
        v = pd.to_numeric(_col(df, y, "numeric"), errors="coerce")
        if x:
            _col(df, x)
            tops = df[x].value_counts().head(10).index
            data = [_box(v[df[x] == k].dropna(), str(k)) for k in tops if v[df[x] == k].notna().any()]
        else:
            data = [_box(v.dropna(), y)]
    elif t == "heatmap":
        data = correlations(df)
    else:
        raise AppError(400, "invalid_chart", "Unsupported chart type.")
    return {"type": t, "data": data}


# ---------- cleaning (never touches the original) ----------
def apply_ops(df: pd.DataFrame, ops: list[dict]) -> pd.DataFrame:
    d = df.copy()
    for op in ops:
        kind, col = op.get("op"), op.get("column")
        if kind == "drop_duplicates":
            d = d.drop_duplicates()
        elif kind == "drop_missing":
            cols = op.get("columns") or None
            for c in cols or []:
                _col(d, c)
            d = d.dropna(subset=cols)
        elif kind == "fill_missing":
            s = _col(d, col)
            how = op.get("strategy")
            if how == "drop":
                d = d.dropna(subset=[col])
            elif how in ("mean", "median"):
                _col(d, col, "numeric")
                d[col] = s.fillna(s.mean() if how == "mean" else s.median())
            elif how == "mode":
                m = s.mode()
                if len(m):
                    d[col] = s.fillna(m.iloc[0])
            elif how == "value":
                val = op.get("value")
                if pd.api.types.is_numeric_dtype(s):
                    try:
                        val = float(val)
                    except (TypeError, ValueError):
                        raise AppError(400, "invalid_value", f"'{col}' is numeric; give a number.")
                d[col] = s.fillna(val)
            else:
                raise AppError(400, "invalid_strategy", "Strategy must be drop, mean, median, mode or value.")
        elif kind == "filter_numeric":
            num = pd.to_numeric(_col(d, col, "numeric"), errors="coerce")
            if op.get("min") is not None:
                d = d[num >= float(op["min"])]
                num = num[d.index]
            if op.get("max") is not None:
                d = d[num <= float(op["max"])]
        elif kind == "select_columns":
            cols = op.get("columns") or []
            for c in cols:
                _col(d, c)
            if not cols:
                raise AppError(400, "invalid_columns", "Select at least one column.")
            d = d[cols]
        else:
            raise AppError(400, "invalid_operation", f"Unknown operation '{kind}'.")
    return d


# ---------- natural-language questions -> fixed, validated operations ----------
def ask(df: pd.DataFrame, q: str) -> dict:
    ql = q.lower()
    mentioned = [c for c in df.columns if c.lower() in ql]
    num_m = [c for c in mentioned if pd.api.types.is_numeric_dtype(df[c])]
    cat_m = [c for c in mentioned if c not in num_m]
    res = {"answer": "", "table": None, "chart": None, "source": "calculated with pandas (no AI model involved)"}

    if "missing" in ql or "null" in ql or "empty" in ql:
        t = [{"column": c, "missing": int(df[c].isna().sum()),
              "pct": round(100 * df[c].isna().mean(), 2)} for c in df.columns if df[c].isna().any()]
        res.update(answer=f"{len(t)} column(s) contain missing values." if t else "No column has missing values.",
                   table=t or None)
    elif "duplicate" in ql:
        res["answer"] = f"There are {int(df.duplicated().sum())} fully duplicated rows."
    elif "correl" in ql:
        c = correlations(df)
        res.update(answer="Strongest numeric correlations (Pearson r). Correlation does not prove causation."
                   if c["top_pairs"] else "Need at least two numeric columns.", table=c["top_pairs"] or None)
    elif any(w in ql for w in ("outlier", "unusual", "anomal")):
        t = [{"column": c, **{k: v for k, v in _outliers(df[c]).items() if k != "method"}}
             for c in df.columns if col_type(df[c]) == "numeric"]
        res.update(answer="Values outside 1.5 x IQR from the quartiles are flagged as unusual. "
                          "Unusual is not the same as wrong.", table=t or None)
    elif any(w in ql for w in ("trend", "monthly", "over time")):
        dc = next((c for c in df.columns if col_type(df[c]) == "datetime"), None)
        vc = (num_m or [c for c in df.columns if col_type(df[c]) == "numeric"] or [None])[0]
        if not dc or not vc:
            res["answer"] = "A trend needs one date column and one numeric column; this dataset lacks one."
        else:
            d = df[[dc, vc]].copy()
            d[dc] = pd.to_datetime(d[dc], errors="coerce")
            m = d.dropna().set_index(dc)[vc].resample("MS").sum()
            res.update(answer=f"Monthly total of '{vc}' by '{dc}'.",
                       chart={"type": "line", "data": [{"x": k.strftime("%Y-%m"), "y": _py(v)} for k, v in m.items()]})
    elif any(w in ql for w in ("average", "mean", "sum", "total", "median", "max", "min")) and num_m:
        agg = next(a for a, ws in (("mean", ("average", "mean")), ("sum", ("sum", "total")),
                                   ("median", ("median",)), ("max", ("max",)), ("min", ("min",)))
                   if any(w in ql for w in ws))
        if cat_m:
            g = groupby(df, cat_m[0], num_m[0], agg)
            res.update(answer=f"{agg} of {num_m[0]} by {cat_m[0]}.", table=g["rows"],
                       chart={"type": "bar", "data": [{"x": r[cat_m[0]], "y": r[f'{agg}_{num_m[0]}']} for r in g["rows"][:30]]})
        else:
            res["answer"] = f"The {agg} of {num_m[0]} is {_py(getattr(df[num_m[0]], agg)())}."
    elif any(w in ql for w in ("summar", "describe", "overview")):
        o = overview(df)
        types = pd.Series([col_type(df[c]) for c in df.columns]).value_counts().to_dict()
        res["answer"] = (f"{o['rows']} rows x {o['cols']} columns; {o['missing_cells']} missing cells; "
                         f"{o['duplicate_rows']} duplicate rows. Column types: {types}.")
    else:
        res["answer"] = ("I can answer: summary, missing values, duplicates, correlations, outliers, monthly trends, "
                         "and 'average/sum/max/min of <numeric column> by <column>'. Use exact column names.")
    return res
