"""EchoSphere Project Synopsis PDF Generator.

Generates the official 1-page EchoSphere Project Synopsis document strictly using
TrueType 'Times New Roman' throughout the entire document, with large, crisp, prominent
academic typography, an expanded signature area, and staff designations/names positioned
at the absolute bottom of the page with zero overflow.
"""

import os
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import black
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily


def register_times_new_roman():
    """Register authentic Microsoft Times New Roman TrueType fonts."""
    font_paths = {
        'TimesNewRoman': r'C:\Windows\Fonts\times.ttf',
        'TimesNewRoman-Bold': r'C:\Windows\Fonts\timesbd.ttf',
        'TimesNewRoman-Italic': r'C:\Windows\Fonts\timesi.ttf',
        'TimesNewRoman-BoldItalic': r'C:\Windows\Fonts\timesbi.ttf',
    }

    for font_name, font_file in font_paths.items():
        if os.path.exists(font_file):
            pdfmetrics.registerFont(TTFont(font_name, font_file))
        else:
            alt_name = 'Times-Roman' if 'Bold' not in font_name else 'Times-Bold'
            return alt_name

    registerFontFamily(
        'TimesNewRoman',
        normal='TimesNewRoman',
        bold='TimesNewRoman-Bold',
        italic='TimesNewRoman-Italic',
        boldItalic='TimesNewRoman-BoldItalic'
    )
    return 'TimesNewRoman'


