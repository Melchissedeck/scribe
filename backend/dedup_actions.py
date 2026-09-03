"""Script ponctuel — supprime les actions en double en base.

Garde une seule occurrence par (recording_id, description) — la plus
ancienne (id le plus bas) — et supprime les autres.

Usage :
    cd backend
    python dedup_actions.py
"""

from app.database import SessionLocal
from app.models.action import Action
from sqlalchemy import func

db = SessionLocal()

try:
    # Trouve les groupes avec plus d'une action identique
    duplicates = (
        db.query(
            Action.recording_id,
            Action.description,
            func.min(Action.id).label("keep_id"),
            func.count(Action.id).label("cnt"),
        )
        .group_by(Action.recording_id, Action.description)
        .having(func.count(Action.id) > 1)
        .all()
    )

    total_deleted = 0
    for row in duplicates:
        deleted = (
            db.query(Action)
            .filter(
                Action.recording_id == row.recording_id,
                Action.description == row.description,
                Action.id != row.keep_id,
            )
            .delete(synchronize_session=False)
        )
        total_deleted += deleted

    db.commit()
    print(f"Doublons supprimés : {total_deleted} ligne(s).")

except Exception as e:
    db.rollback()
    print(f"Erreur : {e}")
finally:
    db.close()
