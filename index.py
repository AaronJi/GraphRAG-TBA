"""Expand action-level cases in memory and run the GraphRAG 0.5.0 index."""

import argparse
import asyncio
import json
import time
from unittest.mock import patch

from data import INPUT, OUTPUT, ROOT, read_jsonl


TAU = 70


def make_documents():
    from graphrag.index.utils.hashing import gen_md5_hash

    actions = read_jsonl(INPUT / "dilemma_actions.jsonl")
    seed = json.loads((INPUT / "seed_principles.json").read_text(encoding="utf-8"))
    principles = sorted(seed["principles"], key=lambda principle: principle["id"])
    associations = read_jsonl(OUTPUT / "associations.jsonl")
    scores = {row["id"]: row["score"] for row in associations}
    if len(scores) != len(associations):
        raise ValueError("Duplicate association ID")

    documents = []
    for action in actions:
        idx, kind = action["idx"], action["action_type"]
        values = zip(action["values_names"], action["value_maslow_labels"], strict=True)
        for position, (value, label) in enumerate(values):
            if label is None:
                continue
            prefix = f"maslow:{idx}:{kind}:v{position}"
            relevant = []
            for principle in principles:
                key = f"{prefix}:{principle['id']}"
                score = scores.pop(key)
                if score >= TAU:
                    relevant.append({"id": principle["id"], "text": principle["text"], "association_score": score})
            if not relevant:
                continue
            text = json.dumps({
                "theory": "Maslow", "source_dilemma_id": idx, "action_type": kind,
                "context": action["context"], "observed_action": action["action"],
                "annotated_value": value, "theory_label": label, "relevant_principles": relevant,
                "note": "An observed action can conflict with a relevant principle. Extract that distinction.",
            }, ensure_ascii=False, indent=2)
            documents.append({"text": text, "id": gen_md5_hash({"text": text}, ("text",)),
                              "title": f"{idx}_{kind}_v{position}.txt"})
    if scores or not documents:
        raise ValueError("Action-level inputs do not match the saved association scores")
    return sorted(documents, key=lambda document: document["title"])


async def build_index(config, dataset, run_id, reporter):
    from graphrag.index.emit.types import TableEmitterType
    from graphrag.index.run import run_pipeline_with_config
    from graphrag.llm.openai import openai_chat_llm

    legacy_completion_args = openai_chat_llm.get_completion_llm_args

    def completion_args(parameters, configuration):
        args = legacy_completion_args(parameters, configuration)
        args["max_completion_tokens"] = args.pop("max_tokens")
        args["reasoning_effort"] = "none"
        defaults = {"frequency_penalty": 0, "presence_penalty": 0, "top_p": 1, "n": 1}
        for name, default in defaults.items():
            if args.get(name) in (None, default):
                args.pop(name, None)
        return args

    # Adapt GraphRAG 0.5.0's request parameters for the duration of this run.
    with patch.object(openai_chat_llm, "get_completion_llm_args", completion_args):
        async for result in run_pipeline_with_config(
            config, dataset=dataset, run_id=run_id, emit=[TableEmitterType.Parquet], progress_reporter=reporter,
        ):
            if result.errors:
                raise RuntimeError(f"GraphRAG workflow failed: {result.workflow}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Assemble and validate the input without model calls")
    parser.add_argument("--reporter", choices=("print", "rich", "none"), default="print")
    args = parser.parse_args()

    import pandas as pd
    from graphrag.config.load_config import load_config
    from graphrag.config.logging import enable_logging_with_config
    from graphrag.config.resolve_path import resolve_paths
    from graphrag.index.create_pipeline_config import create_pipeline_config
    from graphrag.logging.factories import create_progress_reporter
    from graphrag.logging.types import ReporterType

    documents = make_documents()
    print(f"Assembled {len(documents):,} index documents in memory at tau={TAU}.", flush=True)
    settings = load_config(ROOT)
    run_id = time.strftime("%Y%m%d-%H%M%S")
    resolve_paths(settings, run_id)
    pipeline = create_pipeline_config(settings)
    if args.dry_run:
        return
    if settings.llm.api_key in (None, "", "your_openai_api_key", "${OPENAI_API_KEY}"):
        parser.error("Set OPENAI_API_KEY in the environment or .env to run indexing")
    enable_logging_with_config(settings)
    reporter = create_progress_reporter(ReporterType(args.reporter))
    try:
        asyncio.run(build_index(pipeline, pd.DataFrame(documents), run_id, reporter))
    finally:
        reporter.stop()


if __name__ == "__main__":
    main()
