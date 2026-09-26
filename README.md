
## Computer-Use Automation System

A small end-to-end computer-use automation system that discovers, records, and replays workflows in a synthetic banking application.

The system uses an LLM during **discovery** to learn how to complete a task in a browser. A successful discovery is converted into a typed, versioned capability artifact. The saved artifact can then be **replayed deterministically without using the LLM for decisions**.

The project also demonstrates:

- structured capability artifacts
- deterministic replay
- stable browser targeting
- checkpoints and output validation
- expected business outcomes
- recoverable runtime conditions
- hard failures with evidence
- configurable safety policies
- redaction of sensitive values
- same-session human handoff for irreversible actions

The target application is a local synthetic banking application built with FastAPI.


## Tech Stack

- Python 3.10+
- FastAPI
- Playwright
- Pydantic
- Groq API
- Pytest
- Jinja2



## Project Structure

```text
computer-use-automation-system/
│
├── artifacts/
│   ├── lookup_savings_balance.v1.json
│   └── open_savings_account.v1.json
│
├── config/
│   └── policy.json
│
├── demo_app/
│   ├── app.py
│   ├── members.json
│   └── templates/
│
├── evidence/
│   ├── discovery/
│   ├── handoff/
│   ├── replay-business-outcome/
│   ├── replay-hard-failure/
│   ├── replay-recovery/
│   ├── replay-success/
│   └── lookup_savings_balance.v1.json
│
├── src/
│   ├── agent/
│   ├── artifact/
│   ├── evidence/
│   ├── handoff/
│   ├── models/
│   ├── replay/
│   ├── safety/
│   ├── surface/
│   ├── cli.py
│   └── config.py
│
├── tests/
├── .env.example
├── .gitignore
├── README.md
├── REPORT.md
└── requirements.txt
```


## 1. Setup

Clone the repository and move into the project folder.

```bash
git clone <YOUR_PUBLIC_REPOSITORY_URL>
cd computer-use-automation-system
```

Create a Python virtual environment.

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the Python dependencies.

```bash
pip install -r requirements.txt
```

Install the Playwright Chromium browser.

```bash
python -m playwright install chromium
```

---

## 2. Environment Configuration

Copy `.env.example` to `.env`.

### Windows PowerShell

```powershell
Copy-Item .env.example .env
```

### macOS / Linux

```bash
cp .env.example .env
```

The example configuration is:

```env
GROQ_API_KEY=
GROQ_MODEL=openai/gpt-oss-20b
TARGET_URL=http://127.0.0.1:8000
MAX_STEPS=15
RUN_TIMEOUT_SECONDS=120
HEADLESS=false
```

Add a valid Groq API key to the local `.env` file:

```env
GROQ_API_KEY=your_key_here
```

Do not commit `.env`.

Only LLM-based discovery requires the Groq API key.

Deterministic replay does not use the LLM for decisions.

---

## 3. Start the Demo Banking Application

Open a terminal with the virtual environment activated and run:

```bash
python -m uvicorn demo_app.app:app --host 127.0.0.1 --port 8000
```

The application will be available at:

```text
http://127.0.0.1:8000
```

Keep this terminal running while using discovery or replay.

The application contains only synthetic banking data.

---

## 4. Run LLM Discovery

Open a second terminal, activate the same virtual environment, and run:

```bash
python -m src.cli discover --goal "Look up member 10001 and return the current savings balance." --target http://127.0.0.1:8000
```

During discovery, the Groq model repeatedly:

1. observes the current browser state,
2. chooses one typed action,
3. passes the action through the safety policy,
4. performs the browser action,
5. observes the updated state,
6. continues until the requested result is found or a stopping condition is reached.

A successful discovery creates a reusable artifact:

```text
artifacts/lookup_savings_balance.v1.json
```

The artifact contains typed inputs and outputs, ordered browser actions, target information, robustness notes, checkpoints, and a success condition.

A genuine discovery run is saved under:

```text
evidence/discovery/
```

---

## 5. Deterministic Replay

Replay uses the saved capability artifact and does not ask an LLM what action to perform.

For example:

```bash
python -m src.cli replay --artifact artifacts/lookup_savings_balance.v1.json --member-id 30003
```

Expected output includes:

```json
{
  "status": "success",
  "outputs": {
    "savings_balance": "$5520.75"
  },
  "recoveries": [],
  "business_outcome": null,
  "failure": null
}
```

The CLI also prints:

```text
LLM decision calls: 0
```

This demonstrates that replay follows the saved artifact rather than using the model for browser decisions.

---

## 6. Runtime Outcome Examples

The demo application contains controlled scenarios for demonstrating replay behavior.

### Successful Replay

```bash
python -m src.cli replay --artifact artifacts/lookup_savings_balance.v1.json --member-id 30003
```

Expected:

```text
status = success
savings_balance = $5520.75
```

Evidence:

```text
evidence/replay-success/
```

### Expected Business Outcome

Member `99999` does not exist.

```bash
python -m src.cli replay --artifact artifacts/lookup_savings_balance.v1.json --member-id 99999
```

Expected:

```text
status = business_outcome
business_outcome = member_not_found
```

This is treated as a valid business result rather than a system failure.

Evidence:

```text
evidence/replay-business-outcome/
```

### Recoverable Runtime Condition

Member `80008` triggers a temporary Processing Request screen.

