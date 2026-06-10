"""Web API: stateless transforms over the score model."""
import xml.etree.ElementTree as ET

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_demos():
    r = client.get("/api/demos")
    assert r.status_code == 200
    demos = r.json()
    ids = {d["id"] for d in demos}
    assert "yankee-doodle" in ids
    assert all("title" in d for d in demos)


def test_arrange_demo_returns_score_and_musicxml():
    r = client.post("/api/demos/yankee-doodle/arrange", json={"spice": 3})
    assert r.status_code == 200
    body = r.json()
    assert set(body["score"]["voices"]) == {"tenor", "lead", "bari", "bass"}
    root = ET.fromstring(body["musicxml"])
    assert root.tag == "score-partwise"
    assert body["violations"] == []


def test_arrange_unknown_demo_404s():
    r = client.post("/api/demos/nope/arrange", json={"spice": 3})
    assert r.status_code == 404


def test_render_roundtrip():
    score = client.post("/api/demos/yankee-doodle/arrange", json={"spice": 1}).json()["score"]
    r = client.post("/api/render", json={"score": score})
    assert r.status_code == 200
    assert ET.fromstring(r.json()["musicxml"]).tag == "score-partwise"


def test_spice_is_validated():
    r = client.post("/api/demos/yankee-doodle/arrange", json={"spice": 9})
    assert r.status_code == 422
