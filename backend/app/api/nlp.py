from fastapi import APIRouter

from ..schemas import ClassifyIn, DemoIn, KeywordsIn, SummarizeIn, TextIn
from ..services import nlp

router = APIRouter(prefix="/api/nlp")


@router.post("/preprocess")
def preprocess(b: TextIn):
    return nlp.preprocess(b.text)


@router.post("/sentiment")
def sentiment(b: TextIn):
    return nlp.sentiment(b.text)


@router.post("/classify")
def classify(b: ClassifyIn):
    return nlp.classify(b.text, [x.strip() for x in b.labels if x.strip()])


@router.post("/summarize")
def summarize(b: SummarizeIn):
    return nlp.summarize(b.text, b.method, b.sentences)


@router.post("/keywords")
def keywords(b: KeywordsIn):
    return nlp.keywords(b.text, b.top_k)


@router.post("/demo")
def demo(b: DemoIn):
    return nlp.demo(b.mode, b.texts, b.n)


@router.post("/ner")
def ner(b: TextIn):
    return nlp.ner(b.text)
