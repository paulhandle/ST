from fastapi import FastAPI

from app.api.routes import router
from app.db import Base, SessionLocal, engine
from app.seed import seed_training_methods

app = FastAPI(
    title="ST Athlete Training Planner",
    description="Training planning backend for marathon, trail running and triathlon athletes.",
    version="0.1.0",
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
