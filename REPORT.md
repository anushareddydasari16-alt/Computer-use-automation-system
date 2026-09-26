# Computer-Use Automation System Report

## 1. Architecture

The main idea of this project is simple: use an LLM once to learn the steps for a task, save those steps, and then replay them later without asking the LLM to make decisions again.

For discovery, the user gives a goal and a target URL. The system opens the banking application in Chromium using Playwright. The Groq model looks at the current page information and decides one action at a time, such as typing a member ID, clicking a button, or extracting a value. After each action, the page is observed again until the goal is completed or the run reaches a stopping condition such as maximum steps or timeout.

When discovery succeeds, the completed actions are converted into a reusable JSON artifact. The artifact is then used by the replay engine.

Replay is completely separate from the discovery logic. It reads the saved artifact, replaces placeholders with the new input values, performs the recorded steps, checks the expected page state, and returns the result. The replay path does not call the LLM to decide what to do.

I separated the project into small folders for discovery, replay, browser interaction, safety, artifacts, evidence, and human handoff. I kept everything in one application instead of building multiple services because the goal here was to show a complete working flow without adding unnecessary infrastructure.

## 2. Artifact schema

I wanted the artifact to be more than just a list of browser clicks. It needed to describe what the capability does, what input it needs, what output it returns, and how replay should know that a step worked.

The artifact is defined with Pydantic models and stored as JSON. It contains a schema version, capability version, name, description, target application, typed inputs, typed outputs, ordered steps, checkpoints, and a success condition.

Each step contains the action type and information about how to find the target control. Depending on the element, the target can use a role, visible name, form field name, text, or CSS selector.

I also added a `robustness_note` to important targets. This explains why a locator was chosen. For example, the member ID field is found by its form name instead of its position on the page. The savings balance is found from the row containing `Savings` instead of saving the exact dollar value seen during discovery.

The discovery run uses member `10001`, but the saved artifact replaces that value with `{{member_id}}`. Because of this, the same artifact can later be replayed with members such as `30003`, `80008`, or `99999`.

The main artifact is `lookup_savings_balance.v1.json`. It accepts `member_id` as a string and returns `savings_balance` as a string.

## 3. Determinism & error handling

The replay engine follows the saved artifact in order. It does not ask the LLM what the next action should be. This is the main difference between discovery and replay.

For a normal replay, the system replaces the input placeholder, executes each saved action, checks the policy, verifies checkpoints, and collects the requested output. For example, member `30003` returns a savings balance of `$5520.75`.

I also handled different runtime situations separately instead of treating all of them as errors.

Member `99999` does not exist. In this case the system returns `business_outcome = member_not_found`. This is a valid result from the banking application, so I did not treat it as a system failure.

Member `80008` shows a temporary `Processing Request` page. The replay engine recognizes this condition, clicks `Continue`, checks that the new URL is still allowed, records the recovery, and continues the replay. The final run still succeeds and returns `$2468.90`.

Member `70007` is used to simulate a permission problem. When the page shows `Permission Denied`, replay stops and returns a failure containing the failed step, what it expected, what it observed, and a readable error message. It also saves a screenshot for debugging.

There is also a one-time retry for Playwright timeout errors. I kept the retry limited because replay should not continue forever when the application is not responding.

Checkpoints are important because the system should not assume that a click worked. After important steps, replay checks the page text or URL before continuing.

## 4. Heterogeneity & multi-tenant

The current project uses a web application, but I did not want discovery and replay to depend directly on Playwright everywhere in the code.

Browser interaction is placed behind a `Surface` abstraction. The higher-level code uses operations such as open, observe, act, screenshot, and close.

Today, the implementation of that surface uses Playwright. In the future, another implementation could use Windows UI Automation, accessibility APIs, screenshots, OCR, or coordinates for desktop applications.

For the current web application, I prefer semantic targets such as form names, roles, labels, and visible text before relying on CSS. This is more stable than using screen coordinates.

For a multi-tenant setup, I would keep one main capability for the common vendor application and add small tenant or version-specific overrides when needed. For example, one institution might have different button text or a different route prefix.

I did not build the full multi-tenant system in this project. The goal was to make sure the artifact and surface design could support it later without rebuilding the whole automation approach.

## 5. Escalation & handoff

The project also includes a human handoff for an action that should not be completed automatically.

The `open_savings_account` artifact prepares a savings account request. The safe steps are completed by automation. The final `Create Account` action is marked as irreversible.

When replay reaches this step, the safety policy does not allow the system to click the button automatically. Instead, it creates a human intervention request.

The request includes the capability name, current step, reason for stopping, current URL, and a screenshot. Automation pauses, and the same Chromium browser remains open.

The human can review the information and click `Create Account` manually. After that, the human returns to the terminal, records a short description of what was done, and gives control back to the automation.

Replay then looks at the same browser session again and verifies that the expected confirmation page was reached.

I used the command line as the operator interface because a full operator dashboard was outside the scope of this project. The important part was proving that automation could stop, give control to a person, and continue using the same live session.

## 6. Safety

The safety rules are stored in `config/policy.json`.

The policy defines which origins, routes, and action types are allowed. It also defines how safe, reversible, and irreversible actions should be handled.

Before an automated action runs, the system checks the policy. After browser actions that may change the current page, the system observes the new URL and checks it again against the allowed routes.

I added the same check to the automatic recovery flow. This means the `Continue` recovery action cannot move the automation to an unapproved route without being detected.

Irreversible actions are not automatically executed. They require human control.

The logging system also includes redaction. Keys such as passwords, API keys, tokens, and authorization values are removed before being written to evidence. SSN-like values are also redacted.

The real Groq API key is stored only in `.env`, and `.env` is excluded from Git. The example environment file contains only an empty placeholder.

The banking application uses synthetic member data, so no real customer information is needed for the demo.

For a production banking environment, this safety layer would need stronger access control, encrypted evidence storage, authentication, audit logging, and formal data retention rules.

## 7. Cuts

I intentionally kept this project focused on the full required workflow instead of adding extra features.

I did not build a desktop automation adapter, production database, distributed worker system, multi-tenant capability registry, remote operator dashboard, or automatic artifact repair.

I also did not add an LLM fallback during replay. If replay fails, I prefer it to stop and return clear evidence instead of allowing the model to change the saved workflow automatically.

The current observation system mainly uses browser text and control information. A future version could add screenshot and accessibility-based targeting for applications that do not have useful browser structure.

If I continued the project, I would first improve the surface layer for legacy and desktop applications, then add stronger runtime input validation, capability approval/version management, secure evidence storage, and an authenticated operator interface.

The current version focuses on the complete path I wanted to demonstrate: a natural-language goal, real LLM discovery, a reusable artifact, deterministic replay, clear runtime outcomes, safety checks, evidence, and a same-session human handoff.