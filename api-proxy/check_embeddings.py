"""Check the real embedding upstream without printing credentials or vectors."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import urllib.error
import urllib.request
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="https://api.openai.com/v1")
    parser.add_argument("--model", default="text-embedding-3-small")
    parser.add_argument("--dimensions", type=int, default=1536)
    credentials = parser.add_mutually_exclusive_group()
    credentials.add_argument("--key-env", default="OPENAI_API_KEY")
    credentials.add_argument("--api-key-file", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    if args.dimensions <= 0:
        parser.error("--dimensions must be positive")
    key = (
        args.api_key_file.read_text(encoding="utf-8-sig").strip()
        if args.api_key_file
        else os.environ.get(args.key_env, "").strip()
    )
    if not key:
        parser.error(
            "No API key was found in the selected file or environment variable"
        )

    payload = {
        "model": args.model,
        "input": ["Compatibility probe for the original embedding model."],
        "encoding_format": "float",
        "dimensions": args.dimensions,
    }
    request = urllib.request.Request(
        args.base_url.rstrip("/") + "/embeddings",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    report = {
        "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "upstream": args.base_url,
        "requested_model": args.model,
        "requested_dimensions": args.dimensions,
        "ready": False,
    }
    try:
        with urllib.request.urlopen(request, timeout=35) as response:
            data = json.load(response)
            vectors = data.get("data", [])
            dimensions = [len(item["embedding"]) for item in vectors]
            finite = bool(vectors) and all(
                isinstance(value, (int, float)) and math.isfinite(value)
                for item in vectors
                for value in item["embedding"]
            )
            report.update(
                http_status=response.status,
                returned_model=data.get("model"),
                vector_count=len(vectors),
                dimensions=dimensions,
                all_finite=finite,
                usage=data.get("usage"),
                ready=(
                    response.status == 200
                    and data.get("model") == args.model
                    and dimensions == [args.dimensions]
                    and finite
                ),
            )
    except urllib.error.HTTPError as exc:
        try:
            error = json.loads(exc.read()).get("error", {})
        except (ValueError, AttributeError):
            error = {}
        # Error messages can contain fragments of keys; report codes only.
        report.update(
            http_status=exc.code,
            error_type=error.get("type") if isinstance(error, dict) else None,
            error_code=error.get("code") if isinstance(error, dict) else None,
        )
    except (OSError, ValueError, KeyError, TypeError) as exc:
        report["error_type"] = type(exc).__name__

    encoded = json.dumps(report, indent=2)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
