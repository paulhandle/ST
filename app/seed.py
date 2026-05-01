from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import TrainingMethod
from app.training.knowledge_base import TRAINING_METHOD_DEFINITIONS


def seed_training_methods(db: Session) -> None:
    existing = db.execute(select(TrainingMethod.id).limit(1)).first()
    if existing:
        return

    for item in TRAINING_METHOD_DEFINITIONS:
        db.add(TrainingMethod(**item))
    db.commit()
