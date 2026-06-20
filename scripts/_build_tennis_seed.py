#!/usr/bin/env python3
"""One-shot: snapshot the offline Sackmann tennis history into data_sources/tennis_seed/.

Traces a full local build and records every cache key fetched with a long TTL
(>=168h) — i.e. the historical match/metadata/ranking CSVs, never the short-TTL
ESPN live feeds. Those cache files are gzipped into the committed seed dir so
cloud CI can rebuild the tennis tracker without the dead upstream source.
"""
import gzip
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import update_tennis_data as u  # noqa: E402

seeded: dict[str, str] = {}
_orig = u._cache_fetch


def _traced(url: str, ttl_hours: float = 720.0) -> str:
    if ttl_hours >= 168.0:
        seeded[hashlib.md5(url.encode()).hexdigest()] = url
    return _orig(url, ttl_hours)


u._cache_fetch = _traced
print("Running a full build to discover historical fetches…", file=sys.stderr)
u.write_data()

SEED = ROOT / "data_sources" / "tennis_seed"
SEED.mkdir(parents=True, exist_ok=True)

written = 0
total = 0
missing = []
for key, url in sorted(seeded.items()):
    src = u.CACHE / key
    if not src.exists():
        missing.append(url)
        continue
    data = src.read_bytes()
    (SEED / f"{key}.gz").write_bytes(gzip.compress(data, 9))
    written += 1
    total += (SEED / f"{key}.gz").stat().st_size

print(f"Seeded {written} files ({total/1e6:.1f} MB gzipped) into {SEED}")
if missing:
    print(f"  WARNING: {len(missing)} historical URLs had no local cache:", file=sys.stderr)
    for m in missing[:10]:
        print("   -", m, file=sys.stderr)
