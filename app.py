# -*- coding: utf-8 -*-
"""
Retail Sales Dashboard

@author: Angelique
"""

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="Retail Dashboard",
    layout="wide"
)
st.title("Retail Dashboard")


@st.cache_data
def load_data():
    df = pd.read_csv("retail_sales_dataset.csv")
    df["Date"] = pd.to_datetime(df["Date"])
    df["Month"] = df["Date"].dt.to_period("M").astype(str)
    df["Age Group"] = pd.cut(
        df["Age"], bins=[0, 30, 45, 60, 120],
        labels=["18-30", "31-45", "46-60", "60+"]
    )
    return df


df = load_data()

with st.sidebar:
    st.header("Filters")

    categories = sorted(df["Product Category"].unique())
    selected_categories = st.multiselect(
        "Product Category", options=categories, default=categories
    )

    gender = sorted(df["Gender"].unique())
    selected_genders = st.multiselect(
        "Gender", options=gender, default=gender
    )

    age_group_options = ["18-30", "31-45", "46-60", "60+"]
    selected_age_groups = st.multiselect(
        "Age Group", options=age_group_options, default=age_group_options
    )

    months = sorted(df["Month"].unique())
    start_month, end_month = st.select_slider(
        "Month Range",
        options=months,
        value=(months[0], months[-1])
    )

mask = (
    (df["Product Category"].isin(selected_categories)) &
    (df["Gender"].isin(selected_genders)) &
    (df["Age Group"].isin(selected_age_groups)) &
    (df["Month"].between(start_month, end_month))
)

filtered_df = df[mask]

total_revenue = filtered_df["Total Amount"].sum()
total_orders = filtered_df["Transaction ID"].nunique()
avg_order_value = filtered_df["Total Amount"].mean()
total_customers = filtered_df["Customer ID"].nunique()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Revenue", f"${total_revenue:,.0f}")
col2.metric("Total Orders", f"{total_orders:,}")
col3.metric("Avg Order Value", f"${avg_order_value:,.2f}")
col4.metric("Unique Customers", f"{total_customers:,}")

monthly_revenue = filtered_df.groupby("Month")["Total Amount"].sum().reset_index()
fig_trend = px.line(monthly_revenue, x="Month", y="Total Amount", markers=True, title="Revenue Over Time")
st.plotly_chart(fig_trend, use_container_width=True)

left, right = st.columns(2)

with left:
    cat_revenue = (
        filtered_df.groupby("Product Category")["Total Amount"]
        .sum()
        .reset_index()
        .sort_values("Total Amount", ascending=False)
    )
    fig_cat = px.bar(cat_revenue, x="Product Category", y="Total Amount", title="Revenue by Category")
    st.plotly_chart(fig_cat, use_container_width=True)

with right:
    gender_revenue = (
        filtered_df.groupby("Gender")["Total Amount"]
        .sum()
        .reset_index()
        .sort_values("Total Amount", ascending=False)
    )
    fig_gender = px.bar(gender_revenue, x="Gender", y="Total Amount", title="Revenue by Gender")
    st.plotly_chart(fig_gender, use_container_width=True)

fig_age = px.histogram(filtered_df, x="Age", nbins=15, title="Customer Age Distribution")
st.plotly_chart(fig_age, use_container_width=True)