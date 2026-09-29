# Olist E-Commerce Logistics Analysis

[![Live Dashboard](https://img.shields.io/badge/Live_App-Streamlit-FF4B4B?logo=streamlit)](https://olist-ops-pipeline.streamlit.app/)
[![Python 3.10](https://img.shields.io/badge/Python-3.10-3776AB?logo=python)]()
[![DuckDB](https://img.shields.io/badge/SQL-DuckDB-FFF000?logo=duckdb)]()
[![Polars](https://img.shields.io/badge/Data-Polars-CD792C?logo=polars)]()
[![CI/CD](https://img.shields.io/badge/Tests-Pytest-0A9EDC?logo=pytest)]()

## Summary
This project analyzes 100,000+ orders from the Olist Brazilian E-Commerce database to identify the root causes of logistical bottlenecks and their direct impact on *customer satisfaction* (CSAT) and revenue. By engineering an end-to-end ELT pipeline, this repository transforms a highly normalized, 9-table relational database into a high-performance analytical base table, surfacing insights through a live interactive dashboard.

---

## Business Hypotheses & Statistical Proof

Rather than exploratory charting, this analysis was driven by strict hypothesis testing to separate causation from correlation.

### 1. The Reputational Cost of Delay
*   **Hypothesis:** Orders missing their estimated delivery date result in a disproportionate and statistically significant drop in CSAT, actively damaging brand equity.
*   **Methodology (Mann-Whitney U Test):** Because 1-5 star review distributions are ordinal and highly skewed, a standard T-test is mathematically inappropriate. A Mann-Whitney U test was applied to compare the distributions of on-time vs. late delivery review scores.
*   **The Proof:** The test yielded a p-value of `< 0.001`, definitively proving that late deliveries cause average CSAT to plummet from 4.2 to 2.3. The visual density distributions confirmed a massive corresponding spike specifically in 1-star reviews, representing severe churn risk.

### 2. Isolating the Operational Bottleneck
*   **Hypothesis:** The primary bottleneck in the delivery pipeline is carrier transit time (the logistics network) rather than seller fulfillment time (the time taken to pack and dispatch).
*   **Methodology (Distributional Density Analysis):** Analyzed the delta in days between `order_approved_at` → `order_delivered_carrier_date` (Seller Time) against `order_delivered_carrier_date` → `order_delivered_customer_date` (Carrier Time). 
*   **The Proof:** The hypothesis was **disproved**. Overlaid violin plots and KDE (Kernel Density Estimation) revealed a severe long-tail distribution in *Seller Fulfillment Time*. While carriers operated within predictable standard deviations, a statistically significant cluster of third-party sellers routinely took 5 to 10+ days simply to hand the package to the carrier. 

**Core Business Recommendation:** Implement a strict 48-hour SLA for seller dispatch, algorithmic penalization for recurring bad actors, and highlight "Revenue at Risk" to incentivize compliance.

---

## Architecture & Technical Decisions

To demonstrate production-grade data engineering, this project skips standard "in-memory Pandas over CSVs" in favor of a robust, scalable architecture.

*   **In-Memory SQL over Pandas (DuckDB):** 
    Joining 9 distinct tables (Orders, Customers, Reviews, Products, Payments, etc.) containing over 100k rows each via Pandas `merge()` is memory-inefficient and prone to Cartesian explosions. DuckDB was utilized to execute complex SQL aggregations directly on the raw CSVs, treating the local directory as a relational database.
*   **Grain Management & Deduplication:** 
    A common pitfall in multi-item order datasets is duplicate revenue counting. The ETL pipeline intentionally isolates financial aggregations (`SUM(price)`) into a CTE grouped strictly by `order_id` before joining to the main orders table, utilizing `MIN(seller_id)` to force a 1:1 relationship and preserve the integrity of the total order financials.
*   **High-Performance Processing (Polars):** 
    The output of the DuckDB SQL execution is seamlessly handed off to Polars rather than Pandas. Polars' multithreaded, Rust-backed engine processes the final feature engineering (e.g., date-diff calculations for logistics KPIs) instantly.
*   **Columnar Storage (Parquet):** 
    The final Analytical Base Table (ABT) is written to `.parquet` format rather than `.csv`. This enforces strict data typing (preserving timestamps and integers natively) and compresses the file size by roughly 75% for rapid dashboard rendering.
*   **Automated Quality Assurance (Pytest & CI/CD):** 
    "Silent failures" destroy dashboard credibility. A `pytest` suite runs automatically via GitHub Actions on every push, asserting that revenue is never negative, primary keys (`order_id`) remain 100% unique, and dates do not violate chronological physics (e.g., delivery preceding purchase).

---

## Data Limitations & Caveats
*   **Review Survivorship Bias:** Customers who experience extreme emotions (very happy or very angry) are more likely to leave reviews. The CSAT data may slightly under represent the "indifferent" middle-tier of on-time deliveries.
*   **Geographic Routing:** While zip code prefixes are available, exact GPS routing logistics (e.g., weather delays, traffic incidents) are absent, meaning carrier transit delays cannot be fully diagnosed down to the specific environmental cause.

---

## Quick Start (Reproducing the Environment)

```bash
# 1. Clone the repository
git clone https://github.com/Gary-XC/olist-ops-pipeline.git
cd olist-ops-pipeline

# 2. Create virtual environment and install dependencies
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Run the ETL Pipeline (Generates the Parquet file)
python scripts/etl_pipeline.py

# 4. Run Data Quality Tests
pytest scripts/test_pipeline.py

# 5. Launch the Dashboard locally
streamlit run dashboard/app.py
```