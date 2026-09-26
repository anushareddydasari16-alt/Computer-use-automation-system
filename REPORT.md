# Computer-Use Automation System Report

## 1. Architecture

The system is designed around one main separation: the LLM is used to discover a workflow, while production replay executes a saved workflow without asking the LLM what to do.

During discovery, the user supplies a natural-language goal and target URL. A Groq-hosted LLM receives the current browser state and chooses one typed action at a time. The Playwright surface performs the action against the live synthetic banking application. The loop continues until the goal is completed or a stopping condition such as maximum steps, timeout, or a dead-end is reached.

After a successful discovery, the executed steps are compiled into a reusable capability artifact. Literal input values are replaced with parameters so the workflow can be reused for other members.

Replay is intentionally separate from discovery. `ReplayEngine` loads an artifact, substitutes runtime parameters, executes the saved actions in order, verifies checkpoints, collects outputs, and returns a structured result. It has no LLM planner dependency.

The system is divided into small layers: `agent` for discovery, `surface` for UI interaction, `artifact` for capability creation, `replay` for deterministic execution, `safety` for policy and redaction, `evidence` for logs, and `handoff` for human intervention.

I chose a single-process implementation because it keeps the complete vertical slice easy to understand and test. A production system would likely separate browser sessions, orchestration, and durable storage, but that infrastructure was not necessary to demonstrate the core design.

## 2. Artifact schema

The capability artifact is a typed, serializable, and versioned Pydantic model. It is designed as a callable contract rather than a raw transcript of the discovery conversation.

The artifact records the capability name and description, schema version, capability version, target surface and origin, typed inputs, typed outputs, ordered actions, checkpoints, and the final success condition.

Each browser action stores its action type, value if needed, risk level, reason, timeout, and target information. Targets can use role, accessible name, visible text, form name, or CSS. Important targets also contain a `robustness_note` explaining why the chosen locator should remain stable during replay.

For the main capability, discovery starts with member `10001`, but the compiler replaces the literal value with `{{member_id}}`. This makes the same artifact reusable for other members.

The balance extraction was also normalized. Instead of storing the dollar value seen during discovery, the final artifact targets the balance cell in the row containing `Savings`. This prevents replay from depending on the original member's balance.

The main artifact, `lookup_savings_balance.v1.json`, accepts `member_id` as a string and returns `savings_balance` as a string. Schema and capability versions make later changes reviewable rather than silently replacing behavior.

## 3. Determinism & error handling

Replay follows the saved artifact in a fixed order and does not use the LLM for decisions. Runtime values are substituted into saved steps, each action is policy checked, the action is executed through the surface layer, and checkpoints are verified before continuing.

A normal replay with member `30003` returns `$5520.75`. The CLI also reports `LLM decision calls: 0`.

The result contract separates runtime conditions instead of treating every non-happy path as an exception.

An expected business outcome is returned when the application behaves correctly but the requested record does not exist. Member `99999` returns `business_outcome = member_not_found`.

A recoverable condition is handled with predefined deterministic behavior. Member `80008` produces a temporary `Processing Request` screen. Replay recognizes the state, clicks the known `Continue` control, checks that the resulting URL is still allowed by policy, records the recovery, and continues successfully.

A hard failure stops the workflow. Member `70007` produces `Permission Denied`. The returned failure records the failed step, expected state, observed state, and a clear message. A screenshot is also stored as debugging evidence.

Playwright timeouts have a bounded one-time retry path. The system does not use an open-ended recovery loop or ask the LLM to improvise during replay.

Checkpoints are used after important transitions so replay does not assume a click or form submission succeeded. If the expected text or URL is not reached, replay stops rather than continuing blindly.

## 4. Heterogeneity & multi-tenant

The current implementation uses a web application and Playwright, but browser-specific operations are isolated behind a `Surface` abstraction. Discovery and replay interact with operations such as open, observe, act, screenshot, and close instead of depending directly on Playwright throughout the system.

A future desktop implementation could provide another surface adapter using an accessibility API, Windows UI Automation, screenshots, OCR, or coordinate-based interaction while keeping the higher-level action, artifact, replay, safety, and evidence contracts similar.

The current target strategy favors semantic information such as roles, labels, form names, visible text, and constrained CSS instead of screen coordinates. This is appropriate for the implemented web surface, although a real legacy or desktop system may require additional visual or accessibility-based targeting.

For multi-tenant use, I would keep a reviewed base capability for a vendor application and apply small version- or tenant-specific overrides for differences such as route prefixes, branding text, or target descriptions. Safety rules would not be weakened by an override.

Repeated checkpoint or target failures would be treated as drift signals requiring review rather than allowing automation to guess. Full tenant overlay resolution and desktop execution are design extensions only; they are not implemented in this take-home.

## 5. Escalation & handoff

The project implements a real same-session human handoff for an irreversible action.

The `open_savings_account` capability performs the safe preparation steps automatically. The final `Create Account` action is marked irreversible. The safety policy does not allow automation to perform it directly and instead routes the step to the handoff controller.

The intervention request records the capability, goal, current step, reason, current URL, and screenshot. Automation is paused and control ownership is changed from automation to the human.

The same headed Chromium session remains open. The human reviews the account details and manually clicks `Create Account`. The human action is recorded, an after screenshot is captured, and control is then returned to automation. Replay re-observes the existing session and verifies the confirmation checkpoint.

The command line is used as the minimal operator interface. This proves the control-transfer seam without building a full co-browsing product.

Discovery also detects stopping conditions such as timeout, maximum steps, and dead-end states. In this vertical slice those conditions stop with structured evidence. A production extension would route those discovery stops through the same operator intervention mechanism.

## 6. Safety

Safety rules are configured in `config/policy.json` rather than being hidden inside prompts.

The configuration explicitly defines allowed origins, allowed routes, allowed action types, and behavior for safe, reversible, and irreversible actions.

Actions are checked before execution. For automated actions that can change application state or location, replay observes the resulting page and verifies that the URL is still inside the route allowlist. The deterministic processing-screen recovery performs the same post-action URL check.

Irreversible actions require human control rather than automatic execution.

Evidence is passed through a redaction layer before it is written. Sensitive dictionary keys such as passwords, authorization values, tokens, and API keys are redacted, and SSN-like values are also removed from text.

The real Groq API key is stored only in the local `.env` file, which is excluded from Git. `.env.example` contains configuration names but no secret.

The banking application uses synthetic records, which avoids using real regulated customer information.

The main limitation is that redaction is rule-based and the current environment is a local demonstration. A production system would require stronger data classification, encrypted evidence storage, authentication, access control, retention policies, and auditing.

## 7. Cuts

I intentionally kept the project as a small complete vertical slice instead of adding production infrastructure.

I did not build a native desktop adapter, production multi-tenant capability registry, durable workflow database, distributed execution queue, remote operator console, automatic artifact repair, or unrestricted LLM fallback during replay.

The current observation system uses browser-visible text and control metadata rather than a full screenshot-based vision pipeline. This works for the demonstrated web application but does not represent every legacy application surface.

The next technical extension would be a second `Surface` implementation using accessibility and visual information so the same artifact and replay architecture could operate when useful DOM information is unavailable.

For production use I would also replace local evidence storage with encrypted durable storage, add authenticated operator control, capability approval/version management, stronger runtime input validation, and monitoring for repeated checkpoint failures.

These cuts were deliberate. The project focuses on the required complete path: natural-language goal, genuine LLM-driven discovery, typed reusable artifact, deterministic replay, structured runtime outcomes, safety enforcement, evidence, and same-session human handoff.