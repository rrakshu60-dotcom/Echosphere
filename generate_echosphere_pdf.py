import os
import sys
from PIL import Image, ImageDraw, ImageFont

from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable, Image as RLImage
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

# ==========================================
# 1. DIAGRAM GENERATION HELPERS (PIL)
# ==========================================

def get_font(size=14, bold=False):
    """Fallback font loader using default PIL font or standard truetype font if available."""
    try:
        if bold:
            return ImageFont.truetype("arialbd.ttf", size)
        else:
            return ImageFont.truetype("arial.ttf", size)
    except Exception:
        try:
            if bold:
                return ImageFont.truetype("DejaVuSans-Bold.ttf", size)
            else:
                return ImageFont.truetype("DejaVuSans.ttf", size)
        except Exception:
            return ImageFont.load_default()

def draw_rounded_rect(draw, box, radius, fill, outline=None, width=1):
    """Draw a rounded rectangle on a PIL ImageDraw surface."""
    x1, y1, x2, y2 = box
    draw.rounded_rectangle([x1, y1, x2, y2], radius=radius, fill=fill, outline=outline, width=width)

def create_architecture_diagram_image(filename="architecture_diagram.png"):
    """Generates a high-resolution crisp System Architecture Diagram."""
    img_w, img_h = 2200, 1500
    img = Image.new("RGBA", (img_w, img_h), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Fonts
    title_font = get_font(34, bold=True)
    subtitle_font = get_font(20, bold=False)
    header_font = get_font(22, bold=True)
    box_title_font = get_font(18, bold=True)
    box_body_font = get_font(15, bold=False)
    arrow_font = get_font(14, bold=True)

    # Title Banner
    draw_rounded_rect(draw, (50, 40, img_w - 50, 130), 12, fill="#1E3A8A", outline="#1E40AF", width=2)
    draw.text((80, 58), "ECHOSPHERE v2.2 — SYSTEM ARCHITECTURE DIAGRAM", fill="#FFFFFF", font=title_font)
    draw.text((80, 98), "Multi-Tier Hybrid Microservices & Audio Broadcast Infrastructure", fill="#93C5FD", font=subtitle_font)

    # Tiers Definition
    tiers = [
        {
            "title": "PRESENTATION & CLIENT TIER",
            "subtitle": "Cross-Platform User Interfaces (Flutter Framework)",
            "bg": "#EFF6FF", "border": "#3B82F6", "header_bg": "#1D4ED8",
            "box": (80, 170, 700, 1380),
            "items": [
                ("DevAdmin Portal", "System config, role delegation, global broadcast control"),
                ("Principal Dashboard", "College-wide approval, priority triage, analytics"),
                ("College Admin Portal", "Department management, user onboarding, role matrix"),
                ("HOD Interface", "Departmental announcements, draft approvals, archives"),
                ("Teacher Mobile App", "Speech-to-Text creation, class notices, audio queue"),
                ("Student Mobile App", "Push notification receiver, audio feed, categorized view"),
                ("Client Features", "Zero Overflow Guarantee, FCM Receiver, WS Client")
            ]
        },
        {
            "title": "API GATEWAY & CORE BACKEND",
            "subtitle": "FastAPI App Server & Security Middleware",
            "bg": "#ECFDF5", "border": "#10B981", "header_bg": "#047857",
            "box": (750, 170, 1450, 750),
            "items": [
                ("REST API Endpoints", "JSON web services, announcement CRUD, user management"),
                ("JWT Security & RBAC", "Role token validation, permission guards, CORS middleware"),
                ("WebSocket Broker", "Real-time announcement broadcast & live status sync"),
                ("Approval Engine", "Multi-tier state machine (Draft -> Approved -> Archived)"),
                ("Audit Logging Engine", "Immutable action recorder, IP tracking & security trace")
            ]
        },
        {
            "title": "AI/ML INTELLIGENCE MICROSERVICE",
            "subtitle": "FastAPI AI Engine & Smart NLP Pipelines",
            "bg": "#F5F3FF", "border": "#8B5CF6", "header_bg": "#6D28D9",
            "box": (1500, 170, 2120, 750),
            "items": [
                ("Whisper STT", "Voice-to-text announcement composition"),
                ("AI Text Expander", "Bullet points to rich announcement text"),
                ("Emergency Classifier", "Urgency detection & auto priority bump"),
                ("Spam & Moderation", "Content safety check & toxicity filter"),
                ("Smart Categorizer", "Automatic tag & category recommendation"),
                ("Voice Summarizer", "Audio transcript key point extractor")
            ]
        },
        {
            "title": "AUDIO BROADCAST & QUEUE SUBSYSTEM",
            "subtitle": "Asynchronous Audio Synthesis & Hardware Dispatch",
            "bg": "#FFFBEB", "border": "#F59E0B", "header_bg": "#B45309",
            "box": (750, 800, 1450, 1380),
            "items": [
                ("Speaker Queue Worker", "Async job processing, priority play queue"),
                ("Text-to-Speech Engine", "Multi-lingual neural voice audio generation"),
                ("PA Speaker Dispatcher", "Multi-zone physical & IoT virtual speaker driver"),
                ("Push Dispatcher", "Firebase Cloud Messaging (FCM) integration"),
                ("Multi-Channel Router", "Visual displays, mobile feed, audio broadcast sync")
            ]
        },
        {
            "title": "DATA INTEGRITY & CACHING TIER",
            "subtitle": "Relational Storage & In-Memory Messaging",
            "bg": "#F8FAFC", "border": "#64748B", "header_bg": "#334155",
            "box": (1500, 800, 2120, 1380),
            "items": [
                ("PostgreSQL DB", "Primary relational store (SQLAlchemy + Alembic)"),
                ("Redis Cache", "Session storage, WebSocket pub/sub, queue lock"),
                ("Media Storage", "Synthesized MP3/WAV audio & attachments"),
                ("Migration Engine", "Schema versioning & automatic rollback")
            ]
        }
    ]

    for tier in tiers:
        bx1, by1, bx2, by2 = tier["box"]
        # Container background
        draw_rounded_rect(draw, (bx1, by1, bx2, by2), 10, fill=tier["bg"], outline=tier["border"], width=2)
        # Header banner
        draw_rounded_rect(draw, (bx1, by1, bx2, by1 + 60), 10, fill=tier["header_bg"])
        draw.rectangle([bx1, by1 + 30, bx2, by1 + 60], fill=tier["header_bg"])
        draw.text((bx1 + 15, by1 + 10), tier["title"], fill="#FFFFFF", font=header_font)
        draw.text((bx1 + 15, by1 + 38), tier["subtitle"], fill="#E0F2FE", font=get_font(12, bold=False))

        # Content Items
        iy = by1 + 75
        for title, desc in tier["items"]:
            draw_rounded_rect(draw, (bx1 + 15, iy, bx2 - 15, iy + 60), 6, fill="#FFFFFF", outline=tier["border"], width=1)
            draw.text((bx1 + 25, iy + 8), title, fill="#0F172A", font=box_title_font)
            draw.text((bx1 + 25, iy + 33), desc, fill="#475569", font=box_body_font)
            iy += 68

    # Inter-Tier Connection Arrows with Labels
    arrow_color = "#2563EB"
    
    # Client -> Core Backend
    draw.line([(700, 400), (750, 400)], fill=arrow_color, width=4)
    draw.polygon([(750, 400), (740, 392), (740, 408)], fill=arrow_color)
    draw.text((705, 375), "HTTPS / WSS", fill="#1D4ED8", font=arrow_font)

    # Core Backend <-> AI Microservice
    draw.line([(1450, 400), (1500, 400)], fill="#7C3AED", width=4)
    draw.polygon([(1500, 400), (1490, 392), (1490, 408)], fill="#7C3AED")
    draw.text((1452, 375), "gRPC / REST", fill="#6D28D9", font=arrow_font)

    # Core Backend -> Speaker Queue
    draw.line([(1100, 750), (1100, 800)], fill="#D97706", width=4)
    draw.polygon([(1100, 800), (1092, 790), (1108, 790)], fill="#D97706")
    draw.text((1110, 765), "Async Task", fill="#B45309", font=arrow_font)

    # Audio Subsystem -> Data Tier
    draw.line([(1450, 1100), (1500, 1100)], fill="#475569", width=4)
    draw.polygon([(1500, 1100), (1490, 1092), (1490, 1108)], fill="#475569")
    draw.text((1452, 1075), "Queue Sync", fill="#334155", font=arrow_font)

    # Core Backend -> Data Tier
    draw.line([(1450, 600), (1500, 900)], fill="#059669", width=4)
    draw.polygon([(1500, 900), (1485, 890), (1495, 905)], fill="#059669")
    draw.text((1455, 730), "SQL / Redis", fill="#047857", font=arrow_font)

    img.save(filename, "PNG")
    return filename


def create_er_diagram_image(filename="er_diagram.png"):
    """Generates a high-resolution crisp Entity-Relationship (ER) Diagram."""
    img_w, img_h = 2400, 1750
    img = Image.new("RGBA", (img_w, img_h), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)

    title_font = get_font(34, bold=True)
    subtitle_font = get_font(20, bold=False)
    header_font = get_font(18, bold=True)
    field_font = get_font(13, bold=False)
    pk_font = get_font(13, bold=True)
    card_font = get_font(14, bold=True)

    # Title Banner
    draw_rounded_rect(draw, (50, 40, img_w - 50, 130), 12, fill="#0F172A", outline="#334155", width=2)
    draw.text((80, 58), "ECHOSPHERE v2.2 — ENTITY-RELATIONSHIP (ER) DIAGRAM", fill="#FFFFFF", font=title_font)
    draw.text((80, 98), "Relational Database Schema, Cardinality & Foreign Key Dependencies", fill="#94A3B8", font=subtitle_font)

    # Entities configuration
    entities = {
        "Role": {
            "box": (80, 170, 430, 410), "bg": "#EFF6FF", "header_bg": "#1D4ED8",
            "fields": [("id", "INTEGER (PK)"), ("name", "VARCHAR(50)"), ("description", "TEXT"), ("created_at", "TIMESTAMP")]
        },
        "Department": {
            "box": (80, 460, 430, 700), "bg": "#EFF6FF", "header_bg": "#1D4ED8",
            "fields": [("id", "INTEGER (PK)"), ("name", "VARCHAR(100)"), ("code", "VARCHAR(20)"), ("created_at", "TIMESTAMP")]
        },
        "User": {
            "box": (550, 200, 950, 620), "bg": "#FEF3C7", "header_bg": "#D97706",
            "fields": [
                ("id", "INTEGER (PK)"), ("name", "VARCHAR(100)"), ("email", "VARCHAR(150) (UQ)"),
                ("hashed_password", "VARCHAR(255)"), ("role_id", "INTEGER (FK)"),
                ("department_id", "INTEGER (FK)"), ("is_active", "BOOLEAN"),
                ("created_at", "TIMESTAMP"), ("updated_at", "TIMESTAMP")
            ]
        },
        "AnnouncementCategory": {
            "box": (1070, 170, 1470, 410), "bg": "#ECFDF5", "header_bg": "#047857",
            "fields": [("id", "INTEGER (PK)"), ("name", "VARCHAR(50)"), ("description", "TEXT"), ("color_code", "VARCHAR(10)")]
        },
        "Announcement": {
            "box": (1070, 460, 1500, 980), "bg": "#F5F3FF", "header_bg": "#6D28D9",
            "fields": [
                ("id", "INTEGER (PK)"), ("title", "VARCHAR(200)"), ("content", "TEXT"),
                ("author_id", "INTEGER (FK)"), ("category_id", "INTEGER (FK)"),
                ("department_id", "INTEGER (FK)"), ("priority", "VARCHAR(20)"),
                ("status", "VARCHAR(30)"), ("scheduled_at", "TIMESTAMP"),
                ("expires_at", "TIMESTAMP"), ("created_at", "TIMESTAMP"), ("updated_at", "TIMESTAMP")
            ]
        },
        "AnnouncementApproval": {
            "box": (1600, 170, 2050, 450), "bg": "#FDF2F8", "header_bg": "#BE185D",
            "fields": [
                ("id", "INTEGER (PK)"), ("announcement_id", "INTEGER (FK)"),
                ("approver_id", "INTEGER (FK)"), ("status", "VARCHAR(20)"),
                ("comments", "TEXT"), ("reviewed_at", "TIMESTAMP")
            ]
        },
        "AnnouncementArchive": {
            "box": (1600, 480, 2050, 720), "bg": "#F1F5F9", "header_bg": "#475569",
            "fields": [
                ("id", "INTEGER (PK)"), ("announcement_id", "INTEGER (FK)"),
                ("archived_by_id", "INTEGER (FK)"), ("reason", "TEXT"), ("archived_at", "TIMESTAMP")
            ]
        },
        "DeliveryType": {
            "box": (1070, 1030, 1470, 1240), "bg": "#ECFDF5", "header_bg": "#047857",
            "fields": [("id", "INTEGER (PK)"), ("name", "VARCHAR(50)"), ("description", "TEXT")]
        },
        "AnnouncementDelivery": {
            "box": (1600, 1030, 2050, 1270), "bg": "#EFF6FF", "header_bg": "#1D4ED8",
            "fields": [
                ("id", "INTEGER (PK)"), ("announcement_id", "INTEGER (FK)"),
                ("delivery_type_id", "INTEGER (FK)"), ("status", "VARCHAR(20)"), ("delivered_at", "TIMESTAMP")
            ]
        },
        "SpeakerQueue": {
            "box": (1600, 760, 2050, 1000), "bg": "#FFFBEB", "header_bg": "#B45309",
            "fields": [
                ("id", "INTEGER (PK)"), ("announcement_id", "INTEGER (FK)"),
                ("audio_url", "VARCHAR(255)"), ("priority", "INTEGER"),
                ("status", "VARCHAR(20)"), ("played_at", "TIMESTAMP")
            ]
        },
        "Notification": {
            "box": (1070, 1310, 1500, 1680), "bg": "#FDF2F8", "header_bg": "#BE185D",
            "fields": [
                ("id", "INTEGER (PK)"), ("user_id", "INTEGER (FK)"),
                ("announcement_id", "INTEGER (FK)"), ("title", "VARCHAR(150)"),
                ("message", "TEXT"), ("is_read", "BOOLEAN"),
                ("channel", "VARCHAR(30)"), ("created_at", "TIMESTAMP")
            ]
        },
        "AuditLog": {
            "box": (550, 700, 950, 1000), "bg": "#F1F5F9", "header_bg": "#334155",
            "fields": [
                ("id", "INTEGER (PK)"), ("user_id", "INTEGER (FK)"),
                ("action", "VARCHAR(100)"), ("resource_type", "VARCHAR(50)"),
                ("resource_id", "INTEGER"), ("ip_address", "VARCHAR(45)"), ("timestamp", "TIMESTAMP")
            ]
        },
        "PasswordResetToken": {
            "box": (550, 1040, 950, 1280), "bg": "#FEF2F2", "header_bg": "#DC2626",
            "fields": [
                ("id", "INTEGER (PK)"), ("user_id", "INTEGER (FK)"),
                ("token", "VARCHAR(255) (UQ)"), ("expires_at", "TIMESTAMP"), ("is_used", "BOOLEAN")
            ]
        }
    }

    # Render entities
    for name, entity in entities.items():
        bx1, by1, bx2, by2 = entity["box"]
        draw_rounded_rect(draw, (bx1, by1, bx2, by2), 8, fill=entity["bg"], outline=entity["header_bg"], width=2)
        # Header banner
        draw_rounded_rect(draw, (bx1, by1, bx2, by1 + 42), 8, fill=entity["header_bg"])
        draw.rectangle([bx1, by1 + 20, bx2, by1 + 42], fill=entity["header_bg"])
        draw.text((bx1 + 12, by1 + 10), name.upper(), fill="#FFFFFF", font=header_font)

        # Fields list
        fy = by1 + 52
        for fname, ftype in entity["fields"]:
            is_pk_fk = "(PK)" in ftype or "(FK)" in ftype
            f_font = pk_font if is_pk_fk else field_font
            f_color = "#1E293B" if is_pk_fk else "#475569"
            draw.text((bx1 + 12, fy), fname, fill=f_color, font=f_font)
            draw.text((bx1 + 175, fy), ftype, fill="#64748B", font=field_font)
            fy += 24

    # Relationship connectors with cardinality markers
    def draw_rel(p1, p2, c1, c2, color="#2563EB"):
        draw.line([p1, p2], fill=color, width=3)
        draw.text((p1[0] + 8, p1[1] - 15), c1, fill="#1D4ED8", font=card_font)
        draw.text((p2[0] - 22, p2[1] - 15), c2, fill="#1D4ED8", font=card_font)

    # Role (1) -> User (N)
    draw_rel((430, 290), (550, 290), "1", "N")
    # Department (1) -> User (N)
    draw_rel((430, 580), (550, 510), "1", "N")
    # User (1) -> Announcement (N)
    draw_rel((950, 410), (1070, 520), "1", "N")
    # Category (1) -> Announcement (N)
    draw_rel((1270, 410), (1270, 460), "1", "N")
    # Announcement (1) -> AnnouncementApproval (N)
    draw_rel((1500, 500), (1600, 310), "1", "N")
    # User (Approver) (1) -> AnnouncementApproval (N)
    draw.line([(750, 200), (750, 150), (1825, 150), (1825, 170)], fill="#D97706", width=2)
    draw.text((1830, 152), "N", fill="#B45309", font=card_font)
    # Announcement (1) -> AnnouncementArchive (0..1)
    draw_rel((1500, 600), (1600, 600), "1", "0..1")
    # Announcement (1) -> SpeakerQueue (N)
    draw_rel((1500, 720), (1600, 850), "1", "N")
    # Announcement (1) -> AnnouncementDelivery (N)
    draw_rel((1500, 900), (1600, 1100), "1", "N")
    # DeliveryType (1) -> AnnouncementDelivery (N)
    draw_rel((1470, 1130), (1600, 1130), "1", "N")
    # User (1) -> Notification (N)
    draw.line([(750, 620), (750, 1480), (1070, 1480)], fill="#BE185D", width=2)
    draw.text((1045, 1460), "N", fill="#BE185D", font=card_font)
    # User (1) -> AuditLog (N)
    draw_rel((750, 620), (750, 700), "1", "N")
    # User (1) -> PasswordResetToken (N)
    draw.line([(650, 620), (650, 1040)], fill="#DC2626", width=2)

    img.save(filename, "PNG")
    return filename


# ==========================================
# 2. TWO-PASS REPORTLAB CANVAS
# ==========================================

class MasterNumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute and draw total page numbers,
    running headers, and running footers.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(HexColor("#475569"))

        # Running Header (Pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, 750, "ECHOSPHERE v2.2 — SYSTEM ARCHITECTURE, ERD & METHODOLOGY")
            self.setFont("Helvetica", 8)
            self.drawRightString(558, 750, "Exhaustive Technical Engineering Specification")
            self.setStrokeColor(HexColor("#CBD5E1"))
            self.setLineWidth(0.75)
            self.line(54, 742, 558, 742)

        # Running Footer (All Pages)
        self.setStrokeColor(HexColor("#CBD5E1"))
        self.setLineWidth(0.75)
        self.line(54, 45, 558, 45)

        self.setFont("Helvetica", 8)
        self.drawString(54, 32, "Confidential & Proprietary — EchoSphere Software Engineering Group")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 32, page_str)
        self.restoreState()


