import polars as pl
import pytest
import os


# Load the data once for all tests
@pytest.fixture(scope="module")
def abt_data():
    file_path = "data/processed/analytical_base_table.parquet"
    assert os.path.exists(file_path), "ABT Parquet file is missing. Run ETL first."
    return pl.read_parquet(file_path)


def test_no_duplicate_orders(abt_data):
    """Business Logic: One order ID should equal one row in our aggregated table."""
    assert (
        abt_data["order_id"].is_unique().all()
    ), "Critical Error: Duplicate Order IDs found."


def test_financial_integrity(abt_data):
    """Business Logic: Revenue and freight cannot be negative."""
    assert (
        abt_data["total_order_value"].min() >= 0
    ), "Error: Negative total order value."
    assert abt_data["total_freight_value"].min() >= 0, "Error: Negative freight value."


def test_review_score_bounds(abt_data):
    """Business Logic: Reviews must be between 1 and 5, or null."""
    valid_scores = abt_data.filter(abt_data["final_review_score"].is_not_null())
    assert valid_scores["final_review_score"].min() >= 1
    assert valid_scores["final_review_score"].max() <= 5


def test_chronological_integrity(abt_data):
    """Business Logic: An order cannot be delivered before it is purchased."""
    invalid_chronology = abt_data.filter(
        abt_data["actual_delivery_date"] < abt_data["purchase_timestamp"]
    )
    assert (
        invalid_chronology.height == 0
    ), f"Found {invalid_chronology.height} records defying time."
