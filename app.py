from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


st.set_page_config(page_title="Dashboard Comercial Agosto 2026", page_icon="📊", layout="wide")

DATA = Path(__file__).parent / "resumen_sku.csv"
ORDERS_DATA = Path(__file__).parent / "ordenes_pendientes.csv"
df = pd.read_csv(DATA, encoding="utf-8-sig")

st.title("Dashboard Comercial · Agosto 2026")
st.caption("Una vista sencilla: meta de venta → pedidos recibidos → ventas facturadas")

with st.sidebar:
    st.header("¿Qué quieres revisar?")
    estados = sorted(df["Estado"].dropna().unique())
    seleccion = st.multiselect("Estado de los productos", estados, default=estados)
    producto = st.text_input("Buscar un producto")

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
r1c1.metric("Meta esperada (unidades)", f"{forecast:,.0f}")
r1c2.metric("Pedidos recibidos (unidades)", f"{oc:,.0f}", f"{oc/forecast:.1%} de la meta" if forecast else "—")
r1c3.metric("Ya facturado (unidades)", f"{facturado:,.0f}", f"{facturado/forecast:.1%} de la meta" if forecast else "—")

r2c1, r2c2, r2c3 = st.columns(3)
r2c1.metric("Pedidos ya facturados", f"{facturado/oc:.1%}" if oc else "—")
r2c2.metric("Falta facturar (unidades)", f"{pendiente_unidades:,.0f}")
r2c3.metric("Dinero por facturar (USD)", f"${pendiente_usd:,.0f}")
if r2c3.button("🔎 Ver pedidos y productos pendientes", use_container_width=True):
    st.session_state["mostrar_ordenes"] = not st.session_state.get("mostrar_ordenes", False)

por_cada_100 = round(100 * facturado / oc) if oc else 0
st.info(
    f"💡 **En palabras simples:** de cada 100 unidades pedidas, ya facturamos {por_cada_100} "
    f"y todavía faltan {100 - por_cada_100}. Ese pendiente representa cerca de **${pendiente_usd:,.0f}**."
)
with st.expander("¿Cómo se calcula el dinero pendiente?"):
    st.write(
        "Para cada producto tomamos las unidades pedidas que aún no se han facturado y las "
        "multiplicamos por su precio promedio en las órdenes de compra."
    )

if st.session_state.get("mostrar_ordenes", False):
    st.subheader("Pedidos que todavía no se facturaron por completo")
    st.caption(
        "El archivo de facturas dice qué producto se facturó, pero no señala de qué orden salió. "
        "Por eso, el pendiente por orden es una estimación proporcional."
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

    st.caption("Marca la casilla **Sumar** si quieres incluir esa orden. Desmárcala para quitarla de la suma.")
    totales_seleccion = st.empty()
    resumen_editable = resumen_oc.copy()
    resumen_editable.insert(0, "Sumar", True)
    tabla_oc = st.data_editor(
        resumen_editable,
        hide_index=True,
        use_container_width=True,
        column_order=["Sumar", "Cliente", "Orden", "Producto_principal", "Productos",
                      "Pendiente_estimado_unidades", "Pendiente_estimado_USD"],
        disabled=["Cliente", "Orden", "Producto_principal", "Productos",
                  "Pendiente_estimado_unidades", "Pendiente_estimado_USD"],
        key=f"tabla_ordenes_{cliente_oc}",
        column_config={
            "Sumar": st.column_config.CheckboxColumn("¿Sumar?", default=True, width="small"),
            "Cliente": "Cliente",
            "Orden": "Número de orden",
            "Producto_principal": st.column_config.TextColumn("Producto con más pendiente", width="large"),
            "Productos": st.column_config.NumberColumn("Cantidad de productos", format="%d"),
            "Unidades_OC": st.column_config.NumberColumn("Unidades en OC", format="%,.0f"),
            "Pendiente_estimado_unidades": st.column_config.NumberColumn("Unidades que faltan", format="%,.0f"),
            "Pendiente_estimado_USD": st.column_config.NumberColumn("Dinero que falta", format="$%,.2f"),
        },
    )
    resumen_oc = tabla_oc[tabla_oc["Sumar"]].drop(columns="Sumar")
    ordenes_elegidas = set(resumen_oc["Orden"].astype(str))
    orders_filtradas = orders[orders["Orden"].astype(str).isin(ordenes_elegidas)]

    with totales_seleccion.container():
        suma1, suma2, suma3 = st.columns(3)
        suma1.metric("Órdenes incluidas", f"{len(resumen_oc):,}")
        suma2.metric("Unidades que faltan", f"{resumen_oc['Pendiente_estimado_unidades'].sum():,.0f}")
        suma3.metric("Dinero que falta", f"${resumen_oc['Pendiente_estimado_USD'].sum():,.2f}")

    with st.expander("Ver todos los productos de las órdenes seleccionadas"):
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
    st.subheader("Meta, pedidos y facturación por producto")
    graf = vista.nlargest(20, "Forecast_Unidades").melt(
        id_vars="Producto",
        value_vars=["Forecast_Unidades", "OC_Unidades", "Facturado_Unidades"],
        var_name="Indicador",
        value_name="Unidades",
    )
    nombres = {
        "Forecast_Unidades": "Meta",
        "OC_Unidades": "Pedidos",
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
        color_discrete_map={"Meta": "#94a3b8", "Pedidos": "#2563eb", "Facturado": "#16a34a"},
    )
    fig.update_layout(height=680, yaxis={"categoryorder": "total ascending"}, legend_title_text="")
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Estado de los productos")
    st.caption("Aquí puedes ver rápidamente cuáles van bien y cuáles necesitan atención.")
    conteo = vista["Estado"].fillna("Sin estado").value_counts().rename_axis("Estado").reset_index(name="SKUs")
    fig2 = px.pie(conteo, names="Estado", values="SKUs", hole=.55)
    fig2.update_layout(height=350, legend_title_text="")
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Productos con más unidades pendientes")
    brechas = vista.nlargest(10, "Brecha_Forecast_Facturado")[["Producto", "Brecha_Forecast_Facturado", "Estado"]]
    st.dataframe(
        brechas.rename(columns={"Brecha_Forecast_Facturado": "Unidades pendientes"}),
        hide_index=True,
        use_container_width=True,
    )

st.subheader("Detalle completo por producto")
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
        "Forecast_Unidades": st.column_config.NumberColumn("Meta", format="%,.0f"),
        "OC_Unidades": st.column_config.NumberColumn("Pedidos", format="%,.0f"),
        "Facturado_Unidades": st.column_config.NumberColumn("Ya facturado", format="%,.0f"),
        "Pendiente_Unidades_OC": st.column_config.NumberColumn("Falta facturar", format="%,.0f"),
        "Precio_OC": st.column_config.NumberColumn("Precio promedio", format="$%.2f"),
        "Pendiente_USD": st.column_config.NumberColumn("Dinero pendiente", format="$%,.2f"),
        "OC_vs_Forecast": st.column_config.ProgressColumn("Pedidos / Meta", min_value=0, max_value=1.5, format="%.1f"),
        "Facturado_vs_Forecast": st.column_config.ProgressColumn("Facturado / Meta", min_value=0, max_value=1.5, format="%.1f"),
        "Facturado_vs_OC": st.column_config.NumberColumn("Facturado / Pedidos", format="%.1f"),
    },
)
