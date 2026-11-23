import hashlib
import secrets
from io import BytesIO
from xml.sax.saxutils import escape

import qrcode
from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hash_verification_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def new_verification_token() -> tuple[str, str]:
    raw_token = secrets.token_urlsafe(32)
    return raw_token, hash_verification_token(raw_token)


def verification_path(raw_token: str) -> str:
    base = getattr(settings, "TRANSCRIPT_VERIFICATION_BASE_URL", "/verify/transcripts")
    return f"{base.rstrip('/')}/{raw_token}"


def generated_pdf_filename(reference: str, version: int) -> str:
    safe_reference = "".join(char for char in reference if char.isalnum() or char in "-_.")
    return f"transcripts/{safe_reference or 'transcript'}-v{version}.pdf"


def _text(value) -> str:
    return escape("" if value is None else str(value))


def _qr_image(path: str) -> BytesIO:
    image = qrcode.make(path)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def render_transcript_pdf(*, document: dict, results: list[dict], verification_url: str) -> bytes:
    buffer = BytesIO()
    institution = document.get("institution", {})
    student = document.get("student", {})
    title = f"{document.get('kind', 'transcript').title()} Transcript"
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        title=title,
        author=str(institution.get("name", "")),
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
    )
    styles = getSampleStyleSheet()
    heading = ParagraphStyle(
        "TranscriptHeading",
        parent=styles["Heading1"],
        alignment=TA_CENTER,
        fontSize=16,
        spaceAfter=4,
    )
    subheading = ParagraphStyle(
        "TranscriptSubheading",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        fontSize=9,
        textColor=colors.HexColor("#555555"),
        spaceAfter=10,
    )
    section = ParagraphStyle(
        "TranscriptSection",
        parent=styles["Heading2"],
        fontSize=11,
        spaceBefore=8,
        spaceAfter=4,
    )
    body = ParagraphStyle("TranscriptBody", parent=styles["Normal"], fontSize=9, leading=12)
    small = ParagraphStyle("TranscriptSmall", parent=styles["Normal"], fontSize=7.5, leading=9)

    story = [
        Paragraph(escape(institution.get("name", "")), heading),
        Paragraph(escape(institution.get("code", "")), subheading),
        Paragraph(escape(title), heading),
        Paragraph(
            _text(
                f"Reference: {document.get('reference_number', '')} | "
                f"Version: {document.get('version', '')}"
            ),
            subheading,
        ),
    ]

    details = [
        ["Student", _text(student.get("full_name", ""))],
        ["Admission number", _text(student.get("admission_number", ""))],
        ["Programme", _text(student.get("programme", ""))],
        ["Graduation date", _text(student.get("graduation_date", "") or "Not recorded")],
        ["Issued", _text(document.get("issued_at", "") or "Not issued")],
    ]
    details_table = Table(details, colWidths=[38 * mm, 140 * mm])
    details_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#555555")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.extend([Paragraph("Student details", section), details_table])

    rows = [["Session", "Term", "Class", "Subject", "Total", "Grade", "Remark"]]
    for result in results:
        rows.append(
            [
                _text(result.get("session", {}).get("code", "")),
                _text(result.get("term", {}).get("code", "")),
                _text(result.get("class_level", {}).get("code", "")),
                _text(result.get("subject", {}).get("name", "")),
                _text(result.get("total_score", "")),
                _text(result.get("grade", "")),
                _text(result.get("remark", "")),
            ]
        )
    results_table = Table(
        rows,
        colWidths=[20 * mm, 14 * mm, 16 * mm, 52 * mm, 18 * mm, 16 * mm, 42 * mm],
        repeatRows=1,
    )
    results_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEEEEE")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#AAAAAA")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.extend([Paragraph("Academic record", section), results_table])

    completeness = document.get("completeness", {})
    story.extend(
        [
            Paragraph("Verification", section),
            Paragraph(
                _text(
                    "Verify this document at the institution verification page using the code "
                    "in the QR image. The QR image contains only a non-guessable reference."
                ),
                body,
            ),
            Image(_qr_image(verification_url), width=32 * mm, height=32 * mm),
            Spacer(1, 4 * mm),
            Paragraph(_text(f"Verification path: {verification_url}"), small),
            Paragraph(
                _text(
                    "Completeness: "
                    + ("complete" if completeness.get("is_complete") else "provisional/incomplete")
                ),
                small,
            ),
        ]
    )
    doc.build(story)
    return buffer.getvalue()
