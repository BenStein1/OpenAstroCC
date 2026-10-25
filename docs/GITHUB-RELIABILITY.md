# GitHub reliability: Actions runner failures vs git/API errors

## What actually happened on 2026-10-25

The private repository's AppImage workflow was queued and then failed **within ~2 seconds, before a runner was assigned**. Example run:
https://github.com/BenStein1/astro-a50-linux/actions/runs/40184631441
Its only job had **runner_id=0, runner_name empty, steps=[]**. Earlier run
40184305521 behaved identically, including a retry. Therefore **the build
script, Python code and tests never executed in those hosted runs**.
Do not debug PyInstaller as the cause of these particular zero-step failures.

On a **private** GitHub repository, GitHub-hosted runner capacity is charged
against the owning personal account's quota/budget. Immediate failure with
no runner/steps often results from **Actions spending limits, exhausted
included minutes, failed account payment, or entitlement holds**. It is
not enough evidence to identify which cause applies to this account.
GitHub status had some recent Actions incidents (Oct 19/21/22/23), but the
status page shows no GitHub-wide incident for Oct 25 at the time checked;
an account-specific block remains plausible.

### Fastest account-side diagnosis

1. Open the failed run URL above on GitHub.com. Look for an **annotation**
   saying the job did not start because payment failed or spending limit must
   be increased. The REST jobs API's empty steps hides that message; the
   web UI may show it.
2. Under the **personal account that owns BenStein1/astro-a50-linux**,
   open **Settings → Billing and licensing → Spending limits** (the names
   may vary) and check the **Actions** entry, account payment status and
   included minutes. Check **spending limit**, not only **budget alerts**.
   An Actions cap of $0 or used-up minutes can block new private-repo jobs.
3. In the repository open **Settings → Actions → General**; verify Actions
   and use of GitHub-hosted runners are allowed. Don't disable repository
   security protections to make a job run.
4. If account spending is allowed and runner jobs still fail before assignment,
   send GitHub Support the run link above and your account's billing screen.
   Only GitHub can remove an underlying account/payment entitlement block.

If later made **public**, standard GitHub-hosted runner minutes are generally
free for public repositories, though other Actions resource limits apply.
Do not make the repo public solely to bypass billing: first finish vendor
preset redistribution review, privacy/security scrub and release acceptance.

### Controls available inside this repository

- The AppImage workflow uses **Ubuntu 22.04 with Python 3.11** to build a
  portable binary. A package built on a new workstation with glibc 2.42
  is **not** a substitute for a broad-distribution Linux build.
- The workflow cancels superseded runs on the same branch/PR, limiting
  needless private-repo minutes consumed by repeated commits.
- If hosted Actions are blocked, use **scripts/build_appimage_local.sh** to
  create a local test build. This doesn't prove portability on older distros;
  continue to test a release build from the older runner/container.
- AppImage artifacts are published only after offline tests, GUI smoke test
  and SHA-256 verification all pass. A red workflow does **not** mean a
  runnable AppImage was generated.

## Separate problem: transient GitHub API / connector errors

Occasional messages such as **HTTP 502/503**, timeout, or
**RemoteProtocolError: Server disconnected without sending a response**
during repository API calls are distinct from runner allocation. They are
generally intermittent network/API/connector failures rather than a failure
in the A50 application. Recent official GitHub status history shows real
October 2026 outages affecting API, PRs, results and Actions.

For these, keep mutations idempotent and safe:
1. Re-read the branch/target SHA after a failed create/update before retrying.
2. Retry **read-only** requests with bounded exponential backoff.
3. For uncertain write results, check whether the commit or PR exists before
   submitting the operation again. A disconnect may happen *after* a write
   was accepted.
4. On concurrent changes, fetch the new file SHA and reconcile instead of
   blindly overwriting a teammate's edits. Use one PR/branch at a time for
   dependent changes.
5. Monitor https://www.githubstatus.com for real platform incidents;
   do not mistake outage mitigation for a local source fix.

These practices improve reliability, but a repo script cannot fix GitHub's
network, hosted-runner assignment, or account billing entitlements.

## Primary references

- GitHub Actions billing: https://docs.github.com/en/billing/concepts/product-billing/github-actions
- GitHub Status and historical incidents: https://www.githubstatus.com/
- Build/run instructions: docs/APPIMAGE.md
- Live protocol / audio verification: docs/GEN3-IMPLEMENTATION-GUIDE.md
