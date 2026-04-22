from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
THIRD_PARTY = BASE_DIR / "third_party"

if THIRD_PARTY.exists():
    sys.path.insert(0, str(THIRD_PARTY))
sys.path.insert(0, str(BASE_DIR))


def prepare_runtime_data() -> None:
    seed_data_dir = BASE_DIR / "seed_data"
    runtime_data_dir = Path(os.getenv("TCM_DATA_DIR", "/tmp/tcm-data")).resolve()
    runtime_data_dir.mkdir(parents=True, exist_ok=True)

    if seed_data_dir.exists():
        for item in seed_data_dir.iterdir():
            target = runtime_data_dir / item.name
            if target.exists():
                continue
            if item.is_dir():
                shutil.copytree(item, target)
            else:
                shutil.copy2(item, target)

    os.environ.setdefault("TCM_DATA_DIR", str(runtime_data_dir))
    os.environ.setdefault("TCM_PRO_DB_PATH", str(runtime_data_dir / "professional_knowledge.db"))
    os.environ.setdefault("TCM_PRO_DATA_DIR", str(BASE_DIR / "_professional_source"))


prepare_runtime_data()

from app.main import app  # noqa: E402
import uvicorn  # noqa: E402


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9000)
