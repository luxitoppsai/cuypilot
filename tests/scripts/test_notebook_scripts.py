"""notebook_outline.py (notebook-to-module) y data_flow.py (functional-docs)."""

import ast
import json

from cuypilot.catalog import CATALOG_DIR

DATABRICKS_NB = """# Databricks notebook source
# MAGIC %md
# MAGIC # Ventas diarias

# COMMAND ----------

dbutils.widgets.text("fecha", "")
fecha = dbutils.widgets.get("fecha")
ventas = spark.table("prod.ventas.transacciones")

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT * FROM prod.ventas.clientes c JOIN prod.ventas.zonas z ON c.zona = z.id

# COMMAND ----------

def neto(df):
    \"\"\"Calcula el monto neto.\"\"\"
    return df.withColumn("monto_neto", df.monto / 1.18)

resultado = neto(ventas).filter(ventas.fecha == fecha)
display(resultado)
resultado.write.mode("overwrite").saveAsTable("prod.ventas.resumen_diario")

# COMMAND ----------

# MAGIC %run ./utils
"""


def test_outline_databricks_notebook(write, run_script, tmp_path):
    nb = write("ventas.py", DATABRICKS_NB)
    cells = json.loads(run_script("notebook-to-module", "notebook_outline.py", str(nb), "--json"))

    assert [c["kind"] for c in cells] == ["md", "python", "sql", "python", "run"]
    assert cells[0]["title"] == "Ventas diarias"
    assert cells[1]["widgets"] == ["fecha"] and cells[1]["reads"] == ["prod.ventas.transacciones"]
    assert cells[2]["reads"] == ["prod.ventas.clientes", "prod.ventas.zonas"]
    assert cells[3]["defines"] == ["neto"]
    assert cells[3]["writes"] == ["prod.ventas.resumen_diario"]
    assert cells[3]["display"] == 1
    assert cells[3]["uses_from_earlier_cells"] == ["fecha (cell 2)", "ventas (cell 2)"]
    assert cells[4]["command"] == "./utils"


def test_outline_ipynb_with_magics(write, run_script, tmp_path):
    nb = {
        "cells": [
            {"cell_type": "markdown", "source": ["## Exploración"]},
            {"cell_type": "code", "source": ["%pip install x\n", "df = spark.read.parquet('/mnt/raw/x')\n"]},
            {"cell_type": "code", "source": ["%sql\n", "INSERT INTO prod.a SELECT * FROM prod.b"]},
            {"cell_type": "code", "source": ["df.toPandas()"]},
        ]
    }
    path = write("exp.ipynb", json.dumps(nb))
    out = run_script("notebook-to-module", "notebook_outline.py", str(path))
    assert "cell   2 [python] reads: /mnt/raw/x" in out
    assert "cell   3 [sql] reads: prod.b; writes: prod.a" in out
    assert "cell   4 [python] uses from earlier cells: df (cell 2)" in out


def test_data_flow_of_module_and_notebook(write, run_script, tmp_path):
    write(
        "pipeline/job.py",
        '''
        import argparse
        from pyspark.sql import functions as F

        def run(spark, catalog):
            """Construye la tabla de clientes activos."""
            raw = spark.read.format("delta").load("/mnt/bronze/clientes")
            zonas = spark.sql("SELECT id, nombre FROM prod.ref.zonas")
            out = (raw.withColumn("activo", F.col("estado") == "A")
                      .withColumnRenamed("cod", "codigo_cliente")
                      .withColumns({"anio": F.year("fecha"), "mes": F.month("fecha")}))
            out.write.saveAsTable(f"{catalog}.gold.clientes_activos")

        def main():
            parser = argparse.ArgumentParser()
            parser.add_argument("--catalog")
        ''',
    )
    write("pipeline/ventas.py", DATABRICKS_NB)
    flows = json.loads(run_script("functional-docs", "data_flow.py", str(tmp_path / "pipeline"), "--json"))
    job, nb = flows

    assert job["reads"] == ["/mnt/bronze/clientes", "prod.ref.zonas"]
    assert job["writes"] == ["<f'{catalog}.gold.clientes_activos'>"]
    assert job["params"] == ["arg:--catalog"]
    assert job["steps"][0] == "run() - Construye la tabla de clientes activos."
    assert job["new_columns"] == ["activo", "cod -> codigo_cliente", "anio", "mes"]
    assert nb["reads"] == ["prod.ventas.transacciones", "prod.ventas.clientes", "prod.ventas.zonas"]
    assert nb["writes"] == ["prod.ventas.resumen_diario"] and nb["runs"] == ["./utils"]
    assert nb["params"] == ["widget:fecha"]


def _shared_functions(path):
    tree = ast.parse(path.read_text())
    names = {"split_cells", "literal", "tables_in_sql", "chain", "calls_in_order", "io_calls"}
    found = {n.name: ast.dump(n) for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names}
    consts = {
        t.id: ast.dump(n.value)
        for n in tree.body
        if isinstance(n, ast.Assign)
        for t in n.targets
        if isinstance(t, ast.Name)
        and t.id in {"MAGIC_KINDS", "READ_SOURCES", "WRITE_TARGETS", "SQL_READ", "SQL_WRITE"}
    }
    assert len(found) == len(names) and len(consts) == 5
    return found, consts


def test_shared_helpers_stay_identical():
    a = _shared_functions(CATALOG_DIR / "skills/functional-docs/scripts/data_flow.py")
    b = _shared_functions(CATALOG_DIR / "skills/notebook-to-module/scripts/notebook_outline.py")
    assert a == b, "las funciones compartidas difieren: copia el bloque 'shared helpers' entre ambos scripts"


def test_reassigned_variable_still_counts_as_input_and_imports_do_not(write, run_script, tmp_path):
    nb = write(
        "nb.py",
        "# Databricks notebook source\nfrom pyspark.sql import functions as F\nventas = spark.table('t')\n"
        "\n# COMMAND ----------\n\nventas = ventas.withColumn('x', F.lit(1))\ntotal = 1\nprint(total)\n",
    )
    cells = json.loads(run_script("notebook-to-module", "notebook_outline.py", str(nb), "--json"))
    assert cells[1]["uses_from_earlier_cells"] == ["ventas (cell 1)"]
