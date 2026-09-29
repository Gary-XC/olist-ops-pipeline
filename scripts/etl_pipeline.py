import duckdb
import polars as pl
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")


def build_analytical_base_table():
    logging.info("Starting ETL Pipeline: Connecting to DuckDB...")
    conn = duckdb.connect(database=":memory:")

    # Aggregate at the order_id level. instead of focusing on individual line items
    # instead focusing about the total order value, whether the entire
    # order was late, and what the customer's final review score was.

    sql_query = """
    WITH order_financials AS (
        SELECT 
            order_id,
            MIN(seller_id) as seller_id,
            SUM(price) as total_products_value,
            SUM(freight_value) as total_freight_value,
            SUM(price + freight_value) as total_order_value
        FROM 'data/raw/olist_order_items_dataset.csv'
        GROUP BY order_id
    ),
    order_reviews AS (
        -- Taking the minimum review score in case of multiple reviews for a single order
        SELECT 
            order_id,
            MIN(review_score) as final_review_score
        FROM 'data/raw/olist_order_reviews_dataset.csv'
        GROUP BY order_id
    )
    
    SELECT 
        o.order_id,
        o.customer_id,
        f.seller_id,
        o.order_status,
        
        -- Temporal Features
        CAST(o.order_purchase_timestamp AS TIMESTAMP) AS purchase_timestamp,
        CAST(o.order_approved_at AS TIMESTAMP) AS approved_at,
        CAST(o.order_delivered_carrier_date AS TIMESTAMP) AS carrier_dispatch_date,
        CAST(o.order_delivered_customer_date AS TIMESTAMP) AS actual_delivery_date,
        CAST(o.order_estimated_delivery_date AS TIMESTAMP) AS estimated_delivery_date,
        
        -- Custom KPIs (Hypothesis Testing Prep)
        f.total_products_value,
        f.total_freight_value,
        f.total_order_value,
        ROUND((f.total_freight_value / NULLIF(f.total_order_value, 0)) * 100, 2) AS freight_ratio_pct,
        
        -- Bottleneck Calculations (in days)
        DATE_DIFF('day', CAST(o.order_approved_at AS TIMESTAMP), CAST(o.order_delivered_carrier_date AS TIMESTAMP)) AS seller_fulfillment_days,
        DATE_DIFF('day', CAST(o.order_delivered_carrier_date AS TIMESTAMP), CAST(o.order_delivered_customer_date AS TIMESTAMP)) AS carrier_transit_days,
        DATE_DIFF('day', CAST(o.order_estimated_delivery_date AS TIMESTAMP), CAST(o.order_delivered_customer_date AS TIMESTAMP)) AS delivery_delay_days,
        
        CASE WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date THEN 1 ELSE 0 END AS is_late_delivery,
        
        r.final_review_score
        
    FROM 'data/raw/olist_orders_dataset.csv' o
    JOIN order_financials f ON o.order_id = f.order_id
    LEFT JOIN order_reviews r ON o.order_id = r.order_id
    
    -- Business Logic: We only want to analyze completed logistics lifecycles
    WHERE o.order_status = 'delivered' 
      AND o.order_delivered_customer_date IS NOT NULL
    """

    logging.info("Executing complex SQL joins and metric aggregations...")
    # DuckDB seamlessly translates the query result into a high-performance Polars DataFrame
    df = conn.execute(sql_query).pl()

    logging.info(f"Pipeline processed {df.height} rows and {df.width} columns.")

    # Save as Parquet to retain data types (timestamps, integers) and compress file size
    output_path = "data/processed/analytical_base_table.parquet"
    df.write_parquet(output_path)
    logging.info(f"Analytical Base Table saved successfully to {output_path}")


if __name__ == "__main__":
    build_analytical_base_table()
