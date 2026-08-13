"""Prepare AISHELL-1 test data and evaluate an ASR HTTP service.

This helper is intentionally standalone:
- prepare: download/extract AISHELL-1 and build a test manifest
- eval: call the ASR service and compute CER/WER/SER/latency

AISHELL-1 reference:
https://www.openslr.org/33/
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import re
import string
import tarfile
import time
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_AISHELL_URL = "http://www.openslr.org/resources/33/data_aishell.tgz"


def write_json(data: Any, path: Path | None) -> None:
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    print(text)


def download_file(url: str, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists() and out_path.stat().st_size > 0:
        print(f"[skip] archive exists: {out_path}")
        return

    print(f"[info] downloading {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "A22-AISHELL-Eval/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp, out_path.open("wb") as f:
        total = int(resp.headers.get("Content-Length") or 0)
        done = 0
        last_report = time.time()
        while True:
            chunk = resp.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            now = time.time()
            if now - last_report >= 5:
                if total:
                    print(f"[download] {done / 1024**3:.2f} / {total / 1024**3:.2f} GiB")
                else:
                    print(f"[download] {done / 1024**3:.2f} GiB")
                last_report = now
    print(f"[ok] downloaded: {out_path}")


def safe_extract_tgz(archive: Path, out_dir: Path) -> None:
    marker = out_dir / ".aishell_extracted"
    if marker.exists():
        print(f"[skip] extraction marker exists: {marker}")
        return

    out_dir.mkdir(parents=True, exist_ok=True)
    root = out_dir.resolve()
    print(f"[info] extracting {archive} -> {out_dir}")
    with tarfile.open(archive, "r:gz") as tf:
        for member in tf.getmembers():
            target = (out_dir / member.name).resolve()
            if root not in target.parents and target != root:
                raise RuntimeError(f"Unsafe tar member path: {member.name}")
        tf.extractall(out_dir)
    marker.write_text(time.strftime("%Y-%m-%d %H:%M:%S"), encoding="utf-8")
    print("[ok] extracted")


def find_data_aishell_root(root: Path) -> Path:
    candidates = [
        root / "data_aishell",
        root,
    ]
    for candidate in candidates:
        if (candidate / "transcript").exists() and (candidate / "wav").exists():
            return candidate
    matches = list(root.rglob("aishell_transcript_v0.8.txt"))
    if matches:
        return matches[0].parents[1]
    raise FileNotFoundError(f"Cannot find AISHELL-1 extracted root under: {root}")


def load_transcripts(data_root: Path) -> dict[str, str]:
    transcript_path = data_root / "transcript" / "aishell_transcript_v0.8.txt"
    if not transcript_path.exists():
        raise FileNotFoundError(f"Missing transcript file: {transcript_path}")

    refs: dict[str, str] = {}
    with transcript_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(maxsplit=1)
            if len(parts) != 2:
                continue
            utt_id, text = parts
            refs[utt_id] = text.strip()
    return refs


def _tar_contains_split(archive: Path, split: str) -> bool:
    prefix = f"{split}/"
    with tarfile.open(archive, "r:gz") as tf:
        for member in tf:
            return member.name.startswith(prefix)
    return False


def extract_split_archives(data_root: Path, split: str) -> dict[str, Any]:
    wav_root = data_root / "wav"
    split_root = wav_root / split
    if split_root.exists() and any(split_root.rglob("*.wav")):
        return {
            "split": split,
            "extracted": False,
            "reason": "split wav directory already exists",
            "wav_root": str(split_root),
        }

    archives = sorted(wav_root.glob("S*.tar.gz"))
    if not archives:
        return {
            "split": split,
            "extracted": False,
            "reason": "no per-speaker archives found",
            "wav_root": str(split_root),
        }

    selected = [archive for archive in archives if _tar_contains_split(archive, split)]
    if not selected:
        return {
            "split": split,
            "extracted": False,
            "reason": f"no archive contains split prefix {split}/",
            "wav_root": str(split_root),
        }

    root = wav_root.resolve()
    for index, archive in enumerate(selected, start=1):
        print(f"[extract-split] {index}/{len(selected)} {archive.name}")
        with tarfile.open(archive, "r:gz") as tf:
            members = [m for m in tf.getmembers() if m.name.startswith(f"{split}/")]
            for member in members:
                target = (wav_root / member.name).resolve()
                if root not in target.parents and target != root:
                    raise RuntimeError(f"Unsafe tar member path: {member.name}")
            tf.extractall(wav_root, members=members)

    return {
        "split": split,
        "extracted": True,
        "archive_count": len(selected),
        "wav_root": str(split_root),
    }


def build_manifest(data_root: Path, out_path: Path, split: str = "test") -> dict[str, Any]:
    refs = load_transcripts(data_root)
    wav_root = data_root / "wav" / split
    split_extract_report = extract_split_archives(data_root, split)
    if not wav_root.exists():
        raise FileNotFoundError(f"Missing AISHELL wav split: {wav_root}")

    records = []
    missing_ref = []
    for wav in sorted(wav_root.rglob("*.wav")):
        utt_id = wav.stem
        ref = refs.get(utt_id)
        if ref is None:
            missing_ref.append(str(wav))
            continue
        records.append({"utt_id": utt_id, "audio": str(wav), "reference": ref})

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    report = {
        "data_root": str(data_root),
        "split": split,
        "manifest": str(out_path),
        "count": len(records),
        "missing_ref_count": len(missing_ref),
        "missing_ref_samples": missing_ref[:10],
        "split_extract": split_extract_report,
    }
    return report


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).upper()
    chars = []
    for ch in text:
        cat = unicodedata.category(ch)
        if ch.isspace() or cat.startswith("P") or cat.startswith("S"):
            continue
        chars.append(ch)
    return "".join(chars)


def char_tokens(text: str) -> list[str]:
    return list(normalize_text(text))


def word_tokens(text: str) -> list[str]:
    normalized = normalize_text(text)
    try:
        import jieba  # type: ignore

        return [tok for tok in jieba.cut(normalized) if tok.strip()]
    except Exception:
        # Fallback: Chinese characters as tokens, contiguous ASCII as one token.
        tokens: list[str] = []
        ascii_buf = []
        for ch in normalized:
            if ch in string.ascii_uppercase + string.digits:
                ascii_buf.append(ch)
                continue
            if ascii_buf:
                tokens.append("".join(ascii_buf))
                ascii_buf.clear()
            tokens.append(ch)
        if ascii_buf:
            tokens.append("".join(ascii_buf))
        return tokens


def edit_distance(a: list[str], b: list[str]) -> int:
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, start=1):
        cur = [i]
        for j, y in enumerate(b, start=1):
            cur.append(min(
                prev[j] + 1,
                cur[j - 1] + 1,
                prev[j - 1] + (0 if x == y else 1),
            ))
        prev = cur
    return prev[-1]


def request_json(url: str, data: bytes, headers: dict[str, str], timeout: float) -> dict[str, Any]:
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read()
        return json.loads(body.decode("utf-8", errors="replace"))


def transcribe(path: Path, args: argparse.Namespace, turn_id: int) -> dict[str, Any]:
    raw = path.read_bytes()
    if args.mode == "official_binary":
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        return request_json(args.url, raw, {"Content-Type": mime}, args.timeout)

    payload = {
        "session_id": args.session_id,
        "turn_id": turn_id,
        "audio_base64": base64.b64encode(raw).decode("ascii"),
        "audio_format": path.suffix.lstrip(".").lower() or "wav",
    }
    return request_json(
        args.url,
        json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        {"Content-Type": "application/json"},
        args.timeout,
    )


def extract_text(response: dict[str, Any], mode: str) -> str:
    if mode == "official_binary":
        return str(response.get("result") or "")
    return str(response.get("transcript_text") or response.get("result") or "")


def eval_manifest(args: argparse.Namespace) -> None:
    manifest = Path(args.manifest)
    records = [
        json.loads(line)
        for line in manifest.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if args.limit:
        records = records[: args.limit]

    out_jsonl = Path(args.out_jsonl) if args.out_jsonl else None
    if out_jsonl:
        out_jsonl.parent.mkdir(parents=True, exist_ok=True)
        out_jsonl.write_text("", encoding="utf-8")

    totals = {
        "total": len(records),
        "ok": 0,
        "failed": 0,
        "char_ref": 0,
        "char_err": 0,
        "word_ref": 0,
        "word_err": 0,
        "sentence_err": 0,
        "latency_sum": 0.0,
    }

    for idx, record in enumerate(records, start=1):
        started = time.time()
        item: dict[str, Any] = {
            "index": idx,
            "utt_id": record["utt_id"],
            "audio": record["audio"],
            "reference": record["reference"],
        }
        try:
            response = transcribe(Path(record["audio"]), args, idx)
            hyp = extract_text(response, args.mode)
            latency = time.time() - started

            ref_chars = char_tokens(record["reference"])
            hyp_chars = char_tokens(hyp)
            ref_words = word_tokens(record["reference"])
            hyp_words = word_tokens(hyp)
            char_err = edit_distance(ref_chars, hyp_chars)
            word_err = edit_distance(ref_words, hyp_words)
            sentence_err = int(normalize_text(record["reference"]) != normalize_text(hyp))

            item.update({
                "ok": True,
                "latency_sec": round(latency, 3),
                "hypothesis": hyp,
                "cer": char_err / max(1, len(ref_chars)),
                "wer": word_err / max(1, len(ref_words)),
                "ser": sentence_err,
                "response": response if args.keep_response else None,
            })
            totals["ok"] += 1
            totals["char_ref"] += len(ref_chars)
            totals["char_err"] += char_err
            totals["word_ref"] += len(ref_words)
            totals["word_err"] += word_err
            totals["sentence_err"] += sentence_err
            totals["latency_sum"] += latency
        except (OSError, urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as exc:
            item.update({"ok": False, "latency_sec": round(time.time() - started, 3), "error": str(exc)})
            totals["failed"] += 1

        line = json.dumps(item, ensure_ascii=False)
        print(line)
        if out_jsonl:
            with out_jsonl.open("a", encoding="utf-8") as f:
                f.write(line + "\n")

    ok = totals["ok"]
    summary = {
        "manifest": str(manifest),
        "url": args.url,
        "mode": args.mode,
        "total": totals["total"],
        "ok": ok,
        "failed": totals["failed"],
        "success_rate": ok / max(1, totals["total"]),
        "cer": totals["char_err"] / max(1, totals["char_ref"]),
        "wer": totals["word_err"] / max(1, totals["word_ref"]),
        "ser": totals["sentence_err"] / max(1, ok),
        "avg_latency_sec": totals["latency_sum"] / max(1, ok),
        "notes": [
            "CER is the primary Chinese ASR metric.",
            "WER uses jieba tokenization if installed; otherwise it falls back to Chinese-character tokens.",
        ],
    }
    write_json(summary, Path(args.summary) if args.summary else None)


def prepare(args: argparse.Namespace) -> None:
    root = Path(args.root)
    archive = Path(args.archive) if args.archive else root / "data_aishell.tgz"
    if args.download:
        download_file(args.url, archive)
    if args.extract:
        safe_extract_tgz(archive, root)
    data_root = find_data_aishell_root(root)
    report = build_manifest(data_root, Path(args.manifest), split=args.split)
    write_json(report, Path(args.report) if args.report else None)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AISHELL-1 ASR evaluation helper.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("prepare", help="Download/extract AISHELL-1 and build a test manifest.")
    p.add_argument("--root", required=True, help="Directory that stores/extracts AISHELL-1.")
    p.add_argument("--archive", help="Optional existing data_aishell.tgz path.")
    p.add_argument("--url", default=DEFAULT_AISHELL_URL)
    p.add_argument("--download", action="store_true", help="Download data_aishell.tgz if archive is missing.")
    p.add_argument("--extract", action="store_true", help="Extract data_aishell.tgz.")
    p.add_argument("--split", default="test", choices=["train", "dev", "test"])
    p.add_argument("--manifest", required=True)
    p.add_argument("--report")
    p.set_defaults(func=prepare)

    p = sub.add_parser("eval", help="Evaluate ASR service on an AISHELL manifest.")
    p.add_argument("--manifest", required=True)
    p.add_argument("--url", required=True)
    p.add_argument("--mode", choices=["a22_json", "official_binary"], default="a22_json")
    p.add_argument("--session-id", default="aishell_eval")
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--timeout", type=float, default=180)
    p.add_argument("--out-jsonl")
    p.add_argument("--summary")
    p.add_argument("--keep-response", action="store_true")
    p.set_defaults(func=eval_manifest)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
