"""
End-to-end integration test for the full pipeline:
  CSV input -> clarifying questions -> narrative generation ->
  figure verification -> PPTX render

Three scenarios:
  1. Clean CSV — all figures reconcile
  2. CSV with a deliberately wrong figure — verification should flag it
  3. Edge cases — empty column, text where number expected
"""
import io
import sys
import os
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
import numpy as np

from app.services.ingest.csv_adapter import CsvAdapter
from app.services.ingest.quality_checker import run_quality_checks
from app.services.ingest.schema_detector import detect_schema
from app.services.questions.generator import generate_questions
from app.services.questions.parser import parse_answers
from app.services.narratives.angle_detector import detect_angles
from app.services.narratives.template_engine import generate_narratives, compute_confidence
from app.services.narratives.assumption_extractor import extract_assumptions
from app.services.verify.figure_extractor import extract_figures
from app.services.verify.reconciliation_checks import run_all_checks
from app.services.verify.figure_tracer import trace_figures
from app.services.render.pptx_builder import build_pptx, RenderContext, VerificationGateError


def make_csv_bytes(csv_text: str) -> io.BytesIO:
    return io.BytesIO(csv_text.encode("utf-8"))


# ── Scenario 1: Clean CSV ───────────────────────────────────────────

CLEAN_CSV = """\
Date,Region,Revenue,Costs,Profit
2024-01-01,North,10000,6000,4000
2024-02-01,South,12000,7000,5000
2024-03-01,East,11000,6500,4500
2024-04-01,West,13000,7500,5500
2024-05-01,North,14000,8000,6000
2024-06-01,South,15000,8500,6500
2024-07-01,East,16000,9000,7000
2024-08-01,West,17000,9500,7500
2024-09-01,North,18000,10000,8000
2024-10-01,South,19000,10500,8500
2024-11-01,East,20000,11000,9000
2024-12-01,West,21000,11500,9500
"""


