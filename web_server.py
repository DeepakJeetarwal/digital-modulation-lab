
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parent
WEB_DIR = PROJECT_ROOT / "web"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.simulate import run_request

app = FastAPI(title="Digital Modulation Lab")


class SimulationRequest(BaseModel):
    schemes: list[str] = Field(
        default=["BPSK", "QPSK", "8-PSK", "16-QAM"]
    )
    scheme: str = "BPSK"
    snr: int = Field(default=8, ge=0, le=20)
    num_bits: int = Field(default=30000, ge=12000, le=120000)
    seed: int = 42


@app.get("/")
def home():
    return FileResponse(str(WEB_DIR / "index.html"))


@app.get("/style.css")
def stylesheet():
    return FileResponse(str(WEB_DIR / "style.css"), media_type="text/css")


@app.get("/app.js")
def javascript():
    return FileResponse(
        str(WEB_DIR / "app.js"),
        media_type="application/javascript",
    )


@app.post("/api/simulate")
def simulate(request: SimulationRequest):
    try:
        return run_request(request.model_dump())
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        print(f"Simulation error: {exc}")
        raise HTTPException(
            status_code=500,
            detail="The simulation failed. Check the server terminal.",
        ) from exc


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "Digital Modulation Lab",
    }
