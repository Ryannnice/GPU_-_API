"""Check Mem0's actual FastEmbed provider and an isolated CPU vector search."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cache-dir", type=Path, default=Path.home() / ".cli-proxy-api/embedding-cache"
    )
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    os.environ["FASTEMBED_CACHE_PATH"] = str(args.cache_dir.resolve())
    os.environ.setdefault("MEM0_TELEMETRY", "false")

    import numpy as np
    from mem0.configs.embeddings.base import BaseEmbedderConfig
    from mem0.embeddings.fastembed import FastEmbedEmbedding
    from qdrant_client import QdrantClient, models

    model_name = "BAAI/bge-small-en-v1.5"
    embedder = FastEmbedEmbedding(
        BaseEmbedderConfig(model=model_name, embedding_dims=384)
    )
    relevant = (
        "The customer wants sales forecasts every month, delivered as a CSV file."
    )
    unrelated = "Volcanic rock forms when molten lava cools and solidifies."
    query = "How often should the sales forecast be sent and in which file format?"
    vectors = [
        np.asarray(embedder.embed(text), dtype=np.float32)
        for text in [relevant, unrelated, query]
    ]
    repeat = np.asarray(embedder.embed(relevant), dtype=np.float32)
    onnx_model = embedder.dense_model.model
    providers = onnx_model.model.get_providers()
    model_dir = Path(onnx_model._model_dir)
    artifact_path = model_dir / "model_optimized.onnx"

    client = QdrantClient(":memory:")
    try:
        client.create_collection(
            "cpu_bge_probe",
            vectors_config=models.VectorParams(
                size=384, distance=models.Distance.COSINE
            ),
        )
        client.upsert(
            "cpu_bge_probe",
            points=[
                models.PointStruct(
                    id=1, vector=vectors[0].tolist(), payload={"kind": "relevant"}
                ),
                models.PointStruct(
                    id=2, vector=vectors[1].tolist(), payload={"kind": "unrelated"}
                ),
            ],
        )
        hits = client.query_points(
            "cpu_bge_probe", query=vectors[2].tolist(), limit=2
        ).points
    finally:
        client.close()

    checks = {
        "all_vectors_384_dimensions": all(vector.shape == (384,) for vector in vectors),
        "all_values_finite": all(bool(np.isfinite(vector).all()) for vector in vectors),
        "cpu_execution_only": providers == ["CPUExecutionProvider"],
        "repeated_input_stable": bool(np.allclose(vectors[0], repeat, atol=1e-6)),
        "semantic_retrieval_correct": len(hits) == 2
        and hits[0].id == 1
        and hits[0].score > hits[1].score,
    }
    report = {
        "embedding_model": model_name,
        "embedding_provider": "mem0.embeddings.fastembed.FastEmbedEmbedding",
        "artifact_repository": "qdrant/bge-small-en-v1.5-onnx-q",
        "artifact_directory": str(model_dir),
        "artifact_sha256": hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
        "cache_directory": str(args.cache_dir.resolve()),
        "versions": {
            name: importlib.metadata.version(name)
            for name in ["mem0ai", "fastembed", "onnxruntime", "qdrant-client"]
        },
        "execution_providers": providers,
        "vector_norms": [float(np.linalg.norm(vector)) for vector in vectors],
        "retrieval": [{"id": hit.id, "score": hit.score} for hit in hits],
        "checks": checks,
        "passed": all(checks.values()),
        "strict_original_embedding_reproduction": False,
    }
    encoded = json.dumps(report, indent=2)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
