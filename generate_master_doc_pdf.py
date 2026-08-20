import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable, Image as RLImage
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

class MasterNumberedCanvas(canvas.Canvas):
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
        self.setFillColor(HexColor("#334155"))

        if self._pageNumber > 1:
            self.drawString(54, 750, "ECHOSPHERE v2.2 — MASTER SYSTEM ARCHITECTURE & ERD DOCUMENTATION")
            self.setFont("Helvetica", 8)
            self.drawRightString(558, 750, "Final Project Manual & Specification")
            self.setStrokeColor(HexColor("#CBD5E1"))
            self.setLineWidth(0.75)
            self.line(54, 742, 558, 742)

        self.setStrokeColor(HexColor("#CBD5E1"))
        self.setLineWidth(0.75)
        self.line(54, 45, 558, 45)

        self.setFont("Helvetica", 8)
        self.drawString(54, 32, "Confidential & Proprietary — EchoSphere Systems Engineering Division")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 32, page_str)
        self.restoreState()


def create_callout(text, title="KEY ARCHITECTURAL HIGHLIGHT", bg_color="#F8FAFC", border_color="#1E3A8A"):
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CalloutTitle', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=9, leading=11, textColor=HexColor(border_color), spaceAfter=3
    )
    body_style = ParagraphStyle(
        'CalloutBody', parent=styles['Normal'],
        fontName='Helvetica', fontSize=8.5, leading=11.5, textColor=HexColor('#1E293B')
    )
    content = [Paragraph(title.upper(), title_style), Paragraph(text, body_style)]
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


