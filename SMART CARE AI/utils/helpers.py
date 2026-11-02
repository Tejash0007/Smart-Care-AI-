"""
Utility and helper functions for SmartCare AI.
Provides clinical screening classifications, BMI calculations,
custom CSS injection, and professional PDF report generation via ReportLab.
"""

import os
import html
from typing import Dict, Any, List, Optional
from datetime import datetime
import streamlit as st


# ==============================================================================
# CLINICAL SCREENING CLASSIFICATIONS (NON-DIAGNOSTIC GUIDANCE ONLY)
# ==============================================================================

def get_bmi_category(bmi: float) -> Dict[str, str]:
    """
    Categorize BMI value based on standard WHO guidelines.
    Returns category name, color code, and educational guidance.
    Note: BMI is a screening metric, not a clinical diagnosis.
    """
    if bmi <= 0:
        return {"category": "N/A", "color": "#64748B", "badge": "secondary", "info": "Invalid height/weight"}
    elif bmi < 18.5:
        return {
            "category": "Underweight",
            "color": "#3498DB",
            "badge": "info",
            "info": "Lower than standard screening range. Consider discussing balanced nutrition with a doctor."
        }
    elif bmi <= 24.9:
        return {
            "category": "Normal Weight",
            "color": "#20A779",
            "badge": "success",
            "info": "Within the standard healthy screening range for general population."
        }
    elif bmi <= 29.9:
        return {
            "category": "Overweight",
            "color": "#E5A000",
            "badge": "warning",
            "info": "Above standard screening range. Regular physical activity and dietary balance recommended."
        }
    else:
        return {
            "category": "Obesity",
            "color": "#E45B65",
            "badge": "danger",
            "info": "Significantly above standard range. Professional healthcare consultation advised."
        }


def get_bp_classification(systolic: int, diastolic: int) -> Dict[str, str]:
    """
    Provide educational screening categorization for Blood Pressure based on AHA guidelines.
    Not a diagnosis; single readings can be influenced by stress, hydration, and activity.
    """
    if systolic < 120 and diastolic < 80:
        return {
            "status": "Normal BP",
            "color": "#20A779",
            "info": "Systolic < 120 mmHg and Diastolic < 80 mmHg"
        }
    elif 120 <= systolic <= 129 and diastolic < 80:
        return {
            "status": "Elevated BP",
            "color": "#E5A000",
            "info": "Systolic 120-129 mmHg and Diastolic < 80 mmHg"
        }
    elif (130 <= systolic <= 139) or (80 <= diastolic <= 89):
        return {
            "status": "Stage 1 Hypertension Range",
            "color": "#E5A000",
            "info": "Systolic 130-139 mmHg or Diastolic 80-89 mmHg"
        }
    else:
        return {
            "status": "Stage 2 Hypertension Range",
            "color": "#E45B65",
            "info": "Systolic ≥ 140 mmHg or Diastolic ≥ 90 mmHg"
        }


def get_glucose_classification(glucose: float, context: str) -> Dict[str, str]:
    """Provide standard reference classification for blood glucose readings."""
    ctx = str(context).lower()
    if "fast" in ctx:
        if glucose < 70:
            return {"status": "Low (Hypoglycemic Range)", "color": "#3498DB"}
        elif glucose <= 99:
            return {"status": "Normal Fasting", "color": "#20A779"}
        elif glucose <= 125:
            return {"status": "Impaired Fasting (Prediabetes Range)", "color": "#E5A000"}
        else:
            return {"status": "Elevated Fasting", "color": "#E45B65"}
    elif "post" in ctx:
        if glucose < 140:
            return {"status": "Normal Post-Meal", "color": "#20A779"}
        elif glucose <= 199:
            return {"status": "Elevated Post-Meal", "color": "#E5A000"}
        else:
            return {"status": "High Post-Meal", "color": "#E45B65"}
    else:
        if glucose <= 140:
            return {"status": "Normal Random", "color": "#20A779"}
        else:
            return {"status": "Elevated Random", "color": "#E5A000"}


def get_heart_rate_classification(bpm: int) -> Dict[str, str]:
    """Resting heart rate guidelines for adults."""
    if bpm < 60:
        return {"status": "Bradycardia (Low / Athletic)", "color": "#3498DB"}
    elif bpm <= 100:
        return {"status": "Normal Resting Rate", "color": "#20A779"}
    else:
        return {"status": "Tachycardia (Elevated)", "color": "#E45B65"}


