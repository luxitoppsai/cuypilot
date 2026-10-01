import json


def lint(run_script, path):
    return json.loads(run_script("pyspark-optimize", "spark_lint.py", str(path), "--json"))


def codes(findings):
    return sorted(f["code"] for f in findings)


BAD = """
from pyspark.sql import functions as F
from pyspark.sql.functions import udf

@udf("string")
def upper(s):
    return s.upper()

@udf
def lower(s):
    return s.lower()

clean = F.udf(lambda s: s.strip())
spark.udf.register("twice", lambda x: x * 2)

def run(spark, df, cols, name):
    rows = df.collect()
    for c in cols:
        df = df.withColumn(c, F.lit(1))
        print(df.count())
    pairs = df.rdd.map(lambda r: r)
    df.repartition(1).write.parquet("/x")
    df.cache()
    big = df.crossJoin(df)
    spark.sql(f"SELECT * FROM t WHERE name = '{name}'")
    df.show()
    spark.read.csv("/f.csv", header=True, inferSchema=True)
    for row in df.collect():
        pass
"""

GOOD = """
from pyspark.sql import functions as F
from pyspark.sql.functions import pandas_udf

@pandas_udf("string")
def upper(s):
    return s.str.upper()

def run(spark, df, cols, name, schema):
    total = df.groupBy("k").agg(F.count("*")).collect()
    df = df.withColumns({c: F.lit(1) for c in cols})
    df.coalesce(8).write.parquet("/x")
    df.cache()
    df.unpersist()
    spark.sql("SELECT * FROM t WHERE name = :name", args={"name": name})
    spark.read.schema(schema).csv("/f.csv", header=True)
    names = [c.upper() for c in cols]
    for c in names:
        print(c.count("a"))
"""


def test_detects_every_rule(write, run_script, tmp_path):
    write("bad.py", BAD)
    found = codes(lint(run_script, tmp_path))
    for code in [f"SP{i:03d}" for i in range(1, 13) if i != 2]:
        assert code in found, code
    assert found.count("SP001") == 4  # @udf(...), @udf, F.udf, spark.udf.register
    assert "SP002" in found  # rows = df.collect()


def test_correct_equivalent_code_is_clean(write, run_script, tmp_path):
    write("good.py", GOOD)
    findings = lint(run_script, tmp_path)
    # Solo queda el collect() de un resultado agregado, con severidad baja.
    assert [(f["code"], f["severity"]) for f in findings] == [("SP002", "LOW")]


def test_display_is_fine_in_databricks_notebooks(write, run_script, tmp_path):
    write("nb.py", "# Databricks notebook source\ndisplay(df)\ndf.show()\n")
    assert lint(run_script, tmp_path) == []


def test_ipynb_reports_cell_and_line(write, run_script, tmp_path):
    nb = {
        "cells": [
            {"cell_type": "markdown", "source": ["# Title"]},
            {"cell_type": "code", "source": ["%sql\n", "SELECT 1"]},
            {"cell_type": "code", "source": ["%pip install x\n", "rows = df.toPandas()\n"]},
        ]
    }
    write("analysis.ipynb", json.dumps(nb))
    findings = lint(run_script, tmp_path)
    assert [(f["code"], f["location"].split(":", 1)[1]) for f in findings] == [("SP002", "cell3:2")]


def test_text_output(write, run_script, tmp_path):
    write("m.py", "df.rdd.count()\n")
    out = run_script("pyspark-optimize", "spark_lint.py", str(tmp_path))
    assert "SP005" in out and "1 finding(s) in 1 file(s)." in out
