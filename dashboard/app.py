import streamlit as st
import os
import polars as pl
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 1. Page Configuration
st.set_page_config(page_title="Olist Logistics Command Center", layout="wide")
st.title("Olist Logistics Command Center")
st.markdown(
    "Monitoring the financial and reputational impact of seller fulfillment bottlenecks."
)


# 2. Data Loading (Cached for performance)
@st.cache_data
def load_data():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Load the Parquet file generated in Phase 3
    file_path = os.path.join(current_dir, "analytical_base_table.parquet")
    return pl.read_parquet(file_path).to_pandas()


df = load_data()

# 3. Sidebar Filters (Interactivity for the Hiring Manager)
st.sidebar.header("Filter Operations")
status_filter = st.sidebar.radio(
    "Delivery Status:", ["All", "Late Only", "On Time Only"]
)

if status_filter == "Late Only":
    filtered_df = df[df["is_late_delivery"] == 1]
elif status_filter == "On Time Only":
    filtered_df = df[df["is_late_delivery"] == 0]
else:
    filtered_df = df

# 4. Top Row: Executive BANs (Big-Ass Numbers)
col1, col2, col3, col4 = st.columns(4)

total_orders = len(filtered_df)
late_orders = len(filtered_df[filtered_df["is_late_delivery"] == 1])
defect_rate = (late_orders / total_orders) * 100 if total_orders > 0 else 0
revenue_at_risk = filtered_df[filtered_df["is_late_delivery"] == 1][
    "total_order_value"
].sum()
avg_csat = filtered_df["final_review_score"].mean()

with col1:
    st.metric(label="Total Orders Analyzed", value=f"{total_orders:,}")
with col2:
    st.metric(label="Late Delivery Defect Rate", value=f"{defect_rate:.1f}%")
with col3:
    st.metric(label="Revenue at Risk (Late Orders)", value=f"${revenue_at_risk:,.0f}")
with col4:
    st.metric(label="Average CSAT Score", value=f"{avg_csat:.2f} ⭐")

st.markdown("---")

# 5. Middle Row: Data Storytelling Charts
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    st.subheader("The Cost of Delay")
    # Recreating the CSAT stacked bar chart logic
    review_dist = (
        df.groupby(["is_late_delivery", "final_review_score"])
        .size()
        .reset_index(name="count")
    )
    review_dist["percentage"] = review_dist.groupby("is_late_delivery")[
        "count"
    ].transform(lambda x: x / x.sum() * 100)
    review_dist["is_late_delivery"] = review_dist["is_late_delivery"].map(
        {0: "On Time", 1: "Late Delivery"}
    )

    fig_csat = px.bar(
        review_dist,
        x="percentage",
        y="is_late_delivery",
        color="final_review_score",
        orientation="h",
        color_discrete_sequence=["#e74c3c", "#e67e22", "#f1c40f", "#3498db", "#2ecc71"],
    )
    fig_csat.update_layout(
        xaxis_title="% of Total Orders",
        yaxis_title="",
        showlegend=False,
        margin=dict(l=0, r=0, t=30, b=0),
    )
    st.plotly_chart(fig_csat, use_container_width=True)

with chart_col2:
    st.subheader("Root Cause: Seller Bottlenecks")
    # Recreating the bottleneck density plot
    valid_logistics = df[
        (df["seller_fulfillment_days"] >= 0) & (df["seller_fulfillment_days"] <= 30)
    ]
    fig_bottleneck = go.Figure()
    fig_bottleneck.add_trace(
        go.Violin(
            x=valid_logistics["seller_fulfillment_days"],
            name="Seller Fulfillment",
            line_color="#34495e",
            side="positive",
        )
    )
    fig_bottleneck.add_trace(
        go.Violin(
            x=valid_logistics["carrier_transit_days"],
            name="Carrier Transit",
            line_color="#3498db",
            side="positive",
        )
    )
    fig_bottleneck.update_layout(
        xaxis_title="Days",
        yaxis_title="",
        violingap=0,
        violinmode="overlay",
        margin=dict(l=0, r=0, t=30, b=0),
    )
    st.plotly_chart(fig_bottleneck, use_container_width=True)

st.markdown("---")

# 6. Bottom Row: Granular Data for Drill-Down
st.subheader("Actionable Seller Data (Fulfillment > 5 Days)")
# Filter for bad actors to give operations a target list
bad_sellers = (
    df[df["seller_fulfillment_days"] > 5][
        [
            "seller_id",
            "total_order_value",
            "seller_fulfillment_days",
            "is_late_delivery",
            "final_review_score",
        ]
    ]
    .sort_values(by="seller_fulfillment_days", ascending=False)
    .head(100)
)

st.dataframe(bad_sellers, use_container_width=True)