# ==============================================================================
# CSS STYLING INJECTOR & METRIC CARDS
# ==============================================================================

def load_css():
    """Inject custom medical-themed CSS styling into the Streamlit app."""
    css_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "style.css")
    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def render_metric_card(
    title: str,
    value: Any,
    subtitle: str,
    category: str = "teal",  # "blue", "teal", "purple", "green", "amber", "coral"
    icon: str = "📊"
) -> str:
    """
    Generate a modern, accessible healthcare SaaS metric card HTML string
    with large readable typography, category accent border, and subtle tinted background.
    """
    card_class = f"saas-metric-card card-{category}"
    return f"""
    <div class="{card_class}">
        <div class="metric-top-row">
            <span class="metric-header">{html.escape(str(title))}</span>
            <span class="metric-icon">{icon}</span>
        </div>
        <div class="metric-big-num">{html.escape(str(value))}</div>
        <div class="metric-subtitle">{html.escape(str(subtitle))}</div>
    </div>
    """


def style_plotly_fig(fig, title: str = "", height: int = 340):
    """
    Apply modern healthcare SaaS aesthetic to any Plotly figure:
    clean white canvas, crisp dark text, accessible gridlines, and readable legends.
    """
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(size=15, color="#243447", family="'Inter', -apple-system, sans-serif"),
            x=0.01,
            y=0.96
        ),
        font=dict(family="'Inter', -apple-system, sans-serif", color="#243447", size=12),
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        height=height,
        margin=dict(l=30, r=20, t=45, b=30),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=11, color="#243447")
        ),
        hoverlabel=dict(
            bgcolor="#FFFFFF",
            bordercolor="#CBD5E1",
            font=dict(size=12, color="#243447")
        )
    )
    fig.update_xaxes(showgrid=True, gridcolor="#E2E8F0", zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="#E2E8F0", zeroline=False)
    return fig


# ==============================================================================
# PDF REPORT GENERATOR (REPORTLAB)
# ==============================================================================

def _safe(text: Any) -> str:
    """Escape XML special characters to prevent ReportLab parsing crashes."""
    if text is None:
        return ""
    return html.escape(str(text))