def generate_synopsis_pdf(output_filename="EchoSphere_Synopsis_Final.pdf"):
    """Build and save the single-page EchoSphere synopsis PDF with large, readable typography."""
    base_font = register_times_new_roman()
    bold_font = f"{base_font}-Bold" if base_font == 'TimesNewRoman' else 'Times-Bold'

    pdf_path = os.path.abspath(output_filename)

    # A4 dimensions: 595.28 pt width x 841.89 pt height
    # Margins: Left/Right = 36 pt (0.5 in), Top = 20 pt, Bottom = 16 pt
    # Usable width = 595.28 - 72 = 523.28 pt
    # Usable height = 841.89 - 36 = 805.89 pt
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=20,
        bottomMargin=16,
    )

    styles = getSampleStyleSheet()

    # --- Strict Times New Roman Typography Styles (Prominent & Clear) ---
    header_colg_style = ParagraphStyle(
        'HeaderColg',
        parent=styles['Normal'],
        fontName=bold_font,
        fontSize=13,
        leading=15.5,
        alignment=TA_CENTER,
        textColor=black,
    )

    header_dept_style = ParagraphStyle(
        'HeaderDept',
        parent=styles['Normal'],
        fontName=bold_font,
        fontSize=11,
        leading=13.5,
        alignment=TA_CENTER,
        textColor=black,
    )

    header_ay_style = ParagraphStyle(
        'HeaderAY',
        parent=styles['Normal'],
        fontName=base_font,
        fontSize=10,
        leading=12.5,
        alignment=TA_CENTER,
        textColor=black,
    )

    header_sem_style = ParagraphStyle(
        'HeaderSem',
        parent=styles['Normal'],
        fontName=bold_font,
        fontSize=10.2,
        leading=13,
        alignment=TA_CENTER,
        textColor=black,
    )

    box_cell_style = ParagraphStyle(
        'BoxCell',
        parent=styles['Normal'],
        fontName=base_font,
        fontSize=9.7,
        leading=12.1,
        alignment=TA_JUSTIFY,
        textColor=black,
    )

    section_heading_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Normal'],
        fontName=bold_font,
        fontSize=10.5,
        leading=12.8,
        alignment=TA_LEFT,
        textColor=black,
    )

    body_text_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontName=base_font,
        fontSize=9.7,
        leading=12.1,
        alignment=TA_JUSTIFY,
        textColor=black,
    )

    list_item_style = ParagraphStyle(
        'ListItemCustom',
        parent=styles['Normal'],
        fontName=base_font,
        fontSize=9.7,
        leading=11.9,
        alignment=TA_JUSTIFY,
        textColor=black,
        leftIndent=12,
        firstLineIndent=-12,
    )

    table_header_style = ParagraphStyle(
        'TableHead',
        parent=styles['Normal'],
        fontName=bold_font,
        fontSize=9.5,
        leading=11.5,
        alignment=TA_CENTER,
        textColor=black,
    )

    table_center_style = ParagraphStyle(
        'TableCenter',
        parent=styles['Normal'],
        fontName=base_font,
        fontSize=9.5,
        leading=11.5,
        alignment=TA_CENTER,
        textColor=black,
    )

    table_left_style = ParagraphStyle(
        'TableLeft',
        parent=styles['Normal'],
        fontName=base_font,
        fontSize=9.5,
        leading=11.5,
        alignment=TA_LEFT,
        textColor=black,
    )

    sig_block_style = ParagraphStyle(
        'SigBlock',
        parent=styles['Normal'],
        fontName=base_font,
        fontSize=9.5,
        leading=12.8,
        alignment=TA_CENTER,
        textColor=black,
    )

    story = []
    printable_width = 523.28

    # 1. COLLEGE / DEPARTMENT HEADER
    story.append(Paragraph("DON BOSCO INSTITUTE OF TECHNOLOGY BENGALURU", header_colg_style))
    story.append(Spacer(1, 1.5))
    story.append(Paragraph("Department of CSE (AI &amp; ML)", header_dept_style))
    story.append(Spacer(1, 1.5))
    story.append(Paragraph("Academic year: 2026-27 (ODD)", header_ay_style))
    story.append(Spacer(1, 1.5))
    story.append(Paragraph("Major Project Phase-II (BCI786) (7th Semester)", header_sem_style))

    # Space before First Table
    story.append(Spacer(1, 6))

    # 2. FIRST TABLE (Project Title, Abstract, Keywords)
    first_table_data = [
        [
            Paragraph(
                "<b>Project Title:</b> EchoSphere - A Secure AI- and IoT-Enabled Framework for Smart Campus Communication and Announcement Automation",
                box_cell_style,
            )
        ],
        [
            Paragraph(
                "<b>Abstract:</b> EchoSphere is a centralized smart campus announcement management platform designed to replace physical notice boards with role-based access control (RBAC) across 6 hierarchical roles (DevAdmin, Principal, College Admin, HoD, Teacher, Student), automated multi-tier approval workflows, and multi-channel real-time broadcasting. The system integrates an AI microservice engine (utilizing Google Gemini 1.5 and Whisper STT for notice drafting, summarization, spam filtering, duplicate detection, priority/category tagging, and voice synthesis) with real-time WebSocket feeds, FCM mobile push notifications, and a planned IoT smart speaker hardware module (ESP32-S3 / Raspberry Pi Zero 2 W with PCM5102A I2S DAC and TPA3116D2 amplifier). The cross-platform Flutter application (deployed for Android and Windows) ensures zero-layout visual overflow and maintains an immutable database audit log.",
                box_cell_style,
            )
        ],
        [
            Paragraph(
                "<b>Keywords:</b> Artificial Intelligence, Smart Campus, Multi-Tier Approval, Role-Based Access Control, IoT Speaker Nodes, Voice Synthesis, Flutter, FastAPI, PostgreSQL.",
                box_cell_style,
            )
        ],
    ]

    first_table = Table(first_table_data, colWidths=[printable_width])
    first_table.setStyle(
        TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.75, black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, black),
            ('TOPPADDING', (0, 0), (-1, -1), 2.5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
            ('LEFTPADDING', (0, 0), (-1, -1), 4.5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4.5),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ])
    )
    story.append(first_table)
    story.append(Spacer(1, 4))

    # 3. PROBLEM STATEMENT
    story.append(Paragraph("<b>Problem Statement:</b>", section_heading_style))
    story.append(Spacer(1, 1))
    story.append(
        Paragraph(
            "Traditional campus communication relies on physical notice boards, manual public address (PA) announcements, "
            "scattered messaging groups, and paper circulars, leading to communication delays, missed notices, lack of approval "
            "verification, spamming, and an inability to deliver urgent emergency announcements instantaneously to both mobile "
            "devices and physical campus locations. Existing platforms lack automated AI content validation, priority triage, "
            "and integrated hardware speaker queuing. EchoSphere addresses these challenges by providing a secure, AI-assisted "
            "framework that automates notice creation, enforces hierarchical multi-tier approvals, schedules broadcasts, and "
            "delivers real-time notifications across mobile feeds, push alerts, and physical IoT speakers.",
            body_text_style,
        )
    )
    story.append(Spacer(1, 4))

    # 4. OBJECTIVES
    story.append(Paragraph("<b>Objectives:</b>", section_heading_style))
    story.append(Spacer(1, 1))
    objectives = [
        "1. Develop a multi-tiered smart campus announcement platform enforcing 6-role hierarchical RBAC (DevAdmin, Principal, College Admin, HoD, Teacher, Student).",
        "2. Enforce structured approval workflows (Draft -> Pending Approval -> Approved / Rejected / Scheduled / Archived) with immutable audit logs.",
        "3. Integrate an AI microservice engine (Google Gemini 1.5 & Whisper STT) for notice drafting, expansion, spam filtering, duplicate detection, and voice synthesis.",
        "4. Architect departmental IoT smart speaker hardware nodes (ESP32-S3 / Raspberry Pi Zero 2 W with PCM5102A DAC, TPA3116D2 amplifier, and MQTT topic queues) for public broadcasts.",
        "5. Enable real-time multi-channel delivery via WebSockets (in-app feeds), Firebase Cloud Messaging (FCM push notifications), and zero-layout overflow Android/Windows apps.",
    ]
    for obj in objectives:
        story.append(Paragraph(obj, list_item_style))
        story.append(Spacer(1, 1.0))
    story.append(Spacer(1, 3))

    # 5. OUTCOME
    story.append(Paragraph("<b>Outcome:</b>", section_heading_style))
    story.append(Spacer(1, 1))
    story.append(
        Paragraph(
            "EchoSphere provides an adaptive, secure campus announcement platform combining AI notice enhancement, multi-tier "
            "approval workflows, multi-channel real-time delivery, hardware smart speaker architecture, and security audit logging. "
            "The system eliminates manual communication bottlenecks and improves the timeliness, accuracy, and reach of academic "
            "and emergency announcements.",
            body_text_style,
        )
    )
    story.append(Spacer(1, 4))

    # 6. LANGUAGE / SOFTWARE TOOLS USED
    story.append(Paragraph("<b>Language / Software Tools used:</b>", section_heading_style))
    story.append(Spacer(1, 1))
    story.append(
        Paragraph(
            "<b>OS &amp; Clients:</b> Windows; Android (Mobile/Tablet), Windows (Desktop) | "
            "<b>Languages:</b> Python 3.11+, Dart 3.x | "
            "<b>Frameworks:</b> Flutter 3.x, FastAPI (Uvicorn, Async SQLAlchemy, Pydantic, Alembic) | "
            "<b>Database &amp; Cache:</b> PostgreSQL 15, Redis | "
            "<b>AI/ML &amp; Voice Stack:</b> Google Gemini 1.5 API, Whisper STT, PyTorch, Neural TTS | "
            "<b>Hardware Module (Planned):</b> ESP32-S3 / Raspberry Pi Zero 2 W, PCM5102A I2S DAC, TPA3116D2 Class-D Amplifier, 5V Relay Module, PA / Ceiling Speakers | "
            "<b>APIs &amp; Protocols:</b> REST API, WebSockets, MQTT, FCM",
            body_text_style,
        )
    )
    story.append(Spacer(1, 4))

    # 7. GROUP INFORMATION TABLE
    story.append(Paragraph("<b>Group Information:</b>", section_heading_style))
    story.append(Spacer(1, 1))

    group_data = [
        [
            Paragraph("<b>SL.<br/>NO.</b>", table_header_style),
            Paragraph("<b>USN</b>", table_header_style),
            Paragraph("<b>NAME</b>", table_header_style),
            Paragraph("<b>Signature</b>", table_header_style),
        ],
        [
            Paragraph("1", table_center_style),
            Paragraph("1DB23CI079", table_center_style),
            Paragraph("RAKSHITHA S", table_left_style),
            Paragraph("", table_left_style),
        ],
        [
            Paragraph("2", table_center_style),
            Paragraph("1DB23CI085", table_center_style),
            Paragraph("S ANUSHKA", table_left_style),
            Paragraph("", table_left_style),
        ],
        [
            Paragraph("3", table_center_style),
            Paragraph("1DB23CI101", table_center_style),
            Paragraph("SHRUTHI M G", table_left_style),
            Paragraph("", table_left_style),
        ],
        [
            Paragraph("4", table_center_style),
            Paragraph("1DB23CI072", table_center_style),
            Paragraph("POOJITHA H S", table_left_style),
            Paragraph("", table_left_style),
        ],
    ]

    group_table = Table(group_data, colWidths=[42, 98, 190, 193.28], rowHeights=[18, 15, 15, 15, 15])
    group_table.setStyle(
        TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.75, black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, black),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ])
    )
    story.append(group_table)

    # Large signature space (55 pt) pushing staff block flush to the absolute bottom of the page
    story.append(Spacer(1, 55))

    # 8. STAFF DESIGNATIONS & NAMES (Anchored at absolute bottom of page)
    sig_col_w = printable_width / 3.0
    sig_data = [
        [
            Paragraph("<b>Project Guide</b><br/>Dr. B Kursheed", sig_block_style),
            Paragraph("<b>Project Coordinator</b><br/>Mrs. Bharati Rathod", sig_block_style),
            Paragraph("<b>HoD</b><br/>Dr. Shashidhar H R", sig_block_style),
        ]
    ]

    sig_table = Table(sig_data, colWidths=[sig_col_w, sig_col_w, sig_col_w])
    sig_table.setStyle(
        TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ])
    )
    story.append(sig_table)

    # Check page count
    class PageCountChecker:
        def __init__(self):
            self.count = 0

        def __call__(self, canvas, doc):
            self.count += 1

    checker = PageCountChecker()
    doc.build(story, onFirstPage=checker, onLaterPages=checker)
    print(f"Generated PDF with {checker.count} page(s).")
    assert checker.count == 1, f"Error: PDF generated {checker.count} pages instead of exactly 1 page!"
    return checker.count


if __name__ == "__main__":
    generate_synopsis_pdf()
