---
phase: 11-e2e-accessibility
plan: 02
subsystem: cli
tags: [admin-cli, accounts, e2e, security, typer]
requires: []
provides:
  - "`ensure_user(users, email, password, display_name, verified)` use case in `application/accounts/users.py`, returning `created` / `verified` / `already verified` / `unverified`"
  - "public `is_valid_email(email)` in `application/accounts/register.py` — the one email rule shared by `register` and the CLI"
  - "`letmegetin-admin user ensure <email> [--verified/--no-verified] [--display-name]`, wired through a commit-only `_run_user_admin` runner (no referential grid rebuild)"
  - "operator path to mint an already email-verified account for the e2e suite, with the password read from `LETMEGETIN_USER_PASSWORD` or a `hide_input` prompt — never argv"
affects: [11-03]

actuals:
  tokens: 3972
  tasks: 2
  commits: 1
  plan_head_before: 819c389dac8e7c92bae25b0009ec1219dd35bbc9
  plan_head_after: 501a89fbcbf802bb9736b2637efff2ff7dc9ecdd

tech-stack:
  added: []
  patterns:
    - "A command that seeds an account does not go through `_run_admin`: that helper bumps the referential version and rebuilds the category grids (`bump=True`), which accounts do not touch. `_run_user_admin` mirrors `_run_api_key_admin` — open a session, call the use case, commit, map `DomainError` to `Exit(1)`."
    - "A secret the operator supplies is never a Typer option: an option value is in argv and therefore in `ps` output and shell history. The password is read from `LETMEGETIN_USER_PASSWORD` or `typer.prompt(..., hide_input=True)` inside the command body, and the command prints only the email and the outcome token."
    - "An idempotent seed verifies, it does not overwrite: an existing account is matched against the supplied password (`verify_password`) and a mismatch is a `DomainError`, because a silent skip would leave the e2e suite holding a credential the operator believes they just set."

key-files:
  created:
    - src/letmegetin/application/accounts/users.py
    - tests/unit/test_ensure_user.py
    - tests/integration/test_user_command.py
  modified:
    - src/letmegetin/admin.py
    - src/letmegetin/application/accounts/register.py

key-decisions:
  - "`is_valid_email` is the public name for the email rule and `register` now calls it: the private `_EMAIL` regex stays module-private, so the CLI and the HTTP register endpoint cannot drift."
  - "`ensure_user` returns an outcome token rather than a `User`: the CLI needs one printable word and the caller must not be handed the stored hash."
  - "The `--verified/--no-verified` flag defaults to `False`, so an unflagged re-run on an unverified account reports `unverified` and writes nothing — the flag is an explicit request, not a side effect."
  - "Existing accounts are matched with `verify_password` before any write: `DomainError(\"password does not match the existing account\")` is the loud failure the plan requires, and no password-update path exists on the port to misuse."

requirements-completed: []
requirements-advanced: [E2E-01]

coverage:
  - id: D1
    description: "A fresh email creates one already-verified account whose hash `verify_password` accepts for the supplied password."
    requirement: E2E-01
    verification:
      - kind: unit
        ref: "tests/unit/test_ensure_user.py#test_ensure_user_fresh_email_creates_one_verified_row[True]"
        status: pass
      - kind: integration
        ref: "tests/integration/test_user_command.py#test_ensure_creates_a_verified_account_once"
        status: pass
  - id: D2
    description: "Re-running with the same password is idempotent: same row, `already verified`, no second insert."
    requirement: E2E-01
    verification:
      - kind: unit
        ref: "tests/unit/test_ensure_user.py#test_ensure_user_reports_an_already_verified_account"
        status: pass
      - kind: integration
        ref: "tests/integration/test_user_command.py#test_ensure_creates_a_verified_account_once"
        status: pass
  - id: D3
    description: "An existing unverified account is verified in place without a second insert."
    requirement: E2E-01
    verification:
      - kind: unit
        ref: "tests/unit/test_ensure_user.py#test_ensure_user_verifies_an_existing_unverified_account_once"
        status: pass
  - id: D4
    description: "A different password fails loudly (DomainError → exit 1) and changes nothing."
    requirement: E2E-01
    verification:
      - kind: unit
        ref: "tests/unit/test_ensure_user.py#test_ensure_user_fails_on_a_password_mismatch"
        status: pass
      - kind: integration
        ref: "tests/integration/test_user_command.py#test_ensure_fails_loudly_on_a_password_mismatch"
        status: pass
  - id: D5
    description: "`--password` does not exist: Typer rejects the unknown option with a non-zero exit."
    requirement: E2E-01
    verification:
      - kind: integration
        ref: "tests/integration/test_user_command.py#test_ensure_rejects_a_password_option"
        status: pass
  - id: D6
    description: "Invalid email and short password are rejected with `DomainError`, and no outcome or message ever contains the password."
    requirement: E2E-01
    verification:
      - kind: unit
        ref: "tests/unit/test_ensure_user.py#test_ensure_user_rejects_an_invalid_email"
        status: pass
      - kind: unit
        ref: "tests/unit/test_ensure_user.py#test_ensure_user_rejects_a_short_password"
        status: pass
      - kind: unit
        ref: "tests/unit/test_ensure_user.py#test_ensure_user_never_returns_the_password"
        status: pass
