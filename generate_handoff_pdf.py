import os
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

class HandoffNumberedCanvas(canvas.Canvas):
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
            self.drawString(54, 750, "ECHOSPHERE v2.2 — HARDWARE IMPLEMENTATION & DEVELOPER HANDOFF GUIDE")
            self.setFont("Helvetica", 8)
            self.drawRightString(558, 750, "Technical Task Specification")
            self.setStrokeColor(HexColor("#CBD5E1"))
            self.setLineWidth(0.75)
            self.line(54, 742, 558, 742)

        self.setStrokeColor(HexColor("#CBD5E1"))
        self.setLineWidth(0.75)
        self.line(54, 45, 558, 45)

        self.setFont("Helvetica", 8)
        self.drawString(54, 32, "Confidential — EchoSphere Engineering & Systems Research Division")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 32, page_str)
        self.restoreState()


def build_handoff_pdf(filename="EchoSphere_Hardware_Implementation_Handoff.pdf"):
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

    title_style = ParagraphStyle('HTitle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=18, leading=22, textColor=c_primary, spaceAfter=6)
    sub_style = ParagraphStyle('HSub', parent=styles['Normal'], fontName='Helvetica', fontSize=11, leading=14, textColor=c_secondary, spaceAfter=12)
    h1_style = ParagraphStyle('HH1', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=12, leading=15, textColor=c_primary, spaceBefore=14, spaceAfter=6, keepWithNext=True)
    body_style = ParagraphStyle('HBody', parent=styles['Normal'], fontName='Helvetica', fontSize=8.8, leading=12, textColor=c_dark, spaceAfter=6)
    code_style = ParagraphStyle('HCode', parent=styles['Normal'], fontName='Courier', fontSize=7.5, leading=9.5, textColor=c_dark, backColor=HexColor('#F1F5F9'), borderColor=HexColor('#CBD5E1'), borderWidth=0.5, borderPadding=5, spaceAfter=6)
    
    tbl_header = ParagraphStyle('TH', fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=HexColor('#FFFFFF'))
    tbl_cell = ParagraphStyle('TC', fontName='Helvetica', fontSize=7.8, leading=10, textColor=HexColor('#1E293B'))

    story = []

    story.append(Paragraph("EchoSphere v2.2: Hardware Connection & Speaker Subsystem — Developer Implementation Handoff Guide", title_style))
    story.append(Paragraph("Technical Task Specification & Code Implementation Handoff Manual for Hardware Engineer", sub_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=c_primary, spaceAfter=10))

    story.append(Paragraph("1. EXECUTIVE TASK OVERVIEW", h1_style))
    story.append(Paragraph(
        "The database models (<code>speaker_queue.py</code>), Flutter UI layout (<code>speaker_queue_page.dart</code>), and main API architecture are built. "
        "Your task is to complete the <b>Hardware Connection Tier</b> by implementing the backend endpoints, TTS audio service, MQTT broker driver, physical ESP32 firmware, and dynamic Flutter connection.", body_style
    ))
    story.append(Spacer(1, 8))

    story.append(Paragraph("2. BACKEND HARDWARE API ENDPOINTS TO BUILD", h1_style))
    api_data = [
        [Paragraph("HTTP Method", tbl_header), Paragraph("Route", tbl_header), Paragraph("Authorization Role", tbl_header), Paragraph("Description & Logic", tbl_header)],
        [Paragraph("GET", tbl_cell), Paragraph("`/api/v1/hardware/speakers`", tbl_cell), Paragraph("HoD, Admin, DevAdmin", tbl_cell), Paragraph("Query PostgreSQL for all registered speaker nodes & heartbeat status.", tbl_cell)],
        [Paragraph("POST", tbl_cell), Paragraph("`/api/v1/hardware/speakers/register`", tbl_cell), Paragraph("College Admin, DevAdmin", tbl_cell), Paragraph("Register new speaker MAC address, IP, and bind to `department_id`.", tbl_cell)],
        [Paragraph("POST", tbl_cell), Paragraph("`/api/v1/hardware/speakers/{id}/broadcast`", tbl_cell), Paragraph("HoD, Admin, Principal", tbl_cell), Paragraph("Trigger immediate audio playback of approved notice on speaker node.", tbl_cell)],
        [Paragraph("POST", tbl_cell), Paragraph("`/api/v1/hardware/speakers/override`", tbl_cell), Paragraph("Admin, Principal", tbl_cell), Paragraph("Issue immediate EMERGENCY_OVERRIDE command across all department speakers.", tbl_cell)]
    ]
    t_api = Table(api_data, colWidths=[65, 130, 110, 199])
    t_api.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_primary),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#CBD5E1')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor('#FFFFFF'), HexColor('#F8FAFC')])
    ]))
    story.append(t_api)
    story.append(Spacer(1, 10))

    story.append(Paragraph("3. TEXT-TO-SPEECH (TTS) VOICE SYNTHESIS SERVICE", h1_style))
    tts_code = (
        "# Create backend/app/services/tts_service.py\n"
        "import os, gtts\n\n"
        "AUDIO_DIR = 'backend/app/static/audio_streams'\n\n"
        "async def generate_announcement_audio(announcement_id: int, text: str) -> str:\n"
        "    os.makedirs(AUDIO_DIR, exist_ok=True)\n"
        "    file_path = os.path.join(AUDIO_DIR, f'announcement_{announcement_id}.mp3')\n"
        "    tts = gtts.gTTS(text=text, lang='en', slow=False)\n"
        "    tts.save(file_path)\n"
        "    return file_path"
    )
    story.append(Paragraph(tts_code, code_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("4. MQTT HARDWARE COMMUNICATION SERVICE", h1_style))
    mqtt_code = (
        "# Create backend/app/services/hardware_speaker_service.py\n"
        "import json, paho.mqtt.client as mqtt\n\n"
        "def dispatch_speaker_audio_command(dept_code: str, announcement_id: int, audio_url: str, is_emergency: bool = False):\n"
        "    client = mqtt.Client()\n"
        "    client.connect('localhost', 1883, 60)\n"
        "    topic = f'echosphere/dept/{dept_code}/speakers/command'\n"
        "    payload = {\n"
        "        'command': 'PLAY_EMERGENCY' if is_emergency else 'PLAY_ANNOUNCEMENT',\n"
        "        'announcement_id': announcement_id,\n"
        "        'audio_url': audio_url,\n"
        "        'volume': 100 if is_emergency else 85\n"
        "    }\n"
        "    client.publish(topic, json.dumps(payload), qos=1)\n"
        "    client.disconnect()"
    )
    story.append(Paragraph(mqtt_code, code_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("5. MICROCONTROLLER FIRMWARE SCRIPT (ESP32 / RASPBERRY PI)", h1_style))
    fw_code = (
        "# Hardware Client Python/MicroPython Script (speaker_node_client.py)\n"
        "import time, json, urllib.request, paho.mqtt.client as mqtt, pygame\n\n"
        "DEPT_CODE = 'CSE'\n"
        "pygame.mixer.init()\n\n"
        "def on_message(client, userdata, msg):\n"
        "    data = json.loads(msg.payload.decode())\n"
        "    urllib.request.urlretrieve(data['audio_url'], '/tmp/announcement.mp3')\n"
        "    pygame.mixer.music.load('/tmp/announcement.mp3')\n"
        "    pygame.mixer.music.play()\n\n"
        "client = mqtt.Client(client_id=f'Speaker_{DEPT_CODE}')\n"
        "client.on_message = on_message\n"
        "client.connect('192.168.1.100', 1883, 60)\n"
        "client.subscribe(f'echosphere/dept/{DEPT_CODE}/speakers/command')\n"
        "client.loop_start()"
    )
    story.append(Paragraph(fw_code, code_style))

    doc.build(story, canvasmaker=HandoffNumberedCanvas)
    print(f"Handoff PDF Successfully Generated at: {pdf_path}")

if __name__ == "__main__":
    build_handoff_pdf()
