
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

DATA_FILE = Path(__file__).parent / "BOQ_All_Jobs.xlsx"
PLANNED, USED = "#2a78d6", "#eb6834"   # blue = BOQ / planned, orange = used / claimed


@st.cache_data
def load_data(path):
    df = pd.read_excel(path, sheet_name=0)
    df["Item_No"] = df["Item_No"].astype(str)
    return df


def stretch(fn, *args, **kwargs):
    """Full-width element on both new and older Streamlit versions."""
    try:
        return fn(*args, width="stretch", **kwargs)
    except TypeError:
        return fn(*args, use_container_width=True, **kwargs)


def money(x):
    return f"R {x:,.2f}"


def pick(label, options, key):
    """Selectbox with an 'All' option."""
    return st.sidebar.selectbox(label, ["All"] + sorted(options), key=key)


st.set_page_config(page_title="BOQ Material Tracker", layout="wide")
df = load_data(DATA_FILE)

# ---------------- Sidebar: Job -> Bill -> Category -> Material -> Work type
st.sidebar.header("Select")
job = st.sidebar.selectbox("Job", df["Job"].unique().tolist())
d = df[df["Job"] == job]

bill = pick("Bill", d["Bill"].unique(), "bill")
if bill != "All":
    d = d[d["Bill"] == bill]

category = pick("Category", d["Category"].unique(), "cat")
if category != "All":
    d = d[d["Category"] == category]

material = pick("Material", d["Material"].unique(), "mat")
if material != "All":
    d = d[d["Material"] == material]

work = pick("Work type", d["Work_Type"].unique(), "work")
if work != "All":
    d = d[d["Work_Type"] == work]

only_used = st.sidebar.checkbox("Only show items with quantity used", value=False)
if only_used:
    d = d[d["Qty_Used"] > 0]

# ---------------- Header + totals
st.title(f"{job}")
st.caption(" → ".join(x for x in [bill, category, material, work] if x != "All") or "All items")

if d.empty:
    st.info("No items match this selection.")
    st.stop()

boq_cost, actual_cost = d["BOQ_Cost"].sum(), d["Actual_Cost"].sum()
c1, c2, c3, c4 = st.columns(4)
c1.metric("BOQ budget", money(boq_cost))
c2.metric("Actual cost (claimed)", money(actual_cost))
c3.metric("Difference (budget − actual)", money(boq_cost - actual_cost))
c4.metric("% of budget spent", f"{(actual_cost / boq_cost * 100) if boq_cost else 0:.1f}%")

# Only one unit selected -> quantities can be added up
units = d["Unit"].unique()
if len(units) == 1:
    q1, q2, q3 = st.columns(3)
    q1.metric(f"BOQ quantity ({units[0]})", f"{d['BOQ_Qty'].sum():,.2f}")
    q2.metric(f"Quantity used ({units[0]})", f"{d['Qty_Used'].sum():,.2f}")
    q3.metric(f"Remaining ({units[0]})", f"{d['Qty_Remaining'].sum():,.2f}")

# ---------------- Charts
d = d.assign(Label=d["Material"] + " · " + d["Work_Type"] + " (" + d["Item_No"] + ")")


def bar_chart(planned_col, used_col, title, axis_title, prefix=""):
    """Grouped bars; horizontal when there are many items so labels stay readable."""
    horizontal = len(d) > 12
    fig = go.Figure()
    for name, col, color in [("BOQ / planned", planned_col, PLANNED),
                             ("Used / claimed", used_col, USED)]:
        if horizontal:
            xy = dict(y=d["Label"], x=d[col], orientation="h")
            cat, val = "%{y}", "%{x:,.2f}"
        else:
            xy = dict(x=d["Label"], y=d[col])
            cat, val = "%{x}", "%{y:,.2f}"
        fig.add_bar(name=name, marker_color=color,
                    hovertemplate=f"{cat}<br>{name}: {prefix}{val}<extra></extra>", **xy)
    fig.update_layout(title=title, barmode="group", bargap=0.25, bargroupgap=0.08,
                      height=max(420, 34 * len(d) + 160) if horizontal else 480,
                      legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0),
                      margin=dict(t=80, b=10, l=10, r=10))
    if horizontal:
        fig.update_layout(xaxis_title=axis_title)
        fig.update_yaxes(autorange="reversed")
    else:
        fig.update_layout(yaxis_title=axis_title, xaxis_tickangle=-30)
    return fig


tab_q, tab_c, tab_t = st.tabs(["Quantity", "Cost", "Table"])

with tab_q:
    if len(units) > 1:
        st.caption("Mixed units in this selection (" + ", ".join(units) +
                   ") – narrow the selection to compare like with like.")
    stretch(st.plotly_chart, bar_chart("BOQ_Qty", "Qty_Used", "Quantity: BOQ vs used", "Quantity"))

with tab_c:
    stretch(st.plotly_chart, bar_chart("BOQ_Cost", "Actual_Cost",
                                       "Cost: BOQ budget vs actual", "Rand (R)", "R "))
    claims = pd.DataFrame({
        "Claim": [f"Claim {i}" for i in range(1, 5)],
        "Amount": [d[f"Claim{i}_Amount"].sum() for i in range(1, 5)],
    })
    claims = claims[claims["Amount"] != 0]
    if not claims.empty:
        fig = go.Figure(go.Bar(x=claims["Claim"], y=claims["Amount"], marker_color=USED,
                               text=[money(a) for a in claims["Amount"]], textposition="outside",
                               hovertemplate="%{x}: R %{y:,.2f}<extra></extra>"))
        fig.update_layout(title="Amount claimed per claim", yaxis_title="Rand (R)", height=380,
                          margin=dict(t=60, b=10, l=10, r=10))
        stretch(st.plotly_chart, fig)

with tab_t:
    show = ["Item_No", "Category", "Material", "Work_Type", "Unit", "Rate", "BOQ_Qty", "Qty_Used",
            "Qty_Remaining", "Pct_Used", "BOQ_Cost", "Actual_Cost", "Cost_Difference", "MOS_Qty"]
    tbl = d[show].assign(Pct_Used=d["Pct_Used"] * 100)
    stretch(
        st.dataframe, tbl, hide_index=True,
        column_config={
            "Rate": st.column_config.NumberColumn(format="R %.2f"),
            "BOQ_Cost": st.column_config.NumberColumn("BOQ cost", format="R %.2f"),
            "Actual_Cost": st.column_config.NumberColumn("Actual cost", format="R %.2f"),
            "Cost_Difference": st.column_config.NumberColumn("Difference", format="R %.2f"),
            "Pct_Used": st.column_config.ProgressColumn("% used", min_value=0, max_value=100,
                                                        format="%.0f%%"),
        },
    )
    st.download_button("Download this selection (CSV)", d[show].to_csv(index=False),
                       file_name=f"{job}_selection.csv")

# ---------------- Product detail when one material is chosen
if material != "All":
    st.subheader(f"About: {material}")
    desc = d["Full_Description"].dropna()
    if not desc.empty:
        st.write(desc.iloc[0]) 