# Secure mobile alert publishing

The website stays readable without an account. Publishing requires a token and server-side write restrictions. Push is opt-in: `NTFY_ALERTS_ENABLED` defaults to `false`. The old public channel is not considered trusted until its anonymous write access is blocked.

## ntfy.sh hosted option

The live [ntfy.sh plan endpoint](https://ntfy.sh/v1/tiers) checked on October 3, 2026 lists zero topic reservations on the free tier. Supporter offers three reservations for $6/month or $60/year. Prices can change. Creating a free account alone does not protect a topic, and adding a token to an unreserved topic does not block other writers.

1. Create an account and select a plan with topic reservations.
2. In account settings, reserve `mathews-flood-23128`. Choose **everyone: read-only** (public subscriptions, owner publishes). If someone else owns the name, choose a new topic and update subscribers.
3. Create a dedicated access token. ntfy tokens inherit account permissions; use an account dedicated to this service and revoke unused tokens.
4. In this GitHub repository's **Settings → Secrets and variables → Actions**, add the secret `NTFY_TOKEN`. Do not paste it into an issue, a pull request, this file, or the website.
5. Add repository variables `NTFY_TOPIC=mathews-flood-23128`, `NTFY_SERVER=https://ntfy.sh`, and `NTFY_ALERTS_ENABLED=true`.
6. Run the update workflow manually. Before publishing, the code performs a read-only authenticated account lookup and requires a matching reservation with `everyone=read-only`. Wrong or missing configuration fails visibly. No notification is sent when fresh data indicates no hazard.

The code never creates an account, reserves a paid topic, purchases a subscription, or sends an unsolicited test alert. A human can explicitly run `python3 check_alerts.py --test-ntfy` after configuration to test phone delivery.

## Self-hosted option without a software subscription

[ntfy is open source](https://docs.ntfy.sh/config/#access-control). Use an existing HTTPS server; hosting/domain costs may still apply. GitHub Pages cannot host the ntfy backend.

Configure the ntfy server with a durable authentication database and a default-deny policy:

```yaml
# /etc/ntfy/server.yml
base-url: https://alerts.example.org
listen-http: ':8080'  # Behind a TLS reverse proxy; keep the backend port private.
auth-file: /var/lib/ntfy/user.db
auth-default-access: deny-all
```

On that server, create a regular publisher, allow only its topic writes, allow anonymous subscriptions, and generate its token:

```sh
ntfy user add flood-publisher
ntfy access flood-publisher mathews-flood-23128 write-only
ntfy access everyone mathews-flood-23128 read-only
ntfy token add flood-publisher
```

Use `NTFY_SERVER=https://alerts.example.org`, the same topic, and a GitHub Actions secret containing the token. Check the server's ACL listing before enabling `NTFY_ACL_CONFIRMED=true`. This manual acknowledgement is required because self-hosted ACLs do not use the hosted topic-reservation API. Set `NTFY_ALERTS_ENABLED=true` only after verifying the ACLs and phone subscriptions on the new server. Subscribers must select the new server in the app.

Production iOS instant delivery for a self-hosted server may require an upstream connection as described in the [ntfy iOS documentation](https://docs.ntfy.sh/config/#ios-instant-notifications). Test on the actual devices before relying on delivery timing.

## Delivery and state behavior

- Normal local CLI runs do not send push messages. Pass `--ntfy` to enable authenticated publishing; `--dry-run --ntfy` performs an offline simulation and never logs a token.
- Redirects are refused so a server cannot forward the publisher token to another origin. Only HTTPS origins and simple topic names are accepted.
- Transient publish failures are retried three times. Authentication errors fail immediately. Delivery or state-write failures return a nonzero CLI status and do not silently advance suppression state.
- State is atomically replaced after successful delivery. If the state file is corrupt, publishing stops visibly rather than resetting and duplicating alerts. Delivery is at least once: a crash after a successful publish but before durable state persistence may cause a retry.
- Missing observations, stale updates, incomplete forecast coverage, or missing wind/rain guidance cannot trigger ALL CLEAR. Fresh known elevated hazards may still produce warnings during a partial outage.
- A four-hour crest-time tolerance prevents one-hour forecast revisions from becoming duplicate events; risk and stage escalations remain enabled.

## Scheduling and independent monitoring

GitHub Actions schedules are best effort. Running at minutes 7 and 37 avoids common top-of-hour contention but is not a delivery guarantee. The portal shows update/observation times and rechecks age in the browser every minute. After 90 minutes it hides safety-dependent cards and reports stale data.

Run the read-only command below every 5–10 minutes from an **independent** monitoring host or service. Alert the operator if it exits 1; configuring an operator's destination is a separate setup step.

```sh
python3 check_pipeline_health.py
```

For a self-hosted deployment, a systemd timer or an external scheduler can run the pipeline independently of GitHub scheduling. Keep a single writer for the alert state; do not run overlapping publishers with separate state files. Example sequence on a persistent checkout:

```sh
python3 ingest_realtime.py
python3 generate_dashboard.py
python3 check_alerts.py --ntfy
```

Moving the scheduler requires configuring that host's state persistence and website upload. This pull request provides monitoring and safe stale behavior; it does not provision or claim to fix GitHub's scheduler infrastructure.

## Before enabling production push

Verify the topic's server-side ACLs, set the token secret, and verify the desired server/topic variables. Keep publishing disabled until those settings are in place. Topic names and public subscription URLs are intentionally public; tokens are never included in generated JSON, HTML, caches, or git commits.
