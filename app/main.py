import re

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.db import Base, SessionLocal, engine
from app.seed import seed_training_methods

app = FastAPI(
    title="ST Athlete Training Planner",
    description="Training planning backend for marathon, trail running and triathlon athletes.",
    version="0.1.0",
)

# Allow the web dev server (random port on localhost) to call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=re.compile(r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$").pattern,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_training_methods(db)


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "ST", "status": "running"}
