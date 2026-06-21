# Deferred Work

## Deferred from: code review of 1-4-data-validation-review-sign-off (2026-06-19)

- Content-Type header forced to JSON on all requests in `apiFetch` — will break future FormData/multipart uploads. Only set header when body is JSON.
- File read into memory before size check in ingest endpoint (`ingest.py:44-48`) — large uploads buffered before rejection. Consider chunked read or upstream body limit.
- No 404 catch-all route in React Router — navigating to undefined paths renders blank page.
- `apiFetch` assumes all success responses have JSON body — a future 204 No Content response would throw.

## Deferred from: code review of 2-4-narrative-picker-screen (2026-06-20)

- `updated_at` column on `deck_selections` has no DB-level ON UPDATE trigger — ORM `onupdate` is app-side only. If any direct SQL update bypasses SQLAlchemy, `updated_at` will be stale.
- No authorization check on deck ownership in select-narrative and qa-summary endpoints — auth is explicitly deferred across all stories per project architecture decisions.

## Deferred from: code review of 3-1-figure-extraction-reconciliation-checks-service (2026-06-20)

- No idempotency on POST /verify — repeated calls create duplicate ReconciliationReport rows. No unique constraint on (deck_id, narrative_id) and no check for recent existing report.
- No rate limiting on verify endpoint — expensive CPU-bound work (combinatorial checks, DataFrame loading, numpy) can be triggered without throttle.
- Check A (Sum-of-Parts) returns vacuous pass when no sum relationship found at all — by spec design, but fabricated totals that aren't close to any combination pass silently.
- `infer_datetime_format` parameter deprecated/removed in pandas 2.x in data_loader.py — date columns may silently fail to convert, causing Check C/D/E to skip time-series analysis.

## Deferred from: code review of 3-3-fix-dismiss-re-verify-flow (2026-06-21)

- `handleExcludeRows` hardcodes `check_a` and sends empty `row_ids` — placeholder from Story 3.2, not introduced by this story.
- Backend `CheckResult.status` is `str` vs frontend `Literal["pass"|"fail"|"dismissed"]` — pre-existing inconsistency from Story 3.1.
- Edit narrative navigation doesn't pass state to auto-open detail panel — downstream screen behavior, not this story's scope.

## Deferred from: code review of 3-2-verification-screen-figures-checks-tabs (2026-06-21)

- POST used for readonly verify mode — re-runs full verification pipeline instead of fetching existing report. Pre-existing API design issue.
- No body scroll lock when DismissModal or SourceRowsPanel is open — background scrolls behind overlays on mobile/trackpad. UX polish.
- `CheckResult.status` backend schema is `str` not `Literal` — accepts any string, no validation against expected values.
- Assumption re-rejection not blocked — already-rejected assumptions can be re-rejected, appending duplicate entries to actions array.

## Deferred from: code review of 4-1-pptx-rendering-service-deck-download (2026-06-21)

- No access control / auth on render and download endpoints — pre-existing PLACEHOLDER_USER_ID pattern across all endpoints.
- Download anchor-click bypasses future auth headers — both RenderScreen and VerificationScreen use anchor element instead of apiFetch+blob for downloads, will break when auth is added.
- No composite index on (deck_id, rendered_at) for download ORDER BY — adequate at current scale, degrades with many renders per deck.
- Q&A/assumptions slides overflow with large datasets — all items render into single fixed-height text frame with no pagination.

## Deferred from: code review of 4-1-pptx-rendering-service-deck-download Round 2 (2026-06-21)

- assumptions_json model typed as dict|None but used as list[dict] — Narrative model type annotation misleading, runtime works because actual data is always list[dict].
- answers_json model typed as dict|None but _merge_qa expects list — QuestionSession model same issue as above.
- S3-DB transaction inconsistency — if upload_file succeeds but db.commit() fails, orphaned file in S3. No transactional coordination between S3 and database.
- Audit log failure silently swallowed — try/except around AuditLog creation. Pre-existing pattern from verify.py Story 3.1+.
- No performance validation of < 1 second rendering target — AC3 performance requirement unvalidated, no timing tests.
- Frontend download anchor-click bypasses auth headers — pre-existing pattern, will break when auth is added.
- Large viz_recommendation list creates unbounded slides — no cap on data slide count from JSONB data.
- handleApplyFix/handleAcknowledge re-throw errors without catch — unhandled promise rejections in VerificationScreen, pre-existing.

## Deferred from: code review of 1-3-excel-json-ingestion-adapters (2026-06-21)

- quality_issues vs issues key mismatch — quality_checker returns "quality_issues" but validate_acknowledge reads "issues", always counting 0 acknowledged issues. Pre-existing from Story 1.2/1.4.
- File uploaded to S3 before parse validation — orphaned files on parse failure. Pre-existing from Story 1.2.
- No ValidationReport Pydantic model — quality_report typed as bare dict, no schema enforcement. Pre-existing from Story 1.2.
- Empty DataFrame accepted as CLEAN with no warning — empty files produce CLEAN status. Pre-existing design decision.
- File contents held in memory twice (~200MB at 100MB limit) — pre-existing from Story 1.2.
- ZeroDivisionError in _check_duplicates on empty DataFrame — divides by len(df) which is 0. Pre-existing from Story 1.2.
