"""Probe conversation state and embeddings without using experiment data."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import secrets
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def output_text(response: dict[str, Any]) -> str:
    return "".join(
        part.get("text", "")
        for item in response.get("output", [])
        if item.get("type") == "message"
        for part in item.get("content", [])
        if part.get("type") == "output_text"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8317/v1")
    parser.add_argument(
        "--api-key-file", type=Path, default=Path.home() / ".cli-proxy-api/api_key.txt"
    )
    parser.add_argument("--model", default="gpt-5.6-luna")
    parser.add_argument("--embedding-model", default="text-embedding-3-small")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    key = args.api_key_file.read_text(encoding="utf-8-sig").strip()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def request(
        method: str, path: str, body: dict[str, Any] | None = None
    ) -> tuple[int, Any]:
        req = urllib.request.Request(
            args.base_url.rstrip("/") + path,
            data=json.dumps(body).encode("utf-8") if body is not None else None,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            method=method,
        )
        try:
            with opener.open(req, timeout=90) as response:
                raw = response.read().decode("utf-8")
                status = response.status
        except urllib.error.HTTPError as exc:
            status = exc.code
            raw = exc.read().decode("utf-8", errors="replace")
        try:
            return status, json.loads(raw)
        except json.JSONDecodeError:
            return status, {"body": raw[:1000]}

    def record_response(status: int, response: Any) -> dict[str, Any]:
        if not isinstance(response, dict):
            return {"http_status": status, "body_type": type(response).__name__}
        return {
            "http_status": status,
            "id": response.get("id"),
            "store": response.get("store"),
            "previous_response_id": response.get("previous_response_id"),
            "text": output_text(response),
            "output_item_types": [
                item.get("type") for item in response.get("output", [])
            ],
            "usage": response.get("usage"),
            "error": response.get("error", response.get("body")),
        }

    nonce = "PROBE_" + secrets.token_hex(10).upper()
    original = {
        "role": "user",
        "content": f"The private test code for this conversation is {nonce}. Remember it. Reply with ACK only.",
    }
    followup = {
        "role": "user",
        "content": "What private test code did I give you in the previous turn? Reply with that code only, or UNKNOWN if it is not in your context.",
    }
    common = {"model": args.model, "reasoning": {"effort": "low"}, "stream": False}
    report: dict[str, Any] = {
        "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "base_url": args.base_url,
        "model": args.model,
        "nonce": nonce,
    }
    start = time.monotonic()
    status, embedding = request(
        "POST",
        "/embeddings",
        {
            "model": args.embedding_model,
            "input": "A small compatibility probe.",
            "encoding_format": "float",
        },
    )
    report["embeddings"] = {
        "http_status": status,
        "requested_model": args.embedding_model,
        "returned_model": embedding.get("model")
        if isinstance(embedding, dict)
        else None,
        "error": embedding.get("error", embedding.get("body"))
        if isinstance(embedding, dict)
        else None,
    }
    print("Embeddings probe completed.", flush=True)

    status, first = request(
        "POST", "/responses", {**common, "input": [original], "store": True}
    )
    report["first_turn"] = record_response(status, first)
    print("First Responses turn completed.", flush=True)
    if status == 200 and isinstance(first, dict) and first.get("id"):
        status, continued = request(
            "POST",
            "/responses",
            {
                **common,
                "input": [followup],
                "previous_response_id": first["id"],
                "store": True,
            },
        )
        report["previous_response_id"] = record_response(status, continued)
        report["previous_response_id"]["recalls_nonce"] = (
            status == 200 and nonce in output_text(continued)
        )
        print("Response-ID continuation probe completed.", flush=True)

        # Preserve complete output items, including reasoning, tool calls and phase.
        history = [original, *first.get("output", []), followup]
        status, explicit = request(
            "POST", "/responses", {**common, "input": history, "store": False}
        )
        report["explicit_history"] = record_response(status, explicit)
        report["explicit_history"]["recalls_nonce"] = (
            status == 200 and nonce in output_text(explicit)
        )
        print("Explicit-history continuation probe completed.", flush=True)

        status, retrieved = request("GET", "/responses/" + first["id"])
        report["retrieve_response"] = record_response(status, retrieved)

    report["elapsed_seconds"] = round(time.monotonic() - start, 2)
    encoded = json.dumps(report, indent=2, ensure_ascii=False)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)


if __name__ == "__main__":
    main()
