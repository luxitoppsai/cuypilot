"""Shared pytest fixtures for PySpark unit tests (copied from the cuypilot pyspark-testing skill)."""

import pytest
from pyspark.sql import SparkSession


@pytest.fixture(scope="session")
def spark():
    """One small local SparkSession for the whole test run.

    :returns: A local SparkSession tuned for fast, deterministic tests.
    """
    session = (
        SparkSession.builder.master("local[1]")
        .appName("unit-tests")
        .config("spark.sql.shuffle.partitions", "1")
        .config("spark.default.parallelism", "1")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.session.timeZone", "UTC")
        .getOrCreate()
    )
    yield session
    session.stop()
