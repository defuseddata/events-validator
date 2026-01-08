import streamlit as st
from helpers.helpers import export_schema
import io
import json
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch


def render_exporter():

    left, center, right = st.columns([2,5,2])

    if st.session_state.schema:
        schema = export_schema()
        with left:
            st.container()
        with right:
            st.container()
        with center:
            with st.container(horizontal_alignment="left", vertical_alignment="bottom"):
                left, right = st.columns([5,5])
                with left:
                    st.title("Export Schema")
                    st.text("Here you can export your schema in accepted format.")
                with right:
                    with st.container(horizontal=True, vertical_alignment="bottom"):

                        pdf_bytes = download_schema_pdf(schema)

                        st.download_button(
                            "Download PDF",
                            data=pdf_bytes,
                            file_name="schema.pdf",
                            mime="application/pdf",
                            type="primary"
                        )
            st.json(schema)

def download_schema_pdf(schema: dict):
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    import io
    import xml.sax.saxutils as saxutils

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()

    H2 = ParagraphStyle(
        "H2",
        parent=styles["Heading2"],
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#202124"),
        spaceAfter=12,
        spaceBefore=12
    )

    normal = ParagraphStyle(
        "Normal",
        parent=styles["BodyText"],
        fontSize=10,
        leading=14
    )

    story = []

    # -------------------
    # SECTION: Parameters
    # -------------------

    story.append(Paragraph(
    f"Schema name: {schema['event_name']['value'] or 'not provided'} "
    f"version: {schema['version']['value'] or 'not provided'}",
    normal
))



    params_table = [
        ["Name", "Type", "Required", "value", "Description"]
    ]

    # MAIN PARAMETERS
    for name, param in schema.items():

        p_type = param.get("type", "")
        value = param.get("value", "")
        required = "Yes"

        # <-- TU: używamy klucza "description" (małymi literami)
        raw_desc = param.get("description", "") or ""
        # escape XML special chars and convert newlines to <br/><br/> for paragraphs
        safe_desc = saxutils.escape(str(raw_desc)).replace("\n", "<br/><br/>")
        description_para = Paragraph(safe_desc, normal)

        params_table.append([
            Paragraph(f"<b>{name}</b>", normal),
            Paragraph(p_type, normal),
            Paragraph(required, normal),
            Paragraph(str(value), normal),
            description_para
        ])

    # Common table style (reuse for nested tables)
    table_style = TableStyle([
        # header
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f3f4")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("ALIGN", (0, 0), (-1, 0), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),

        # body
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 10),

        # lines
        ("LINEBELOW", (0, 0), (-1, 0), 0.75, colors.HexColor("#dadce0")),
        ("LINEBELOW", (0, 1), (-1, -1), 0.25, colors.HexColor("#dadce0")),

        # padding
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ])

    params_col_widths = [120, 70, 60, 100, 190]
    table = Table(params_table, colWidths=params_col_widths)
    table.setStyle(table_style)

    story.append(table)
    story.append(Spacer(1, 20))

    # -------------------------
    # SECTION: Dynamic nested (array) parameters
    # -------------------------
    for name, param in schema.items():
        if param.get("type") == "array" and isinstance(param.get("nestedSchema"), dict):

            # Section title uses the actual field name (dynamic)
            story.append(Paragraph(f"{name}: nested keys", H2))

            item_table_data = [
                ["Name", "Type", "Required", "value", "Description"]
            ]

            for nested_name, nested_spec in param["nestedSchema"].items():

                n_type = nested_spec.get("type", "")
                n_value = nested_spec.get("value", "")
                n_required = "Yes" #future : add required

                # nested description also under key "description"
                raw_n_desc = nested_spec.get("description", "") or ""
                safe_n_desc = saxutils.escape(str(raw_n_desc)).replace("\n", "<br/><br/>")

                item_table_data.append([
                    Paragraph(f"<b>{nested_name}</b>", normal),
                    Paragraph(n_type, normal),
                    Paragraph(n_required, normal),
                    Paragraph(str(n_value), normal),
                    Paragraph(safe_n_desc, normal)
                ])

            nested_table = Table(item_table_data, colWidths=params_col_widths)
            nested_table.setStyle(table_style)
            story.append(nested_table)
            story.append(Spacer(1, 16))

    # Build PDF into the buffer
    doc.build(story)

    buffer.seek(0)
    return buffer.getvalue()
