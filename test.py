from app.resource._global.sources import GlobalSources

_abs_source = GlobalSources.get_source(
    name="snt_local_abs",
)
_dataset_names = [
    "population_estimates_sa2_year",
    "migration_regional_recent_year",
    "migration_regional_archived_year",
]
for _name in _dataset_names:
    _dataset = _abs_source.dataset(_name)
    _dataset.run()
    print(f"Ran dataset: {_name}")

# _rba_source = GlobalSources.get_source(
#     name="snt_local_rba",
# )
# for _name in _rba_source.list_dataset_names():
#     _dataset = _rba_source.dataset(_name)
#     _dataset.run()
#     print(f"Ran dataset: {_name}")

# for _name in _abs_source.list_dataset_names():
#     _dataset = _abs_source.dataset(_name)
#     _dataset.run()
#     print(f"Ran dataset: {_name}")

# _rba_source = GlobalSources.get_source(
#     name="snt_local_nswvg",
# )
# for _dataset in _rba_source.list_datasets():
#     _dataset.run()
#     print(f"Ran dataset: {_dataset.name}")
