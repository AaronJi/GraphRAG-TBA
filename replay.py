"""Compare the saved Direct and TBA choices using the historical index and skills."""

from collections import defaultdict
import json

from data import INPUT, OUTPUT, read_jsonl
from index import TAU
from metrics import compare, print_comparison
from query import question, read_reports, top_skills


def main():
    cases = read_jsonl(INPUT / "evaluation_cases.jsonl")
    report_ids = {int(report["community"]) for report in read_reports(OUTPUT)}
    associations = read_jsonl(OUTPUT / "associations.jsonl")
    audit = json.loads((OUTPUT / "association_summary.json").read_text(encoding="utf-8"))
    if (len({row["id"] for row in associations}) != len(associations) or len(associations) != audit["candidate_tuples"]
            or sum(row["score"] >= TAU for row in associations) != audit["accepted_tuples"]):
        raise ValueError("Association counts differ from the historical run")

    by_case = defaultdict(list)
    for skill in read_jsonl(OUTPUT / "skills.jsonl"):
        by_case[skill["idx"]].append(skill)
    mappings = {case["idx"]: question(case)[1] for case in cases}
    if by_case.keys() != mappings.keys() or any(
        len(skills) != len(report_ids) or {skill["community"] for skill in skills} != report_ids
        for skills in by_case.values()
    ):
        raise ValueError("Saved skills do not cover every case and level-0 community")

    predictions = read_jsonl(OUTPUT / "predictions.jsonl")
    for row in predictions:
        mapping = mappings[row["idx"]]
        selected = top_skills(by_case[row["idx"]]) if row["method"] == "TBA" else []
        if (row["option_mapping"] != mapping or row["choice"] != mapping[row["choice_letter"]]
                or row["selected_skills"] != selected):
            raise ValueError("Saved prediction differs from the replayed A/B order or skill selection")

    results = compare(cases, predictions)
    recorded = json.loads((OUTPUT / "rate_summary.json").read_text(encoding="utf-8"))
    if results != [{key: row[key] for key in result} for result, row in zip(results, recorded, strict=True)]:
        raise ValueError("Recomputed rates differ from the historical run")
    print_comparison(results)


if __name__ == "__main__":
    main()
