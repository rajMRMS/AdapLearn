# DTransformer — Technical Documentation

Last updated: 2025-09-30

This document describes the DTransformer project (code, data, training/evaluation, and operational notes). It is intended for engineers who want to run, modify, or extend the codebase.

## 1. Project summary

DTransformer is a knowledge tracing / student modeling codebase. It includes:
- A Transformer-based model implementation (`DTransformer`) and several baseline models in `baselines/` (AKT, DKT, DKVMN).
- Data loaders and evaluation utilities in `DTransformer/`.
- CLI scripts for training and evaluation in `scripts/`.
- A small Flask app for live test-taking in `live_test/` (scaffolding and utility scripts).

The codebase supports CPU runs and (where available) CUDA GPU runs. Checkpointing saves both model and optimizer state so training can be resumed cleanly.

## 2. Repository layout (important files)

- `pyproject.toml` — project metadata and dependencies.
- `DTransformer/` — core package
  - `data.py` — dataset readers, `KTData` and `Lines` helpers.
  - `model.py` — DTransformer model implementation.
  - `eval.py` — evaluation helpers and metrics.
  - `config.py` — configuration defaults.
  - `visualize.py`, `tests/` — visualization and unit tests.
- `baselines/` — DKT, DKVMN, AKT baseline models.
- `data/` — dataset files and `datasets.toml` manifest.
- `scripts/` — command-line entry points:
  - `train.py` — training pipeline (checkpointing, resume support, CLI args).
  - `test.py` — evaluation script.
  - `train/*.py` utilities created during the session (stats helpers).
- `live_test/` — Flask app for live question serving (templates, DB init, API).
- `output/` — recommended location for logs, checkpoints, and config snapshots.

## 3. Environment & dependencies

Recommended Python: 3.10+ (project used 3.12 in dev). Install via virtualenv or conda.
Dependencies include (from `pyproject.toml`):
- torch (CPU or CUDA build)
- tomlkit
- tqdm
- flask (for live_test)
- pytest, ruff (dev/test)

Install with pip (example):

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# or install the minimum listed in pyproject.toml
```

Note: if you want GPU support, install a PyTorch wheel matching your CUDA version (see pytorch.org). The training script falls back to CPU automatically if the requested device isn't available.

## 4. Data format and loader details

Data are stored in `data/<dataset>/train.txt` and `data/<dataset>/test.txt`. Each dataset file contains repeated blocks describing one student's trajectory. Each block uses `group = len(inputs) + 1` lines — the `KTData` constructor uses `Lines(..., group=...)` to partition the file.

Block format (for the default `assist09` where `inputs = ["pid","q","s"]`):
1. sequence length (an integer)
2. question ids (comma-separated integers)
3. skill/pid ids (comma-separated integers)
4. responses (comma-separated 0/1 integers)

The `DTransformer.data.KTData` class constructs batches of shape [batch, seq_len] and pads shorter sequences with -1.

Important: The `datasets.toml` manifest contains per-dataset metadata (train/test paths, n_questions, n_pid, inputs). For ASSIST09 the manifest entry is:

```toml
[assist09]
train = "assist09/train.txt"
test = "assist09/test.txt"
n_questions = 123
n_pid = 17751
inputs = ["pid", "q", "s"]
```

But the raw files may contain question IDs larger than `n_questions` (IDs are global/external IDs). When computing vocabulary sizes use the actual data if you need precise counts (scripts were added to compute dataset statistics).

## 5. Model overview

- `DTransformer` (in `DTransformer/model.py`) is a Transformer-based knowledge tracing model parameterized by `d_model`, `n_layers`, `n_heads`, `n_know` and other hyperparameters.
- Baselines are available in `baselines/`: `AKT.py`, `DKT.py`, `DKVMN.py` and can be selected via CLI.

Key model features:
- Optional contrastive learning loss (CL) controlled by `--cl_loss` and `--lambda` (~weight).
- Optional projection layer (`--proj`) and hard negative sampling (`--hard_neg`).

## 6. Training script (`scripts/train.py`) — usage and key points

Usage (example PowerShell):

```powershell
python scripts/train.py --dataset assist09 --model DTransformer --device cuda `
  -n 30 -bs 32 -lr 1e-3 -o output\train_assist09_gpu
```

Key CLI arguments (high level):
- `--dataset` (required) — key from `data/datasets.toml`.
- `--model` — model name or `DTransformer` (default loads DTransformer implementation).
- `--device` — `cpu` or `cuda` (script falls back to `cpu` if CUDA unavailable).
- `-n/--n_epochs` — training epochs.
- `-bs/--batch_size` and `-tbs/--test_batch_size`.
- `-f/--from_file` — path to checkpoint to resume from.
- `--start_epoch` — epoch offset used when naming saved checkpoints (useful when resuming).
- `-o/--output_dir` — directory to save `config.json` and checkpoint snapshots.

Checkpoint format (new behavior):
- The training script now saves full checkpoints as a Python dict with keys:
  - `epoch` (int): real epoch number used for file naming
  - `model_state_dict`: the model parameters
  - `optimizer_state_dict`: optimizer parameters
  - `auc`: validation AUC metric at save time

Example saved filename: `model-020-0.8041.pt` where `020` is the real epoch.

Resume logic (how it works):
- If `--from_file` points to a file saved with the full-checkpoint format, `train.py` will load:
  - `model_state_dict` → model.load_state_dict
  - `optimizer_state_dict` → optimizer.load_state_dict (best effort)
  - `epoch` → used to set an internal `epoch_offset` when naming subsequent snapshots
