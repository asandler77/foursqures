from __future__ import annotations

import csv
from pathlib import Path

from .ai_player import AIPlayer, FEATURE_COLUMNS


def _split_training_files(data_dir: Path) -> tuple[list[Path], list[Path]]:
    required = set(FEATURE_COLUMNS + ["action_id"])
    valid: list[Path] = []
    invalid: list[Path] = []
    for path in sorted(data_dir.glob("*.csv")):
        with path.open("r", newline="") as handle:
            reader = csv.DictReader(handle)
            fields = set(reader.fieldnames or [])
            if required.issubset(fields):
                valid.append(path)
            else:
                invalid.append(path)
    return valid, invalid


def train_from_folder(data_dir: Path) -> None:
    if not data_dir.exists():
        raise FileNotFoundError(f"Training folder not found: {data_dir}")

    valid, invalid = _split_training_files(data_dir)
    print(f"Found {len(valid) + len(invalid)} csv files")
    print(f"Valid: {len(valid)} | Invalid: {len(invalid)}")
    if invalid:
        print("Skipping invalid files (missing required columns):")
        for path in invalid[:10]:
            print(f"- {path}")
        if len(invalid) > 10:
            print("...")
    if not valid:
        raise ValueError("No valid training files found")

    ai = AIPlayer.default()
    for path in valid:
        ai.train_from_csv(path)
    print(f"Training complete; model saved to {ai.model_path}")


def main() -> None:
    import sys

    if len(sys.argv) != 2:
        print("Usage: python -m app.train_model <train_files_folder>")
        sys.exit(2)
    train_from_folder(Path(sys.argv[1]))


if __name__ == "__main__":
    main()
