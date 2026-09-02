import io
import re
from typing import cast

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.models.recording import Recording

STATUS_LABELS = {'todo': 'À faire', 'in_progress': 'En cours', 'done': 'Terminé'}

_PRIMARY = colors.HexColor('#2563EB')
_HEADER_BG = colors.HexColor('#EAF1FF')
_BORDER = colors.HexColor('#E3E9F2')
_MUTED = colors.HexColor('#64748B')
_ROW_ALT = colors.HexColor('#F9FAFC')


def _md_inline(text: str) -> str:
    """Convert **bold** and *italic* Markdown to reportlab markup (after HTML escaping)."""
    text = _escape(text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
    return text


def _escape(text: str | None) -> str:
    # reportlab interprete le texte des Paragraph comme du mini-XML : il
    # faut echapper le contenu (qui peut venir du LLM ou d'une saisie
    # utilisateur) avant d'y inserer nos propres balises (<br/>, etc.).
    if not text:
        return ''
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


class PDFExportService:
    """Génère le compte-rendu PDF d'une réunion (thème, résumé, décisions, actions)."""

    def __init__(self):
        styles = getSampleStyleSheet()
        self.title_style = ParagraphStyle(
            'ScribeTitle', parent=styles['Title'], fontSize=20, alignment=0, spaceAfter=4,
        )
        self.meta_style = ParagraphStyle(
            'ScribeMeta', parent=styles['Normal'], textColor=_MUTED, fontSize=10, spaceAfter=18,
        )
        self.section_style = ParagraphStyle(
            'ScribeSection', parent=styles['Heading2'], textColor=_PRIMARY, fontSize=13,
            spaceBefore=18, spaceAfter=8,
        )
        self.body_style = ParagraphStyle(
            'ScribeBody', parent=styles['Normal'], fontSize=10.5, leading=15,
        )
        self.table_cell_style = ParagraphStyle(
            'ScribeTableCell', parent=self.body_style, fontSize=9.5, leading=13,
        )

    def generate_pdf(self, recording: Recording) -> bytes:
        """Génère le compte-rendu PDF d'une réunion.

        Le document inclut le thème, la date, le résumé (converti depuis le
        Markdown), les décisions et le tableau des actions.

        Args:
            recording: Réunion pour laquelle générer le compte-rendu.

        Returns:
            Le contenu binaire du fichier PDF généré.
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=2 * cm,
            rightMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
            title=str(recording.theme) if recording.theme else 'Compte-rendu Scribe',
        )

        story = []
        story.append(Paragraph(_escape(self._theme(recording)), self.title_style))
        story.append(Paragraph(self._date_label(recording), self.meta_style))

        story.append(Paragraph('Résumé', self.section_style))
        story.extend(self._parse_summary(str(recording.summary) if recording.summary else ''))

        decisions = self._decisions(recording)
        if decisions:
            story.append(Paragraph('Décisions', self.section_style))
            for decision in decisions:
                story.append(Paragraph(f'•&nbsp;&nbsp;{_escape(decision)}', self.body_style))
                story.append(Spacer(1, 2))

        story.append(Paragraph('Actions', self.section_style))
        actions = list(recording.actions)
        if not actions:
            story.append(Paragraph('Aucune action identifiée pour cette réunion.', self.body_style))
        else:
            story.append(self._actions_table(actions))

        doc.build(story)
        return buffer.getvalue()

    def _theme(self, recording: Recording) -> str:
        theme = str(recording.theme).strip() if recording.theme else ''
        return theme or 'Réunion sans titre'

    def _date_label(self, recording: Recording) -> str:
        if not recording.started_at:
            return ''
        return recording.started_at.strftime('%d/%m/%Y à %H:%M')

    def _decisions(self, recording: Recording) -> list[str]:
        if not recording.decisions:
            return []
        return [str(decision) for decision in cast(list, recording.decisions)]

    def _parse_summary(self, summary: str) -> list:
        """Convert a Markdown summary into a list of reportlab flowables."""
        if not summary.strip():
            return [Paragraph('Aucun résumé disponible pour cette réunion.', self.body_style)]
        flowables = []
        for line in summary.split('\n'):
            line = line.rstrip()
            if not line:
                flowables.append(Spacer(1, 3))
            elif line.startswith('### '):
                flowables.append(Paragraph(_md_inline(line[4:]), self.section_style))
            elif line.startswith('## '):
                flowables.append(Paragraph(_md_inline(line[3:]), self.section_style))
            elif line.startswith('# '):
                flowables.append(Paragraph(_md_inline(line[2:]), self.section_style))
            elif line.startswith('- ') or line.startswith('* '):
                flowables.append(Paragraph(f'•&nbsp;&nbsp;{_md_inline(line[2:])}', self.body_style))
            else:
                flowables.append(Paragraph(_md_inline(line), self.body_style))
        return flowables

    def _actions_table(self, actions: list) -> Table:
        header = ['Description', 'Responsable', 'Statut', 'Échéance']
        rows = [[Paragraph(h, self.table_cell_style) for h in header]]

        for action in actions:
            speaker = action.speaker
            responsable = speaker.provisional_name if speaker else '—'
            status_label = STATUS_LABELS.get(str(action.status), str(action.status))
            due_date = action.due_date.strftime('%d/%m/%Y') if action.due_date else '—'

            rows.append([
                Paragraph(_escape(str(action.description)), self.table_cell_style),
                Paragraph(_escape(responsable), self.table_cell_style),
                Paragraph(_escape(status_label), self.table_cell_style),
                Paragraph(_escape(due_date), self.table_cell_style),
            ])

        table = Table(rows, colWidths=[7.5 * cm, 3.2 * cm, 2.6 * cm, 2.7 * cm], repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), _HEADER_BG),
            ('TEXTCOLOR', (0, 0), (-1, 0), _PRIMARY),
            ('GRID', (0, 0), (-1, -1), 0.5, _BORDER),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, _ROW_ALT]),
        ]))
        return table
