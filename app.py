from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


st.set_page_config(page_title="Dashboard Comercial Agosto 2026", page_icon="📊", layout="wide")

DATA = Path(__file__).parent / "resumen_sku.csv"
df = pd.read_csv(DATA, encoding="utf-8-sig")

st.title("Dashboard Comercial Agosto 2026")
st.caption("Forecast → Órdenes de compra → Facturación | Vista gerencial")

with st.sidebar:
    st.header("Filtros")
    estados = sorted(df["Estado"].dropna().unique())
    seleccion = st.multiselect("Estado comercial", estados, default=estados)
    producto = st.text_input("Buscar producto")

vista = df[df["Estado"].isin(seleccion)].copy()
if producto:
    vista = vista[vista["Producto"].str.contains(producto, case=False, na=False)]

forecast = df["Forecast_Unidades"].sum()
oc = df["OC_Unidades"].sum()
facturado = df["Facturado_Unidades"].sum()
pendiente_unidades = df["Pendiente_Unidades_OC"].sum()
pendiente_usd = df["Pendiente_USD"].sum()

st.markdown(
    """
    <style>
    div[data-testid="stMetric"] {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 18px 20px;
        min-height: 132px;
    }
    div[data-testid="stMetricValue"] {
        font-size: clamp(1.9rem, 3vw, 2.65rem);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

r1c1, r1c2, r1c3 = st.columns(3)
r1c1.metric("Forecast", f"{forecast:,.0f} unidades")
r1c2.metric("Órdenes de compra recibidas", f"{oc:,.0f} unidades", f"{oc/forecast:.1%} del forecast" if forecast else "—")
r1c3.metric("Facturado", f"{facturado:,.0f} unidades", f"{facturado/forecast:.1%} del forecast" if forecast else "—")

r2c1, r2c2, r2c3 = st.columns(3)
r2c1.metric("Cumplimiento de OC", f"{facturado/oc:.1%}" if oc else "—")
r2c2.metric("Pendiente de facturar", f"{pendiente_unidades:,.0f} unidades")
r2c3.metric("Venta pendiente", f"USD {pendiente_usd:,.2f}")

st.info(
    "La venta pendiente se calcula por SKU como max(OC − facturado, 0) × precio promedio de OC. "
    "Los sobrecumplimientos de otros SKU no reducen esta oportunidad pendiente."
)

left, right = st.columns((3, 2))
with left:
    st.subheader("Cumplimiento por producto")
    graf = vista.nlargest(20, "Forecast_Unidades").melt(
        id_vars="Producto",
        value_vars=["Forecast_Unidades", "OC_Unidades", "Facturado_Unidades"],
        var_name="Indicador",
        value_name="Unidades",
    )
    nombres = {
        "Forecast_Unidades": "Forecast",
        "OC_Unidades": "OC",
        "Facturado_Unidades": "Facturado",
    }
    graf["Indicador"] = graf["Indicador"].map(nombres)
    fig = px.bar(
        graf,
        x="Unidades",
        y="Producto",
        color="Indicador",
        barmode="group",
        orientation="h",
        color_discrete_map={"Forecast": "#94a3b8", "OC": "#2563eb", "Facturado": "#16a34a"},
    )
    fig.update_layout(height=680, yaxis={"categoryorder": "total ascending"}, legend_title_text="")
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Semáforo comercial")
    conteo = vista["Estado"].fillna("Sin estado").value_counts().rename_axis("Estado").reset_index(name="SKUs")
    fig2 = px.pie(conteo, names="Estado", values="SKUs", hole=.55)
    fig2.update_layout(height=350, legend_title_text="")
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Principales brechas")
    brechas = vista.nlargest(10, "Brecha_Forecast_Facturado")[["Producto", "Brecha_Forecast_Facturado", "Estado"]]
    st.dataframe(
        brechas.rename(columns={"Brecha_Forecast_Facturado": "Unidades pendientes"}),
        hide_index=True,
        use_container_width=True,
    )

st.subheader("Detalle SKU")
detalle = vista[[
    "Codigo", "Producto", "Forecast_Unidades", "OC_Unidades", "Facturado_Unidades",
    "Pendiente_Unidades_OC", "Precio_OC", "Pendiente_USD",
    "OC_vs_Forecast", "Facturado_vs_Forecast", "Facturado_vs_OC", "Estado",
]].copy()
st.dataframe(
    detalle,
    hide_index=True,
    use_container_width=True,
    column_config={
        "Forecast_Unidades": st.column_config.NumberColumn("Forecast", format="%,.0f"),
        "OC_Unidades": st.column_config.NumberColumn("OC", format="%,.0f"),
        "Facturado_Unidades": st.column_config.NumberColumn("Facturado", format="%,.0f"),
        "Pendiente_Unidades_OC": st.column_config.NumberColumn("Pendiente", format="%,.0f"),
        "Precio_OC": st.column_config.NumberColumn("Precio OC", format="$%.2f"),
        "Pendiente_USD": st.column_config.NumberColumn("Pendiente USD", format="$%,.2f"),
        "OC_vs_Forecast": st.column_config.ProgressColumn("OC / Forecast", min_value=0, max_value=1.5, format="%.1f"),
        "Facturado_vs_Forecast": st.column_config.ProgressColumn("Fact. / Forecast", min_value=0, max_value=1.5, format="%.1f"),
        "Facturado_vs_OC": st.column_config.NumberColumn("Fact. / OC", format="%.1f"),
    },
)
