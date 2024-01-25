from sqlalchemy.orm import Session
import hashlib
import os

from .. import models, schemas


# ------
# Actor
# ------

def _pwd_hash(pwd: str) -> str:
    salt = os.getenv("PASSWORD_SALT", "abcde")
    return hashlib.sha512((salt + pwd).encode()).hexdigest()


def get(db: Session, actor_id: int) -> models.Actor | None:
    # hashed_passwordは返さない
    return db.query(models.Actor).filter(models.Actor.id == actor_id).first()


def get_by_name(db: Session, name: str) -> models.Actor | None:
    return db.query(models.Actor).filter(models.Actor.name == name).first()


def create(db: Session, actor: schemas.ActorCreate) -> models.Actor:
    hashed_password = _pwd_hash(actor.password)
    db_actor = models.Actor(
        name=actor.name,
        hashed_password=hashed_password
    )
    db.add(db_actor)
    db.commit()
    db.refresh(db_actor)
    return db_actor


def verify_password(actor: schemas.Actor, password: str) -> bool:
    return actor.hashed_password == _pwd_hash(password)
