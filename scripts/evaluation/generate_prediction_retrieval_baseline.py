"""Generate an A22 prediction_emotion.npy retrieval baseline.

This is an offline evaluation helper. It does not touch runtime services.

The baseline treats each Emotion CSV as a target listener sequence and uses the
opposite role in the same clip as the speaker/context sequence. For every val
target, it retrieves train samples with similar speaker summaries and returns
their paired listener Emotion sequences as K candidates.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


EMOTION_DIM = 25

RECOLA_ROLE_MAP = {
    "P25": "P1",
    "P26": "P2",
    "P41": "P1",
    "P42": "P2",
    "P45": "P1",
    "P46": "P2",
}


@dataclass(frozen=True)
class PairSample:
    target_path: Path
    source_path: Path
    target_seq: np.ndarray
    source_summary: np.ndarray


def load_emotion_csv(path: Path) -> np.ndarray:
    rows: list[list[float]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue
            try:
                values = [float(x) for x in row[:EMOTION_DIM]]
            except ValueError:
                # Header row.
                continue
            if len(values) == EMOTION_DIM:
                rows.append(values)
    if not rows:
        raise ValueError(f"No numeric {EMOTION_DIM}-D rows found in {path}")
    arr = np.asarray(rows, dtype=np.float32)
    arr = np.nan_to_num(arr, nan=0.0, posinf=1.0, neginf=-1.0)
    return arr


def resize_sequence(seq: np.ndarray, target_t: int) -> np.ndarray:
    if seq.shape[0] == target_t:
        return seq.astype(np.float32, copy=False)
    if seq.shape[0] <= 1:
        return np.repeat(seq[:1], target_t, axis=0).astype(np.float32)

    src_x = np.linspace(0.0, 1.0, seq.shape[0], dtype=np.float32)
    dst_x = np.linspace(0.0, 1.0, target_t, dtype=np.float32)
    out = np.empty((target_t, seq.shape[1]), dtype=np.float32)
    for dim in range(seq.shape[1]):
        out[:, dim] = np.interp(dst_x, src_x, seq[:, dim]).astype(np.float32)
    return out


def sequence_summary(seq: np.ndarray) -> np.ndarray:
    first = seq[0]
    last = seq[-1]
    diff = np.diff(seq, axis=0) if seq.shape[0] > 1 else np.zeros_like(seq)
    parts = [
        seq.mean(axis=0),
        seq.std(axis=0),
        np.percentile(seq, 25, axis=0),
        np.percentile(seq, 75, axis=0),
        last - first,
        np.mean(np.abs(diff), axis=0),
    ]
    return np.concatenate(parts).astype(np.float32)


def opposite_role(role: str) -> str | None:
    lowered = role.lower()
    if lowered == "p1":
        return "P2"
    if lowered == "p2":
        return "P1"
    return None


def iter_emotion_csv(root: Path) -> list[Path]:
    return sorted(
        p for p in root.rglob("*.csv")
        if not p.name.startswith("._") and p.is_file()
    )


def official_rel_to_emotion_csv(split_root: Path, rel_path: str) -> Path:
    parts = Path(rel_path).parts
    if len(parts) < 4:
        raise ValueError(f"Unexpected official path: {rel_path}")
    dataset = parts[0]
    if dataset == "NoXI":
        session = parts[1]
        role_name = parts[2]
        clip = parts[3]
        if role_name == "Expert_video":
            role = "P1"
        elif role_name == "Novice_video":
            role = "P2"
        else:
            raise ValueError(f"Unknown NoXI role: {role_name}")
        return split_root / "Emotion" / dataset / session / role / f"{clip}.csv"
    if dataset == "RECOLA":
        if len(parts) < 4:
            raise ValueError(f"Unexpected RECOLA path: {rel_path}")
        group = parts[1]
        person = RECOLA_ROLE_MAP.get(parts[2], parts[2])
        clip = parts[3]
        return split_root / "Emotion" / dataset / group / person / f"{clip}.csv"
    raise ValueError(f"Unknown dataset in official path: {rel_path}")


def build_pairs_from_index(split_root: Path, index_csv: Path, *, limit: int = 0) -> list[PairSample]:
    pairs: list[PairSample] = []
    cache: dict[Path, np.ndarray] = {}
    rows: list[tuple[str, str]] = []
    with index_csv.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            speaker = (row.get("speaker_path") or "").strip()
            listener = (row.get("listener_path") or "").strip()
            if speaker and listener:
                rows.append((speaker, listener))

    # Official order: forward speaker->listener, then swapped direction.
    ordered = rows + [(listener, speaker) for speaker, listener in rows]
    for speaker_rel, listener_rel in ordered:
        source_path = official_rel_to_emotion_csv(split_root, speaker_rel)
        target_path = official_rel_to_emotion_csv(split_root, listener_rel)
        if not source_path.exists() or not target_path.exists():
            continue
        try:
            source_seq = cache.get(source_path)
            if source_seq is None:
                source_seq = load_emotion_csv(source_path)
                cache[source_path] = source_seq
            target_seq = cache.get(target_path)
            if target_seq is None:
                target_seq = load_emotion_csv(target_path)
                cache[target_path] = target_seq
        except Exception:
            continue
        pairs.append(
            PairSample(
                target_path=target_path,
                source_path=source_path,
                target_seq=target_seq,
                source_summary=sequence_summary(source_seq),
            )
        )
        if limit and len(pairs) >= limit:
            break
    return pairs


def build_pairs(split_root: Path, *, limit: int = 0) -> list[PairSample]:
    emotion_root = split_root / "Emotion"
    pairs: list[PairSample] = []
    cache: dict[Path, np.ndarray] = {}

    for target_path in iter_emotion_csv(emotion_root):
        role = target_path.parent.name
        other = opposite_role(role)
        if other is None:
            continue
        source_path = target_path.parent.parent / other / target_path.name
        if not source_path.exists():
            continue
        try:
            target_seq = cache.get(target_path)
            if target_seq is None:
                target_seq = load_emotion_csv(target_path)
                cache[target_path] = target_seq
            source_seq = cache.get(source_path)
            if source_seq is None:
                source_seq = load_emotion_csv(source_path)
                cache[source_path] = source_seq
        except Exception:
            continue
        pairs.append(
            PairSample(
                target_path=target_path,
                source_path=source_path,
                target_seq=target_seq,
                source_summary=sequence_summary(source_seq),
            )
        )
        if limit and len(pairs) >= limit:
            break
    return pairs


def standardize(train_features: np.ndarray, val_features: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mean = train_features.mean(axis=0, keepdims=True)
    std = train_features.std(axis=0, keepdims=True)
    std = np.where(std < 1e-6, 1.0, std)
    return (train_features - mean) / std, (val_features - mean) / std


def generate(args: argparse.Namespace) -> None:
    data_root = Path(args.data_root)
    train_pairs = build_pairs(data_root / "train", limit=args.train_limit)
    if args.index_csv:
        val_pairs = build_pairs_from_index(
            data_root / "val",
            Path(args.index_csv),
            limit=args.val_limit,
        )
    else:
        val_pairs = build_pairs(data_root / "val", limit=args.val_limit)
    if not train_pairs:
        raise RuntimeError("No train P1/P2 paired Emotion samples found.")
    if not val_pairs:
        raise RuntimeError("No val P1/P2 paired Emotion samples found.")

    k = args.k
    target_t = args.t
    rng = np.random.default_rng(args.seed)

    train_features = np.stack([p.source_summary for p in train_pairs], axis=0)
    val_features = np.stack([p.source_summary for p in val_pairs], axis=0)
    train_z, val_z = standardize(train_features, val_features)

    prediction = np.empty((len(val_pairs), k, target_t, EMOTION_DIM), dtype=np.float32)
    manifest: dict[str, Any] = {
        "method": "speaker_to_listener_train_retrieval_baseline",
        "data_root": str(data_root),
        "shape": [len(val_pairs), k, target_t, EMOTION_DIM],
        "train_pairs": len(train_pairs),
        "val_pairs": len(val_pairs),
        "notes": [
            "Each val target uses the opposite-role val sequence only as retrieval query.",
            "Returned candidates are paired listener Emotion sequences from train split.",
            "No val target label is copied into its own prediction.",
            "When --index-csv is provided, val samples follow official person_specific_val.csv expansion order.",
        ],
        "samples": [],
    }

    for idx, val_pair in enumerate(val_pairs):
        diff = train_z - val_z[idx]
        dist = np.einsum("ij,ij->i", diff, diff)
        nearest = np.argsort(dist)[: max(k, args.candidate_pool)]
        if len(nearest) < k:
            nearest = np.resize(nearest, k)
        chosen = nearest[:k]

        sample_matches = []
        for cand_idx, train_idx in enumerate(chosen):
            seq = resize_sequence(train_pairs[int(train_idx)].target_seq, target_t)
            if args.jitter > 0:
                noise = rng.normal(0.0, args.jitter, size=seq.shape).astype(np.float32)
                seq = seq + noise
            seq[:, :15] = np.clip(seq[:, :15], 0.0, 1.0)
            seq[:, 15:17] = np.clip(seq[:, 15:17], -1.0, 1.0)
            exp = np.clip(seq[:, 17:25], 0.0, 1.0)
            exp_sum = exp.sum(axis=1, keepdims=True)
            exp_sum = np.where(exp_sum < 1e-6, 1.0, exp_sum)
            seq[:, 17:25] = exp / exp_sum
            prediction[idx, cand_idx] = seq.astype(np.float32)
            sample_matches.append(
                {
                    "rank": cand_idx + 1,
                    "distance": float(dist[int(train_idx)]),
                    "train_target": str(train_pairs[int(train_idx)].target_path),
                    "train_source": str(train_pairs[int(train_idx)].source_path),
                }
            )

        if idx < args.manifest_sample_limit:
            manifest["samples"].append(
                {
                    "index": idx,
                    "val_target": str(val_pair.target_path),
                    "val_source": str(val_pair.source_path),
                    "matches": sample_matches,
                }
            )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(out_path, prediction)

    manifest_path = Path(args.manifest) if args.manifest else out_path.with_suffix(".manifest.json")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    report = {
        "prediction": str(out_path),
        "manifest": str(manifest_path),
        "shape": list(prediction.shape),
        "dtype": str(prediction.dtype),
        "min": float(prediction.min()),
        "max": float(prediction.max()),
        "train_pairs": len(train_pairs),
        "val_pairs": len(val_pairs),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate A22 prediction_emotion.npy retrieval baseline.")
    parser.add_argument("--data-root", required=True, help="Dataset root containing train/ and val/.")
    parser.add_argument("--index-csv", help="Official person_specific_val.csv for val order expansion.")
    parser.add_argument("--out", required=True, help="Output prediction_emotion.npy path.")
    parser.add_argument("--manifest", help="Output manifest JSON path.")
    parser.add_argument("--k", type=int, default=10, help="Number of candidates per sample.")
    parser.add_argument("--t", type=int, default=750, help="Output sequence length.")
    parser.add_argument("--candidate-pool", type=int, default=20)
    parser.add_argument("--train-limit", type=int, default=0, help="Debug limit for train pairs.")
    parser.add_argument("--val-limit", type=int, default=0, help="Debug limit for val pairs.")
    parser.add_argument("--manifest-sample-limit", type=int, default=50)
    parser.add_argument("--jitter", type=float, default=0.0, help="Optional small Gaussian noise.")
    parser.add_argument("--seed", type=int, default=2026)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    generate(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
