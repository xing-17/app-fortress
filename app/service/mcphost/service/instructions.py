from __future__ import annotations

_INSTRUCTIONS = """\
Read-only access to the data assets of one or more Fortress nodes.

Datasets are named "<source>.<dataset>" and are tables in SQL under that exact name.
Typical flow: list_datasets -> get_schema -> query. Use get_quality to check completeness before
trusting a dataset. Use list_runs to see whether the last runs of a dataset completed or failed,
and get_dataset_run to read one of them by id.
Use list_nodes to see which nodes exist and which of them are reachable.
Use list_machine_snapshots to see how loaded the machine of a node was (cpu, memory, disk, network).
A query runs on ONE node and can not join datasets of different nodes: pass `node` to `query`
when several nodes are served.
"""

_LIST_NODES_DOC = """\
List every node this host serves, with whether it is reachable and the sources it holds.

A node with `"reachable": false` is down or too slow and carries an `error`; its data is
missing from the other tools until it is back.
"""

_LIST_DATASETS_DOC = """\
List the datasets of all nodes, with description, update frequency and partition keys.

Every dataset carries the `node` that holds it. Dataset names look like "<source>.<dataset>" and
can be used as is in `query` and `get_schema`. `nodes` tells, for each node, whether it answered:
the datasets of a node with `"reachable": false` are missing from the list.
Pass `source` to list only one source, `node` to ask only one node.
"""

_GET_SCHEMA_DOC = """\
Show the columns and types of a dataset, and which partitions exist.

`dataset` is "<source>.<dataset>". The node that holds it is found automatically; pass `node` only
when the same dataset exists on several nodes. The partition keys are also columns in SQL and are
always VARCHAR: CAST them when you need numbers or dates, e.g. CAST(date AS DATE).
The schema may differ between partitions: each entry of `definitions` is one schema with the
number of partitions that carry it and the range (min, max as strings) of each partition key.
Columns missing in a partition read as NULL in `query`.
"""

_GET_QUALITY_DOC = """\
Show data quality of a dataset per partition file: row count, rows without NULL, duplicate rows,
and the columns that contain NULLs or hold a single value.

`dataset` is "<source>.<dataset>". The node that holds it is found automatically; pass `node` only
when the same dataset exists on several nodes. Only the `limit` most recently modified files are
returned. A file with `"checked": false` has no quality record.
"""

_LIST_RUNS_DOC = """\
Show the run records of a dataset, newest first: when each run started and finished, how long it
took, its status (started, completed, failed), the parameters it was called with, the rows and
columns it wrote and, for a failed run, the error.

`dataset` is "<source>.<dataset>". The node that holds it is found automatically; pass `node` only
when the same dataset exists on several nodes. Pass `status` to keep only one status, `limit` to
cap the number of runs (default 20, at most 100). A run that stays `started` for long may have
died without recording its end. The node keeps only its latest runs per dataset.
"""

_GET_RUN_DOC = """\
Show one run record of a dataset by `id` (from `list_runs`): status
(started, completed, failed), start and finish time, duration, parameters, rows and columns
written and, for a failed run, the error.

`dataset` is "<source>.<dataset>". The node that holds it is found automatically; pass `node` only
when the same dataset exists on several nodes. A run that stays `started` for long may have died
without recording its end.
"""

_QUERY_DOC = """\
Run ONE read-only SQL SELECT (DuckDB dialect) over the datasets of one node and return the rows.

Use dataset names as "<source>.<dataset>", e.g. SELECT count(*) FROM tushare.tradedates.
The query runs on a single node and sees only that node's datasets: when several nodes are served
pass `node` (see `list_datasets`), to combine data of two nodes query each and merge the answers
yourself. Partition keys are VARCHAR columns, CAST them when needed. Only a single SELECT or WITH
statement is allowed: no multiple statements, no writes, no SET, ATTACH or file functions.
Results are NOT saved, keep what you need from the answer. The result is capped in rows and size:
when `truncated` is true the rows are incomplete, aggregate or filter in SQL instead of
reading everything. The query is interrupted when it runs too long.
"""

_LIST_MACHINE_SNAPSHOTS_DOC = """\
Show how the machine of each node was doing over time: one snapshot per minute (oldest first) with
cpu, memory, swap and disk usage, the memory, cpu and thread count of the node process, and the
network totals.

Without `hours` every snapshot the node keeps is returned (12 hours by default), pass `hours` to
get only the last few. Each snapshot has a `timestamp` in epoch seconds. `net_sent_mb` and
`net_recv_mb` are totals since boot: take the difference of two snapshots to get the traffic.
`proc_*` and `net_*` are null when they could not be read. A node restart empties its history.
The answer holds one entry per node with `"reachable"`; a node that is down carries an `error`.
Pass `node` to ask only one node.
"""