def generate_pdf_report(patient: Dict[str, Any], records: List[Dict[str, Any]]) -> bytes:
    """
    Generate a clean, structured, printable PDF health report for the selected patient.
    Uses ReportLab to construct formatted tables, demographic headers, and disclaimers.
    """
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
        KeepTogether,
        HRFlowable
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    import io

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    header_style = ParagraphStyle(
        "HeaderTitle",
        parent=styles["Heading1"],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0f4c81"),
        alignment=1, # Center
        spaceAfter=4
    )
    
    subtitle_style = ParagraphStyle(
        "SubTitle",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#555555"),
        alignment=1, # Center
        spaceAfter=12
    )

    section_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#1b6ca8"),
        spaceBefore=10,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        "BodySmall",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#333333")
    )

    disclaimer_style = ParagraphStyle(
        "Disclaimer",
        parent=styles["Normal"],
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#6c757d"),
        alignment=1
    )

    story = []

    # Title & Hospital Banner
    story.append(Paragraph("SmartCare AI – Patient Health Summary Report", header_style))
    story.append(Paragraph("AI-Powered Smart Healthcare System • Digital Health Records", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0f4c81"), spaceAfter=14))

    # Patient Demographics
    story.append(Paragraph("Patient Demographics", section_style))
    demo_data = [
        [
            Paragraph(f"<b>Patient ID:</b> {_safe(patient.get('patient_id', 'N/A'))}", body_style),
            Paragraph(f"<b>Full Name:</b> {_safe(patient.get('name', 'N/A'))}", body_style),
        ],
        [
            Paragraph(f"<b>Age:</b> {_safe(patient.get('age', 'N/A'))} yrs", body_style),
            Paragraph(f"<b>Gender:</b> {_safe(patient.get('gender', 'N/A'))}", body_style),
        ],
        [
            Paragraph(f"<b>Contact:</b> {_safe(patient.get('contact', 'N/A'))}", body_style),
            Paragraph(f"<b>Blood Group:</b> {_safe(patient.get('blood_group', 'Unknown'))}", body_style),
        ],
        [
            Paragraph(f"<b>Registration Date:</b> {_safe(patient.get('registration_date', 'N/A'))}", body_style),
            Paragraph(f"<b>Report Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}", body_style),
        ],
    ]
    demo_table = Table(demo_data, colWidths=[270, 270])
    demo_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f0f7fc")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#b9d5e9")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#d8e8f3")),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(demo_table)
    story.append(Spacer(1, 14))

    # Recorded Health Measurements Table
    story.append(Paragraph(f"Historical Health Measurements ({len(records)} Records)", section_style))

    if records:
        table_headers = [
            Paragraph("<b>Date</b>", body_style),
            Paragraph("<b>Weight / Height</b>", body_style),
            Paragraph("<b>BMI</b>", body_style),
            Paragraph("<b>Blood Pressure</b>", body_style),
            Paragraph("<b>Blood Glucose</b>", body_style),
            Paragraph("<b>Heart Rate</b>", body_style),
        ]
        table_rows = [table_headers]

        for r in records[:15]: # Show up to 15 latest records for clean page fit
            bmi_cat = get_bmi_category(float(r["bmi"]))
            bp_val = f"{_safe(r['systolic_bp'])}/{_safe(r['diastolic_bp'])} mmHg"
            glu_val = f"{_safe(r['blood_glucose'])} mg/dL ({_safe(r['glucose_context'])})"

            row = [
                Paragraph(_safe(r["recording_date"]), body_style),
                Paragraph(f"{_safe(r['weight_kg'])} kg / {_safe(r['height_cm'])} cm", body_style),
                Paragraph(f"{_safe(r['bmi'])} ({_safe(bmi_cat['category'])})", body_style),
                Paragraph(bp_val, body_style),
                Paragraph(glu_val, body_style),
                Paragraph(f"{_safe(r['heart_rate'])} BPM", body_style),
            ]
            table_rows.append(row)

        records_table = Table(table_rows, colWidths=[70, 100, 105, 95, 110, 60])
        records_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#e1eef6")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#0f4c81")),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#d0dbe2")),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(records_table)
    else:
        story.append(Paragraph("<i>No health records currently logged for this patient.</i>", body_style))

    story.append(Spacer(1, 14))

    # General Screening Reference Guide
    story.append(Paragraph("Reference Ranges for Routine Screening", section_style))
    ref_data = [
        [
            Paragraph("<b>Metric</b>", body_style),
            Paragraph("<b>Standard Healthy Reference Range</b>", body_style),
            Paragraph("<b>Screening Significance</b>", body_style)
        ],
        [
            Paragraph("Body Mass Index (BMI)", body_style),
            Paragraph("18.5 – 24.9 kg/m²", body_style),
            Paragraph("General population screening for body weight category.", body_style)
        ],
        [
            Paragraph("Blood Pressure (AHA)", body_style),
            Paragraph("< 120 / < 80 mmHg", body_style),
            Paragraph("Cardiovascular screening indicator.", body_style)
        ],
        [
            Paragraph("Fasting Blood Glucose", body_style),
            Paragraph("70 – 99 mg/dL", body_style),
            Paragraph("Baseline metabolic screening.", body_style)
        ],
        [
            Paragraph("Resting Heart Rate", body_style),
            Paragraph("60 – 100 BPM", body_style),
            Paragraph("Standard adult resting pulse.", body_style)
        ],
    ]
    ref_table = Table(ref_data, colWidths=[120, 150, 270])
    ref_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f8f9fa")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e9ecef")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(ref_table)

    story.append(Spacer(1, 18))

    # Mandatory Medical Disclaimer Box
    disclaimer_text = (
        "<b>CLINICAL DISCLAIMER & NOTICE:</b><br/>"
        "This summary is generated for educational, personal wellness tracking, and documentation purposes only. "
        "The metrics recorded do not constitute a laboratory diagnosis, medical prognosis, or prescription. "
        "SmartCare AI does NOT replace the judgment, examination, or advice of a licensed healthcare provider. "
        "Always seek the counsel of your physician regarding any medical symptoms or treatment decisions."
    )
    disclaimer_table = Table([[Paragraph(disclaimer_text, disclaimer_style)]], colWidths=[540])
    disclaimer_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#fff3cd")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#ffeeba")),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(KeepTogether(disclaimer_table))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
