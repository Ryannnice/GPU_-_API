"""Verify the CLBench history patch in memory; never edit the experiment tree."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import sys
import types
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    root = args.upstream.resolve()
    source_path = root / "src/systems/utils/provider_adapters.py"
    source = source_path.read_text(encoding="utf-8-sig")
    patch_path = Path(__file__).parent / "patches/clbench-stateless-history.patch"
    patch_lines = patch_path.read_text().splitlines(keepends=True)
    old, new = [], []
    for line in patch_lines:
        if line.startswith(("diff ", "--- ", "+++ ", "@@")):
            continue
        if line.startswith((" ", "-")):
            old.append(line[1:])
        if line.startswith((" ", "+")):
            new.append(line[1:])
    old_text, new_text = "".join(old), "".join(new)
    if source.count(old_text) != 1:
        raise SystemExit(
            "Patch context changed; inspect the current adapter before applying it."
        )
    fixed_source = source.replace(old_text, new_text, 1)

    os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")
    sys.path.insert(0, str(root))
    original = importlib.import_module("src.systems.utils.provider_adapters")
    patched_name = original.__name__ + "_history_probe"
    patched = types.ModuleType(patched_name)
    patched.__package__ = original.__package__
    patched.__file__ = str(source_path)
    sys.modules[patched_name] = patched
    exec(compile(fixed_source, str(source_path), "exec"), patched.__dict__)

    messages = [
        {"role": "user", "content": "The test code is HISTORY_CHECK_314159."},
        {"role": "assistant", "content": "ACK"},
        {"role": "user", "content": "What test code did I provide?"},
    ]

    def make_client(module: types.ModuleType, store: bool):
        client = module.ProviderTurnClient(
            model="openai/gpt-5.6-luna",
            openai_store=store,
            system_prompt="Current-turn instructions.",
            anthropic_max_tokens=1024,
        )
        client.state.previous_response_id = "resp_synthetic_previous_turn"
        client.state.sent_message_count = 2
        return client

    before = make_client(original, False)._openai_common_kwargs(messages)
    after_client = make_client(patched, False)
    after = after_client._openai_common_kwargs(messages)
    stateful = make_client(patched, True)._openai_common_kwargs(messages)
    after_client.reset()
    reset = after_client._openai_common_kwargs([messages[-1]])

    checks = {
        "reproduces_original_history_loss": before["input"] == [messages[-1]],
        "patched_stateless_preserves_full_history": after["input"] == messages,
        "patched_stateless_does_not_send_response_id": "previous_response_id"
        not in after,
        "patched_stateless_resends_current_instructions": after["instructions"]
        == "Current-turn instructions.",
        "stateful_continuation_unchanged": (
            stateful["input"] == [messages[-1]]
            and stateful["previous_response_id"] == "resp_synthetic_previous_turn"
        ),
        "reset_clears_previous_run_state": (
            reset["input"] == [messages[-1]]
            and after_client.state.previous_response_id is None
            and after_client.state.sent_message_count == 0
        ),
    }
    report = {
        "upstream": str(root),
        "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
        "experiment_files_modified": False,
        "model_requests_made": 0,
        "checks": checks,
        "passed": all(checks.values()),
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
