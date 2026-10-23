from __future__ import annotations

_INSTRUCTIONS = """\
Read-only access to the data assets of a Fortress node.

Datasets are named "<source>.<dataset>" and are tables in SQL under that exact name.
Typical flow: list_datasets -> get_schema -> query. Use get_quality to check completeness before
trusting a dataset.
"""

_LIST_DATASETS_DOC = """\
List the datasets the node holds, with description, update frequency and partition keys.

Dataset names look like "<source>.<dataset>" and can be used as is in `query` and `get_schema`.
Pass `source` to list only one source.
"""

_GET_SCHEMA_DOC = """\
Show the columns and types of a dataset, and which partitions exist.

`dataset` is "<source>.<dataset>". The partition keys are also columns in SQL and are always
VARCHAR: CAST them when you need numbers or dates, e.g. CAST(date AS DATE).
The schema may differ between partitions: each entry of `definitions` is one schema with the
number of partitions that carry it and the range (min, max as strings) of each partition key.
Columns missing in a partition read as NULL in `query`.
"""

_GET_QUALITY_DOC = """\
Show data quality of a dataset per partition file: row count, rows without NULL, duplicate rows,
and the columns that contain NULLs or hold a single value.

`dataset` is "<source>.<dataset>". Only the `limit` most recently modified files are returned.
A file with `"checked": false` has no quality record.
"""

_QUERY_DOC = """\
Run ONE read-only SQL SELECT (DuckDB dialect) over the datasets and return the rows.

Use dataset names as "<source>.<dataset>", e.g. SELECT count(*) FROM tushare.tradedates.
Partition keys are VARCHAR columns, CAST them when needed. Only a single SELECT or WITH statement
is allowed: no multiple statements, no writes, no SET, ATTACH or file functions.
Results are NOT saved, keep what you need from the answer. The result is capped in rows and size:
when `truncated` is true the rows are incomplete, aggregate or filter in SQL instead of
reading everything. The query is interrupted when it runs too long.
"""