---

# Phase 11 Plan 02: `admin user ensure` Summary

The e2e suite now has a credential it can log in with: `letmegetin-admin user ensure --verified
<email>` creates an already email-verified account in one idempotent call, refuses to continue when
the supplied password does not match the stored one, and never accepts the password on the command
line.

## What changed

**`application/accounts/register.py`.** `is_valid_email(email) -> bool` is now the public name for
the email rule sitting next to `MIN_PASSWORD_LENGTH`; `register` calls it instead of matching
`_EMAIL` inline. The regex stays module-private — nothing outside imports it.

**`application/accounts/users.py` (new).** `ensure_user(users, email, password, display_name,
verified)` normalizes the email, validates it and the password length with `register`'s rules, then:

- no existing row → `User(id=0, …, email_verified=verified)` through `users.add`, returns `created`;
- existing row → `verify_password(password, existing.password_hash)` first; a mismatch raises
  `DomainError("password does not match the existing account")`, so a re-run can never leave the
  account holding a secret the operator did not supply. On a match: `verified` on an unverified
  account calls `mark_email_verified` (`verified`), an already-verified account returns
  `already verified`, and an unflagged unverified account returns `unverified` and writes nothing.

The module depends only on `UserRepository`, `hash_password`/`verify_password` and `DomainError`.

**`admin.py`.** A `user` sub-app with one command. `_run_user_admin` mirrors `_run_api_key_admin`
(session → `SqlAlchemyUserRepository` → use case → commit → `DomainError` as `Exit(1)`) and
deliberately does **not** use `_run_admin`, whose default `bump=True` rebuilds the category grids —
accounts do not touch the referential. `_read_user_password` takes `LETMEGETIN_USER_PASSWORD`, falls
back to `typer.prompt("Password", hide_input=True)`, and exits 1 with a stderr message when both are
empty. The command prints `user {email}: {outcome}` and nothing else.

## Verification

```
uv run ruff check .            → All checks passed!
uv run ruff format --check .   → 214 files already formatted
uv run mypy                    → Success: no issues found in 75 source files
uv run bandit -r src -c pyproject.toml → No issues identified (5680 lines scanned)
uv run pytest -q --cov=letmegetin --cov-branch --cov-fail-under=85
                               → 261 passed, 1 warning in 38.69s
                                 Required test coverage of 85% reached. Total coverage: 92.54%
uv run python -m letmegetin.admin user ensure --help
                               → email argument, --display-name, --verified/--no-verified; no --password
uv run python -m letmegetin.admin families audit
                               → families ok: every criterion and filter has at least one family
```

The integration test runs against the local PostGIS (`letmegetin_test`), uses
`cli-test-e2e@example.test` and deletes every `cli-test-%` user before and after each test, so the
shared database is left as it was. `families audit` still passes afterwards.

## Deviations from Plan

None — the plan executed as written. `_read_user_password` is the only addition beyond the plan's
literal command body: the fallback-and-exit logic lives in a small helper next to the runner rather
than inline, so the command body stays three lines.

## Threat notes

- **T-11-04 (password transit, high):** mitigated as planned — the password arrives via
  `LETMEGETIN_USER_PASSWORD` or a `hide_input` prompt, `--password` is not an option and is rejected
  as an unknown option (asserted), and the command echoes only `user {email}: {outcome}`. Bandit
  flags nothing.
- **T-11-05 (`email_verified=True` bypass, medium):** the flag is written through
  `UserRepository.add` / `mark_email_verified`, the same write path as the verification flow; the
  command has no HTTP surface, matching `api-key`'s operator-only trust model.
- **T-11-SC (package installs, high):** no dependency added.

## Known stubs

None.

## For the next plans

- **11-03 must read the same secret.** The password supplied to `admin user ensure` has to be
  mirrored as the e2e repo's GitHub secret `E2E_USER_PASSWORD`; the account email is whatever the
  operator passes (the plan's examples use `e2e@…`), so 11-03 must pin one canonical address and use
  it in both places.
- **The command is dev-stack-safe and prod-stack-capable.** Nothing in it is environment-specific,
  but the e2e suite targets `https://app.dev.letmegetin.org`, so the run belongs on `lmgi-dev`.
- **`--verified` is explicit.** An e2e re-seed that forgets the flag on a fresh account reports
  `created` with `email_verified = false`, and the `verifyToContribute`/`verifyToReview` prompts would
  then block the journeys — so 11-03's setup step must pass `--verified`.

## Self-Check: PASSED

- `src/letmegetin/application/accounts/users.py`, `tests/unit/test_ensure_user.py`,
  `tests/integration/test_user_command.py` exist.
- `.planning/phases/11-e2e-accessibility/11-02-SUMMARY.md` exists.
- Commit `501a89f` is an ancestor of HEAD (`git merge-base --is-ancestor`); one commit measured from
  the plan ledger (`819c389..501a89f`, `git rev-list --count` = 1).
