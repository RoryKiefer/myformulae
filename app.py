"""Sanic web app: type an expression in x, get a step-by-step algebra solution."""
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sanic import Sanic, response
from sanic.request import Request

from algebra.engine import AlgebraError, detect_mode, run

BASE_DIR = Path(__file__).parent

app = Sanic("algebra_helper")
app.static("/static", BASE_DIR / "static")

jinja_env = Environment(
    loader=FileSystemLoader(BASE_DIR / "templates"),
    autoescape=select_autoescape(["html"]),
)


@app.get("/")
async def index(request: Request):
    template = jinja_env.get_template("index.html")
    return response.html(template.render())


@app.post("/api/solve")
async def solve(request: Request):
    body = request.json or {}
    text = (body.get("expression") or "").strip()
    mode = body.get("mode") or "auto"
    if mode == "auto":
        mode = detect_mode(text)

    if not text:
        return response.json({"error": "Please enter an expression."}, status=400)

    try:
        result = run(mode, text)
    except AlgebraError as e:
        return response.json({"error": str(e)}, status=400)
    except Exception:
        return response.json({"error": "Something went wrong evaluating that expression."}, status=400)

    return response.json(
        {
            "mode": result.mode,
            "input_display": result.input_display,
            "final": result.final,
            "steps": result.steps,
            "note": result.note,
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, dev=True)