- If `--from_file` is a plain model `state_dict` (older format), the model weights are loaded but optimizer state is not restored; in that case pass `--start_epoch <N>` to ensure saved filenames continue numbering from the desired epoch.
- If `--device` is set to `cuda` but the local Torch isn't compiled with CUDA, the script prints a warning and automatically switches to `cpu` to avoid crashes.

Resume example (continue from epoch 19 up to 30; saved checkpoint is `model-019-0.8082.pt`):

```powershell
python scripts/train.py --dataset assist09 --model DTransformer --device cuda -n 11 `
  --start_epoch 19 --from_file "output\train_assist09_gpu\model-019-0.8082.pt" `
  -o "output\train_assist09_resume_from_019"
```

This runs 11 more training epochs; the script will produce `model-020-...` through `model-030-...` in the specified output directory. If CUDA is unavailable the script will warn and fall back to CPU.

## 7. Evaluation script (`scripts/test.py`)

The test script evaluates saved models on the specified dataset. After recent changes to checkpoint format, ensure `test.py` is run with the full-checkpoint file or patched to load the `model_state_dict` from a full checkpoint. If `test.py` accepts a plain `state_dict`, you can pass only `model_state_dict`.

Example:

```powershell
python scripts/test.py --dataset assist09 --from_file "output\train_assist09_resume_from_019\model-030-0.8054.pt"
```

(If `test.py` doesn't accept full checkpoints, either extract `model_state_dict` in a small helper or I can patch `test.py` to accept both formats.)

## 8. Data statistics and utilities

During the session a set of small helper scripts were added to `scripts/` for convenience:
- `scripts/compute_assist09_stats.py` — compute train+test combined statistics.
- `scripts/compute_assist09_train_only.py` — compute stats just for `train.txt`.
- `scripts/compute_assist09_test_only.py` — compute stats just for `test.txt`.

These scripts print:
- Number of blocks (students/trajectories), unique question IDs (problems), unique skills (skill/pid IDs), and total interactions.

Example outputs already computed for `assist09`:
- Train only: students=3,135; problems=17,085; skills=123; interactions=231,566.
- Test only: students=1,364; problems=15,189; skills=121; interactions=105,292.
- Combined: students=4,499; problems=17,728; skills=123; interactions=336,858.

## 9. Live test application

A small Flask app (in `live_test/`) provides a UI for generating and serving practice questions and recording submissions. It uses a local SQLite DB and a simple set of templates. The app is optional and mainly for demonstrations.

## 10. Checkpoint management and recommended workflow

- Save config: `train.py` writes `config.json` to the `--output_dir` automatically (a snapshot of the run arguments). Keep it with checkpoints for reproducibility.
- Regular checkpoints: Save after each epoch (the training script does this), with filenames describing epoch and metric.
- Resume training: Prefer full-checkpoints (model + optimizer + epoch). If you only have a model `state_dict`, pass `--start_epoch` to preserve numbering and accept optimizer re-init differences.
- Long-running runs: back up checkpoints or push to a remote storage periodically.

## 11. Troubleshooting

- "Torch not compiled with CUDA enabled" — occurs when `--device cuda` is requested but the local PyTorch isn't a CUDA build. Fix by installing a CUDA-matching PyTorch wheel or run with `--device cpu`.
- Mismatched state dict/optimizer errors when loading optimizer state: optimizer structure (param groups) must match; if not, the script will skip loading optimizer state and continue.
- Data parsing errors: the data loader expects grouped lines; run the `scripts/compute_*` utilities to detect malformed blocks.

## 12. Commands cheat sheet (PowerShell)

Run training (fresh):

```powershell
python scripts\train.py --dataset assist09 --model DTransformer --device cpu -n 30 -bs 32 -o output\train_assist09_cpu
```

Resume from full-checkpoint (example):

```powershell
python scripts\train.py --dataset assist09 --model DTransformer --device cuda -n 11 --from_file "output\train_assist09_gpu\model-019-0.8082.pt" --start_epoch 19 -o "output\train_assist09_resume_from_019"
```

Inspect a checkpoint (quick Python):

```powershell
python - <<'PY'
import torch
ckpt = torch.load(r'output\train_assist09_resume_from_019\model-020-0.8041.pt', map_location='cpu')
print(sorted(ckpt.keys()))
print('epoch', ckpt.get('epoch'))
PY
```

Evaluate a checkpoint:

```powershell
python scripts\test.py --dataset assist09 --from_file "output\train_assist09_resume_from_019\model-030-0.8054.pt"
```

## 13. Development notes & next steps

Suggested low-risk improvements:
- Patch `scripts/test.py` to accept the full-checkpoint format and to print which format was loaded (plain vs full checkpoint).
- Add an optional `--save-best-only` flag to `train.py` to avoid writing every epoch's snapshot in long runs.
- Add a small `scripts/extract_model_state.py` helper to convert older `.pt` files (model-only) into the full-checkpoint format by adding optimizer placeholders and epoch metadata.
- Add unit tests around checkpoint save/load to guarantee fidelity across runs.

## 14. Contacts & provenance

This file was generated from the repository state on 2025-09-30. For questions about the DTransformer architecture or training hyperparameters, refer to:
- `DTransformer/model.py`
- `DTransformer/eval.py`
- `scripts/train.py`


---

If you'd like this saved as a different filename (PDF, HTML), or want sections expanded (deep architecture walk-through, per-layer shapes, or reproducible experiments table), tell me which section to expand and I will update the document.