"""FastAPI server for the Prior Approval Claim Validator.

Mirrors the reference travel-planner project's app.py structure.
"""

from pathlib import Path
import traceback
import uvicorn

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from backend import run_claim_validator

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="Prior Approval AI",
    description="AI-Assisted Warranty Claim Validation with LangGraph Multi-Agent RAG",
    version="1.0.0",
)

app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "static")),
    name="static",
)

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ClaimRequest(BaseModel):
    narrative: str
    parts: list[str]
    thread_id: str | None = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={},
    )


@app.post("/api/validate")
async def validate_claim(request_data: ClaimRequest):
    try:
        narrative = request_data.narrative.strip()
        parts = [p.strip() for p in request_data.parts if p.strip()]

        if not narrative:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "Narrative cannot be empty."},
            )

        if not parts:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "Parts list cannot be empty."},
            )

        result = run_claim_validator(
            narrative=narrative,
            parts=parts,
            thread_id=request_data.thread_id,
        )

        return JSONResponse(
            content={
                "success": True,
                "thread_id": result["thread_id"],
                "decision": result["decision"],
                "overall_score": result["overall_score"],
                "part_results": result["part_results"],
                "explanation": result["explanation"],
                "parsed_claim": result["parsed_claim"],
                "llm_calls": result["llm_calls"],
            }
        )

    except Exception as e:
        print("ERROR:", e)
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"Internal error: {type(e).__name__}: {str(e)}"},
        )


@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "Prior Approval AI Validator is running"}


@app.get("/favicon.ico")
async def favicon():
    return JSONResponse(content={})


if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
