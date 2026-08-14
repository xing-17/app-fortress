# from bastion.component import Component


from bastion.control.asset.local.local import LocalAsset
from bastion.infra.store.memory.memory import MemoryStore

store = MemoryStore(name="test-memory-store")

print(store.describe())

test_asset = LocalAsset(
    name="test-local-asset",
    kind="parquet",
    path="./test-local-asset",
)
print(test_asset.get_location_uri())
print(test_asset.export())
