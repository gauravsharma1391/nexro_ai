from fastapi import APIRouter, File, UploadFile

from ..schemas import TrainIn
from ..services import dl

router = APIRouter(prefix="/api/deep-learning")


@router.get("/status")
def status():
    return dl.status()


@router.post("/train", status_code=202)
def train(b: TrainIn):
    return {"job_id": dl.start_training(b.hidden, b.lr, b.batch, b.epochs)}


@router.get("/jobs/{jid}")
def job(jid: str):
    return dl.get_job(jid)


@router.get("/sample")
def sample():
    return dl.sample()


@router.post("/predict")
async def predict(file: UploadFile = File(...), invert: bool = True):
    return dl.predict_image(await file.read(2 * 1024 * 1024 + 1), invert)
