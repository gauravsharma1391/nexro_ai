import io

import pandas as pd
import pytest

from app.core.errors import AppError
from app.services import analytics as A
from app.services import nlp

CSV = b"date,region,sales\n2024-01-05,N,100\n2024-01-20,S,150\n2024-02-03,N,\n2024-02-10,S,5000\n2024-02-10,S,5000\n"


def df():
    return A.parse_upload("x.csv", CSV)


def test_summary_counts():
    s = A.summary(df())
    assert s["overview"]["duplicate_rows"] == 1 and s["overview"]["missing_cells"] == 1
    assert {c["name"]: c["type"] for c in s["columns"]}["date"] == "datetime"


def test_outliers_use_iqr():
    d = pd.DataFrame({"v": [1, 2, 2, 3, 3, 3, 4, 100]})
    assert A._outliers(d["v"])["count"] == 1


def test_cleaning_does_not_change_original():
    d = df()
    out = A.apply_ops(d, [{"op": "drop_duplicates"}])
    assert len(d) == 5 and len(out) == 4


@pytest.mark.parametrize("name,content,code", [("a.exe", b"x", "unsupported_file"), ("a.csv", b"", "empty_file"),
                                               ("a.csv", b"\n", "unreadable_file")])
def test_bad_uploads(name, content, code):
    with pytest.raises(AppError) as e:
        A.parse_upload(name, content)
    assert e.value.code == code


def test_header_only_csv_is_rejected():
    with pytest.raises(AppError):
        A.parse_upload("a.csv", b"a,b\n")


def test_unknown_column_and_filename_sanitizing():
    with pytest.raises(AppError):
        A.chart(df(), {"type": "bar", "x": "nope"})
    assert "/" not in A.safe_name("../../etc/passwd") and A.safe_name("..\\..\\x.csv") == "x.csv"


def test_ask_is_deterministic():
    assert "missing" in A.ask(df(), "which columns have missing values")["answer"].lower()


def test_keywords_and_extractive_summary():
    t = "Data science needs clean data. Clean data wins. The cat sat. Birds fly south."
    assert nlp.keywords(t)["frequency"][0]["term"] == "data"
    assert len(nlp.summarize(t, "extractive", 2)["summary"]) < len(t)


def test_cosine_identical_texts():
    assert nlp.demo("cosine", ["red apple", "red apple"])["matrix"][0][1] == pytest.approx(1.0)
