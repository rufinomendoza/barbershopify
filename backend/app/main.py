"""FastAPI layer: a thin, stateless web wrapper around the music package."""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from barbershop.arranger.arrange import ArrangeInput, arrange
from barbershop.arranger.config import ArrangerConfig
from barbershop.arranger.validate import metrics, validate
from barbershop.demos import DEMOS
from barbershop.musicxml import to_musicxml
from barbershop.score import Score

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
        "score": score.model_dump(),
        "musicxml": to_musicxml(score),
        "violations": [str(v) for v in validate(score)],
        "metrics": metrics(score),
    }


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
