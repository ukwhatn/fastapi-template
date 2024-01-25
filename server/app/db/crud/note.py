from sqlalchemy.orm import Session

from .. import models, schemas


# ------
# Template
# ------

# def get(db: Session, note_id: int) -> models.Note | None:
#     return db.query(models.Note).filter(models.Note.id == note_id).first()
#
#
# def get_by_actor(db: Session, actor_id: int) -> list[models.Note]:
#     return db.query(models.Note).filter(models.Note.actor_id == actor_id).all()
#
#
# def get_by_actor_and_id(db: Session, actor_id: int, note_id: int) -> models.Note | None:
#     return db.query(models.Note).filter(models.Note.actor_id == actor_id, models.Note.id == note_id).first()
#
#
# def create(db: Session, note: schemas.NoteCreate) -> models.Note:
#     db_note = models.Note(
#         actor_id=note.actor_id,
#         title=note.title,
#         content=note.content
#     )
#     db.add(db_note)
#     db.commit()
#     db.refresh(db_note)
#     return db_note
