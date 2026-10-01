"""Example of PySpark unit tests (copied from the cuypilot pyspark-testing skill)."""

import pytest
from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.testing import assertDataFrameEqual


def add_net_amount(df: DataFrame, tax_rate: float) -> DataFrame:
    """Example transformation under test: adds ``net_amount`` = ``amount`` without tax.

    :param df: Input with column ``amount``.
    :param tax_rate: Tax rate as a fraction (e.g. ``0.18``).
    :returns: The input plus ``net_amount`` (null when ``amount`` is null).
    """
    return df.withColumn("net_amount", F.round(F.col("amount") / (1 + tax_rate), 2))


SCHEMA_IN = "id INT, amount DOUBLE"
SCHEMA_OUT = "id INT, amount DOUBLE, net_amount DOUBLE"


def test_net_amount_removes_tax(spark):
    df = spark.createDataFrame([(1, 118.0), (2, 0.0)], SCHEMA_IN)
    expected = spark.createDataFrame([(1, 118.0, 100.0), (2, 0.0, 0.0)], SCHEMA_OUT)
    assertDataFrameEqual(add_net_amount(df, 0.18), expected)


def test_null_amount_stays_null(spark):
    df = spark.createDataFrame([(1, None)], SCHEMA_IN)
    expected = spark.createDataFrame([(1, None, None)], SCHEMA_OUT)
    assertDataFrameEqual(add_net_amount(df, 0.18), expected)


def test_empty_input_returns_empty_output(spark):
    df = spark.createDataFrame([], SCHEMA_IN)
    assert add_net_amount(df, 0.18).isEmpty()


@pytest.mark.parametrize(("amount", "net"), [(1.18, 1.0), (-118.0, -100.0)])
def test_rounding_and_refunds(spark, amount, net):
    df = spark.createDataFrame([(1, amount)], SCHEMA_IN)
    assert add_net_amount(df, 0.18).first()["net_amount"] == net
