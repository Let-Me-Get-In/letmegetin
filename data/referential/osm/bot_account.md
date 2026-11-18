# LetMeGetIn bot account

## Account

- Proposed OSM account name: **`LetMeGetIn_bot`**. It does not upload anything yet: this phase only
  generates an `.osmChange` file for a human operator to review and send. The name must be registered
  and recorded here before the first upload is ever wired.
- Contact: Sébastien Billion — contact@letmegetin.org — https://letmegetin.org
- The account is declared as a bot on its OSM user page, and every changeset it makes carries the
  reviewed comment template (`changeset_comment_template.txt`), which names the project and links the
  published wiki page.

## Credentials

Credentials are **never stored in this repository**, in any form: no password, no OAuth token, no
`.env` file, no test fixture. Production secrets live in the Infisical project pinned in `AGENTS.md`
and are injected at process start (`./scripts/with-secrets.sh`). A token pasted anywhere else — a
commit, a log line, a ticket — is a leak and must be rotated.

## Activation

Uploading is deferred until the OSM community has reviewed this proposal and approved the account.
Until then the generator writes files only; it imports no network client, and that absence is
asserted by a test.
