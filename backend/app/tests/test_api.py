import io


def test_health(client):
    assert client.get("/api/health").json()["status"] == "ok"


def test_chat_demo_mode_persists_history(client):
    r = client.post("/api/chat", json={"message": "hello"})
    assert r.status_code == 200 and "demo mode" in r.text.lower()
    cid = r.headers["x-conversation-id"]
    conv = client.get(f"/api/conversations/{cid}").json()
    assert [m["role"] for m in conv["messages"]] == ["user", "assistant"]
    assert client.patch(f"/api/conversations/{cid}", json={"title": "Renamed"}).status_code == 200
    assert client.delete(f"/api/conversations/{cid}").status_code == 200
    assert client.get(f"/api/conversations/{cid}").status_code == 404


def test_chat_rejects_empty_and_unconfigured_provider(client):
    assert client.post("/api/chat", json={"message": "   "}).status_code == 422
    r = client.post("/api/chat", json={"message": "hi", "provider": "anthropic"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "provider_not_ready"


def test_nlp_validation_and_unavailable_model(client):
    assert client.post("/api/nlp/preprocess", json={"text": ""}).status_code == 422
    assert client.post("/api/nlp/keywords", json={"text": "Data is good. Data is useful."}).status_code == 200
    assert client.post("/api/nlp/sentiment", json={"text": "great"}).status_code in (200, 503)


def test_analytics_end_to_end(client):
    csv = b"a,b\n1,x\n2,y\n2,y\n,z\n"
    up = client.post("/api/analytics/upload", files={"file": ("d.csv", io.BytesIO(csv), "text/csv")})
    assert up.status_code == 201
    did = up.json()["dataset_id"]
    assert client.get(f"/api/analytics/{did}/preview").json()["total"] == 4
    assert client.post(f"/api/analytics/{did}/summary").json()["overview"]["duplicate_rows"] == 1
    assert client.post(f"/api/analytics/{did}/chart", json={"type": "bar", "x": "b"}).status_code == 200
    prev = client.post(f"/api/analytics/{did}/clean", json={"ops": [{"op": "drop_duplicates"}]}).json()
    assert prev["after"]["rows"] == 3 and prev["new_dataset_id"] is None
    new = client.post(f"/api/analytics/{did}/clean", json={"ops": [{"op": "drop_duplicates"}], "apply": True}).json()
    assert new["new_dataset_id"] != did
    assert client.get(f"/api/analytics/{did}/preview").json()["total"] == 4  # original untouched
    assert "a,b" in client.get(f"/api/analytics/{new['new_dataset_id']}/export.csv").text


def test_bad_uploads_and_ids(client):
    r = client.post("/api/analytics/upload", files={"file": ("x.txt", io.BytesIO(b"hi"), "text/plain")})
    assert r.status_code == 415
    assert client.get("/api/analytics/not-an-id/preview").status_code == 400
    assert client.get("/api/analytics/" + "a" * 32 + "/preview").status_code == 404


def test_deep_learning_requires_training(client):
    assert client.get("/api/deep-learning/sample").status_code == 409
    r = client.post("/api/deep-learning/train", json={"hidden": 9999})
    assert r.status_code == 422
