from typing import Optional

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import Response

from ..core import db
from ..core.config import settings
from ..core.errors import AppError
from ..schemas import AskIn, ChartSpec, CleanIn, GroupByIn
from ..services import analytics as A

router = APIRouter(prefix="/api/analytics")


@router.post("/upload", status_code=201)
async def upload(file: UploadFile = File(...)):
    limit = settings.max_upload_mb * 1024 * 1024
    content = await file.read(limit + 1)
    if len(content) > limit:
        raise AppError(413, "file_too_large", f"Files are limited to {settings.max_upload_mb} MB.")
    name = A.safe_name(file.filename)
    df = A.parse_upload(name, content)
    did = A.save_new(df, name)
    return {"dataset_id": did, "filename": name, **A.overview(df)}


@router.get("/datasets")
def datasets():
    return db.list_datasets()


@router.get("/{did}/preview")
def preview(did: str, page: int = 1, page_size: int = 25, search: Optional[str] = None, sort: Optional[str] = None,
            desc: bool = False, filter_col: Optional[str] = None, min: Optional[float] = None,
            max: Optional[float] = None):
    return A.preview(A.load(did), page, page_size, search, sort, desc, filter_col, min, max)


@router.post("/{did}/summary")
def summary(did: str):
    return A.summary(A.load(did))


@router.post("/{did}/chart")
def chart(did: str, spec: ChartSpec):
    return A.chart(A.load(did), spec.model_dump())


@router.post("/{did}/groupby")
def groupby(did: str, b: GroupByIn):
    return A.groupby(A.load(did), b.by, b.column, b.agg)


@router.post("/{did}/clean")
def clean(did: str, b: CleanIn):
    """Preview by default. With apply=true the result is saved as a NEW dataset; the original is never changed."""
    df = A.load(did)
    out = A.apply_ops(df, b.ops)
    res = {"before": A.overview(df), "after": A.overview(out), "preview": A.records(out.head(10)),
           "applied": False, "new_dataset_id": None}
    if b.apply:
        meta = db.get_dataset(did)
        res.update(applied=True, new_dataset_id=A.save_new(out, f"cleaned_{meta['filename'] if meta else 'data.csv'}", did))
    return res


@router.post("/{did}/ask")
def ask(did: str, b: AskIn):
    return A.ask(A.load(did), b.question)


@router.get("/{did}/export.csv")
def export_csv(did: str):
    return Response(A.load(did).to_csv(index=False), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="{did[:8]}.csv"'})


@router.get("/{did}/export.json")
def export_json(did: str):
    return A.summary(A.load(did))
