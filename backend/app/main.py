"""FastAPI layer: a thin, stateless web wrapper around the music package."""
from __future__ import annotations

import re
import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from barbershop.arranger.arrange import ArrangeInput, arrange
from barbershop.arranger.config import ArrangerConfig
from barbershop.arranger.validate import metrics, validate
from barbershop.demos import DEMOS
from barbershop.musicxml import to_musicxml
from barbershop.score import Score

TEST_SONGS_DIR = Path(__file__).resolve().parents[2] / "test_songs"
ALLOWED_SUFFIXES = {".mp3", ".m4a", ".wav"}

app = FastAPI(title="barbershopify")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ArrangeOptions(BaseModel):
    spice: int = Field(default=3, ge=1, le=5)


class ArrangeRequest(BaseModel):
    input: ArrangeInput
    spice: int = Field(default=3, ge=1, le=5)


class RenderRequest(BaseModel):
    score: Score


def _arrangement_response(inp: ArrangeInput, spice: int) -> dict:
    score = arrange(inp, ArrangerConfig(spice=spice))
    return {
        "input": inp.model_dump(),  # cached client-side so re-arrange skips analysis
        "score": score.model_dump(),
        "musicxml": to_musicxml(score),
        "violations": [str(v) for v in validate(score)],
        "metrics": metrics(score),
    }


def _song_title(stem: str) -> str:
    return re.sub(r"[-_]+", " ", stem).title()


@app.get("/api/demos")
def list_demos() -> list[dict]:
    return [{"id": demo_id, "title": inp.title} for demo_id, inp in DEMOS.items()]


@app.post("/api/demos/{demo_id}/arrange")
def arrange_demo(demo_id: str, options: ArrangeOptions) -> dict:
    if demo_id not in DEMOS:
        raise HTTPException(status_code=404, detail=f"unknown demo {demo_id!r}")
    return _arrangement_response(DEMOS[demo_id], options.spice)


@app.post("/api/arrange")
def arrange_input(req: ArrangeRequest) -> dict:
    return _arrangement_response(req.input, req.spice)


@app.post("/api/render")
def render(req: RenderRequest) -> dict:
    return {"musicxml": to_musicxml(req.score)}


@app.get("/api/test-songs")
def list_test_songs() -> list[dict]:
    if not TEST_SONGS_DIR.is_dir():
        return []
    return [
        {"id": p.stem, "title": _song_title(p.stem)}
        for p in sorted(TEST_SONGS_DIR.glob("*.mp3"))
    ]


@app.post("/api/test-songs/{song_id}/arrange")
def arrange_test_song(song_id: str, options: ArrangeOptions) -> dict:
    path = TEST_SONGS_DIR / f"{song_id}.mp3"
    if not re.fullmatch(r"[a-z0-9-]+", song_id) or not path.exists():
        raise HTTPException(status_code=404, detail=f"unknown test song {song_id!r}")
    from barbershop.analysis.pipeline import analyze  # heavy import, deferred

    result = analyze(str(path), title=_song_title(song_id))
    return _arrangement_response(result.input, options.spice)


@app.post("/api/upload")
async def upload_and_arrange(file: UploadFile, spice: int = 3) -> dict:
    suffix = Path(file.filename or "upload").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(
            status_code=422,
            detail=f"unsupported file type {suffix!r}; use .mp3, .m4a or .wav",
        )
    if not 1 <= spice <= 5:
        raise HTTPException(status_code=422, detail="spice must be 1-5")
    from barbershop.analysis.pipeline import analyze  # heavy import, deferred

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
        while chunk := await file.read(1 << 20):
            tmp.write(chunk)
        tmp.flush()
        try:
            result = analyze(tmp.name, title=Path(file.filename or "Upload").stem)
        except ValueError as err:
            raise HTTPException(status_code=422, detail=str(err)) from err
    return _arrangement_response(result.input, spice)
