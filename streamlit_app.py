import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import json
import tempfile

st.set_page_config(page_title="Catálogo de Productos", page_icon="📦")
st.title("📊 Catálogo de Productos desde Google Sheets")

uploaded_file = st.file_uploader("Sube tu archivo de credenciales (.json)", type="json")

def cargar_datos(credenciales):
    try:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]

        # Guardar temporalmente el archivo subido
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

if uploaded_file is not None:
    if st.button("Cargar datos"):
        df = cargar_datos(uploaded_file)
        if df is not None and not df.empty:
            st.success("✅ Datos cargados correctamente.")
            st.dataframe(df)
        else:
            st.warning("No se encontraron datos o la hoja está vacía.")
else:
    st.info("🔹 Sube tu archivo de credenciales JSON para comenzar.")
