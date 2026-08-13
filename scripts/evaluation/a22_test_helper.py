"""A22 dataset and service test helper.

This helper intentionally avoids changing the runtime system.  It provides:

1. Dataset preflight checks for extracted train/val folders.
2. Prediction tensor shape checks for prediction_emotion.npy.
3. ASR batch API checks for both the official binary API and this repo's
   /transcribe JSON API.
"""

from __future__ import annotations

import argparse
import base64
import csv
import json
import mimetypes
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def _json_dump(data: Any, path: Path | None) -> None:
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    print(text)


def _load_numpy():
    try:
        import numpy as np  # type: ignore
    except Exception as exc:  # pragma: no cover - diagnostic path
        raise RuntimeError("numpy is required for this command.") from exc
    return np


def _first_existing(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


def inspect_data(args: argparse.Namespace) -> None:
    root = Path(args.data_root)
    report: dict[str, Any] = {
        "data_root": str(root),
        "exists": root.exists(),
        "splits": {},
        "notes": [],
    }
    if not root.exists():
        report["notes"].append("data_root does not exist. Extract train.rar/val.rar first.")
        _json_dump(report, Path(args.out) if args.out else None)
        return

    np = None
    for split in args.splits.split(","):
        split = split.strip()
        if not split:
            continue
        split_root = root / split
        split_report: dict[str, Any] = {
            "exists": split_root.exists(),
            "counts": {},
            "sample_emotion_shape": None,
            "sample_3d_fv_shape": None,
            "warnings": [],
        }
        if not split_root.exists():
            split_report["warnings"].append(f"Missing split directory: {split_root}")
            report["splits"][split] = split_report
            continue

        patterns = {
            "videos": "Video_files/**/*.mp4",
            "audios_wav": "Audio_files/**/*.wav",
            "audios_mp3": "Audio_files/**/*.mp3",
            "emotion_csv": "Emotion/**/*.csv",
            "fv_npy": "3D_FV_files/**/*.npy",
        }
        for key, pattern in patterns.items():
            split_report["counts"][key] = sum(1 for _ in split_root.glob(pattern))

        emotion_sample = _first_existing(list(split_root.glob("Emotion/**/*.csv"))[:10])
        if emotion_sample:
            try:
                with emotion_sample.open("r", encoding="utf-8-sig", newline="") as f:
                    reader = csv.reader(f)
                    header = next(reader, None)
                    row = next(reader, None)
                split_report["sample_emotion_file"] = str(emotion_sample)
                split_report["sample_emotion_columns"] = len(row or header or [])
                if len(row or []) != 25:
                    split_report["warnings"].append(
                        "Emotion CSV data row should normally have 25 columns."
                    )
            except Exception as exc:
                split_report["warnings"].append(f"Failed to read emotion sample: {exc}")

        npy_sample = _first_existing(list(split_root.glob("3D_FV_files/**/*.npy"))[:10])
        if npy_sample:
            try:
                if np is None:
                    np = _load_numpy()
                try:
                    arr = np.load(npy_sample, mmap_mode="r")
                except ValueError as exc:
                    if "pickled data" not in str(exc):
                        raise
                    arr = np.load(npy_sample, allow_pickle=True)
                split_report["sample_3d_fv_file"] = str(npy_sample)
                split_report["sample_3d_fv_shape"] = list(arr.shape)
            except Exception as exc:
                split_report["warnings"].append(f"Failed to read 3D_FV sample: {exc}")

        report["splits"][split] = split_report

    _json_dump(report, Path(args.out) if args.out else None)


def check_prediction(args: argparse.Namespace) -> None:
    np = _load_numpy()
    prediction_path = Path(args.prediction)
    arr = np.load(prediction_path, mmap_mode="r")
    report: dict[str, Any] = {
        "prediction": str(prediction_path),
        "shape": list(arr.shape),
        "dtype": str(arr.dtype),
        "valid_rank": arr.ndim == 4,
        "valid_last_dim": arr.ndim == 4 and arr.shape[-1] == args.expected_d,
        "warnings": [],
    }
    if arr.ndim != 4:
        report["warnings"].append("prediction_emotion.npy must have shape [N, K, T, 25].")
    else:
        n, k, t, d = arr.shape
        report["N"] = int(n)
        report["K"] = int(k)
        report["T"] = int(t)
        report["D"] = int(d)
        if args.expected_k and k != args.expected_k:
            report["warnings"].append(f"Expected K={args.expected_k}, got K={k}.")
        if args.expected_t and t != args.expected_t:
            report["warnings"].append(f"Expected T={args.expected_t}, got T={t}.")
        if d != args.expected_d:
            report["warnings"].append(f"Expected D={args.expected_d}, got D={d}.")
        if args.expected_n and n != args.expected_n:
            report["warnings"].append(f"Expected N={args.expected_n}, got N={n}.")

        sample = np.asarray(arr[: min(n, 4), : min(k, 2)], dtype=np.float32)
        report["finite_sample"] = bool(np.isfinite(sample).all())
        report["sample_min"] = float(np.nanmin(sample))
        report["sample_max"] = float(np.nanmax(sample))

    _json_dump(report, Path(args.out) if args.out else None)


def _request_json(url: str, data: bytes, headers: dict[str, str], timeout: float) -> dict[str, Any]:
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read()
        return json.loads(body.decode("utf-8", errors="replace"))


def asr_batch(args: argparse.Namespace) -> None:
    audio_root = Path(args.audio_dir)
    files = sorted(audio_root.rglob(args.glob))
    if args.limit:
        files = files[: args.limit]

    results = []
    out_path = Path(args.out) if args.out else None
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("", encoding="utf-8")

    for idx, path in enumerate(files, start=1):
        started = time.time()
        record: dict[str, Any] = {"index": idx, "file": str(path)}
        try:
            raw = path.read_bytes()
            if args.mode == "official-binary":
                mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
                payload = raw
                headers = {"Content-Type": mime}
            else:
                audio_b64 = base64.b64encode(raw).decode("ascii")
                payload_obj = {
                    "session_id": args.session_id,
                    "turn_id": idx,
                    "audio_base64": audio_b64,
                    "audio_format": path.suffix.lstrip(".").lower() or "wav",
                }
                payload = json.dumps(payload_obj, ensure_ascii=False).encode("utf-8")
                headers = {"Content-Type": "application/json"}

            response = _request_json(args.url, payload, headers, timeout=args.timeout)
            record["ok"] = True
            record["latency_sec"] = round(time.time() - started, 3)
            record["response"] = response
            if args.mode == "official-binary":
                record["text"] = response.get("result")
            else:
                record["text"] = response.get("transcript_text")
        except (urllib.error.URLError, urllib.error.HTTPError, OSError, json.JSONDecodeError) as exc:
            record["ok"] = False
            record["latency_sec"] = round(time.time() - started, 3)
            record["error"] = str(exc)

        results.append(record)
        line = json.dumps(record, ensure_ascii=False)
        print(line)
        if out_path:
            with out_path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")

    ok_count = sum(1 for item in results if item.get("ok"))
    summary = {"total": len(results), "ok": ok_count, "failed": len(results) - ok_count}
    print("SUMMARY", json.dumps(summary, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="A22 evaluation helper.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("inspect-data", help="Inspect extracted train/val dataset structure.")
    p.add_argument("--data-root", required=True)
    p.add_argument("--splits", default="train,val")
    p.add_argument("--out")
    p.set_defaults(func=inspect_data)

    p = sub.add_parser("check-prediction", help="Check prediction_emotion.npy shape and basic values.")
    p.add_argument("--prediction", required=True)
    p.add_argument("--expected-n", type=int, default=0)
    p.add_argument("--expected-k", type=int, default=10)
    p.add_argument("--expected-t", type=int, default=750)
    p.add_argument("--expected-d", type=int, default=25)
    p.add_argument("--out")
    p.set_defaults(func=check_prediction)

    p = sub.add_parser("asr-batch", help="Batch-test ASR API with audio files.")
    p.add_argument("--url", required=True)
    p.add_argument("--audio-dir", required=True)
    p.add_argument("--glob", default="*.mp3")
    p.add_argument("--mode", choices=["official-binary", "a22-transcribe-json"], default="a22-transcribe-json")
    p.add_argument("--session-id", default="eval_s1")
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--timeout", type=float, default=120)
    p.add_argument("--out")
    p.set_defaults(func=asr_batch)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