def run_scenario_1():
    print("=" * 70)
    print("SCENARIO 1: Clean CSV — all figures should reconcile")
    print("=" * 70)
    results = {"stage": {}, "passed": True, "errors": []}

    # Stage 1: INGEST
    try:
        adapter = CsvAdapter()
        df = adapter.parse(make_csv_bytes(CLEAN_CSV))
        schema = adapter.detect_schema(df)
        quality = run_quality_checks(df)

        results["stage"]["ingest"] = {
            "status": "OK",
            "rows": len(df),
            "cols": len(df.columns),
            "schema_keys": list(schema.keys()),
            "quality_status": quality["status"],
            "quality_issues": len(quality["quality_issues"]),
        }
        print(f"  INGEST: {len(df)} rows, {len(df.columns)} cols, quality={quality['status']}")
        for issue in quality["quality_issues"]:
            print(f"    Issue: {issue['description']} (severity={issue['severity']})")
    except Exception as e:
        results["stage"]["ingest"] = {"status": "FAIL", "error": str(e)}
        results["passed"] = False
        results["errors"].append(f"INGEST: {e}")
        traceback.print_exc()
        return results

    # Stage 2: QUESTIONS
    try:
        # schema_detector returns {col_name: {type, nullability, cardinality}}
        # but generator expects same format
        questions = generate_questions(schema, {
            "issues": quality["quality_issues"],
            "total_rows": len(df),
        })

        # Simulate user answering questions
        answers = []
        for q in questions:
            if "headline" in q["template"].lower():
                answers.append({"question_id": q["id"], "text": "Revenue"})
            elif "audience" in q["template"].lower():
                answers.append({"question_id": q["id"], "text": "Board of Directors"})
            elif "time period" in q["template"].lower():
                answers.append({"question_id": q["id"], "text": "Year-over-Year"})
            elif "key message" in q["template"].lower():
                answers.append({"question_id": q["id"], "text": "Growth Story"})
            else:
                answers.append({"question_id": q["id"], "text": "skip"})

        parsed = parse_answers(questions, answers)

        results["stage"]["questions"] = {
            "status": "OK",
            "question_count": len(questions),
            "answered": len(answers),
            "ready_to_generate": parsed["ready_to_generate"],
        }
        print(f"  QUESTIONS: {len(questions)} questions, ready={parsed['ready_to_generate']}")
    except Exception as e:
        results["stage"]["questions"] = {"status": "FAIL", "error": str(e)}
        results["passed"] = False
        results["errors"].append(f"QUESTIONS: {e}")
        traceback.print_exc()
        return results

    # Stage 3: NARRATIVES
    try:
        # Need schema in "columns" format for angle_detector
        schema_for_angles = {
            "columns": [
                {"name": col, "type": info["type"]}
                for col, info in schema.items()
            ]
        }

        # Parse dates for angle detection
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
        elif "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

        angles = detect_angles(df, schema_for_angles)
        narratives = generate_narratives(angles, parsed["parsed"], schema_for_angles, df)
        assumptions = extract_assumptions(df, angles, narratives, parsed["parsed"])

        # Compute confidence for each narrative
        for narr in narratives:
            angle = next((a for a in angles if a["id"] == narr.get("angle_id")), None)
            if angle:
                narr["confidence"] = compute_confidence(df, angle, parsed["parsed"])
            else:
                narr["confidence"] = 0.5

        results["stage"]["narratives"] = {
            "status": "OK",
            "angles_detected": len(angles),
            "angle_types": [a["type"] for a in angles],
            "narratives_generated": len(narratives),
            "assumptions_count": len(assumptions),
        }
        print(f"  NARRATIVES: {len(angles)} angles {[a['type'] for a in angles]}, "
              f"{len(narratives)} narratives, {len(assumptions)} assumptions")
        for narr in narratives:
            print(f"    Narrative ({narr['story_angle']}): {narr['narrative_text'][:100]}...")
    except Exception as e:
        results["stage"]["narratives"] = {"status": "FAIL", "error": str(e)}
        results["passed"] = False
        results["errors"].append(f"NARRATIVES: {e}")
        traceback.print_exc()
        return results

    # Stage 4: VERIFY
    try:
        selected_narrative = narratives[0]
        narrative_text = selected_narrative["narrative_text"]

        figures = extract_figures(narrative_text)
        checks = run_all_checks(figures, df, narrative_text, schema_for_angles)
        traces = trace_figures(figures, df, schema_for_angles)

        check_statuses = {k: v["status"] for k, v in checks.items()}
        all_passed = all(v["status"] == "pass" for v in checks.values())
        mismatch_count = sum(1 for t in traces if t["match_status"] == "mismatch")

        results["stage"]["verify"] = {
            "status": "OK",
            "figures_extracted": len(figures),
            "check_results": check_statuses,
            "all_checks_passed": all_passed,
            "trace_mismatches": mismatch_count,
        }
        print(f"  VERIFY: {len(figures)} figures extracted")
        print(f"    Checks: {check_statuses}")
        print(f"    All passed: {all_passed}")
        for fig, trace in zip(figures, traces):
            print(f"    Figure '{fig['value']}' -> {trace['match_status']} "
                  f"({trace['formula']}, variance={trace['variance_pct']:.2f}%)")
    except Exception as e:
        results["stage"]["verify"] = {"status": "FAIL", "error": str(e)}
        results["passed"] = False
        results["errors"].append(f"VERIFY: {e}")
        traceback.print_exc()
        return results

    # Stage 5: RENDER
    try:
        recon_summary = {
            "total_checks": 5,
            "passed_count": sum(1 for v in checks.values() if v["status"] == "pass"),
            "failed_count": sum(1 for v in checks.values() if v["status"] == "fail"),
            "dismissed_count": 0,
        }

        qa_pairs = []
        for q, a in zip(questions, answers):
            qa_pairs.append({"question": q["template"], "answer": a["text"]})

        ctx = RenderContext(
            deck_name="Q4 Revenue Analysis",
            data_source_filename="clean_data.csv",
            narrative_text=selected_narrative["narrative_text"],
            narrative_confidence=selected_narrative.get("confidence", 0.5),
            story_angle=selected_narrative["story_angle"],
            viz_recommendation=selected_narrative.get("viz_recommendation"),
            assumptions=assumptions,
            questions_and_answers=qa_pairs,
            quality_notes=[{"severity": "info", "description": d["description"]}
                           for d in quality["quality_issues"]],
            reconciliation_summary=recon_summary,
            verified_at="2024-12-21T10:00:00Z",
        )

        pptx_bytes = build_pptx(ctx)

        results["stage"]["render"] = {
            "status": "OK",
            "pptx_size_bytes": len(pptx_bytes),
            "pptx_valid": len(pptx_bytes) > 1000,
        }
        print(f"  RENDER: PPTX generated, {len(pptx_bytes)} bytes")

        # Save for manual inspection
        out_path = os.path.join(os.path.dirname(__file__), "scenario1_output.pptx")
        with open(out_path, "wb") as f:
            f.write(pptx_bytes)
        print(f"    Saved to {out_path}")

    except Exception as e:
        results["stage"]["render"] = {"status": "FAIL", "error": str(e)}
        results["passed"] = False
        results["errors"].append(f"RENDER: {e}")
        traceback.print_exc()

    return results


