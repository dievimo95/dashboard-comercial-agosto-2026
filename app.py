from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


st.set_page_config(page_title="Dashboard Comercial Agosto 2026", page_icon="📊", layout="wide")

DATA = Path(__file__).parent / "resumen_sku.csv"
ORDERS_DATA = Path(__file__).parent / "ordenes_pendientes.csv"
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
        font-size: clamp(1.65rem, 2.6vw, 2.35rem);
    }
    div[data-testid="stButton"] button {
        border-radius: 10px;
        font-weight: 650;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

r1c1, r1c2, r1c3 = st.columns(3)
r1c1.metric("Forecast (unidades)", f"{forecast:,.0f}")
r1c2.metric("OC recibidas (unidades)", f"{oc:,.0f}", f"{oc/forecast:.1%} del forecast" if forecast else "—")
r1c3.metric("Facturado (unidades)", f"{facturado:,.0f}", f"{facturado/forecast:.1%} del forecast" if forecast else "—")

r2c1, r2c2, r2c3 = st.columns(3)
r2c1.metric("Cumplimiento de OC", f"{facturado/oc:.1%}" if oc else "—")
r2c2.metric("Pendiente (unidades)", f"{pendiente_unidades:,.0f}")
r2c3.metric("Venta pendiente (USD)", f"${pendiente_usd:,.0f}")
if r2c3.button("🔎 Ver órdenes pendientes", use_container_width=True):
    st.session_state["mostrar_ordenes"] = not st.session_state.get("mostrar_ordenes", False)

st.info(
    "La venta pendiente se calcula por SKU como max(OC − facturado, 0) × precio promedio de OC. "
    "Los sobrecumplimientos de otros SKU no reducen esta oportunidad pendiente."
)

if st.session_state.get("mostrar_ordenes", False):
    st.subheader("Órdenes de compra con facturación pendiente")
    st.caption(
        "La facturación disponible está consolidada por SKU y no contiene el número de OC. "
        "Por eso, el saldo se distribuye proporcionalmente entre las órdenes que incluyen cada producto."
    )
    orders = pd.read_csv(ORDERS_DATA, encoding="utf-8-sig")
    resumen_oc = orders.groupby(["Cliente", "Orden"], as_index=False).agg(
        Productos=("Codigo", "nunique"),
        Unidades_OC=("OC_Unidades_documento", "sum"),
        Pendiente_estimado_unidades=("Pendiente_estimado_unidades", "sum"),
        Pendiente_estimado_USD=("Pendiente_estimado_USD", "sum"),
    ).sort_values("Pendiente_estimado_USD", ascending=False)
    producto_principal = (
        orders.sort_values("Pendiente_estimado_USD", ascending=False)
        .drop_duplicates(["Cliente", "Orden"])[["Cliente", "Orden", "Producto"]]
        .rename(columns={"Producto": "Producto_principal"})
    )
    resumen_oc = resumen_oc.merge(producto_principal, on=["Cliente", "Orden"], how="left")

    clientes_oc = ["Todos"] + sorted(resumen_oc["Cliente"].dropna().unique().tolist())
    cliente_oc = st.selectbox("Filtrar cliente", clientes_oc, key="cliente_oc")
    if cliente_oc != "Todos":
        resumen_oc = resumen_oc[resumen_oc["Cliente"] == cliente_oc]

    resumen_oc["Clave_OC"] = resumen_oc["Cliente"].astype(str) + " | " + resumen_oc["Orden"].astype(str)
    opciones_oc = resumen_oc["Clave_OC"].tolist()
    seleccion_oc = st.multiselect(
        "Órdenes incluidas en la suma",
        opciones_oc,
        default=opciones_oc,
        key=f"ordenes_incluidas_{cliente_oc}",
        help="Desmarca una orden para excluirla de los totales y de la tabla.",
    )
    resumen_oc = resumen_oc[resumen_oc["Clave_OC"].isin(seleccion_oc)].drop(columns="Clave_OC")
    ordenes_elegidas = set(resumen_oc["Orden"].astype(str))
    orders_filtradas = orders[orders["Orden"].astype(str).isin(ordenes_elegidas)]

    suma1, suma2, suma3 = st.columns(3)
    suma1.metric("Órdenes seleccionadas", f"{len(resumen_oc):,}")
    suma2.metric("Unidades seleccionadas", f"{resumen_oc['Pendiente_estimado_unidades'].sum():,.0f}")
    suma3.metric("Venta seleccionada", f"${resumen_oc['Pendiente_estimado_USD'].sum():,.2f}")

    st.dataframe(
        resumen_oc,
        hide_index=True,
        use_container_width=True,
        column_order=["Cliente", "Orden", "Producto_principal", "Productos",
                      "Pendiente_estimado_unidades", "Pendiente_estimado_USD"],
        column_config={
            "Cliente": "Cliente",
            "Orden": "Número de orden",
            "Producto_principal": st.column_config.TextColumn("Producto principal pendiente", width="large"),
            "Productos": st.column_config.NumberColumn("Productos en la orden", format="%d"),
            "Unidades_OC": st.column_config.NumberColumn("Unidades en OC", format="%,.0f"),
            "Pendiente_estimado_unidades": st.column_config.NumberColumn("Pendiente estimado", format="%,.0f"),
            "Pendiente_estimado_USD": st.column_config.NumberColumn("Venta pendiente estimada", format="$%,.2f"),
        },
    )

    with st.expander("Ver productos dentro de las órdenes"):
        st.dataframe(
            orders_filtradas.sort_values("Pendiente_estimado_USD", ascending=False),
            hide_index=True,
            use_container_width=True,
            column_order=["Cliente", "Orden", "Producto", "OC_Unidades_documento",
                          "Pendiente_estimado_unidades", "Precio_OC", "Pendiente_estimado_USD"],
            column_config={
                "Orden": "Número de orden",
                "OC_Unidades_documento": st.column_config.NumberColumn("Unidades en OC", format="%,.0f"),
                "Pendiente_estimado_unidades": st.column_config.NumberColumn("Pendiente estimado", format="%,.0f"),
                "Precio_OC": st.column_config.NumberColumn("Precio", format="$%.2f"),
                "Pendiente_estimado_USD": st.column_config.NumberColumn("Pendiente USD", format="$%,.2f"),
            },
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
