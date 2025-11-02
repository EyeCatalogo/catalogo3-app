import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import tempfile
import requests
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Image, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors

st.set_page_config(page_title="Catálogo de Productos", page_icon="📦")
st.title("📊 Catálogo de Productos desde Google Sheets")

uploaded_file = st.file_uploader("Sube tu archivo de credenciales (.json)", type="json")


# --- Función para cargar los datos ---
def cargar_datos(credenciales):
    try:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]

        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as temp:
            temp.write(credenciales.read())
            temp_path = temp.name

        creds = ServiceAccountCredentials.from_json_keyfile_name(temp_path, scope)
        client = gspread.authorize(creds)

        sheet = client.open("Catalogo").sheet1
        data = sheet.get_all_records()

        return pd.DataFrame(data)

    except Exception as e:
        st.error(f"🚫 Error al conectar con Google Sheets: {e}")
        return None


# --- Cargar datos ---
if uploaded_file is not None:
    if st.button("Cargar datos"):
        df = cargar_datos(uploaded_file)
        if df is not None and not df.empty:
            st.success("✅ Datos cargados correctamente.")
            st.dataframe(df)
            st.session_state["df"] = df
        else:
            st.warning("No se encontraron datos o la hoja está vacía.")
else:
    st.info("🔹 Sube tu archivo de credenciales JSON para comenzar.")


# --- Generar PDF ---
if "df" in st.session_state:
    df = st.session_state["df"]

    st.subheader("📄 Generar catálogo PDF")

    def generar_catalogo_pdf(dataframe):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        story = []
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name="ProductoTitulo", fontSize=12, leading=14, spaceAfter=4, alignment=1, textColor=colors.HexColor("#2E4053")))
        styles.add(ParagraphStyle(name="ProductoTexto", fontSize=10, leading=12, spaceAfter=2))

        productos_por_fila = 2
        filas_por_pagina = 3
        productos_por_pagina = productos_por_fila * filas_por_pagina

        for i in range(0, len(dataframe), productos_por_pagina):
            page_data = dataframe.iloc[i:i+productos_por_pagina]
            celdas = []
            fila = []

            for _, row in page_data.iterrows():
                nombre = str(row.get("nombre", row.get("Nombre", "")))
                categoria = str(row.get("categoria", row.get("Categoria", "")))
                precio = str(row.get("precio", row.get("Precio", "")))
                stock = str(row.get("stock", row.get("Stock", "")))
                imagen_url = row.get("imagen", row.get("Imagen", ""))

                # --- Descargar imagen desde URL ---
                try:
                    imagen_url = str(imagen_url).strip()
                    if not imagen_url or imagen_url == "nan":
                        raise ValueError("URL vacía")

                    # Si es un enlace de Google Drive, convertirlo a directo
                    if "drive.google.com" in imagen_url:
                        if "/d/" in imagen_url:
                            file_id = imagen_url.split("/d/")[1].split("/")[0]
                        elif "id=" in imagen_url:
                            file_id = imagen_url.split("id=")[1].split("&")[0]
                        else:
                            file_id = ""
                        if file_id:
                            imagen_url = f"https://drive.google.com/uc?export=view&id={file_id}"

                    response = requests.get(imagen_url, timeout=10)
                    if response.status_code == 200 and "image" in response.headers.get("content-type", ""):
                        img_data = BytesIO(response.content)
                        img = Image(img_data, width=5*cm, height=5*cm)
                    else:
                        # Placeholder si la imagen no se descarga correctamente
                        placeholder = Table(
                            [[Paragraph("Imagen no disponible", styles["ProductoTexto"])]],
                            colWidths=[5*cm], rowHeights=[5*cm]
                        )
                        placeholder.setStyle(TableStyle([
                            ("BACKGROUND", (0, 0), (-1, -1), colors.lightgrey),
                            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                            ("BOX", (0, 0), (-1, -1), 0.25, colors.grey),
                        ]))
                        img = placeholder
                except Exception:
                    # Placeholder si ocurre un error
                    placeholder = Table(
                        [[Paragraph("Sin imagen", styles["ProductoTexto"])]],
                        colWidths=[5*cm], rowHeights=[5*cm]
                    )
                    placeholder.setStyle(TableStyle([
                        ("BACKGROUND", (0, 0), (-1, -1), colors.lightgrey),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("BOX", (0, 0), (-1, -1), 0.25, colors.grey),
                    ]))
                    img = placeholder

                # --- Ficha del producto ---
                ficha = [
                    img,
                    Paragraph(f"<b>{nombre}</b>", styles["ProductoTitulo"]),
                    Paragraph(f"Categoría: {categoria}", styles["ProductoTexto"]),
                    Paragraph(f"Precio: ${precio}", styles["ProductoTexto"]),
                    Paragraph(f"Stock: {stock}", styles["ProductoTexto"]),
                ]

                ficha_table = Table([[ficha[0]], [ficha[1]], [ficha[2]], [ficha[3]], [ficha[4]]])
                ficha_table.setStyle(TableStyle([
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("BOX", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]))

                fila.append(ficha_table)

                if len(fila) == productos_por_fila:
                    celdas.append(fila)
                    fila = []

            if fila:
                celdas.append(fila)

            tabla = Table(celdas, colWidths=[9*cm]*productos_por_fila)
            tabla.setStyle(TableStyle([
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]))
            story.append(tabla)
            story.append(Spacer(1, 1*cm))

        doc.build(story)
        buffer.seek(0)
        return buffer

    if st.button("📘 Generar Catálogo PDF"):
        pdf_buffer = generar_catalogo_pdf(df)
        st.success("Catálogo generado correctamente ✅")
        st.download_button(
            label="⬇️ Descargar Catálogo",
            data=pdf_buffer,
            file_name="catalogo.pdf",
            mime="application/pdf"
        )