# ── Scenario 2: Narrative with wrong figure ─────────────────────────

def run_scenario_2():
    """Generate narratives from clean data, then simulate a user editing
    a figure to a wrong value.  Verification should catch the mismatch
    and the service-layer render gate should block PPTX generation."""
    print("\n" + "=" * 70)
    print("SCENARIO 2: Wrong figure in narrative — expect verification to block render")
    print("=" * 70)
    results = {"stage": {}, "passed": True, "errors": []}

    # Stage 1: INGEST — use the same clean CSV
    try:
        adapter = CsvAdapter()
        df = adapter.parse(make_csv_bytes(CLEAN_CSV))
        schema = detect_schema(df)
        quality = run_quality_checks(df)

        results["stage"]["ingest"] = {
            "status": "OK",
            "quality_status": quality["status"],
        }
        print(f"  INGEST: {len(df)} rows, quality={quality['status']}")
    except Exception as e:
        results["stage"]["ingest"] = {"status": "FAIL", "error": str(e)}
        results["passed"] = False
        results["errors"].append(f"INGEST: {e}")
        traceback.print_exc()
        return results

    # Stage 2: QUESTIONS
    try:
        questions = generate_questions(schema, {
            "issues": quality["quality_issues"],
            "total_rows": len(df),
        })
        answers = []
        for q in questions:
            if "headline" in q["template"].lower():
                answers.append({"question_id": q["id"], "text": "Revenue"})
            elif "audience" in q["template"].lower():
                answers.append({"question_id": q["id"], "text": "Investors"})
            else:
                answers.append({"question_id": q["id"], "text": "Growth Story"})

        parsed = parse_answers(questions, answers)
        results["stage"]["questions"] = {"status": "OK"}
        print(f"  QUESTIONS: {len(questions)} questions, ready={parsed['ready_to_generate']}")
    except Exception as e:
        results["stage"]["questions"] = {"status": "FAIL", "error": str(e)}
        results["passed"] = False
        results["errors"].append(f"QUESTIONS: {e}")
        traceback.print_exc()
        return results

    # Stage 3: NARRATIVES
    try:
        schema_for_angles = {
            "columns": [
                {"name": col, "type": info["type"]}
                for col, info in schema.items()
            ]
        }
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

        angles = detect_angles(df, schema_for_angles)
        narratives = generate_narratives(angles, parsed["parsed"], schema_for_angles, df)
        assumptions = extract_assumptions(df, angles, narratives, parsed["parsed"])

        for narr in narratives:
            angle = next((a for a in angles if a["id"] == narr.get("angle_id")), None)
            if angle:
                narr["confidence"] = compute_confidence(df, angle, parsed["parsed"])
            else:
                narr["confidence"] = 0.5

        results["stage"]["narratives"] = {
            "status": "OK",
            "angles": [a["type"] for a in angles],
            "narratives_count": len(narratives),
        }
        print(f"  NARRATIVES: {len(angles)} angles {[a['type'] for a in angles]}, "
              f"{len(narratives)} narratives")
    except Exception as e:
        results["stage"]["narratives"] = {"status": "FAIL", "error": str(e)}
        results["passed"] = False
        results["errors"].append(f"NARRATIVES: {e}")
        traceback.print_exc()
        return results

    # Stage 4: VERIFY — simulate user editing a figure to a wrong value
    try:
        selected = narratives[0]
        original_text = selected["narrative_text"]

        # Inject a wrong figure: replace the first data-derived number with 99999.00
        import re
        edited_text = re.sub(r"\d{4,}\.\d{2}", "99999.00", original_text, count=1)
        print(f"  USER EDIT: replaced first data figure with 99999.00")
        print(f"    Original: {original_text[:120]}...")
        print(f"    Edited:   {edited_text[:120]}...")

        figures = extract_figures(edited_text)
        checks = run_all_checks(figures, df, edited_text, schema_for_angles)
        traces = trace_figures(figures, df, schema_for_angles)

        check_statuses = {k: v["status"] for k, v in checks.items()}
        any_failed = any(v["status"] == "fail" for v in checks.values())
        mismatch_traces = [t for t in traces if t["match_status"] == "mismatch"]

        results["stage"]["verify"] = {
            "status": "OK",
            "figures_extracted": len(figures),
            "check_results": check_statuses,
            "any_check_failed": any_failed,
            "mismatch_count": len(mismatch_traces),
            "blocking": any_failed,
        }

        print(f"  VERIFY: {len(figures)} figures extracted")
        print(f"    Checks: {check_statuses}")
        print(f"    Any failed (blocking): {any_failed}")
        for fig, trace in zip(figures, traces):
            print(f"    Figure '{fig['value']}' -> {trace['match_status']} "
                  f"({trace['formula']}, variance={trace['variance_pct']:.2f}%)")

        if not any_failed and len(mismatch_traces) == 0:
            print("  !! WARNING: No failures detected despite wrong figure in narrative")
            results["stage"]["verify"]["warning"] = "Expected blocking issue but none found"

    except Exception as e:
        results["stage"]["verify"] = {"status": "FAIL", "error": str(e)}
        results["passed"] = False
        results["errors"].append(f"VERIFY: {e}")
        traceback.print_exc()
        return results

    # Stage 5: RENDER — should be blocked by service-layer gate
    try:
        recon_summary = {
            "total_checks": 5,
            "passed_count": sum(1 for v in checks.values() if v["status"] == "pass"),
            "failed_count": sum(1 for v in checks.values() if v["status"] == "fail"),
            "dismissed_count": 0,
        }
        ctx = RenderContext(
            deck_name="Revenue Report (Wrong Figure)",
            data_source_filename="clean_data.csv",
            narrative_text=edited_text,
            narrative_confidence=selected.get("confidence", 0.5),
            story_angle=selected["story_angle"],
            viz_recommendation=selected.get("viz_recommendation"),
            assumptions=assumptions,
            reconciliation_summary=recon_summary,
            verified_at="2024-12-21T10:00:00Z",
        )
        pptx_bytes = build_pptx(ctx)
        # If we get here, the gate didn't fire
        results["stage"]["render"] = {
            "status": "OK_BUT_UNEXPECTED",
            "pptx_size_bytes": len(pptx_bytes),
            "note": "Rendered despite expected verification failure",
        }
        print(f"  RENDER: UNEXPECTED — PPTX generated ({len(pptx_bytes)} bytes), gate didn't fire")

    except VerificationGateError as e:
        print(f"  RENDER: BLOCKED by service-layer gate (as expected)")
        print(f"    {e}")
        results["stage"]["render"] = {
            "status": "BLOCKED_BY_VERIFY",
            "reason": str(e),
        }
    except Exception as e:
        results["stage"]["render"] = {"status": "FAIL", "error": str(e)}
        results["passed"] = False
        results["errors"].append(f"RENDER: {e}")
        traceback.print_exc()

    return results


