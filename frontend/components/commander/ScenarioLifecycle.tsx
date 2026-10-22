"use client";

import React, { useCallback, useEffect, useState } from "react";
import { commanderApi } from "@/lib/api";
import { Button } from "@/components/common/Button";

type ScenarioView = {
  id: string;
  status: string;
  expected_revision: string;
  latest_approval_id: string | null;
  window_start: string | null;
  window_end: string | null;
};

const show = (value: unknown) => value === null || value === undefined ? "Unavailable" : String(value);
const utc = (local: string) => local ? new Date(local).toISOString() : undefined;

export function ScenarioLifecycle({ scenarioId, onChanged }: { scenarioId: string; onChanged: () => Promise<void> }) {
  const [scenario, setScenario] = useState<ScenarioView | null>(null);
  const [comparison, setComparison] = useState<Record<string, any> | null>(null);
  const [outcome, setOutcome] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [result, setResult] = useState<"IMPLEMENTED" | "NOT_IMPLEMENTED">("IMPLEMENTED");
  const [effectiveAt, setEffectiveAt] = useState("");
  const [externalReference, setExternalReference] = useState("");
  const [reasonCode, setReasonCode] = useState("OPERATIONAL_CHANGE");
  const [attested, setAttested] = useState(false);
  const [replayClock, setReplayClock] = useState("");
  const [observationClock, setObservationClock] = useState("");
  const [reviewNote, setReviewNote] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [detail, compare, observed] = await Promise.all([
        commanderApi.getScenario(scenarioId),
        commanderApi.getScenarioComparison(scenarioId),
        commanderApi.getScenarioOutcome(scenarioId),
      ]);
      setScenario(detail);
      setComparison(compare);
      setOutcome(observed);
    } catch (err: any) {
      setError(err.message || "Scenario workflow is unavailable");
    } finally {
      setLoading(false);
    }
  }, [scenarioId]);

  useEffect(() => { void refresh(); }, [refresh]);

  async function perform(action: () => Promise<any>, success: string) {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const response = await action();
      setMessage(response?.reason_code ? `${success} ${response.reason_code}.` : success);
      await refresh();
      await onChanged();
    } catch (err: any) {
      setError(err.message || "Action failed");
    } finally {
      setBusy(false);
    }
  }

  function record(event: React.FormEvent) {
    event.preventDefault();
    if (!scenario?.latest_approval_id) { setError("Approval record unavailable; refresh before recording action."); return; }
    if (result === "IMPLEMENTED") {
      if (!attested || !effectiveAt || !externalReference.trim()) {
        setError("Confirm the exact approved assignments, effective time, and external reference.");
        return;
      }
      void perform(() => commanderApi.recordScenarioImplementation(scenarioId, {
        approval_id: scenario.latest_approval_id!,
        expected_revision: scenario.expected_revision,
        result,
        effective_at: utc(effectiveAt),
        external_reference: externalReference.trim(),
        confirm_approved_assignments: true,
        ...(replayClock ? { synthetic_replay_clock: utc(replayClock) } : {}),
      }), "External implementation recorded. Observation is pending until evidence is complete.");
    } else {
      void perform(() => commanderApi.recordScenarioImplementation(scenarioId, {
        approval_id: scenario.latest_approval_id!,
        expected_revision: scenario.expected_revision,
        result,
        reason_code: reasonCode,
      }), "Decision not to implement recorded.");
    }
  }

  const metricRows = comparison ? Object.entries(comparison).flatMap(([group, values]) =>
    ["workload", "night_duty", "recovery"].includes(group) && values && typeof values === "object"
      ? Object.entries(values).filter(([, value]) => value && typeof value === "object" && "current" in value).map(([name, value]) => ({ group, name, value: value as any }))
      : []
  ) : [];

  if (loading && !scenario) return <p className="text-xs text-[#677766]">Loading governed comparison and workflow…</p>;

  return (
    <section className="min-w-0 space-y-4 rounded-xl border border-[#CFDDCE] bg-white p-3 sm:p-4" aria-label="Scenario comparison and outcome workflow">
      <div>
        <h4 className="font-serif text-sm font-bold text-[#182417]">Governed comparison and external action</h4>
        <p className="text-xs text-[#677766]">Proposal: {show(scenario?.status)} · Planning window: {show(scenario?.window_start)} to {show(scenario?.window_end)}</p>
      </div>
      {error && <p role="alert" className="rounded-lg bg-red-50 p-2 text-xs text-red-800">{error}</p>}
      {message && <p role="status" className="rounded-lg bg-green-50 p-2 text-xs text-green-800">{message}</p>}
      {metricRows.length > 0 ? (
        <div className="max-w-full overflow-x-auto">
          <table className="w-full min-w-[460px] text-left text-xs">
            <thead><tr className="border-b border-[#CFDDCE]"><th className="py-2">Indicator</th><th>Current</th><th>Proposed</th><th>Difference</th></tr></thead>
            <tbody>{metricRows.map(({ group, name, value }) => <tr key={`${group}-${name}`} className="border-b border-[#E4ECE3]">
              <th className="py-2 font-medium">{name.replaceAll("_", " ")}</th>
              <td>{show(value.current)}</td><td>{show(value.proposed)}</td><td>{show(value.difference)} {value.unit || ""}</td>
            </tr>)}</tbody>
          </table>
        </div>
      ) : <p className="text-xs text-[#677766]">Comparison unavailable; do not infer a projected improvement.</p>}
      <p className="text-xs text-[#677766]">Projected WSI: {show(comparison?.wsi?.projected_wsi_status)}. Approval never changes the published roster.</p>

      {scenario?.status === "APPROVED" && (
        <form onSubmit={record} className="space-y-3 rounded-lg border border-[#CFDDCE] bg-[#FAF9F5] p-3">
          <h5 className="font-semibold text-sm">Record what happened outside PRAHARI</h5>
          <div className="flex flex-wrap gap-4 text-xs">
            <label><input type="radio" checked={result === "IMPLEMENTED"} onChange={() => setResult("IMPLEMENTED")} /> Implemented</label>
            <label><input type="radio" checked={result === "NOT_IMPLEMENTED"} onChange={() => setResult("NOT_IMPLEMENTED")} /> Not implemented</label>
          </div>
          {result === "IMPLEMENTED" ? <>
            <label className="block text-xs font-medium">Actual effective time (your local time)
              <input required type="datetime-local" value={effectiveAt} onChange={(e) => setEffectiveAt(e.target.value)} className="mt-1 block w-full max-w-sm rounded border border-[#CFDDCE] p-2" />
            </label>
            <label className="block text-xs font-medium">External operational reference
              <input required maxLength={120} value={externalReference} onChange={(e) => setExternalReference(e.target.value)} className="mt-1 block w-full max-w-sm rounded border border-[#CFDDCE] p-2" />
            </label>
            <label className="flex items-start gap-2 text-xs"><input type="checkbox" required checked={attested} onChange={(e) => setAttested(e.target.checked)} /> I verified the actual external assignments exactly match this approved proposal. This records evidence; it does not activate a roster.</label>
            <label className="block text-xs font-medium">Synthetic demo replay clock (optional; label will be recorded)
              <input type="datetime-local" value={replayClock} onChange={(e) => setReplayClock(e.target.value)} className="mt-1 block w-full max-w-sm rounded border border-[#CFDDCE] p-2" />
            </label>
          </> : <label className="block text-xs font-medium">Operational reason
            <select value={reasonCode} onChange={(e) => setReasonCode(e.target.value)} className="mt-1 block w-full max-w-sm rounded border border-[#CFDDCE] p-2">
              <option value="OPERATIONAL_CHANGE">Operational change</option><option value="NOT_ADOPTED">Not adopted</option><option value="SOURCE_CHANGED">Source changed</option>
            </select>
          </label>}
          <Button type="submit" loading={busy} disabled={busy}>Record external action</Button>
        </form>
      )}

      <div className="space-y-2 rounded-lg border border-[#CFDDCE] p-3 text-xs">
        <h5 className="font-semibold text-sm">VERIFY · observed evidence</h5>
        <p>Implementation: {show(outcome?.implementation_status || scenario?.status)} · Workflow: {show(outcome?.workflow_status)} · Availability: {show(outcome?.availability_status)}</p>
        {outcome?.before_window && <p>Before: {outcome.before_window.start_at} to {outcome.before_window.end_at}</p>}
        {outcome?.after_window && <p>After: {outcome.after_window.start_at} to {outcome.after_window.end_at}</p>}
        {outcome?.reason_code && <p>Evidence state: {outcome.reason_code}</p>}
        {outcome?.before_metrics && <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 rounded bg-[#FAF9F5] p-2">
          <p>Duty hours before/after: {show(outcome.before_metrics.duty_hours?.affected_total)} / {show(outcome.after_metrics?.duty_hours?.affected_total)}</p>
          <p>Rest opportunity before/after: {show(outcome.before_metrics.rest?.mean_rest_hours)} / {show(outcome.after_metrics?.rest?.mean_rest_hours)} hours</p>
          <p>Required-slot coverage before/after: {show(outcome.before_metrics.required_slots?.ratio)} / {show(outcome.after_metrics?.required_slots?.ratio)}</p>
          <p>WSI evidence: {show(outcome.wsi?.status)}</p>
        </div>}
        {outcome?.interpretation && <p>{outcome.interpretation}</p>}
        {scenario?.status === "IMPLEMENTED" && outcome?.workflow_status === "PENDING" && <div className="space-y-2">
          <label className="block font-medium">Synthetic demo observation clock (only for labelled replay)
            <input type="datetime-local" value={observationClock} onChange={(e) => setObservationClock(e.target.value)} className="mt-1 block w-full max-w-sm rounded border border-[#CFDDCE] p-2" />
          </label>
          <Button type="button" size="sm" disabled={busy} loading={busy} onClick={() => void perform(() => commanderApi.observeScenarioOutcome(scenarioId, utc(observationClock)), "Observation checked.")}>Check observation</Button>
        </div>}
        {outcome?.workflow_status === "OBSERVED" && <form onSubmit={(event) => { event.preventDefault(); if (reviewNote.trim().length >= 5) void perform(() => commanderApi.reviewScenarioOutcome(scenarioId, { expected_revision: outcome.expected_revision, review_note: reviewNote.trim() }), "Human review recorded."); }} className="flex flex-col sm:flex-row gap-2">
          <input required minLength={5} maxLength={500} value={reviewNote} onChange={(e) => setReviewNote(e.target.value)} placeholder="Operational review note" className="min-w-0 flex-1 rounded border border-[#CFDDCE] p-2" />
          <Button type="submit" size="sm" loading={busy} disabled={busy}>Review observed outcome</Button>
        </form>}
      </div>
    </section>
  );
}
