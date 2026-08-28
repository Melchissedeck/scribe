from datetime import date, datetime, time

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.dependencies import get_current_user
from app.models.action import Action
from app.models.recording import Recording
from app.models.transcript_segment import TranscriptSegment
from app.models.user import User
from app.schemas.action import ActionResponse
from app.schemas.recording import (
    AnonymizeResponse,
    DiarizedTranscriptResponse,
    MeetingDetailResponse,
    MeetingListItem,
    SegmentClassificationOut,
    SegmentClassificationResponse,
    SegmentOut,
    SpeakerOut,
    SpeakingTimeEntry,
    SpeakingTimeResponse,
    ThemeResponse,
    ThemeUpdate,
)
from app.services.anonymization_service import anonymize_recording
from app.services.llm_service import LLMService
from pdf_export_service import PDFExportService

router = APIRouter(prefix='/meetings', tags=['meetings'])

EXCERPT_LENGTH = 150


def _build_excerpt(summary: str | None) -> str | None:
    if not summary:
        return None
    if len(summary) <= EXCERPT_LENGTH:
        return summary
    return summary[:EXCERPT_LENGTH].rstrip() + '...'


@router.get('', response_model=list[MeetingListItem])
def list_meetings(
    theme: str | None = Query(default=None, description="Filtre sur le thème (recherche partielle, insensible à la casse)"),
    date_from: date | None = Query(default=None, description="Réunions à partir de cette date (incluse)"),
    date_to: date | None = Query(default=None, description="Réunions jusqu'à cette date (incluse)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Recording).filter(Recording.user_id == current_user.id)

    if theme:
        query = query.filter(Recording.theme.ilike(f'%{theme}%'))

    if date_from:
        query = query.filter(Recording.started_at >= datetime.combine(date_from, time.min))

    if date_to:
        query = query.filter(Recording.started_at <= datetime.combine(date_to, time.max))

    recordings = query.order_by(Recording.started_at.desc()).all()

    return [
        MeetingListItem(
            id=recording.id,
            theme=recording.theme,
            date=recording.started_at,
            status=recording.status,
            summary_status=recording.summary_status,
            summary_excerpt=_build_excerpt(recording.summary),
            duration_minutes=(
                (recording.stopped_at - recording.started_at).total_seconds() / 60
                if recording.stopped_at
                else None
            ),
        )
        for recording in recordings
    ]


@router.patch('/{meeting_id}/theme', response_model=ThemeResponse)
def update_meeting_theme(
    meeting_id: int,
    payload: ThemeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    recording = db.query(Recording).filter(
        Recording.id == meeting_id, Recording.user_id == current_user.id
    ).first()
    if not recording:
        raise HTTPException(status_code=404, detail='Réunion introuvable.')

    recording.theme = payload.theme.strip() if payload.theme and payload.theme.strip() else None
    db.commit()
    db.refresh(recording)

    return ThemeResponse(recording_id=recording.id, theme=recording.theme)


@router.get('/{meeting_id}/speaking-time', response_model=SpeakingTimeResponse)
def get_speaking_time(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    recording = db.query(Recording).filter(
        Recording.id == meeting_id, Recording.user_id == current_user.id
    ).first()
    if not recording:
        raise HTTPException(status_code=404, detail='Réunion introuvable.')

    segments = db.query(TranscriptSegment).filter(
        TranscriptSegment.recording_id == meeting_id
    ).all()

    durations: dict[str, float] = {}
    for seg in segments:
        duration = max(0.0, seg.end - seg.start)
        durations[seg.speaker] = durations.get(seg.speaker, 0.0) + duration

    total = sum(durations.values())

    if total == 0:
        return SpeakingTimeResponse(meeting_id=meeting_id, entries=[])

    entries = [
        SpeakingTimeEntry(
            speaker=speaker,
            seconds=round(seconds, 1),
            percentage=round(seconds / total * 100, 1),
        )
        for speaker, seconds in sorted(durations.items(), key=lambda x: -x[1])
    ]

    return SpeakingTimeResponse(meeting_id=meeting_id, entries=entries)


@router.get('/{meeting_id}/diarized-transcript', response_model=DiarizedTranscriptResponse)
def get_diarized_transcript(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    recording = (
        db.query(Recording)
        .filter(Recording.id == meeting_id, Recording.user_id == current_user.id)
        .first()
    )
    if not recording:
        raise HTTPException(status_code=404, detail='Réunion introuvable.')

    segments = (
        db.query(TranscriptSegment)
        .filter(TranscriptSegment.recording_id == meeting_id)
        .order_by(TranscriptSegment.start)
        .all()
    )

    if not segments:
        raise HTTPException(
            status_code=404,
            detail='Aucune diarisation disponible pour cette réunion.',
        )

    return DiarizedTranscriptResponse(
        meeting_id=meeting_id,
        segments=[
            SegmentOut(speaker_name=seg.speaker, text=seg.text)
            for seg in segments
        ],
    )


@router.post('/{meeting_id}/classify-segments', response_model=SegmentClassificationResponse)
def classify_segments(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    recording = (
        db.query(Recording)
        .filter(Recording.id == meeting_id, Recording.user_id == current_user.id)
        .first()
    )
    if not recording:
        raise HTTPException(status_code=404, detail='Réunion introuvable.')

    segments = (
        db.query(TranscriptSegment)
        .filter(TranscriptSegment.recording_id == meeting_id)
        .order_by(TranscriptSegment.start)
        .all()
    )
    if not segments:
        raise HTTPException(
            status_code=400,
            detail='Aucune transcription diarisée disponible pour cette réunion.',
        )

    llm_service = LLMService()
    result = llm_service.classify_segments([str(seg.text) for seg in segments])
    if result is None:
        # Ne peut se produire ici : classify_segments ne renvoie None que
        # pour une liste de segments vide, déjà exclue par le contrôle
        # plus haut. Un échec réel de l'appel API lève LLMError, gérée
        # globalement (voir app/main.py). Ce garde-fou reste pour le typage.
        raise HTTPException(
            status_code=502,
            detail='Le service de classification est momentanément indisponible.',
        )

    classifications_by_index = {c.index: c for c in result.classifications}
    for i, seg in enumerate(segments):
        classification = classifications_by_index.get(i)
        if classification is None:
            continue
        seg.tone = classification.tone
        seg.theme = classification.theme
        seg.urgency = classification.urgency

    db.commit()

    return SegmentClassificationResponse(
        meeting_id=recording.id,
        segments=[
            SegmentClassificationOut(
                id=seg.id,
                speaker_name=seg.speaker,
                text=seg.text,
                start=seg.start,
                tone=seg.tone,
                theme=seg.theme,
                urgency=seg.urgency,
            )
            for seg in segments
        ],
    )


@router.get('/{meeting_id}/segments-classification', response_model=SegmentClassificationResponse)
def get_segments_classification(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    recording = (
        db.query(Recording)
        .filter(Recording.id == meeting_id, Recording.user_id == current_user.id)
        .first()
    )
    if not recording:
        raise HTTPException(status_code=404, detail='Réunion introuvable.')

    segments = (
        db.query(TranscriptSegment)
        .filter(TranscriptSegment.recording_id == meeting_id)
        .order_by(TranscriptSegment.start)
        .all()
    )
    if not segments:
        raise HTTPException(
            status_code=404,
            detail='Aucune diarisation disponible pour cette réunion.',
        )

    return SegmentClassificationResponse(
        meeting_id=recording.id,
        segments=[
            SegmentClassificationOut(
                id=seg.id,
                speaker_name=seg.speaker,
                text=seg.text,
                start=seg.start,
                tone=seg.tone,
                theme=seg.theme,
                urgency=seg.urgency,
            )
            for seg in segments
        ],
    )


@router.post('/{meeting_id}/anonymize', response_model=AnonymizeResponse)
def anonymize_meeting(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remplace les noms des locuteurs d'une réunion par un libellé générique.

    Action irréversible (US-69, droit à l'effacement RGPD) : le nom
    d'origine n'est conservé nulle part une fois l'opération effectuée.
    """
    recording = (
        db.query(Recording)
        .filter(Recording.id == meeting_id, Recording.user_id == current_user.id)
        .first()
    )
    if not recording:
        raise HTTPException(status_code=404, detail='Réunion introuvable.')

    anonymize_recording(db, recording.id)

    segments = (
        db.query(TranscriptSegment)
        .filter(TranscriptSegment.recording_id == meeting_id)
        .order_by(TranscriptSegment.start)
        .all()
    )

    return AnonymizeResponse(
        recording_id=recording.id,
        segments=[
            SegmentOut(speaker_name=seg.speaker, text=seg.text, start=seg.start)
            for seg in segments
        ],
    )


@router.get('/{meeting_id}/details', response_model=MeetingDetailResponse)
def get_meeting_details(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    recording = (
        db.query(Recording)
        .filter(Recording.id == meeting_id, Recording.user_id == current_user.id)
        .options(
            selectinload(Recording.speakers),
            selectinload(Recording.segments),
            selectinload(Recording.actions),
        )
        .first()
    )
    if not recording:
        raise HTTPException(status_code=404, detail='Réunion introuvable.')

    segments = sorted(recording.segments, key=lambda seg: seg.start)

    return MeetingDetailResponse(
        id=recording.id,
        theme=recording.theme,
        status=recording.status,
        platform=recording.platform,
        diarization_status=recording.diarization_status,
        started_at=recording.started_at,
        stopped_at=recording.stopped_at,
        summary=recording.summary,
        speakers=[SpeakerOut.model_validate(speaker) for speaker in recording.speakers],
        segments=[SegmentOut(speaker_name=seg.speaker, text=seg.text, start=seg.start) for seg in segments],
        actions=[ActionResponse.model_validate(action) for action in recording.actions],
    )


@router.get('/{meeting_id}/export-pdf')
def export_meeting_pdf(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    recording = (
        db.query(Recording)
        .filter(Recording.id == meeting_id, Recording.user_id == current_user.id)
        .options(
            selectinload(Recording.actions).selectinload(Action.speaker),
        )
        .first()
    )
    if not recording:
        raise HTTPException(status_code=404, detail='Réunion introuvable.')

    pdf_bytes = PDFExportService().generate_pdf(recording)

    return Response(
        content=pdf_bytes,
        media_type='application/pdf',
        headers={'Content-Disposition': f'attachment; filename="compte-rendu-{meeting_id}.pdf"'},
    )