# ==========================================
# 3. CALLOUT BUILDER
# ==========================================

def create_callout(text, title="KEY ARCHITECTURAL HIGHLIGHT", bg_color="#F8FAFC", border_color="#1E3A8A"):
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CalloutTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=11,
        textColor=HexColor(border_color),
        spaceAfter=3
    )
    body_style = ParagraphStyle(
        'CalloutBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11.5,
        textColor=HexColor('#1E293B')
    )

    content = [
        Paragraph(title.upper(), title_style),
        Paragraph(text, body_style)
    ]

    t = Table([[content]], colWidths=[504])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), HexColor(bg_color)),
        ('LINELEFT', (0, 0), (0, 0), 3.5, HexColor(border_color)),
        ('BOX', (0, 0), (-1, -1), 0.5, HexColor("#E2E8F0")),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))
    return t


# ==========================================
# 4. MAIN PDF BUILDER
# ==========================================

def build_pdf(filename="EchoSphere_System_Architecture_ERD_Methodology.pdf"):
    # Generate diagrams
    arch_img_path = create_architecture_diagram_image()
    er_img_path = create_er_diagram_image()

    pdf_path = os.path.abspath(filename)
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()

    # Custom typography styles
    title_style = ParagraphStyle(
        'DocTitle', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=26, leading=30, textColor=HexColor('#0F172A'), spaceAfter=8
    )
    subtitle_style = ParagraphStyle(
        'DocSubTitle', parent=styles['Normal'],
        fontName='Helvetica', fontSize=13, leading=17, textColor=HexColor('#2563EB'), spaceAfter=20
    )
    h1_style = ParagraphStyle(
        'Heading1_Custom', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=16, leading=20, textColor=HexColor('#0F172A'), spaceBefore=18, spaceAfter=8, keepWithNext=True
    )
    h2_style = ParagraphStyle(
        'Heading2_Custom', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=12, leading=16, textColor=HexColor('#1E3A8A'), spaceBefore=12, spaceAfter=6, keepWithNext=True
    )
    body_style = ParagraphStyle(
        'Body_Custom', parent=styles['Normal'],
        fontName='Helvetica', fontSize=9.5, leading=13.5, textColor=HexColor('#334155'), spaceAfter=8
    )
    bullet_style = ParagraphStyle(
        'Bullet_Custom', parent=body_style,
        leftIndent=15, firstLineIndent=-10, spaceAfter=4
    )
    table_header_style = ParagraphStyle(
        'TableHeader', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=8.5, leading=10, textColor=HexColor('#FFFFFF'), alignment=0
    )
    table_cell_style = ParagraphStyle(
        'TableCell', parent=styles['Normal'],
        fontName='Helvetica', fontSize=8, leading=10.5, textColor=HexColor('#1E293B')
    )
    table_cell_bold = ParagraphStyle(
        'TableCellBold', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=8, leading=10.5, textColor=HexColor('#0F172A')
    )

    story = []

    # ---------------------------------------------------------
    # COVER / HEADER PAGE
    # ---------------------------------------------------------
    story.append(Spacer(1, 10))
    story.append(Paragraph("ECHOSPHERE v2.2", title_style))
    story.append(Paragraph("System Architecture, ER Diagram & Operational Methodology Manual", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=HexColor('#2563EB'), spaceBefore=0, spaceAfter=15))

    # Executive Box
    meta_table_data = [
        [Paragraph("<b>System Name:</b> EchoSphere Campus Broadcast", table_cell_style), Paragraph("<b>Version:</b> 2.2 Release", table_cell_style)],
        [Paragraph("<b>Architecture:</b> Hybrid Microservices & Event Audio", table_cell_style), Paragraph("<b>Primary Target:</b> Android Mobile APK", table_cell_style)],
        [Paragraph("<b>Database:</b> PostgreSQL 15 + Redis Pub/Sub", table_cell_style), Paragraph("<b>AI Subsystem:</b> Whisper STT & FastNLP", table_cell_style)],
        [Paragraph("<b>Document Scope:</b> Architectural Specification, ERD, Methodology", table_cell_style), Paragraph("<b>Classification:</b> Proprietary Technical Manual", table_cell_style)]
    ]
    meta_table = Table(meta_table_data, colWidths=[252, 252])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), HexColor('#F8FAFC')),
        ('BOX', (0, 0), (-1, -1), 1, HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, HexColor('#E2E8F0')),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 15))

    # Executive Overview Callout
    exec_summary = (
        "<b>EchoSphere v2.2</b> represents a state-of-the-art multi-channel campus announcement and public address system. "
        "Engineered with a high-concurrency FastAPI core backend, a dedicated AI/ML microservice, and a cross-platform Flutter client, "
        "EchoSphere automates the entire lifecycle of campus communication—from voice-assisted drafting, spam/toxicity filtering, "
        "and multi-level role authorization to real-time physical speaker output and mobile push dispatch."
    )
    story.append(create_callout(exec_summary, title="EXECUTIVE SUMMARY & SYSTEM SCOPE", bg_color="#EFF6FF", border_color="#2563EB"))
    story.append(Spacer(1, 15))

    # ---------------------------------------------------------
    # SECTION 1: SYSTEM ARCHITECTURE SPECIFICATION
    # ---------------------------------------------------------
    story.append(Paragraph("1. System Architecture Specification", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=HexColor('#0F172A'), spaceBefore=2, spaceAfter=10))

    story.append(Paragraph(
        "EchoSphere v2.2 employs a high-performance <b>Multi-Tier Hybrid Microservices Architecture</b> designed for scalability, zero visual overflow across mobile aspect ratios, and reliable real-time broadcast execution.",
        body_style
    ))

    # Visual Architecture Diagram Image
    story.append(Spacer(1, 5))
    story.append(RLImage(arch_img_path, width=504, height=343))
    story.append(Spacer(1, 10))

    # Tier Breakdown Table
    arch_table_data = [
        [Paragraph("Architectural Tier", table_header_style), Paragraph("Technologies", table_header_style), Paragraph("Core Responsibilities & Components", table_header_style)],
        [
            Paragraph("Presentation / Client", table_cell_bold),
            Paragraph("Flutter 3.x, Dart, FCM SDK", table_cell_style),
            Paragraph("Cross-platform mobile & web client covering 6 roles. Enforces Zero Overflow Guarantee via responsive flexible constraints.", table_cell_style)
        ],
        [
            Paragraph("API Gateway & Core Backend", table_cell_bold),
            Paragraph("FastAPI, Python 3.11, OAuth2/JWT, WebSockets", table_cell_style),
            Paragraph("RESTful endpoints, JWT security middleware, RBAC enforcement, WebSocket live feed, approval flow state machine.", table_cell_style)
        ],
        [
            Paragraph("AI/ML Intelligence Service", table_cell_bold),
            Paragraph("FastAPI, Whisper STT, PyTorch, Transformers", table_cell_style),
            Paragraph("Speech-to-text drafting, AI bullet text expander, emergency urgency classifier, toxicity/spam moderation, smart tag recommendation.", table_cell_style)
        ],
        [
            Paragraph("Audio & Broadcast Subsystem", table_cell_bold),
            Paragraph("Asyncio Workers, Neural TTS, Celery/Redis", table_cell_style),
            Paragraph("Priority speaker queue worker, multi-lingual TTS audio synthesis, physical PA zone driver, FCM push dispatcher.", table_cell_style)
        ],
        [
            Paragraph("Data Integrity & Caching", table_cell_bold),
            Paragraph("PostgreSQL 15, SQLAlchemy, Alembic, Redis", table_cell_style),
            Paragraph("ACID relational database store with 3NF schema, immutable audit logging, Redis session cache, and WebSocket pub/sub broker.", table_cell_style)
        ]
    ]
    arch_table = Table(arch_table_data, colWidths=[110, 110, 284])
    arch_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#1E3A8A')),
        ('BOX', (0, 0), (-1, -1), 1, HexColor('#94A3B8')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, HexColor('#CBD5E1')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('PADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(arch_table)
    story.append(Spacer(1, 15))

    # Page Break for ERD Section
    story.append(PageBreak())

    # ---------------------------------------------------------
    # SECTION 2: ENTITY-RELATIONSHIP (ER) DIAGRAM & SCHEMA
    # ---------------------------------------------------------
    story.append(Paragraph("2. Entity-Relationship (ER) Diagram & Schema", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=HexColor('#0F172A'), spaceBefore=2, spaceAfter=10))

    story.append(Paragraph(
        "The EchoSphere v2.2 relational database schema is structured in <b>Third Normal Form (3NF)</b> to eliminate redundancy, enforce strict referential integrity, and maintain a complete audit trace of all communication activities.",
        body_style
    ))

    # Visual ER Diagram Image
    story.append(Spacer(1, 5))
    story.append(RLImage(er_img_path, width=504, height=367))
    story.append(Spacer(1, 12))

    # Data Dictionary Specifications
    story.append(Paragraph("Comprehensive Data Dictionary & Entity Specifications", h2_style))

    # Table specs data generator
    models_spec = [
        ("User", "Stores user profiles, credentials, role assignments, and department affiliations.", [
            ("id", "INTEGER", "PK, Auto", "Unique user identifier"),
            ("name", "VARCHAR(100)", "NOT NULL", "Full name of the user"),
            ("email", "VARCHAR(150)", "UQ, NOT NULL", "Official campus email address"),
            ("hashed_password", "VARCHAR(255)", "NOT NULL", "Bcrypt hashed security password"),
            ("role_id", "INTEGER", "FK -> Role.id", "Assigned RBAC system role"),
            ("department_id", "INTEGER", "FK -> Dept.id", "Associated department reference"),
            ("is_active", "BOOLEAN", "DEFAULT TRUE", "Account active/disabled flag")
        ]),
        ("Announcement", "Core entity representing campus communications across approval states.", [
            ("id", "INTEGER", "PK, Auto", "Unique announcement identifier"),
            ("title", "VARCHAR(200)", "NOT NULL", "Announcement headline/subject"),
            ("content", "TEXT", "NOT NULL", "Full announcement body text"),
            ("author_id", "INTEGER", "FK -> User.id", "Creator / author user reference"),
            ("category_id", "INTEGER", "FK -> Cat.id", "Category taxonomy classification"),
            ("department_id", "INTEGER", "FK -> Dept.id", "Target department filter (NULL = All)"),
            ("priority", "VARCHAR(20)", "DEFAULT 'NORMAL'", "Urgency priority level (EMERGENCY, HIGH, NORMAL)"),
            ("status", "VARCHAR(30)", "DEFAULT 'DRAFT'", "Lifecycle status (DRAFT, PENDING, APPROVED, REJECTED, ARCHIVED)")
        ]),
        ("SpeakerQueue", "Manages audio synthesis jobs and physical PA speaker play queues.", [
            ("id", "INTEGER", "PK, Auto", "Queue item identifier"),
            ("announcement_id", "INTEGER", "FK -> Ann.id", "Target announcement for audio playback"),
            ("audio_url", "VARCHAR(255)", "NOT NULL", "Path to synthesized MP3/WAV file"),
            ("priority", "INTEGER", "DEFAULT 0", "Play queue priority weight"),
            ("status", "VARCHAR(20)", "DEFAULT 'PENDING'", "Execution state (PENDING, PLAYING, COMPLETED, FAILED)")
        ]),
        ("AuditLog", "Immutable security log tracking system actions, approvals, and logins.", [
            ("id", "INTEGER", "PK, Auto", "Audit entry identifier"),
            ("user_id", "INTEGER", "FK -> User.id", "Actor performing the action"),
            ("action", "VARCHAR(100)", "NOT NULL", "Action keyword (LOGIN, CREATE, APPROVE, ARCHIVE)"),
            ("resource_type", "VARCHAR(50)", "NOT NULL", "Target entity table name"),
            ("ip_address", "VARCHAR(45)", "NOT NULL", "Client IP address for security tracing")
        ])
    ]

    for model_name, desc, fields in models_spec:
        story.append(Paragraph(f"Entity: <b>{model_name}</b> — <i>{desc}</i>", h2_style))
        tbl_data = [[Paragraph("Column", table_header_style), Paragraph("Data Type", table_header_style), Paragraph("Constraints", table_header_style), Paragraph("Description", table_header_style)]]
        for fn, ft, fc, fd in fields:
            tbl_data.append([
                Paragraph(fn, table_cell_bold),
                Paragraph(ft, table_cell_style),
                Paragraph(fc, table_cell_style),
                Paragraph(fd, table_cell_style)
            ])
        t = Table(tbl_data, colWidths=[110, 95, 95, 204])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#334155')),
            ('BOX', (0, 0), (-1, -1), 0.75, HexColor('#94A3B8')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, HexColor('#CBD5E1')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(t)
        story.append(Spacer(1, 6))

    # Page Break for Methodology Section
    story.append(PageBreak())

    # ---------------------------------------------------------
    # SECTION 3: SYSTEM METHODOLOGY & OPERATIONAL WORKFLOWS
    # ---------------------------------------------------------
    story.append(Paragraph("3. System Methodology & Operational Workflows", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=HexColor('#0F172A'), spaceBefore=2, spaceAfter=10))

    story.append(Paragraph(
        "EchoSphere v2.2 follows an <b>Agile Software Engineering Methodology</b> combined with strict <b>Role-Based Access Control (RBAC)</b>, "
        "a unified <b>DevAdmin UI Synchronization Rule</b>, and an automated <b>AI-Augmented Announcement Lifecycle Pipeline</b>.",
        body_style
    ))

    # RBAC Matrix Subsection
    story.append(Paragraph("3.1 Role-Based Access Control (RBAC) & Feature Matrix", h2_style))
    story.append(Paragraph(
        "EchoSphere enforces a strict authorization hierarchy across 6 distinct user roles to guarantee security, departmental privacy, and controlled broadcast authority:",
        body_style
    ))

    rbac_data = [
        [Paragraph("Feature / Capability", table_header_style), Paragraph("DevAdmin", table_header_style), Paragraph("Principal", table_header_style), Paragraph("College Admin", table_header_style), Paragraph("HOD", table_header_style), Paragraph("Teacher", table_header_style), Paragraph("Student", table_header_style)],
        [Paragraph("Create Announcement", table_cell_bold), Paragraph("Yes", table_cell_style), Paragraph("Yes", table_cell_style), Paragraph("Yes", table_cell_style), Paragraph("Yes", table_cell_style), Paragraph("Yes", table_cell_style), Paragraph("No", table_cell_style)],
        [Paragraph("AI Voice/STT Drafting", table_cell_bold), Paragraph("Yes", table_cell_style), Paragraph("Yes", table_cell_style), Paragraph("Yes", table_cell_style), Paragraph("Yes", table_cell_style), Paragraph("Yes", table_cell_style), Paragraph("No", table_cell_style)],
        [Paragraph("Approve College Notices", table_cell_bold), Paragraph("Yes", table_cell_style), Paragraph("Yes", table_cell_style), Paragraph("Yes", table_cell_style), Paragraph("No", table_cell_style), Paragraph("No", table_cell_style), Paragraph("No", table_cell_style)],
        [Paragraph("Approve Dept Notices", table_cell_bold), Paragraph("Yes", table_cell_style), Paragraph("Yes", table_cell_style), Paragraph("Yes", table_cell_style), Paragraph("Yes", table_cell_style), Paragraph("No", table_cell_style), Paragraph("No", table_cell_style)],
        [Paragraph("Emergency Override", table_cell_bold), Paragraph("Yes", table_cell_style), Paragraph("Yes", table_cell_style), Paragraph("No", table_cell_style), Paragraph("No", table_cell_style), Paragraph("No", table_cell_style), Paragraph("No", table_cell_style)],
        [Paragraph("Speaker Queue Control", table_cell_bold), Paragraph("Yes", table_cell_style), Paragraph("Yes", table_cell_style), Paragraph("Yes", table_cell_style), Paragraph("View Only", table_cell_style), Paragraph("No", table_cell_style), Paragraph("No", table_cell_style)],
        [Paragraph("View Broadcast Feed", table_cell_bold), Paragraph("Yes", table_cell_style), Paragraph("Yes", table_cell_style), Paragraph("Yes", table_cell_style), Paragraph("Yes", table_cell_style), Paragraph("Yes", table_cell_style), Paragraph("Yes", table_cell_style)],
        [Paragraph("System Audit Logs", table_cell_bold), Paragraph("Yes", table_cell_style), Paragraph("View Only", table_cell_style), Paragraph("No", table_cell_style), Paragraph("No", table_cell_style), Paragraph("No", table_cell_style), Paragraph("No", table_cell_style)]
    ]
    rbac_table = Table(rbac_data, colWidths=[120, 64, 64, 64, 64, 64, 64])
    rbac_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#1E3A8A')),
        ('BOX', (0, 0), (-1, -1), 1, HexColor('#94A3B8')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, HexColor('#CBD5E1')),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(rbac_table)
    story.append(Spacer(1, 10))

    # DevAdmin UI Rule Callout
    devadmin_rule_text = (
        "<b>MANDATORY WORKSPACE RULE:</b> Any visual UI/UX design enhancement or layout component improvement implemented on "
        "the Developer Administrator (<code>devadmin</code>) interface must automatically be propagated across all other role pages "
        "(Principal, College Admin, HOD, Teacher, Student). Permission boundaries and role restrictions remain strictly enforced."
    )
    story.append(create_callout(devadmin_rule_text, title="UI CONSISTENCY & ROLE PROPAGATION GUARANTEE", bg_color="#FEF3C7", border_color="#D97706"))
    story.append(Spacer(1, 12))

    # Announcement Lifecycle Flow
    story.append(Paragraph("3.2 Announcement Lifecycle & Audio Dispatch Methodology", h2_style))
    story.append(Paragraph(
        "The end-to-end communication lifecycle inside EchoSphere v2.2 operates through a multi-stage sequential state machine:",
        body_style
    ))

    lifecycle_steps = [
        ("1. Draft Creation & AI Composition", "Author drafts an announcement manually or speaks via Whisper Speech-to-Text. The AI Text Expander automatically converts rough notes into rich, structured content."),
        ("2. AI Content Moderation & Emergency Triage", "The AI Microservice screens the text for spam/toxicity and evaluates emergency markers. High urgency triggers an emergency priority escalation."),
        ("3. Multi-Level Approval Routing", "Depending on scope, the announcement is routed to HOD (Department level) or Principal/College Admin (Campus level) for review and approval."),
        ("4. Audio Synthesis & Speaker Queueing", "Upon approval, the system generates multi-lingual neural TTS MP3 audio and pushes a job to the Speaker Queue with appropriate priority weights."),
        ("5. Multi-Channel Synchronization & Dispatch", "Simultaneously dispatches FCM mobile push notifications, updates WebSocket live feeds, and triggers physical/virtual PA speaker audio output."),
        ("6. Archival & Audit Trailing", "Expired announcements are automatically archived with full audit logging recorded in PostgreSQL for compliance and safety analysis.")
    ]

    for title, desc in lifecycle_steps:
        story.append(Paragraph(f"• <b>{title}:</b> {desc}", bullet_style))

    story.append(Spacer(1, 10))

    # Zero Overflow Constraint Callout
    zero_overflow_text = (
        "<b>ZERO OVERFLOW CONSTRAINT:</b> All mobile and desktop screens are engineered using fluid layout widgets "
        "(<code>Expanded</code>, <code>Flexible</code>, <code>SingleChildScrollView</code>, <code>Wrap</code>) to guarantee zero layout overflow "
        "errors across all screen sizes (320px compact phones to 4K desktop displays)."
    )
    story.append(create_callout(zero_overflow_text, title="LAYOUT RESPONSIVENESS & ZERO OVERFLOW GUARANTEE", bg_color="#ECFDF5", border_color="#059669"))
    story.append(Spacer(1, 15))

    # Build Document
    doc.build(story, canvasmaker=MasterNumberedCanvas)
    print(f"Successfully generated PDF: {pdf_path}")
    return pdf_path

if __name__ == "__main__":
    build_pdf()
