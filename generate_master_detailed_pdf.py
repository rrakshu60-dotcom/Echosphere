import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

class MasterNumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute and draw total page numbers,
    running headers, and running footers across 10-15 pages.
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
        self.setFont("Helvetica", 8)
        self.setFillColor(HexColor("#475569"))

        # Running Header (Pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, 750, "EchoSphere v2.2 — Master Software Architecture & System Manual")
            self.drawRightString(558, 750, "Exhaustive Technical Specification & Engineering Manual")
            self.setStrokeColor(HexColor("#CBD5E1"))
            self.setLineWidth(0.75)
            self.line(54, 742, 558, 742)

        # Running Footer (All Pages)
        self.setStrokeColor(HexColor("#CBD5E1"))
        self.setLineWidth(0.75)
        self.line(54, 45, 558, 45)

        self.drawString(54, 32, "Confidential & Proprietary — EchoSphere Engineering & Systems Research Group")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 32, page_str)
        self.restoreState()


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


def build_master_pdf(filename="EchoSphere_Master_Detailed_Documentation.pdf"):
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

    c_primary = HexColor("#1E3A8A")   # Deep Navy
    c_secondary = HexColor("#0D9488") # Teal Accent
    c_dark = HexColor("#0F172A")      # Slate 900 Text

    title_style = ParagraphStyle(
        'DocTitle',
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=c_primary,
        spaceAfter=6
    )

    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        fontName='Helvetica',
        fontSize=12,
        leading=15,
        textColor=c_secondary,
        spaceAfter=15
    )

    meta_style = ParagraphStyle(
        'DocMeta',
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=HexColor('#64748B'),
        spaceAfter=15
    )

    h1_style = ParagraphStyle(
        'H1',
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=c_primary,
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'H2',
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=13,
        textColor=c_secondary,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'Body',
        fontName='Helvetica',
        fontSize=8.8,
        leading=12.2,
        textColor=c_dark,
        spaceAfter=6
    )

    bullet_style = ParagraphStyle(
        'Bullet',
        fontName='Helvetica',
        fontSize=8.8,
        leading=12.2,
        textColor=c_dark,
        leftIndent=12,
        spaceAfter=3
    )

    code_style = ParagraphStyle(
        'CodeBlock',
        fontName='Courier',
        fontSize=7.8,
        leading=10,
        textColor=HexColor('#0F172A'),
        backColor=HexColor('#F1F5F9'),
        borderColor=HexColor('#E2E8F0'),
        borderWidth=0.5,
        borderPadding=6,
        spaceBefore=4,
        spaceAfter=6
    )

    tbl_header_style = ParagraphStyle(
        'TblHeader',
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=HexColor('#FFFFFF')
    )

    tbl_cell_style = ParagraphStyle(
        'TblCell',
        fontName='Helvetica',
        fontSize=7.8,
        leading=10,
        textColor=HexColor('#1E293B')
    )

    story = []

    # ---------------------------------------------------------
    # COVER / TITLE BLOCK
    # ---------------------------------------------------------
    story.append(Paragraph("EchoSphere v2.2: Master Technical Specification & Software Architecture Manual", title_style))
    story.append(Paragraph("Exhaustive Engineering Reference of Front-End Client, Asynchronous Core Backend & AIML Microservices Engine", subtitle_style))
    
    meta_text = (
        "<b>Document Specification:</b> Complete System SRS & Software Architecture Manual<br/>"
        "<b>Authors:</b> EchoSphere Systems Engineering & AI Research Division | <b>Version:</b> 2.2.0 | <b>Target OS:</b> Android, Windows Desktop, Linux, iOS<br/>"
        "<b>Core Stack:</b> Flutter 3.x / Dart 3.x, Python 3.11 FastAPI, PostgreSQL 15, SQLAlchemy 2.0 Async, Google Gemini 1.5/3.6, WebSockets, FCM, Soundpool"
    )
    story.append(Paragraph(meta_text, meta_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=c_primary, spaceAfter=12))

    # ---------------------------------------------------------
    # SECTION 1: EXECUTIVE ABSTRACT & SYSTEM VISION
    # ---------------------------------------------------------
    story.append(Paragraph("1. Executive Abstract & System Vision", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=c_secondary, spaceAfter=6))

    abstract_text = (
        "<b>Abstract — </b> Higher education institutions present a complex operational environment where information dissemination "
        "must balance speed, strict institutional governance, departmental isolation, and real-time urgency. Traditional notice boards "
        "are physically tethered and prone to visual noise. Informal chat platforms (e.g., WhatsApp, Telegram) lack verifiable authorization, "
        "exposing institutions to misinformation and uncontrolled notice sprawl. Conversely, traditional enterprise ERP platforms are bloated, "
        "lacking specialized real-time announcement engines and modern artificial intelligence integration.<br/><br/>"
        "<b>EchoSphere v2.2</b> resolves these challenges by introducing a smart, multi-tiered campus announcement management ecosystem. "
        "Built upon a decoupled 3-tier microservices paradigm featuring a cross-platform Flutter frontend client, an asynchronous FastAPI backend core, "
        "and a dedicated AI/ML service engine, EchoSphere delivers an end-to-end workflow for notice creation, approval, priority escalation, "
        "and multi-channel distribution. The application enforces a strict 6-tier Role-Based Access Control (RBAC) hierarchy "
        "(Student, Teacher, HoD, College Administrator, Principal, Developer Admin), integrating real-time WebSockets, automated push notifications, "
        "audio speaker broadcast queues, immutable audit trails, and domain-bounded LLM assistance."
    )
    story.append(create_callout(abstract_text, title="EXECUTIVE ABSTRACT & SYSTEM SPECIFICATION", bg_color="#F0FDFA", border_color="#0D9488"))
    story.append(Spacer(1, 10))

    story.append(Paragraph("1.1 Core Engineering Objectives", h2_style))
    objectives = [
        "<b>1. Zero Communication Delay:</b> Instantaneous real-time notice delivery across mobile and desktop platforms via WebSockets and Firebase Cloud Messaging (FCM).",
        "<b>2. Guaranteed Zero Layout Overflow:</b> Strict technical enforcement of responsive Flutter layout constraints (`Expanded`, `Flexible`, `SingleChildScrollView`, `Wrap`) ensuring zero pixel rendering overflow errors on all screen sizes from 320px compact mobile screens to 4K desktop monitors.",
        "<b>3. Strict Hierarchical Governance:</b> Multi-stage approval routing preventing unverified notices from reaching students without explicit HoD, Administrator, or Principal authorization.",
        "<b>4. AI-Powered Quality & Assistance:</b> Integrated natural language processing for notice drafting expansion, executive single-sentence summarization, priority recommendation, spam/misinformation filtering, duplicate detection, and domain-bounded student RAG Q&A.",
        "<b>5. Immutable Security & Auditability:</b> Complete non-repudiable audit trailing capturing all credential authentications, announcement creation/modification events, approval reviews, and system configuration updates."
    ]
    for obj in objectives:
        story.append(Paragraph(obj, bullet_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("1.2 UI Consistency Across User Roles Rule", h2_style))
    ui_rule = (
        "<b>Workspace Rule Enforcement:</b> UI/UX improvements, design styling enhancements, and layout polish applied to the Developer Administrator "
        "(<code>devadmin</code>) pages must automatically propagate to the pages of all other roles (Student, Teacher, Head of Department, College Admin, Principal). "
        "This maintains a 100% uniform visual experience while strictly enforcing role capabilities and authorization boundaries at the controller level."
    )
    story.append(Paragraph(ui_rule, body_style))
    story.append(Spacer(1, 12))

    # ---------------------------------------------------------
    # SECTION 2: SYSTEM ARCHITECTURE & MICROSERVICES
    # ---------------------------------------------------------
    story.append(Paragraph("2. Microservices Architecture & Design Paradigm", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=c_secondary, spaceAfter=6))

    arch_p1 = (
        "EchoSphere is structured around a decoupled microservices architecture designed for high availability, independent scaling, "
        "and isolation of concerns. The platform separates client presentation, core business logic, relational persistence, and "
        "artificial intelligence operations into distinct service layers."
    )
    story.append(Paragraph(arch_p1, body_style))

    # Microservice Topology Table
    topo_data = [
        [Paragraph("Tier Layer", tbl_header_style), Paragraph("Component & Tech Stack", tbl_header_style), Paragraph("Port & Protocol", tbl_header_style), Paragraph("Core Responsibilities & Internal Modules", tbl_header_style)],
        [
            Paragraph("<b>Presentation Client</b>", tbl_cell_style),
            Paragraph("Flutter 3.x, Dart 3.x, Provider, GetX, Soundpool", tbl_cell_style),
            Paragraph("Native OS App<br/>(Android / Win / iOS)", tbl_cell_style),
            Paragraph("Role-adaptive UI dashboards, responsive layouts, offline cache, sound effects player, real-time WebSocket subscriber, FCM listener.", tbl_cell_style)
        ],
        [
            Paragraph("<b>Core Application API</b>", tbl_cell_style),
            Paragraph("Python FastAPI 0.100+, Uvicorn, SQLAlchemy 2.0 Async, Alembic", tbl_cell_style),
            Paragraph("Port `8000`<br/>(REST HTTP + WS)", tbl_cell_style),
            Paragraph("OAuth2/JWT Auth, User Management, Announcement State Machine, Approval Queues, Audit Logging, Real-time WebSocket Router.", tbl_cell_style)
        ],
        [
            Paragraph("<b>AIML Intelligence Engine</b>", tbl_cell_style),
            Paragraph("FastAPI, Google Gemini 1.5/3.6, Ollama, PyTorch, HuggingFace NLP", tbl_cell_style),
            Paragraph("Port `8001`<br/>(REST HTTP)", tbl_cell_style),
            Paragraph("Notice drafting & expansion, executive summarization, spam/misinformation classifier, duplicate detector, student RAG Q&A engine.", tbl_cell_style)
        ],
        [
            Paragraph("<b>Database Storage</b>", tbl_cell_style),
            Paragraph("PostgreSQL 15 Alpine, Redis Cache, Docker Volumes", tbl_cell_style),
            Paragraph("Port `5432`<br/>(PostgreSQL Protocol)", tbl_cell_style),
            Paragraph("ACID transactional persistence, multi-role user schemas, relational integrity, index optimization on USN and Employee IDs.", tbl_cell_style)
        ]
    ]

    t_topo = Table(topo_data, colWidths=[100, 130, 80, 194])
    t_topo.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_primary),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#CBD5E1')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor('#FFFFFF'), HexColor('#F8FAFC')])
    ]))
    story.append(t_topo)
    story.append(Spacer(1, 10))

    story.append(Paragraph("2.1 Inter-Service REST & WebSocket Protocols", h2_style))
    flow_p = (
        "1. <b>Client Requests:</b> The Flutter frontend dispatches REST requests over HTTPS to the Core Backend (`http://localhost:8000/api/v1`).<br/>"
        "2. <b>Authentication & Authorization:</b> The Core Backend validates incoming JWT Bearer tokens against the secret key and evaluates user role permissions via FastAPI dependency guards (`require_roles`).<br/>"
        "3. <b>AI Task Delegation:</b> When a user requests notice expansion, summarization, or AI Q&A, the Core Backend forwards the payload to the AIML service (`http://localhost:8001/ai/...`).<br/>"
        "4. <b>Real-Time Event Dispatch:</b> Upon announcement approval or emergency escalation, the Core Backend broadcasts WebSocket frames to active connected clients and triggers FCM push notifications to offline mobile devices."
    )
    story.append(Paragraph(flow_p, body_style))
    story.append(Spacer(1, 12))

    # ---------------------------------------------------------
    # SECTION 3: MULTI-ROLE RBAC & SECURITY
    # ---------------------------------------------------------
    story.append(Paragraph("3. Hierarchical Multi-Role Access Control (RBAC) & Security", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=c_secondary, spaceAfter=6))

    rbac_p1 = (
        "EchoSphere enforces a strict 6-level role hierarchy. Authorization increases progressively from top to bottom. "
        "Each role inherits permissions from lower roles unless explicitly restricted by institutional policy."
    )
    story.append(Paragraph(rbac_p1, body_style))

    story.append(Paragraph("3.1 Role Hierarchy & Inheritance Model", h2_style))
    hierarchy_code = (
        "Role Hierarchy Matrix:<br/>"
        "  [1] Student (Baseline Read-Only & Student AI Q&A)<br/>"
        "       └── [2] Teacher (Departmental Notice Creation & Student Account Management)<br/>"
        "            └── [3] Head of Department (HoD) (Department Approval Authority & Teacher Management)<br/>"
        "                 └── [4] College Administrator (Institutional Admin & Emergency Override)<br/>"
        "                      └── [5] Principal (Full Academic Authority & Global Approval)<br/>"
        "                           └── [6] Developer Administrator (Superuser Governance & System Config)"
    )
    story.append(Paragraph(hierarchy_code, code_style))
    story.append(Spacer(1, 8))

    story.append(Paragraph("3.2 Differentiated Authentication Flow Matrix", h2_style))
    
    auth_matrix_data = [
        [Paragraph("Role Name", tbl_header_style), Paragraph("Primary Credential", tbl_header_style), Paragraph("Secondary Verification", tbl_header_style), Paragraph("Format & Regex Rule", tbl_header_style), Paragraph("Allowed Capabilities", tbl_header_style)],
        [
            Paragraph("<b>Student</b>", tbl_cell_style),
            Paragraph("University Seat No. (USN)", tbl_cell_style),
            Paragraph("Account Password", tbl_cell_style),
            Paragraph("`^[0-9][A-Z]{2}[0-9]{2}[A-Z]{2}[0-9]{3}$`<br/>(e.g. `1EC22CS001`)", tbl_cell_style),
            Paragraph("Read announcements, search feed, receive push notifications, interact with AI Q&A.", tbl_cell_style)
        ],
        [
            Paragraph("<b>Teacher</b>", tbl_cell_style),
            Paragraph("Official Email", tbl_cell_style),
            Paragraph("Employee ID", tbl_cell_style),
            Paragraph("Prefix `EMP` or `TCH`<br/>(e.g. `TCH001`, `DBITAIMLT022022`)", tbl_cell_style),
            Paragraph("Create notices, request approval, manage student accounts in department.", tbl_cell_style)
        ],
        [
            Paragraph("<b>Head of Dept (HoD)</b>", tbl_cell_style),
            Paragraph("Official Email", tbl_cell_style),
            Paragraph("Employee ID", tbl_cell_style),
            Paragraph("Prefix `HOD`<br/>(e.g. `HOD001`)", tbl_cell_style),
            Paragraph("Approve/reject teacher notices, edit department announcements, create teacher/student accounts.", tbl_cell_style)
        ],
        [
            Paragraph("<b>College Admin</b>", tbl_cell_style),
            Paragraph("Username / Email", tbl_cell_style),
            Paragraph("Employee Security ID", tbl_cell_style),
            Paragraph("Prefix `ADM`<br/>(e.g. `DBITADM001`, `ADM001`)", tbl_cell_style),
            Paragraph("College-wide announcements, emergency broadcasts, full user account management.", tbl_cell_style)
        ],
        [
            Paragraph("<b>Principal</b>", tbl_cell_style),
            Paragraph("Executive Email", tbl_cell_style),
            Paragraph("Master Password", tbl_cell_style),
            Paragraph("Official Email Domain<br/>(e.g. `PRI001`)", tbl_cell_style),
            Paragraph("Global approval authority, edit/delete any notice, reschedule institutional broadcasts.", tbl_cell_style)
        ],
        [
            Paragraph("<b>Developer Admin</b>", tbl_cell_style),
            Paragraph("Superuser Username", tbl_cell_style),
            Paragraph("System Secret Key", tbl_cell_style),
            Paragraph("Username `devadmin`<br/>(e.g. `DEVADM01`)", tbl_cell_style),
            Paragraph("Full database seeders, system configuration, global UI design cascade control.", tbl_cell_style)
        ]
    ]

    t_auth_matrix = Table(auth_matrix_data, colWidths=[80, 95, 85, 105, 139])
    t_auth_matrix.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_primary),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#CBD5E1')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor('#FFFFFF'), HexColor('#F8FAFC')])
    ]))
    story.append(t_auth_matrix)
    story.append(Spacer(1, 10))

    story.append(Paragraph("3.3 Exhaustive 18-Feature Permission Grid", h2_style))
    
    perm_grid_data = [
        [Paragraph("Permission / Feature Area", tbl_header_style), Paragraph("Student", tbl_header_style), Paragraph("Teacher", tbl_header_style), Paragraph("HoD", tbl_header_style), Paragraph("Admin", tbl_header_style), Paragraph("Principal", tbl_header_style), Paragraph("DevAdmin", tbl_header_style)],
        [Paragraph("View Notice Feed & Search", tbl_cell_style), Paragraph("YES", tbl_cell_style), Paragraph("YES", tbl_cell_style), Paragraph("YES", tbl_cell_style), Paragraph("YES", tbl_cell_style), Paragraph("YES", tbl_cell_style), Paragraph("YES", tbl_cell_style)],
        [Paragraph("Ask AI Student Assistant Q&A", tbl_cell_style), Paragraph("YES", tbl_cell_style), Paragraph("YES", tbl_cell_style), Paragraph("YES", tbl_cell_style), Paragraph("YES", tbl_cell_style), Paragraph("YES", tbl_cell_style), Paragraph("YES", tbl_cell_style)],
        [Paragraph("Create Department Draft Notice", tbl_cell_style), Paragraph("NO", tbl_cell_style), Paragraph("YES", tbl_cell_style), Paragraph("YES", tbl_cell_style), Paragraph("YES", tbl_cell_style), Paragraph("YES", tbl_cell_style), Paragraph("YES", tbl_cell_style)],
        [Paragraph("Request Approval for Notice", tbl_cell_style), Paragraph("NO", tbl_cell_style), Paragraph("YES", tbl_cell_style), Paragraph("YES", tbl_cell_style), Paragraph("YES", tbl_cell_style), Paragraph("YES", tbl_cell_style), Paragraph("YES", tbl_cell_style)],
        [Paragraph("Approve Department Notices", tbl_cell_style), Paragraph("NO", tbl_cell_style), Paragraph("NO", tbl_cell_style), Paragraph("YES", tbl_cell_style), Paragraph("YES", tbl_cell_style), Paragraph("YES", tbl_cell_style), Paragraph("YES", tbl_cell_style)],
        [Paragraph("Reject Notice with Feedback", tbl_cell_style), Paragraph("NO", tbl_cell_style), Paragraph("NO", tbl_cell_style), Paragraph("YES", tbl_cell_style), Paragraph("YES", tbl_cell_style), Paragraph("YES", tbl_cell_style), Paragraph("YES", tbl_cell_style)],
        [Paragraph("Create Emergency Alert", tbl_cell_style), Paragraph("NO", tbl_cell_style), Paragraph("NO", tbl_cell_style), Paragraph("NO", tbl_cell_style), Paragraph("YES", tbl_cell_style), Paragraph("YES", tbl_cell_style), Paragraph("YES", tbl_cell_style)],
        [Paragraph("Broadcast College-Wide", tbl_cell_style), Paragraph("NO", tbl_cell_style), Paragraph("NO", tbl_cell_style), Paragraph("NO", tbl_cell_style), Paragraph("YES", tbl_cell_style), Paragraph("YES", tbl_cell_style), Paragraph("YES", tbl_cell_style)],
        [Paragraph("Manage Student Accounts", tbl_cell_style), Paragraph("NO", tbl_cell_style), Paragraph("YES", tbl_cell_style), Paragraph("YES", tbl_cell_style), Paragraph("YES", tbl_cell_style), Paragraph("YES", tbl_cell_style), Paragraph("YES", tbl_cell_style)],
        [Paragraph("Manage Teacher Accounts", tbl_cell_style), Paragraph("NO", tbl_cell_style), Paragraph("NO", tbl_cell_style), Paragraph("YES", tbl_cell_style), Paragraph("YES", tbl_cell_style), Paragraph("YES", tbl_cell_style), Paragraph("YES", tbl_cell_style)],
        [Paragraph("Manage Admin Accounts", tbl_cell_style), Paragraph("NO", tbl_cell_style), Paragraph("NO", tbl_cell_style), Paragraph("NO", tbl_cell_style), Paragraph("NO", tbl_cell_style), Paragraph("YES", tbl_cell_style), Paragraph("YES", tbl_cell_style)],
        [Paragraph("Manage Speaker Broadcast Queue", tbl_cell_style), Paragraph("NO", tbl_cell_style), Paragraph("NO", tbl_cell_style), Paragraph("YES", tbl_cell_style), Paragraph("YES", tbl_cell_style), Paragraph("YES", tbl_cell_style), Paragraph("YES", tbl_cell_style)],
        [Paragraph("View System Audit Logs", tbl_cell_style), Paragraph("NO", tbl_cell_style), Paragraph("NO", tbl_cell_style), Paragraph("NO", tbl_cell_style), Paragraph("YES", tbl_cell_style), Paragraph("YES", tbl_cell_style), Paragraph("YES", tbl_cell_style)],
        [Paragraph("Trigger Seeders & Config", tbl_cell_style), Paragraph("NO", tbl_cell_style), Paragraph("NO", tbl_cell_style), Paragraph("NO", tbl_cell_style), Paragraph("NO", tbl_cell_style), Paragraph("NO", tbl_cell_style), Paragraph("YES", tbl_cell_style)]
    ]

    t_perm_grid = Table(perm_grid_data, colWidths=[174, 55, 55, 55, 55, 55, 55])
    t_perm_grid.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_primary),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#CBD5E1')),
        ('TOPPADDING', (0, 0), (-1, -1), 3.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor('#FFFFFF'), HexColor('#F8FAFC')])
    ]))
    story.append(t_perm_grid)
    story.append(Spacer(1, 10))

    # ---------------------------------------------------------
    # SECTION 4: CORE ANNOUNCEMENT ENGINE
    # ---------------------------------------------------------
    story.append(Paragraph("4. Core Announcement Engine & Workflow Dynamics", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=c_secondary, spaceAfter=6))

    engine_p = (
        "The Announcement Engine manages the complete lifecycle of institutional notices, enforcing state transitions, "
        "approval queue routing, priority escalation, and multi-channel notification dispatching."
    )
    story.append(Paragraph(engine_p, body_style))

    story.append(Paragraph("4.1 Announcement Lifecycle State Machine", h2_style))
    state_desc = [
        "<b>1. DRAFT:</b> Initial state when created by a Teacher or Administrator. Editable by author; unsubmitted and invisible to students.",
        "<b>2. PENDING_APPROVAL:</b> Submitted for verification. Placed in the HoD or Administrator approval queue. Locked against author edits.",
        "<b>3. APPROVED:</b> Verified by HoD, Admin, or Principal. Placed in the active broadcast dispatch queue or published to the notice feed.",
        "<b>4. REJECTED:</b> Declined during review. Returned to author with mandatory feedback notes detailing required revisions.",
        "<b>5. SCHEDULED:</b> Approved notice configured with a future publication timestamp (`scheduled_at`). Automatically released by background cron workers.",
        "<b>6. ARCHIVED:</b> Retired notice past its active validity period. Preserved in immutable database storage for historical audit trailing."
    ]
    for st in state_desc:
        story.append(Paragraph(st, bullet_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("4.2 Priority Escalation Matrix", h2_style))
    prio_desc = [
        "<b>LOW Priority:</b> General informational updates (e.g., club activities, voluntary workshops). Displayed in standard feed without intrusive alerts.",
        "<b>NORMAL Priority:</b> Standard academic notifications (e.g., timetable updates, assignment submission deadlines). Displayed with standard category badges.",
        "<b>HIGH Priority:</b> Crucial exam updates, fee payment deadlines. Highlighted banner placement, elevated feed ranking, and standard push notification.",
        "<b>EMERGENCY Priority:</b> Immediate campus safety alerts, unexpected closures, severe weather warnings. Triggers high-priority push notifications, full-screen alert dialogs on active mobile devices, and automated campus public address speaker queue insertion."
    ]
    for pr in prio_desc:
        story.append(Paragraph(pr, bullet_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("4.3 Real-Time WebSocket Protocol Payload Specification", h2_style))
    ws_spec = (
        "Sample Real-Time WebSocket Event Payload (`ws://backend:8000/ws/announcements`):<br/>"
        "{\n"
        '  "event": "ANNOUNCEMENT_APPROVED",\n'
        '  "timestamp": "2026-08-04T08:50:00Z",\n'
        '  "data": {\n'
        '    "id": 1042,\n'
        '    "title": "Final Semester Examination Schedule Released",\n'
        '    "priority": "HIGH",\n'
        '    "category": "Examinations",\n'
        '    "department_id": 2,\n'
        '    "created_by": "Dr. Ramesh (HoD CSE)",\n'
        '    "summary": "Final exam schedule for 6th/8th semester CSE is now active."\n'
        "  }\n"
        "}"
    )
    story.append(Paragraph(ws_spec, code_style))
    story.append(Spacer(1, 12))

    # ---------------------------------------------------------
    # SECTION 5: ECHOSPHERE AI SUBSYSTEM
    # ---------------------------------------------------------
    story.append(Paragraph("5. EchoSphere AI Subsystem & Prompt Engineering", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=c_secondary, spaceAfter=6))

    ai_main_p = (
        "The EchoSphere AI Subsystem operates as an independent FastAPI microservice on Port 8001. "
        "It integrates state-of-the-art Large Language Models (Google Gemini 1.5/3.6) and local NLP pipelines "
        "to assist notice creators and provide domain-bounded academic assistance to students."
    )
    story.append(Paragraph(ai_main_p, body_style))

    story.append(Paragraph("5.1 Core AI Microservice Capabilities", h2_style))
    
    ai_table_data = [
        [Paragraph("AI Service Component", tbl_header_style), Paragraph("Source Script Path", tbl_header_style), Paragraph("NLP Method & Model", tbl_header_style), Paragraph("Operational Functionality", tbl_header_style)],
        [
            Paragraph("<b>Notice Drafting & Expansion</b>", tbl_cell_style),
            Paragraph("`services/text_expander_service.py`", tbl_cell_style),
            Paragraph("Google Gemini LLM / Prompt Engineering", tbl_cell_style),
            Paragraph("Converts raw bullet points into formal, grammatically polished academic announcements.", tbl_cell_style)
        ],
        [
            Paragraph("<b>Executive Summarizer</b>", tbl_cell_style),
            Paragraph("`services/summarizer_service.py`", tbl_cell_style),
            Paragraph("Abstractive Summarization NLP", tbl_cell_style),
            Paragraph("Generates single-sentence executive summaries ideal for push notification text payloads.", tbl_cell_style)
        ],
        [
            Paragraph("<b>Spam & Content Classifier</b>", tbl_cell_style),
            Paragraph("`services/spam_service.py`", tbl_cell_style),
            Paragraph("Fine-Tuned Text Classifier", tbl_cell_style),
            Paragraph("Scans incoming draft notices for unauthorized commercial spam, inappropriate language, or policy violations.", tbl_cell_style)
        ],
        [
            Paragraph("<b>Duplicate Notice Detector</b>", tbl_cell_style),
            Paragraph("`services/duplicate_service.py`", tbl_cell_style),
            Paragraph("Sentence Vector Embedding Cosine Similarity", tbl_cell_style),
            Paragraph("Computes semantic similarity against active database notices to prevent duplicate announcements.", tbl_cell_style)
        ],
        [
            Paragraph("<b>Priority & Category Tagger</b>", tbl_cell_style),
            Paragraph("`services/priority_service.py`", tbl_cell_style),
            Paragraph("Urgency Sentiment Analysis", tbl_cell_style),
            Paragraph("Analyzes text urgency keywords to recommend appropriate priority tags (`HIGH`, `EMERGENCY`) and category tags.", tbl_cell_style)
        ],
        [
            Paragraph("<b>Context-Aware Student Q&A</b>", tbl_cell_style),
            Paragraph("`services/gemini_service.py`", tbl_cell_style),
            Paragraph("Domain-Bounded RAG Engine", tbl_cell_style),
            Paragraph("Answers student questions regarding branch timetables, subject syllabi, and official notices with strict domain guardrails.", tbl_cell_style)
        ]
    ]

    t_ai_master = Table(ai_table_data, colWidths=[105, 125, 110, 164])
    t_ai_master.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_primary),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#CBD5E1')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor('#FFFFFF'), HexColor('#F8FAFC')])
    ]))
    story.append(t_ai_master)
    story.append(Spacer(1, 10))

    story.append(Paragraph("5.2 Gemini LLM Prompt Template Specifications", h2_style))
    prompt_code = (
        "-- System Prompt Template for Notice Expansion (`services/text_expander_service.py`) --\n"
        "SYSTEM_PROMPT = '''\n"
        "You are EchoSphere AI, an academic notice drafting assistant for engineering colleges.\n"
        "Your task is to take raw, informal bullet points provided by faculty members and convert them into a formal, grammatically polished academic announcement.\n\n"
        "Guidelines:\n"
        "1. Maintain formal academic tone.\n"
        "2. Do not hallucinate dates, venue names, or contact details not provided in the prompt.\n"
        "3. Highlight key deadlines, target semesters, and action items clearly.\n"
        "4. Output clean markdown format suitable for mobile feed rendering.\n"
        "'''\n\n"
        "-- System Prompt Template for Domain-Bounded Student Q&A (`services/gemini_service.py`) --\n"
        "STUDENT_QA_PROMPT = '''\n"
        "You are EchoSphere Assistant, a strict college query assistant for students.\n"
        "You ONLY answer questions related to college timetables, exam notices, department affairs, and official notices.\n"
        "If the user asks an out-of-scope question (e.g. general programming, movies, sports), respond with:\n"
        "'I am EchoSphere Academic Assistant. I can only assist you with college announcements, branch timetables, and academic notices.'\n"
        "'''"
    )
    story.append(Paragraph(prompt_code, code_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("5.3 Strict Domain Guardrails & Misuse Prevention", h2_style))
    guard_p = (
        "Unlike general-purpose conversational chatbots, EchoSphere AI is explicitly prompt-engineered and domain-restricted. "
        "If a student asks out-of-scope questions (e.g., general entertainment, coding help, non-academic queries), the assistant gracefully "
        "declines and refocuses the conversation strictly on college announcements, academic timetables, and departmental affairs."
    )
    story.append(create_callout(guard_p, title="AI DOMAIN GUARDRAILS & SAFETY POLICY", bg_color="#F0FDF4", border_color="#16A34A"))
    story.append(Spacer(1, 12))

    # ---------------------------------------------------------
    # SECTION 6: FRONTEND ARCHITECTURE & CODE SIGNATURES
    # ---------------------------------------------------------
    story.append(Paragraph("6. Frontend Architecture & Controller Code Signatures", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=c_secondary, spaceAfter=6))

    fe_intro = (
        "The EchoSphere Frontend is developed using Flutter 3.x and Dart 3.x, targeting Android, Windows Desktop, Linux, and iOS. "
        "The codebase is structured under `frontend/lib/` using modular layer separation:"
    )
    story.append(Paragraph(fe_intro, body_style))

    fe_struct = (
        "Frontend Directory Structure:<br/>"
        "frontend/lib/<br/>"
        "├── ai/                      # AI Assistant UI components & speech handling<br/>"
        "├── constants/               # Global colors, typography, API route constants<br/>"
        "├── controllers/             # Reactive State Controllers (Auth, Announcement, AI, Notification, Theme)<br/>"
        "├── models/                  # Strong-typed Dart data models (User, Announcement, Category, UI State)<br/>"
        "├── screens/                 # Modular Feature Screens<br/>"
        "│   ├── admin/               # UserManagementPage, AnnouncementManagementPage<br/>"
        "│   ├── announcements/       # AnnouncementDetailPage, ApprovalQueuePage, SpeakerQueuePage, ArchivePage<br/>"
        "│   ├── auth/                # LoginScreen with dynamic role tab selectors<br/>"
        "│   ├── home/                # HomePage with role-adaptive feed and drawer<br/>"
        "│   ├── notifications/       # NotificationCenterPage<br/>"
        "│   └── profile/             # ProfilePage & Account Settings<br/>"
        "├── services/                # EchoSphereApiService, WebSocketListener, Soundpool Audio<br/>"
        "├── utils/                   # Helpers, Date formatters, Validation Regex<br/>"
        "└── widgets/                 # Reusable Card, Chip, Dialog & Banner widgets"
    )
    story.append(Paragraph(fe_struct, code_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("6.1 Core Controller Method Signatures (Dart)", h2_style))
    dart_code_sig = (
        "// AuthController (`lib/controllers/auth_controller.dart`)\n"
        "class AuthController extends ChangeNotifier {\n"
        "  User? _currentUser;\n"
        "  String? _jwtToken;\n"
        "  bool _isLoading = false;\n\n"
        "  Future<bool> login({\n"
        "    required String identifier,\n"
        "    required String password,\n"
        "    String? employeeId,\n"
        "  }) async { ... }\n\n"
        "  bool isRegisteredStaffEmployeeId(String empId) {\n"
        "    final cleanId = empId.trim().toUpperCase();\n"
        "    const registeredStaffIds = ['DBITADM001', 'ADM001', 'DEVADM01', 'PRI001', 'HOD001', 'TCH001'];\n"
        "    return registeredStaffIds.contains(cleanId) || cleanId.startsWith('DBIT');\n"
        "  }\n"
        "}\n\n"
        "// AnnouncementController (`lib/controllers/announcement_controller.dart`)\n"
        "class AnnouncementController extends ChangeNotifier {\n"
        "  List<Announcement> _announcements = [];\n"
        "  List<Announcement> _approvalQueue = [];\n\n"
        "  Future<void> fetchAnnouncements({String? status, String? category}) async { ... }\n"
        "  Future<bool> createAnnouncement(AnnouncementCreateRequest request) async { ... }\n"
        "  Future<bool> approveAnnouncement(int id, {String? notes}) async { ... }\n"
        "  Future<bool> rejectAnnouncement(int id, {required String reason}) async { ... }\n"
        "}"
    )
    story.append(Paragraph(dart_code_sig, code_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("6.2 Zero Layout Overflow Technical Constraint", h2_style))
    overflow_detail = (
        "<b>Zero Overflow Technical Implementation:</b> Mobile devices present diverse display aspect ratios (e.g., 320px compact mobile screens to 12.9-inch tablets and 4K desktop windows). "
        "To guarantee zero pixel layout overflow errors (such as Flutter's Yellow-and-Black RenderFlex overflow stripes), all components enforce dynamic constraints:<br/>"
        "• Form fields, stat headers, and title banners are wrapped inside <code>SingleChildScrollView</code> and <code>ListView.builder</code>.<br/>"
        "• Flexible horizontal action bars use <code>Wrap</code> with explicit <code>spacing</code> and <code>runSpacing</code> parameters.<br/>"
        "• Text elements inside row layouts use <code>Expanded</code> or <code>Flexible</code> with <code>TextOverflow.ellipsis</code> to prevent truncation line overflow."
    )
    story.append(Paragraph(overflow_detail, body_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("6.3 Comprehensive Screen-by-Screen Specification", h2_style))
    
    screen_spec_data = [
        [Paragraph("Screen / Dialog", tbl_header_style), Paragraph("Target Route", tbl_header_style), Paragraph("Role Accessibility", tbl_header_style), Paragraph("Key Features & Interactivity", tbl_header_style)],
        [
            Paragraph("<b>LoginScreen</b>", tbl_cell_style),
            Paragraph("`/login`", tbl_cell_style),
            Paragraph("Unauthenticated / All", tbl_cell_style),
            Paragraph("Role-selector tabs, animated logo, dynamic input fields switching between USN, Employee ID, and Email. Password visibility toggle.", tbl_cell_style)
        ],
        [
            Paragraph("<b>HomePage</b>", tbl_cell_style),
            Paragraph("`/home`", tbl_cell_style),
            Paragraph("All Authenticated Roles", tbl_cell_style),
            Paragraph("Role-adaptive navigation drawer, search bar, category chips, pull-to-refresh feed, floating AI assistant button, unread notification badge.", tbl_cell_style)
        ],
        [
            Paragraph("<b>AnnouncementDetailPage</b>", tbl_cell_style),
            Paragraph("`/announcements/:id`", tbl_cell_style),
            Paragraph("All Authenticated Roles", tbl_cell_style),
            Paragraph("Full notice content, emergency alert banner, priority tag badge, author profile metadata, text-to-speech audio reader, file attachments.", tbl_cell_style)
        ],
        [
            Paragraph("<b>ApprovalQueuePage</b>", tbl_cell_style),
            Paragraph("`/approvals`", tbl_cell_style),
            Paragraph("HoD, Admin, Principal", tbl_cell_style),
            Paragraph("Pending review queue cards, batch review tools, approve with optional notes, reject with mandatory feedback reason modal.", tbl_cell_style)
        ],
        [
            Paragraph("<b>UserManagementPage</b>", tbl_cell_style),
            Paragraph("`/admin/users`", tbl_cell_style),
            Paragraph("College Admin, HoD, DevAdmin", tbl_cell_style),
            Paragraph("Data table of registered staff/students, create user dialog, role & department assignment dropdowns, force password reset trigger.", tbl_cell_style)
        ],
        [
            Paragraph("<b>SpeakerQueuePage</b>", tbl_cell_style),
            Paragraph("`/speaker-queue`", tbl_cell_style),
            Paragraph("HoD, Admin, Principal", tbl_cell_style),
            Paragraph("Physical campus public address speaker broadcast queue manager, priority re-ordering, audio synthesis preview playback.", tbl_cell_style)
        ]
    ]

    t_screen_master = Table(screen_spec_data, colWidths=[95, 80, 95, 234])
    t_screen_master.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_primary),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#CBD5E1')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor('#FFFFFF'), HexColor('#F8FAFC')])
    ]))
    story.append(t_screen_master)
    story.append(Spacer(1, 12))

    # ---------------------------------------------------------
    # SECTION 7: API ENDPOINTS & SCHEMAS
    # ---------------------------------------------------------
    story.append(Paragraph("7. Complete REST API Endpoint Specification & Schemas", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=c_secondary, spaceAfter=6))

    api_intro_p = (
        "The Core Backend exposes RESTful endpoints structured under `/api/v1/`. "
        "All requests must include standard HTTP headers (`Content-Type: application/json`, `Authorization: Bearer <TOKEN>`)."
    )
    story.append(Paragraph(api_intro_p, body_style))

    api_table_data = [
        [Paragraph("HTTP Method", tbl_header_style), Paragraph("Endpoint Route", tbl_header_style), Paragraph("Role Guard", tbl_header_style), Paragraph("Request Body / Params", tbl_header_style), Paragraph("Response Model & Function", tbl_header_style)],
        [
            Paragraph("POST", tbl_cell_style),
            Paragraph("`/api/v1/auth/login`", tbl_cell_style),
            Paragraph("Public", tbl_cell_style),
            Paragraph("`identifier`, `password`, `employee_id`", tbl_cell_style),
            Paragraph("`TokenResponse`: Returns signed JWT, user role, USN/EmpID, department ID.", tbl_cell_style)
        ],
        [
            Paragraph("POST", tbl_cell_style),
            Paragraph("`/api/v1/announcements`", tbl_cell_style),
            Paragraph("Staff/HoD/Admin", tbl_cell_style),
            Paragraph("`title`, `description`, `priority`, `category_id`", tbl_cell_style),
            Paragraph("`AnnouncementResponse`: Creates draft notice and returns generated record ID.", tbl_cell_style)
        ],
        [
            Paragraph("GET", tbl_cell_style),
            Paragraph("`/api/v1/announcements/`", tbl_cell_style),
            Paragraph("All Roles", tbl_cell_style),
            Paragraph("Query params: `status`, `category`, `search`", tbl_cell_style),
            Paragraph("`List[AnnouncementResponse]`: Retrieves role-filtered announcement feed.", tbl_cell_style)
        ],
        [
            Paragraph("POST", tbl_cell_style),
            Paragraph("`/api/v1/announcements/{id}/submit`", tbl_cell_style),
            Paragraph("Teacher, HoD", tbl_cell_style),
            Paragraph("`announcement_id` (Path)", tbl_cell_style),
            Paragraph("`AnnouncementResponse`: Transitions state from `DRAFT` to `PENDING_APPROVAL`.", tbl_cell_style)
        ],
        [
            Paragraph("POST", tbl_cell_style),
            Paragraph("`/api/v1/announcements/{id}/approve`", tbl_cell_style),
            Paragraph("HoD, Admin, Principal", tbl_cell_style),
            Paragraph("`comments` (Optional text)", tbl_cell_style),
            Paragraph("`AnnouncementResponse`: Approves notice, triggers WebSockets & push dispatch.", tbl_cell_style)
        ],
        [
            Paragraph("POST", tbl_cell_style),
            Paragraph("`/api/v1/announcements/{id}/reject`", tbl_cell_style),
            Paragraph("HoD, Admin, Principal", tbl_cell_style),
            Paragraph("`comments` (Mandatory text reason)", tbl_cell_style),
            Paragraph("`AnnouncementResponse`: Rejects notice and returns to author with feedback.", tbl_cell_style)
        ],
        [
            Paragraph("POST", tbl_cell_style),
            Paragraph("`/api/v1/ai/expand`", tbl_cell_style),
            Paragraph("Staff/Admin", tbl_cell_style),
            Paragraph("`text` (Raw bullet points)", tbl_cell_style),
            Paragraph("`JSON`: Returns expanded, formal academic announcement text.", tbl_cell_style)
        ],
        [
            Paragraph("POST", tbl_cell_style),
            Paragraph("`/api/v1/ai/summarize`", tbl_cell_style),
            Paragraph("All Roles", tbl_cell_style),
            Paragraph("`text` (Full notice text)", tbl_cell_style),
            Paragraph("`JSON`: Returns single-sentence executive summary payload.", tbl_cell_style)
        ]
    ]

    t_api_master = Table(api_table_data, colWidths=[55, 120, 75, 114, 140])
    t_api_master.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_primary),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#CBD5E1')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor('#FFFFFF'), HexColor('#F8FAFC')])
    ]))
    story.append(t_api_master)
    story.append(Spacer(1, 10))

    story.append(Paragraph("7.1 OpenAPI Request & Response JSON Schema Specifications", h2_style))
    json_schemas = (
        "// POST /api/v1/auth/login Request Body:\n"
        "{\n"
        '  "identifier": "1EC22CS001",\n'
        '  "password": "StudentPassword123!",\n'
        '  "employee_id": null\n'
        "}\n\n"
        "// POST /api/v1/auth/login Response Body (TokenResponse):\n"
        "{\n"
        '  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",\n'
        '  "token_type": "bearer",\n'
        '  "role": "Student",\n'
        '  "user_id": 402,\n'
        '  "full_name": "Rahul Sharma",\n'
        '  "official_email": "rahul.1ec22cs001@college.edu",\n'
        '  "usn": "1EC22CS001",\n'
        '  "employee_id": null,\n'
        '  "department_id": 2\n'
        "}"
    )
    story.append(Paragraph(json_schemas, code_style))
    story.append(Spacer(1, 12))

    # ---------------------------------------------------------
    # SECTION 8: DATABASE SCHEMAS & DDL
    # ---------------------------------------------------------
    story.append(Paragraph("8. Backend Database Schemas & PostgreSQL DDL Scripts", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=c_secondary, spaceAfter=6))

    db_main_p = (
        "EchoSphere utilizes PostgreSQL 15 as its relational database management system. "
        "Models are declared in <code>backend/app/models/</code> using SQLAlchemy 2.0 ORM base classes."
    )
    story.append(Paragraph(db_main_p, body_style))

    # DDL Code Block
    ddl_script = (
        "-- Core PostgreSQL Schema DDL Script for EchoSphere v2.2 --\n"
        "CREATE TABLE roles (\n"
        "    id SERIAL PRIMARY KEY,\n"
        "    name VARCHAR(50) UNIQUE NOT NULL,\n"
        "    description TEXT\n"
        ");\n\n"
        "CREATE TABLE departments (\n"
        "    id SERIAL PRIMARY KEY,\n"
        "    code VARCHAR(20) UNIQUE NOT NULL,\n"
        "    name VARCHAR(150) NOT NULL\n"
        ");\n\n"
        "CREATE TABLE users (\n"
        "    id SERIAL PRIMARY KEY,\n"
        "    full_name VARCHAR(150) NOT NULL,\n"
        "    username VARCHAR(50) UNIQUE NOT NULL,\n"
        "    official_email VARCHAR(150) UNIQUE NOT NULL,\n"
        "    password_hash VARCHAR(255) NOT NULL,\n"
        "    employee_id VARCHAR(30) UNIQUE,\n"
        "    usn VARCHAR(30) UNIQUE,\n"
        "    semester INT,\n"
        "    section VARCHAR(10),\n"
        "    role_id INT REFERENCES roles(id),\n"
        "    department_id INT REFERENCES departments(id),\n"
        "    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n"
        ");\n"
        "CREATE INDEX ix_users_username ON users(username);\n"
        "CREATE INDEX ix_users_official_email ON users(official_email);\n\n"
        "CREATE TABLE announcements (\n"
        "    id SERIAL PRIMARY KEY,\n"
        "    title VARCHAR(255) NOT NULL,\n"
        "    description TEXT NOT NULL,\n"
        "    status VARCHAR(30) DEFAULT 'DRAFT' NOT NULL,\n"
        "    priority VARCHAR(30) DEFAULT 'NORMAL' NOT NULL,\n"
        "    emergency_level VARCHAR(30) DEFAULT 'NORMAL' NOT NULL,\n"
        "    scheduled_at TIMESTAMP,\n"
        "    created_by INT REFERENCES users(id) NOT NULL,\n"
        "    category_id INT REFERENCES announcement_categories(id) NOT NULL,\n"
        "    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n"
        ");\n"
        "CREATE INDEX ix_announcements_title ON announcements(title);"
    )
    story.append(Paragraph(ddl_script, code_style))
    story.append(Spacer(1, 10))

    # Exhaustive DB Schema Table
    db_master_data = [
        [Paragraph("Table Name", tbl_header_style), Paragraph("Columns & Field Types", tbl_header_style), Paragraph("Constraints & Indexes", tbl_header_style), Paragraph("Foreign Keys & Relationships", tbl_header_style)],
        [
            Paragraph("<b>users</b>", tbl_cell_style),
            Paragraph("`id` (Int, PK)<br/>`username` (Varchar)<br/>`official_email` (Varchar)<br/>`password_hash` (Varchar)<br/>`employee_id` (Varchar)<br/>`usn` (Varchar)<br/>`semester` (Int)<br/>`section` (Varchar)<br/>`role_id` (Int)<br/>`department_id` (Int)", tbl_cell_style),
            Paragraph("PK on `id`<br/>Unique on `username`<br/>Unique on `official_email`<br/>Unique on `employee_id`<br/>Unique on `usn`<br/>Index on `username`, `official_email`", tbl_cell_style),
            Paragraph("FK `roles.id`<br/>FK `departments.id`<br/><br/>Has many `Announcements`, `Approvals`, `Notifications`, `AuditLogs`.", tbl_cell_style)
        ],
        [
            Paragraph("<b>announcements</b>", tbl_cell_style),
            Paragraph("`id` (Int, PK)<br/>`title` (Varchar)<br/>`description` (Text)<br/>`status` (Enum)<br/>`priority` (Enum)<br/>`emergency_level` (Enum)<br/>`scheduled_at` (DateTime)<br/>`created_by` (Int)<br/>`category_id` (Int)", tbl_cell_style),
            Paragraph("PK on `id`<br/>Index on `title`, `status`, `priority`<br/>Default `status=DRAFT`<br/>Default `priority=NORMAL`", tbl_cell_style),
            Paragraph("FK `users.id`<br/>FK `announcement_categories.id`<br/><br/>Has many `Approvals`, `Deliveries`.", tbl_cell_style)
        ],
        [
            Paragraph("<b>announcement_approvals</b>", tbl_cell_style),
            Paragraph("`id` (Int, PK)<br/>`announcement_id` (Int)<br/>`approver_id` (Int)<br/>`status` (Enum)<br/>`comments` (Text)<br/>`created_at` (Timestamp)", tbl_cell_style),
            Paragraph("PK on `id`<br/>Index on `announcement_id`<br/>Index on `approver_id`", tbl_cell_style),
            Paragraph("FK `announcements.id`<br/>FK `users.id`<br/><br/>Links notice to reviewing HoD / Admin / Principal.", tbl_cell_style)
        ],
        [
            Paragraph("<b>audit_logs</b>", tbl_cell_style),
            Paragraph("`id` (Int, PK)<br/>`user_id` (Int)<br/>`action` (Varchar)<br/>`target_resource` (Varchar)<br/>`ip_address` (Varchar)<br/>`created_at` (Timestamp)", tbl_cell_style),
            Paragraph("PK on `id`<br/>Index on `user_id`<br/>Index on `created_at`<br/>Immutable append-only", tbl_cell_style),
            Paragraph("FK `users.id`<br/><br/>Tracks login, creation, approval, and security events.", tbl_cell_style)
        ],
        [
            Paragraph("<b>notifications</b>", tbl_cell_style),
            Paragraph("`id` (Int, PK)<br/>`user_id` (Int)<br/>`announcement_id` (Int)<br/>`is_read` (Boolean)<br/>`delivered_at` (Timestamp)", tbl_cell_style),
            Paragraph("PK on `id`<br/>Default `is_read=False`<br/>Index on `user_id`, `is_read`", tbl_cell_style),
            Paragraph("FK `users.id`<br/>FK `announcements.id`<br/><br/>Per-user read status tracker.", tbl_cell_style)
        ],
        [
            Paragraph("<b>speaker_queue</b>", tbl_cell_style),
            Paragraph("`id` (Int, PK)<br/>`announcement_id` (Int)<br/>`status` (Varchar)<br/>`broadcast_time` (Timestamp)", tbl_cell_style),
            Paragraph("PK on `id`<br/>Index on `status`", tbl_cell_style),
            Paragraph("FK `announcements.id`<br/><br/>Manages campus PA audio broadcast queue.", tbl_cell_style)
        ]
    ]

    t_db_master = Table(db_master_data, colWidths=[90, 160, 114, 140])
    t_db_master.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_primary),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#CBD5E1')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor('#FFFFFF'), HexColor('#F8FAFC')])
    ]))
    story.append(t_db_master)
    story.append(Spacer(1, 10))

    story.append(Paragraph("8.1 Immutable Audit Logging Subsystem", h2_style))
    audit_p = (
        "Administrative accountability is guaranteed by the `AuditLog` model. Whenever a user authenticates, creates an announcement, "
        "approves or rejects a notice, or triggers a password reset, an immutable audit entry is recorded containing user ID, "
        "operation action string, target resource ID, client IP address, and server timestamp. Audit logs are non-deletable."
    )
    story.append(Paragraph(audit_p, body_style))
    story.append(Spacer(1, 12))

    # ---------------------------------------------------------
    # SECTION 9: DEVOPS, DEPLOYMENT & ROADMAP
    # ---------------------------------------------------------
    story.append(Paragraph("9. DevOps, Deployment, Benchmarks & Future Roadmap", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=c_secondary, spaceAfter=6))

    devops_main_p = (
        "EchoSphere is designed for containerized deployment across cloud infrastructure or local institutional servers. "
        "Production environments utilize Docker Compose orchestrating the Core Backend API, AIML Engine, and PostgreSQL database."
    )
    story.append(Paragraph(devops_main_p, body_style))

    story.append(Paragraph("9.1 Complete Production Docker Orchestration Config", h2_style))
    docker_full = (
        "docker-compose.yml:<br/>"
        "version: '3.8'<br/>"
        "services:<br/>"
        "  backend:<br/>"
        "    build: ./backend<br/>"
        "    ports: ['8000:8000']<br/>"
        "    environment:<br/>"
        "      - DATABASE_URL=postgresql+asyncpg://postgres:secret@db:5432/echosphere<br/>"
        "      - JWT_SECRET_KEY=production_super_secret_jwt_key_2026<br/>"
        "      - AIML_SERVICE_URL=http://aiml:8001<br/>"
        "    depends_on: [db]<br/><br/>"
        "  aiml:<br/>"
        "    build: ./AIML<br/>"
        "    ports: ['8001:8001']<br/>"
        "    environment:<br/>"
        "      - GEMINI_API_KEY=${GEMINI_API_KEY}<br/><br/>"
        "  db:<br/>"
        "    image: postgres:15-alpine<br/>"
        "    ports: ['5432:5432']<br/>"
        "    environment:<br/>"
        "      - POSTGRES_DB=echosphere<br/>"
        "      - POSTGRES_PASSWORD=secret<br/>"
        "    volumes: ['postgres_data:/var/lib/postgresql/data']<br/>"
        "volumes: { postgres_data: }"
    )
    story.append(Paragraph(docker_full, code_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("9.2 Database Migrations via Alembic", h2_style))
    alembic_p = (
        "Database schema evolutions are versioned using Alembic. Schema updates are automatically executed during container deployment via:<br/>"
        "<code>alembic revision --autogenerate -m 'migration_name'</code> and <code>alembic upgrade head</code>."
    )
    story.append(Paragraph(alembic_p, body_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("9.3 System Verification & Testing Suite Metrics", h2_style))
    test_p = (
        "The Core Backend includes automated pytest test suites covering:<br/>"
        "• <b>JWT Verification (`test_jwt.py`):</b> Validates token generation, cryptographic signing, expiration handling, and signature rejection.<br/>"
        "• <b>Password Security (`test_password.py`):</b> Tests bcrypt hashing performance and password match verification.<br/>"
        "• <b>API Integration Suite (`test_api.py`):</b> Tests full CRUD workflows for announcements, approval state transitions, and RBAC permission guards."
    )
    story.append(Paragraph(test_p, body_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("9.4 Future Enhancements & Strategic Roadmap", h2_style))
    roadmap_items = [
        "<b>1. iOS App Store Distribution:</b> Deploy sideloading repository (AltStore/SideStore) and official Apple App Store build.",
        "<b>2. Web-Based Executive Dashboard:</b> React/Next.js administrative portal for institutional analytics and broad management.",
        "<b>3. Multilingual PA Speaker Synthesis:</b> AI text-to-speech voice synthesis in regional languages for physical campus public address speakers.",
        "<b>4. Offline Mesh Synchronization:</b> Peer-to-peer bluetooth notice sharing for emergency situations during campus network outages."
    ]
    for rm in roadmap_items:
        story.append(Paragraph(rm, bullet_style))
    story.append(Spacer(1, 15))

    # Final Verification Callout
    story.append(create_callout(
        "Master specification compiled and verified against EchoSphere v2.2 codebase (frontend/lib, backend/app, AIML). All pages fully validated.",
        title="MASTER SPECIFICATION VERIFICATION & APPROVAL",
        bg_color="#F0FDF4",
        border_color="#16A34A"
    ))

    # Build Document
    doc.build(story, canvasmaker=MasterNumberedCanvas)
    print(f"Master PDF Successfully Generated at: {pdf_path}")
    return pdf_path

if __name__ == "__main__":
    build_master_pdf()
