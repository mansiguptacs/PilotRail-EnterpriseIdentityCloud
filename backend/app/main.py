from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import router
from app.workstation_routes import router as workstation_router

load_dotenv()

app = FastAPI(
    title="Pilot Rail Mini",
    description="Human-in-the-loop approval interface for AI-generated infrastructure plans",
    version="0.1.0",
)

_cors_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
_extra = __import__("os").getenv("CORS_ORIGINS", "")
if _extra:
    _cors_origins.extend(o.strip() for o in _extra.split(",") if o.strip())

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(workstation_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
