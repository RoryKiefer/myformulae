from app import app


def test_index_serves_html():
    _, response = app.test_client.get("/")
    assert response.status == 200
    assert "Algebra Helper" in response.text


def test_solve_auto_mode():
    _, response = app.test_client.post(
        "/api/solve", json={"expression": "2*x + 3 = 7"}
    )
    assert response.status == 200
    body = response.json
    assert body["mode"] == "solve"
    assert body["final"] == "x = 2"


def test_solve_explicit_mode():
    _, response = app.test_client.post(
        "/api/solve", json={"expression": "2*x + 4*x", "mode": "simplify"}
    )
    assert response.status == 200
    assert response.json["mode"] == "simplify"


def test_solve_missing_expression_returns_400():
    _, response = app.test_client.post("/api/solve", json={"expression": ""})
    assert response.status == 400
    assert "error" in response.json


def test_solve_missing_body_returns_400():
    _, response = app.test_client.post("/api/solve")
    assert response.status == 400
    assert "error" in response.json


def test_solve_invalid_expression_returns_400_with_message():
    _, response = app.test_client.post(
        "/api/solve", json={"expression": "x.__class__"}
    )
    assert response.status == 400
    assert response.json["error"]


def test_solve_unknown_mode_returns_400():
    _, response = app.test_client.post(
        "/api/solve", json={"expression": "x + 1", "mode": "bogus"}
    )
    assert response.status == 400
    assert "error" in response.json
