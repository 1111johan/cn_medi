from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = ROOT_DIR / "cloudbase" / "functions" / "tcm-api-template"
BUILD_DIR = ROOT_DIR / "cloudbase" / "functions" / "tcm-api-build"

DATA_FILES = [
    "knowledge_objects.json",
    "feedback_records.json",
    "review_tasks.json",
    "audit_records.jsonl",
    "professional_knowledge.db",
]


def reset_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def copy_required_files() -> None:
    shutil.copytree(ROOT_DIR / "app", BUILD_DIR / "app", dirs_exist_ok=True)

    seed_dir = BUILD_DIR / "seed_data"
    seed_dir.mkdir(parents=True, exist_ok=True)
    for filename in DATA_FILES:
        source = ROOT_DIR / "data" / filename
        if source.exists():
            shutil.copy2(source, seed_dir / filename)

    shutil.copy2(ROOT_DIR / "requirements.txt", BUILD_DIR / "requirements.txt")
    shutil.copy2(TEMPLATE_DIR / "app.py", BUILD_DIR / "app.py")
    shutil.copy2(TEMPLATE_DIR / "scf_bootstrap", BUILD_DIR / "scf_bootstrap")


def install_dependencies() -> None:
    third_party_dir = BUILD_DIR / "third_party"
    third_party_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "python3",
            "-m",
            "pip",
            "install",
            "-r",
            str(BUILD_DIR / "requirements.txt"),
            "-t",
            str(third_party_dir),
            "--upgrade",
            "--no-cache-dir",
        ],
        check=True,
    )


def make_bootstrap_executable() -> None:
    (BUILD_DIR / "scf_bootstrap").chmod(0o755)


def main() -> None:
    reset_dir(BUILD_DIR)
    copy_required_files()
    install_dependencies()
    make_bootstrap_executable()
    print(f"cloudbase http function prepared at {BUILD_DIR}")


if __name__ == "__main__":
    main()