def build_final_master_pdf(filename="EchoSphere_Master_Documentation.pdf"):
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

    c_primary = HexColor("#1E3A8A")
    c_secondary = HexColor("#0D9488")
    c_dark = HexColor("#0F172A")

    title_style = ParagraphStyle('DocTitle', fontName='Helvetica-Bold', fontSize=22, leading=26, textColor=c_primary, spaceAfter=6)
    subtitle_style = ParagraphStyle('DocSubTitle', fontName='Helvetica', fontSize=12, leading=15, textColor=c_secondary, spaceAfter=15)
    meta_style = ParagraphStyle('DocMeta', fontName='Helvetica', fontSize=8.5, leading=12, textColor=HexColor('#64748B'), spaceAfter=15)
    h1_style = ParagraphStyle('H1', fontName='Helvetica-Bold', fontSize=13, leading=16, textColor=c_primary, spaceBefore=14, spaceAfter=6, keepWithNext=True)
    h2_style = ParagraphStyle('H2', fontName='Helvetica-Bold', fontSize=10.5, leading=13, textColor=c_secondary, spaceBefore=10, spaceAfter=4, keepWithNext=True)
    body_style = ParagraphStyle('Body', fontName='Helvetica', fontSize=8.8, leading=12.2, textColor=c_dark, spaceAfter=6)
    bullet_style = ParagraphStyle('Bullet', fontName='Helvetica', fontSize=8.8, leading=12.2, textColor=c_dark, leftIndent=12, spaceAfter=3)
    code_style = ParagraphStyle('CodeBlock', fontName='Courier', fontSize=7.5, leading=9.5, textColor=HexColor('#0F172A'), backColor=HexColor('#F1F5F9'), borderColor=HexColor('#E2E8F0'), borderWidth=0.5, borderPadding=5, spaceBefore=4, spaceAfter=6)
    
    tbl_header_style = ParagraphStyle('TblHeader', fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=HexColor('#FFFFFF'))
    tbl_cell_style = ParagraphStyle('TblCell', fontName='Helvetica', fontSize=7.8, leading=10, textColor=HexColor('#1E293B'))

    story = []

    # Title Block
    story.append(Paragraph("EchoSphere v2.2: Final Master Documentation — System Architecture, ERD & Methodology", title_style))
    story.append(Paragraph("Exhaustive Engineering Reference of Cross-Platform Client, Core Backend, AIML Microservices & Departmental IoT Hardware Speaker Broadcast Subsystem", subtitle_style))
    
    meta_text = (
        "<b>Document Specification:</b> Complete System SRS, IoT Hardware Specification & Architecture Manual<br/>"
        "<b>Authors:</b> EchoSphere Systems Engineering, Hardware IoT & AI Research Division | <b>Version:</b> 2.2.0 | <b>Target OS:</b> Android, Windows Desktop, Linux, iOS, Embedded ESP32/Linux IoT<br/>"
        "<b>Core Stack:</b> Flutter 3.x / Dart 3.x, Python 3.11 FastAPI, PostgreSQL 15, SQLAlchemy 2.0 Async, Google Gemini 1.5/3.6, WebSockets, MQTT, High-Fidelity TTS Engine, ESP32-S3 / Raspberry Pi Audio Nodes"
    )
    story.append(Paragraph(meta_text, meta_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=c_primary, spaceAfter=12))

    # Executive Abstract
    story.append(Paragraph("1. Executive Summary & System Vision", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=c_secondary, spaceAfter=6))
    
    abstract_text = (
        "<b>Abstract — </b> Higher education institutions present a complex operational environment where information dissemination "
        "must balance speed, strict institutional governance, departmental isolation, real-time urgency, and multi-modal student reach.<br/><br/>"
        "<b>EchoSphere v2.2</b> resolves these challenges by introducing a smart, multi-tiered campus announcement management ecosystem "
        "featuring direct <b>Departmental IoT Hardware Speaker Broadcast Integration</b>. Installed in every academic department (CSE, ECE, ME, CV, EEE, AI/ML, Basic Sciences, Admin Block), "
        "smart IoT speaker nodes deliver synchronized high-clarity voice announcements directly to students on campus, alongside instant mobile push notifications and responsive feed updates.<br/><br/>"
        "Built upon a decoupled microservices paradigm featuring a cross-platform Flutter client, an asynchronous FastAPI core backend, an AI/ML intelligence microservice, "
        "and an MQTT/WebSocket hardware audio controller, EchoSphere enforces a 6-tier Role-Based Access Control hierarchy (Student, Teacher, HoD, College Administrator, Principal, Developer Admin) "
        "with automated text-to-speech audio synthesis, priority speaker queue management, and instant emergency audio override capabilities."
    )
    story.append(create_callout(abstract_text, title="EXECUTIVE ABSTRACT & HARDWARE-INTEGRATED SPECIFICATION", bg_color="#F0FDFA", border_color="#0D9488"))
    story.append(Spacer(1, 10))

    # System Architecture Section & Embedded Diagram
    story.append(Paragraph("2. System Architecture & Diagram", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=c_secondary, spaceAfter=6))

    arch_img_path = os.path.abspath("architecture_diagram.png")
    if os.path.exists(arch_img_path):
        story.append(RLImage(arch_img_path, width=504, height=343))
        story.append(Spacer(1, 4))
        story.append(Paragraph("<b>Figure 1:</b> EchoSphere v2.2 Multi-Tier Microservices Architecture Diagram (Featuring Departmental IoT Hardware Speaker Tier)", ParagraphStyle('Cap', fontName='Helvetica-Oblique', fontSize=8, alignment=1, textColor=HexColor('#475569'))))
        story.append(Spacer(1, 10))

    # ERD Section & Embedded Diagram
    story.append(Paragraph("3. Entity Relationship Diagram (ERD) & Database Schema", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=c_secondary, spaceAfter=6))

    er_img_path = os.path.abspath("er_diagram.png")
    if os.path.exists(er_img_path):
        story.append(RLImage(er_img_path, width=504, height=343))
        story.append(Spacer(1, 4))
        story.append(Paragraph("<b>Figure 2:</b> EchoSphere v2.2 Relational Database Entity Relationship Diagram (ERD)", ParagraphStyle('Cap2', fontName='Helvetica-Oblique', fontSize=8, alignment=1, textColor=HexColor('#475569'))))
        story.append(Spacer(1, 10))

    # Departmental IoT Hardware Speaker System
    story.append(Paragraph("4. Departmental IoT Hardware Speaker Broadcast Architecture", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=c_secondary, spaceAfter=6))

    hw_spec_data = [
        [Paragraph("Hardware Module", tbl_header_style), Paragraph("Component Specification", tbl_header_style), Paragraph("Interface & Connection", tbl_header_style), Paragraph("Operational Functionality", tbl_header_style)],
        [
            Paragraph("<b>Microcontroller Node</b>", tbl_cell_style),
            Paragraph("ESP32-S3 Dual-Core Xtensa LX7 / Raspberry Pi Zero 2 W", tbl_cell_style),
            Paragraph("Wi-Fi 802.11 b/g/n & RJ45 Ethernet", tbl_cell_style),
            Paragraph("Executes hardware client, maintains WebSocket/MQTT heartbeat, processes audio streams.", tbl_cell_style)
        ],
        [
            Paragraph("<b>Audio DAC Module</b>", tbl_cell_style),
            Paragraph("PCM5102A 32-Bit / 384kHz I2S Audio DAC", tbl_cell_style),
            Paragraph("I2S Bus (BCLK, LRCK, DIN)", tbl_cell_style),
            Paragraph("Converts digital TTS stream buffers into low-noise, high-fidelity analog audio signals.", tbl_cell_style)
        ],
        [
            Paragraph("<b>Power Amplifier</b>", tbl_cell_style),
            Paragraph("TPA3116D2 50W Class-D Stereo/Mono Amplifier", tbl_cell_style),
            Paragraph("Analog RCA / 3.5mm Terminal", tbl_cell_style),
            Paragraph("Drives departmental wall-mounted acoustic speakers with adjustable gain control.", tbl_cell_style)
        ],
        [
            Paragraph("<b>Emergency Relay Circuit</b>", tbl_cell_style),
            Paragraph("Optocoupled 5V Relay Module", tbl_cell_style),
            Paragraph("GPIO Signal Line", tbl_cell_style),
            Paragraph("Hardware-level override relay that forces maximum output gain during EMERGENCY Priority Level 1 broadcasts.", tbl_cell_style)
        ]
    ]

    t_hw_spec = Table(hw_spec_data, colWidths=[110, 140, 110, 144])
    t_hw_spec.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_primary),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#CBD5E1')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor('#FFFFFF'), HexColor('#F8FAFC')])
    ]))
    story.append(t_hw_spec)
    story.append(Spacer(1, 10))

    # Methodology & State Machine
    story.append(Paragraph("5. Methodology & Core Announcement Lifecycle State Machine", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=c_secondary, spaceAfter=6))
    
    state_desc = [
        "<b>1. DRAFT:</b> Initial state when created by a Teacher or Administrator. Editable by author; unsubmitted and invisible to students.",
        "<b>2. PENDING_APPROVAL:</b> Submitted for verification. Placed in the HoD or Administrator approval queue. Locked against author edits.",
        "<b>3. APPROVED:</b> Verified by HoD, Admin, or Principal. Placed in active broadcast dispatch queue and published to notice feed.",
        "<b>4. REJECTED:</b> Declined during review. Returned to author with mandatory feedback notes detailing required revisions.",
        "<b>5. SCHEDULED:</b> Approved notice configured with future publication timestamp (`scheduled_at`). Released by background cron workers.",
        "<b>6. ARCHIVED:</b> Retired notice past active validity period. Preserved in immutable database storage for historical audit trailing."
    ]
    for st in state_desc:
        story.append(Paragraph(st, bullet_style))
    story.append(Spacer(1, 10))

    # Final Verification Callout
    story.append(create_callout(
        "Final Master System Documentation compiled with System Architecture Diagram, ERD, Methodology, and Hardware Connection Specs.",
        title="MASTER SPECIFICATION APPROVAL",
        bg_color="#F0FDF4",
        border_color="#16A34A"
    ))

    doc.build(story, canvasmaker=MasterNumberedCanvas)
    print(f"Final Master PDF Successfully Generated at: {pdf_path}")
    return pdf_path

if __name__ == "__main__":
    build_final_master_pdf()