# ── Scenario 3: Edge cases ──────────────────────────────────────────

EDGE_CASE_CSV = """\
Date,Region,Revenue,Costs,Notes
2024-01-01,North,10000,6000,
2024-02-01,,12000,abc,Good quarter
2024-03-01,East,,6500,Missing revenue
2024-04-01,West,13000,,
2024-05-01,North,14000,8000,Normal
"""


def run_scenario_3():
    print("\n" + "=" * 70)
    print("SCENARIO 3: Edge cases — empty column, text where number expected")
    print("=" * 70)
    results = {"stage": {}, "passed": True, "errors": []}

    # Stage 1: INGEST
    try:
        adapter = CsvAdapter()
        df = adapter.parse(make_csv_bytes(EDGE_CASE_CSV))
        schema = detect_schema(df)
        quality = run_quality_checks(df)

        results["stage"]["ingest"] = {
            "status": "OK",
            "rows": len(df),
            "cols": len(df.columns),
            "quality_status": quality["status"],
            "quality_issues_count": len(quality["quality_issues"]),
        }
        print(f"  INGEST: {len(df)} rows, {len(df.columns)} cols, quality={quality['status']}")
        for issue in quality["quality_issues"]:
            print(f"    Issue: {issue['description']} (severity={issue['severity']})")
        print(f"    Schema types: {[(k, v['type']) for k, v in schema.items()]}")
        print(f"    DataFrame dtypes:\n{df.dtypes}")
    except Exception as e:
        results["stage"]["ingest"] = {"status": "FAIL", "error": str(e)}
        results["passed"] = False
        results["errors"].append(f"INGEST: {e}")
        traceback.print_exc()
        return results

    # Stage 2: QUESTIONS
    try:
        questions = generate_questions(schema, {
            "issues": quality["quality_issues"],
            "total_rows": len(df),
        })
        answers = []
        for q in questions:
            if "headline" in q["template"].lower():
                answers.append({"question_id": q["id"], "text": "Revenue"})
            elif "audience" in q["template"].lower():
                answers.append({"question_id": q["id"], "text": "Executive Team"})
            else:
                answers.append({"question_id": q["id"], "text": "skip"})

        parsed = parse_answers(questions, answers)
        results["stage"]["questions"] = {
            "status": "OK",
            "question_count": len(questions),
            "ready_to_generate": parsed["ready_to_generate"],
        }
        print(f"  QUESTIONS: {len(questions)} questions, ready={parsed['ready_to_generate']}")
    except Exception as e:
        results["stage"]["questions"] = {"status": "FAIL", "error": str(e)}
        results["passed"] = False
        results["errors"].append(f"QUESTIONS: {e}")
        traceback.print_exc()
        return results

    # Stage 3: NARRATIVES
    try:
        schema_for_angles = {
            "columns": [
                {"name": col, "type": info["type"]}
                for col, info in schema.items()
            ]
        }

        for col in df.columns:
            if schema.get(col.lower(), {}).get("type") == "datetime" or col.lower() == "date":
                df[col] = pd.to_datetime(df[col], errors="coerce")

        angles = detect_angles(df, schema_for_angles)
        narratives = generate_narratives(angles, parsed["parsed"], schema_for_angles, df)
        assumptions = extract_assumptions(df, angles, narratives, parsed["parsed"])

        for narr in narratives:
            angle = next((a for a in angles if a["id"] == narr.get("angle_id")), None)
            if angle:
                narr["confidence"] = compute_confidence(df, angle, parsed["parsed"])
            else:
                narr["confidence"] = 0.5

        results["stage"]["narratives"] = {
            "status": "OK",
            "angles": [a["type"] for a in angles],
            "narratives_count": len(narratives),
            "assumptions_count": len(assumptions),
        }
        print(f"  NARRATIVES: {len(angles)} angles {[a['type'] for a in angles]}, "
              f"{len(narratives)} narratives, {len(assumptions)} assumptions")
        for narr in narratives:
            print(f"    Narrative ({narr['story_angle']}): {narr['narrative_text'][:120]}...")
    except Exception as e:
        results["stage"]["narratives"] = {"status": "FAIL", "error": str(e)}
        results["passed"] = False
        results["errors"].append(f"NARRATIVES: {e}")
        traceback.print_exc()
        return results

    # Stage 4: VERIFY
    try:
        selected = narratives[0]
        narrative_text = selected["narrative_text"]

        figures = extract_figures(narrative_text)
        checks = run_all_checks(figures, df, narrative_text, schema_for_angles)
        traces = trace_figures(figures, df, schema_for_angles)

        check_statuses = {k: v["status"] for k, v in checks.items()}

        results["stage"]["verify"] = {
            "status": "OK",
            "figures_extracted": len(figures),
            "check_results": check_statuses,
        }
        print(f"  VERIFY: {len(figures)} figures extracted")
        print(f"    Checks: {check_statuses}")
        for fig, trace in zip(figures, traces):
            print(f"    Figure '{fig['value']}' -> {trace['match_status']} "
                  f"({trace['formula']}, variance={trace['variance_pct']:.2f}%)")
    except Exception as e:
        results["stage"]["verify"] = {"status": "FAIL", "error": str(e)}
        results["passed"] = False
        results["errors"].append(f"VERIFY: {e}")
        traceback.print_exc()
        return results

    # Stage 5: RENDER
    try:
        recon_summary = {
            "total_checks": 5,
            "passed_count": sum(1 for v in checks.values() if v["status"] == "pass"),
            "failed_count": sum(1 for v in checks.values() if v["status"] == "fail"),
            "dismissed_count": 0,
        }

        qa_pairs = []
        for q, a in zip(questions, answers):
            qa_pairs.append({"question": q["template"], "answer": a["text"]})

        ctx = RenderContext(
            deck_name="Edge Case Test",
            data_source_filename="edge_case.csv",
            narrative_text=selected["narrative_text"],
            narrative_confidence=selected.get("confidence", 0.5),
            story_angle=selected["story_angle"],
            viz_recommendation=selected.get("viz_recommendation"),
            assumptions=assumptions,
            questions_and_answers=qa_pairs,
            quality_notes=[{"severity": issue["severity"], "description": issue["description"]}
                           for issue in quality["quality_issues"]],
            reconciliation_summary=recon_summary,
            verified_at="2024-12-21T10:00:00Z",
        )
        pptx_bytes = build_pptx(ctx)

        results["stage"]["render"] = {
            "status": "OK",
            "pptx_size_bytes": len(pptx_bytes),
        }
        print(f"  RENDER: PPTX generated, {len(pptx_bytes)} bytes")

        out_path = os.path.join(os.path.dirname(__file__), "scenario3_output.pptx")
        with open(out_path, "wb") as f:
            f.write(pptx_bytes)
        print(f"    Saved to {out_path}")

    except Exception as e:
        results["stage"]["render"] = {"status": "FAIL", "error": str(e)}
        results["passed"] = False
        results["errors"].append(f"RENDER: {e}")
        traceback.print_exc()

    return results


