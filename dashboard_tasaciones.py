import streamlit as st
import pandas as pd
import plotly.express as px

# Configuración del tablero
st.set_page_config(page_title="Dashboard Planilla Tasaciones", layout="wide")

st.title("⚡ Dashboard Interactivo - Planilla Unificada de Tasaciones")

# Subir archivo Excel o cargar por defecto
archivo = st.sidebar.file_uploader("📂 Cargar archivo Excel", type=["xlsx", "xls"])

if archivo is None:
    # Intenta leer el archivo local si existe
    try:
        df_raw = pd.read_excel("01_PLANILLA UNIFICADA (TASACIÓN APROBADA).xlsx", sheet_name="PLANILLA-TASACIÓN APROBADA_CTMQ")
    except Exception:
        st.info("👈 Por favor carga el archivo Excel en el menú lateral para comenzar.")
        st.stop()
else:
    df_raw = pd.read_excel(archivo, sheet_name="PLANILLA-TASACIÓN APROBADA_CTMQ")

# Limpieza básica de columnas
df = df_raw.copy()
df.columns = [str(c).strip() for c in df.columns]

# --- BARRA LATERAL DE FILTROS ---
st.sidebar.header("🎯 Filtros de Datos")

# 1. Filtro por Tramo
tramos_disponibles = sorted([str(x) for x in df['TRAMO'].dropna().unique()])
filtro_tramo = st.sidebar.multiselect("Filtrar por Tramo:", options=tramos_disponibles, default=tramos_disponibles)

# 2. Filtro por Tipo de Predio
tipos_predio = sorted([str(x) for x in df['TIPO DE PREDIO'].dropna().unique()])
filtro_tipo = st.sidebar.multiselect("Tipo de Predio:", options=tipos_predio, default=tipos_predio)

# 3. Filtro por Estado de Formalización
if 'ESTADO DE PROCESO DE FORMALIZACIÓN (CTMQ)' in df.columns:
    estados = sorted([str(x) for x in df['ESTADO DE PROCESO DE FORMALIZACIÓN (CTMQ)'].dropna().unique()])
    filtro_estado = st.sidebar.multiselect("Estado de Proceso:", options=estados, default=estados)
else:
    filtro_estado = []

# 4. Buscador de texto (Titular, DNI, Código)
busqueda_texto = st.sidebar.text_input("🔍 Buscar por Titular / DNI / Código:")

# Aplicación de filtros
df_filtrado = df[
    df['TRAMO'].astype(str).isin(filtro_tramo) &
    df['TIPO DE PREDIO'].astype(str).isin(filtro_tipo)
]

if filtro_estado and 'ESTADO DE PROCESO DE FORMALIZACIÓN (CTMQ)' in df.columns:
    df_filtrado = df_filtrado[df_filtrado['ESTADO DE PROCESO DE FORMALIZACIÓN (CTMQ)'].astype(str).isin(filtro_estado)]

if busqueda_texto:
    columnas_busqueda = ['TITULAR', 'DNI Y/O RUC', 'CÓDIGO LT', 'POSEEDOR']
    cols_existentes = [c for c in columnas_busqueda if c in df_filtrado.columns]
    mascara = df_filtrado[cols_existentes].astype(str).apply(
        lambda col: col.str.contains(busqueda_texto, case=False, na=False)
    ).any(axis=1)
    df_filtrado = df_filtrado[mascara]

# --- TARJETAS DE MÉTRICAS GLOBALES ---
col_monto = 'MONTO TOTAL NEGOCIADO\n(2026)'
if col_monto not in df_filtrado.columns:
    col_monto = [c for c in df_filtrado.columns if 'TOTAL NEGOCIADO' in c.upper()][0]

total_predios = len(df_filtrado)
monto_total = pd.to_numeric(df_filtrado[col_monto], errors='coerce').sum()
torres_total = pd.to_numeric(df_filtrado.get('No. TORRES', 0), errors='coerce').sum()

c1, c2, c3 = st.columns(3)
c1.metric("📌 Total Predios / Registros", f"{total_predios:,}")
c2.metric("💰 Presupuesto Total Negociado", f"S/ {monto_total:,.2f}")
c3.metric("🗼 N° Total de Torres", f"{int(torres_total):,}")

st.divider()

# --- SECCIÓN GRÁFICA INTERACTIVA ---
g1, g2 = st.columns(2)

with g1:
    st.subheader("📊 Distribución de Presupuesto por Tramo")
    df_tramo = df_filtrado.groupby('TRAMO')[col_monto].sum().reset_index()
    fig_tramo = px.bar(
        df_tramo, x='TRAMO', y=col_monto,
        labels={col_monto: 'Monto Total (S/)', 'TRAMO': 'Tramo'},
        color='TRAMO', text_auto='.2s'
    )
    st.plotly_chart(fig_tramo, use_container_width=True)

with g2:
    st.subheader("🥧 Predios por Tipo de Propiedad")
    fig_pie = px.pie(
        df_filtrado, names='TIPO DE PREDIO', values=col_monto,
        hole=0.4, title="Participación Presupuestal por Tipo de Predio"
    )
    st.plotly_chart(fig_pie, use_container_width=True)

st.divider()

# --- TABLA RESUMEN DINÁMICA ---
st.subheader("📋 Resumen Agrupado por Tramo y Tipo de Predio")
tabla_resumen = df_filtrado.pivot_table(
    index=['TRAMO', 'TIPO DE PREDIO'],
    values=[col_monto, 'No. TORRES'],
    aggfunc={col_monto: 'sum', 'No. TORRES': 'count'}
).rename(columns={col_monto: 'Presupuesto Total (S/)', 'No. TORRES': 'Cant. Registros'})

st.dataframe(tabla_resumen.style.format({'Presupuesto Total (S/)': 'S/ {:,.2f}'}), use_container_width=True)

# --- DETALLE INDIVIDUAL DE DATOS ---
st.subheader(f"📑 Detalle de Registros Filtrados ({len(df_filtrado)} filas)")
columnas_visibles = ['TRAMO', 'CÓDIGO LT', 'TIPO DE PREDIO', 'TITULAR', 'DNI Y/O RUC', 'No. TORRES', col_monto]
cols_mostrar = [c for c in columnas_visibles if c in df_filtrado.columns]

st.dataframe(df_filtrado[cols_mostrar], use_container_width=True)

# Descargar datos filtrados
csv = df_filtrado.to_csv(index=False).encode('utf-8-sig')
st.download_button(
    label="📥 Descargar datos filtrados en CSV",
    data=csv,
    file_name="tasaciones_filtradas.csv",
    mime="text/csv"
)
