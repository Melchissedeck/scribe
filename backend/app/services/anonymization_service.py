from sqlalchemy.orm import Session

from app.models.speaker import Speaker
from app.models.transcript_segment import TranscriptSegment


def anonymize_recording(db: Session, recording_id: int) -> None:
    """Remplace les noms des locuteurs d'une réunion par un libellé générique.

    Concerne les réunions visio : Vexa peut fournir le nom réel des
    participants (tel qu'affiché sur la plateforme de visioconférence),
    stocké tel quel dans Speaker.provisional_name et TranscriptSegment.speaker.
    Les réunions dictaphone n'ont pas cette exposition : les locuteurs y sont
    déjà des libellés génériques (SPEAKER_00, Inconnu...) issus de Pyannote,
    sans table Speaker associée.

    Irréversible : le nom d'origine n'est conservé nulle part après appel.

    Args:
        db: Session de base de données.
        recording_id: Identifiant de la réunion à anonymiser.
    """
    speakers = (
        db.query(Speaker)
        .filter(Speaker.recording_id == recording_id)
        .order_by(Speaker.id)
        .all()
    )

    label_map: dict[str, str] = {}
    for index, speaker in enumerate(speakers, start=1):
        new_label = f'Locuteur {index}'
        label_map[speaker.provisional_name] = new_label
        speaker.provisional_name = new_label
        speaker.real_name = None

    if label_map:
        segments = (
            db.query(TranscriptSegment)
            .filter(TranscriptSegment.recording_id == recording_id)
            .all()
        )
        for segment in segments:
            new_label = label_map.get(segment.speaker)
            if new_label is not None:
                segment.speaker = new_label

    db.commit()
