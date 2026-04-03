# Workflow: Operational Risk Controls Analysis

## 3-step control assessment: 5Ws decomposition, Design Effectiveness, Operational Effectiveness.

## Inputs:
- control_description: Full text of the control to be analysed (required)
- control_id: Control identifier e.g. CTRL0048 (optional)
- control_type: Preventive / Detective / Corrective (optional)
- control_owner: Role or team responsible (optional)
- risk_domain: e.g. Operational Risk, Credit Risk, Cyber (optional)

## Step 1 — 5Ws Analysis

You are a senior operational risk analyst. Decompose the control into the 5Ws framework. Extract each dimension. If any dimension is missing or ambiguous, flag it explicitly.

WHO: Who performs this control? Who is accountable? Who is the recipient?
WHAT: What specific action is taken? What evidence is produced?
WHERE: What system, process, or location does this control operate in?
WHEN: What is the frequency? Triggered by event or time-based?
WHY: What risk does this control mitigate? What is the objective?

Rate the description quality: COMPLETE / PARTIAL / INSUFFICIENT.
Recommend specific improvements if PARTIAL or INSUFFICIENT.
Respond with clear headers for each dimension.

## Step 2 — Design Effectiveness

Using the 5Ws output from Step 1, assess DESIGN EFFECTIVENESS.
Design effectiveness: if executed as written, would this control adequately mitigate the risk?

Evaluate across:
1. RISK ALIGNMENT: Does the control directly address the stated risk?
2. COVERAGE: Are there gaps in timing, scope, or population?
3. EVIDENCE: Is the evidence specified sufficient to demonstrate the control operated?
4. ESCALATION: Is there a clear escalation path for exceptions or failures?
5. CONTROL TYPE: Is the control type (Preventive/Detective/Corrective) appropriate?

Rating: EFFECTIVE / PARTIALLY EFFECTIVE / INEFFECTIVE
List specific design gaps as numbered findings. Recommend concrete improvements for each gap.

## Step 3 — Operational Effectiveness

Using Step 1 and Step 2 outputs, assess OPERATIONAL EFFECTIVENESS.
Operational effectiveness: is the control executable and auditable in practice?

Evaluate across:
1. EXECUTABILITY: Can this control realistically be performed as described?
2. OWNERSHIP CLARITY: Is the performing role unambiguous (named role, not vague team)?
3. FREQUENCY FEASIBILITY: Is the frequency realistic to catch the risk in time?
4. EVIDENCE AUDITABILITY: Can an auditor test this control from the described evidence?
5. EXCEPTION HANDLING: Does the description address what happens when the control fails?

Rating: EFFECTIVE / PARTIALLY EFFECTIVE / INEFFECTIVE
Provide OVERALL RATING combining design and operational scores.
Produce a prioritised remediation plan with HIGH / MEDIUM / LOW priority actions.

## Notes for Agent
- Steps must run in strict sequence: Step 1 → Step 2 → Step 3. Do NOT combine steps.
- Each step is LLM synthesis only — no tool calls needed.
- Begin each step with the header: **Step N of 3 — [step name]**
- Pass the full output of each step as context into the next step.
- Wrap final output in canvas mode.