```bash
python -m src.cli replay --artifact artifacts/lookup_savings_balance.v1.json --member-id 80008
```

Replay recognizes the known temporary state, performs the predefined `Continue` recovery action, verifies that the resulting URL remains inside the safety allowlist, records the recovery, and continues.

Expected:

```json
{
  "status": "success",
  "outputs": {
    "savings_balance": "$2468.90"
  },
  "recoveries": [
    {
      "step": 3,
      "condition": "processing_interstitial",
      "action": "click_continue"
    }
  ],
  "business_outcome": null,
  "failure": null
}
```

Evidence:

```text
evidence/replay-recovery/
```

### Hard Failure

Member `70007` triggers a Permission Denied state.

```bash
python -m src.cli replay --artifact artifacts/lookup_savings_balance.v1.json --member-id 70007
```

Expected:

```text
status = failure
observed = Permission Denied
```

Replay stops rather than continuing blindly.

The failure result includes:

- failed step
- expected state
- observed state
- failure message

A screenshot is also captured for debugging.

Evidence:

```text
evidence/replay-hard-failure/
```

---

## 7. Human-in-the-Loop Handoff

The second capability demonstrates an irreversible action that requires a human.

Run:

```bash
python -m src.cli replay --artifact artifacts/open_savings_account.v1.json --member-id 20002 --opening-deposit 100
```

Automation completes the safe preparation steps and stops before the final `Create Account` action.

The terminal displays the intervention context, including:

- capability
- current step
- reason
- current URL

The same Chromium browser session remains open.

The human reviews the account details and clicks:

```text
Create Account
```

The operator then returns to the terminal, confirms completion, and provides a short description of the action.

Automation resumes using the same browser session and verifies the resulting checkpoint.

Evidence for the handoff is stored in:

```text
evidence/handoff/
```

The evidence includes the intervention request, control-owner changes, human action information, and before/after screenshots.

---

## 8. Safety Policy

Automation policy is configured in:

```text
config/policy.json
```

The policy contains explicit configuration for:

- allowed origins
- allowed routes
- allowed action types
- action risk handling

Actions are classified as:

```text
safe
reversible
irreversible
```

Irreversible actions require human control.

Automated browser actions are checked against policy before execution. Navigation-producing actions are also checked after execution so the automation cannot silently leave the configured application routes.

Sensitive values are redacted before structured evidence is written.

The real Groq API key belongs only in `.env`, which is excluded from Git.

---

## 9. Capability Artifacts

### Lookup Savings Balance

```text
artifacts/lookup_savings_balance.v1.json
```

Input:

```text
member_id: string
```

Output:

```text
savings_balance: string
```

The artifact was generated from a successful LLM discovery run and parameterizes the discovered member value as:

```text
{{member_id}}
```

### Open Savings Account

```text
artifacts/open_savings_account.v1.json
```

Inputs:

```text
member_id: string
opening_deposit: number
```

The final account-creation action is classified as irreversible and therefore requires human handoff.

---

## 10. Evidence

The repository includes final evidence under:

```text
evidence/
```

The included evidence demonstrates:

```text
discovery/
replay-success/
replay-business-outcome/
replay-recovery/
replay-hard-failure/
handoff/
lookup_savings_balance.v1.json
```

Structured events are written as JSONL.

Failure and handoff scenarios also include screenshots where appropriate.

The evidence uses synthetic application data and does not contain the Groq API key.

---

## 11. Run Tests

The test suite can be run without a Groq API key and without starting the demo application.

Run:

```bash
python -m pytest tests -v
```

Current result:

```text
9 passed
```

The tests cover:

- artifact parameterization
- artifact immutability during parameterization
- allowed navigation
- blocked external origin
- blocked route
- human requirement for irreversible actions
- sensitive dictionary redaction
- SSN redaction
- deterministic saved-step replay

---

## 12. Discovery vs Replay

The central design separation is:

```text
Natural-language goal
        |
        v
LLM Discovery
observe -> decide -> act
        |
        v
Typed Capability Artifact
        |
        v
Deterministic Replay
no LLM decisions
        |
        v
Structured RunResult
```

The model is used to discover the workflow once.

The resulting capability becomes the reusable production execution contract.

---

## 13. Key Design Choices

### Surface abstraction

Browser interaction is kept behind a surface abstraction rather than being embedded directly into discovery or replay logic.

The current implementation uses Playwright.

A future implementation could provide another surface adapter for accessibility APIs or desktop automation without changing the high-level capability contract.

### Stable targeting

Targets prefer semantic information such as:

- roles
- accessible names
- labels
- form names
- visible text
- constrained CSS fallbacks

The generated artifact also contains short robustness notes explaining why important targets should remain stable during replay.

### Runtime errors

Replay deliberately distinguishes:

```text
success
business_outcome
recoverable condition
hard failure
```

A legitimate result such as Member Not Found is not treated as an application crash.

### Human control

Risky final actions are not automatically executed.

Automation pauses and explicitly transfers control to a human while preserving the same browser session.

---

## 14. Notes

This project intentionally focuses on a small complete vertical slice rather than production infrastructure.

It does not implement:

- production queues or workers
- a multi-tenant capability registry
- native desktop automation
- a remote co-browsing operator console
- automatic artifact repair
- unrestricted LLM fallback during replay

These are discussed as future design extensions in `REPORT.md`.

The local banking application and all member information in this repository are synthetic and are used only to demonstrate the automation workflow.
```
