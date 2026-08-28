class SpeakerAssignmentService:

    # Utilise quand aucun segment de diarisation ne chevauche un segment
    # de transcription (ex: bruit de fond transcrit hors de toute plage
    # de parole detectee par Pyannote). La colonne TranscriptSegment.speaker
    # est NOT NULL en base : un locuteur non identifie doit rester une
    # valeur explicite, jamais None.
    UNKNOWN_SPEAKER = "Inconnu"

    def assign_speakers(
        self,
        transcription_segments: list[dict],
        diarization_segments: list[dict],
    ) -> list[dict]:

        assigned_segments = []

        for transcription in transcription_segments:
            best_speaker = None
            best_overlap = 0.0

            transcription_start = transcription["start"]
            transcription_end = transcription["end"]

            for diarization in diarization_segments:
                diarization_start = diarization["start"]
                diarization_end = diarization["end"]

                overlap_start = max(
                    transcription_start,
                    diarization_start,
                )

                overlap_end = min(
                    transcription_end,
                    diarization_end,
                )

                overlap = max(
                    0.0,
                    overlap_end - overlap_start,
                )

                if overlap > best_overlap:
                    best_overlap = overlap
                    best_speaker = diarization["speaker"]

            assigned_segments.append(
                {
                    **transcription,
                    "speaker": best_speaker or self.UNKNOWN_SPEAKER,
                }
            )

        return assigned_segments