# ── Main ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "#" * 70)
    print("  FULL PIPELINE INTEGRATION TEST")
    print("#" * 70 + "\n")

    r1 = run_scenario_1()
    r2 = run_scenario_2()
    r3 = run_scenario_3()

    print("\n" + "#" * 70)
    print("  SUMMARY")
    print("#" * 70)

    for label, r in [("Scenario 1 (Clean)", r1), ("Scenario 2 (Wrong Figure)", r2), ("Scenario 3 (Edge Cases)", r3)]:
        stages_ok = [k for k, v in r["stage"].items() if v.get("status") in ("OK", "BLOCKED_BY_VERIFY")]
        stages_fail = [k for k, v in r["stage"].items() if v.get("status") == "FAIL"]
        stages_warn = [k for k, v in r["stage"].items() if v.get("status") == "OK_BUT_UNEXPECTED" or v.get("warning")]

        icon = "PASS" if not stages_fail else "FAIL"
        if stages_warn:
            icon = "WARN"
        print(f"\n  {icon}: {label}")
        print(f"    Stages OK: {stages_ok}")
        if stages_fail:
            print(f"    Stages FAILED: {stages_fail}")
        if stages_warn:
            print(f"    Stages WARNING: {stages_warn}")
        for e in r.get("errors", []):
            print(f"    Error: {e}")

        # Print any warnings from verify stage
        verify = r["stage"].get("verify", {})
        if verify.get("warning"):
            print(f"    !! {verify['warning']}")
        if verify.get("status") == "BLOCKED_BY_VERIFY":
            print(f"    (Render correctly blocked by failed verification)")

    print()
