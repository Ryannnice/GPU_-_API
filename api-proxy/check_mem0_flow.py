"""Smoke-test real Mem0 extraction and retrieval in an isolated temporary store."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import tempfile
import time
import uuid
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--support-dir", type=Path, required=True)
    parser.add_argument("--model", default="openai/gpt-5.6-sol")
    parser.add_argument("--base-url", default="http://127.0.0.1:8317/v1")
    parser.add_argument(
        "--api-key-file", type=Path, default=Path.home() / ".cli-proxy-api/api_key.txt"
    )
    parser.add_argument(
        "--cache-dir", type=Path, default=Path.home() / ".cli-proxy-api/embedding-cache"
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path.home() / ".cli-proxy-api"
    )
    parser.add_argument(
        "--unpatched-sampling",
        action="store_true",
        help="Reproduce the original unsupported sampling parameters",
    )
    args = parser.parse_args()
    root = args.output_dir.resolve()
    root.mkdir(parents=True, exist_ok=True)
    key = args.api_key_file.read_text(encoding="utf-8-sig").strip()
    os.environ["OPENAI_API_KEY"] = key
    os.environ["OPENAI_API_BASE"] = os.environ["OPENAI_BASE_URL"] = args.base_url
    os.environ["FASTEMBED_CACHE_PATH"] = str(args.cache_dir.resolve())
    os.environ["MEM0_TELEMETRY"] = "false"
    os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
    run_id = uuid.uuid4().hex
    os.environ["CLREPRO_API_LOG_DIR"] = str(root / "mem0-flow-evidence" / run_id)
    support_path = args.support_dir.resolve() / "sitecustomize.py"
    spec = importlib.util.spec_from_file_location("clbench_probe_support", support_path)
    support = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(support)

    report = {
        "llm_model": args.model,
        "embedding_model": "BAAI/bge-small-en-v1.5",
        "embedding_dims": 384,
        "sampling_compatibility_fix_enabled": not args.unpatched_sampling,
        "support_sha256": hashlib.sha256(support_path.read_bytes()).hexdigest(),
        "evidence_directory": os.environ["CLREPRO_API_LOG_DIR"],
        "passed": False,
    }
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="mem0-flow-probe-", dir=root) as scratch:
        scratch_path = Path(scratch).resolve()
        if not scratch_path.is_relative_to(root):
            raise RuntimeError("Unexpected scratch directory")
        os.environ["MEM0_DIR"] = str(scratch_path / "mem0-home")
        from mem0 import Memory

        llm_config = {"model": args.model, "temperature": 0.0}
        if not args.unpatched_sampling:
            llm_config["temperature"] = None
            llm_config["top_p"] = None
        memory = None
        try:
            memory = Memory.from_config(
                {
                    "llm": {"provider": "litellm", "config": llm_config},
                    "embedder": {
                        "provider": "fastembed",
                        "config": {
                            "model": "BAAI/bge-small-en-v1.5",
                            "embedding_dims": 384,
                        },
                    },
                    "vector_store": {
                        "provider": "qdrant",
                        "config": {
                            "collection_name": "mem0_smoke",
                            "path": str(scratch_path / "qdrant"),
                            "embedding_model_dims": 384,
                        },
                    },
                    "history_db_path": str(scratch_path / "history.db"),
                }
            )
            original_generate = memory.llm.generate_response
            calls = []

            def counted_generate(*call_args, **call_kwargs):
                calls.append(1)
                return original_generate(*call_args, **call_kwargs)

            memory.llm.generate_response = counted_generate
            added = memory.add(
                [
                    {
                        "role": "user",
                        "content": "I manage retail sales planning. I want the sales forecast every month and I always want the report delivered as a CSV file.",
                    }
                ],
                user_id=run_id,
            )
            found = memory.search(
                "How often do I want the sales forecast and in what file format?",
                filters={"user_id": run_id},
                limit=3,
            )
            extracted = added.get("results", [])
            hits = found.get("results", [])
            texts = [item.get("memory", "") for item in hits]
            combined = " ".join(texts).lower()
            report.update(
                extraction_llm_calls=len(calls),
                extracted_memory_count=len(extracted),
                retrieved_memory_count=len(hits),
                retrieved_memories=texts,
                passed=bool(extracted)
                and bool(hits)
                and "csv" in combined
                and "month" in combined
                and len(calls) > 0,
            )
        except Exception as exc:
            report.update(
                error_type=type(exc).__name__,
                error=str(exc).replace(key, "<redacted>")[:700],
            )
        finally:
            if memory is not None:
                memory.vector_store.client.close()
                memory.db.close()

    report["elapsed_seconds"] = round(time.monotonic() - started, 2)
    encoded = json.dumps(report, indent=2)
    suffix = "unpatched" if args.unpatched_sampling else "patched"
    (root / f"mem0-flow-probe-{suffix}.json").write_text(
        encoded + "\n", encoding="utf-8"
    )
    print(encoded)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
