"""Checkpoint save/load for pipeline resumability."""

from __future__ import annotations

import json
import os

from .models import PipelineState

CHECKPOINT_FILENAME = ".extractor-state.json"


def checkpoint_path(output_dir: str) -> str:
    """Return the full path to the checkpoint file."""
    return os.path.join(output_dir, CHECKPOINT_FILENAME)


def save_checkpoint(state: PipelineState, output_dir: str) -> None:
    """Atomically save pipeline state to checkpoint file.

    Writes to a .tmp file first, then renames — this prevents
    corruption if the process is killed mid-write.
    """
    os.makedirs(output_dir, exist_ok=True)
    path = checkpoint_path(output_dir)
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(state.to_dict(), f, indent=2)
    os.replace(tmp_path, path)


def load_checkpoint(output_dir: str) -> PipelineState | None:
    """Load pipeline state from checkpoint file, or None if not found."""
    path = checkpoint_path(output_dir)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return PipelineState.from_dict(data)


def clear_checkpoint(output_dir: str) -> None:
    """Remove the checkpoint file after successful completion."""
    path = checkpoint_path(output_dir)
    if os.path.exists(path):
        os.remove(path)
