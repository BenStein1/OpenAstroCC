# Releasing OpenAstroCC

OpenAstroCC builds automatically on GitHub-hosted Ubuntu 22.04 x86_64.

## Build and publish rules

| Event | Outcome |
|---|---|
| Pull request | Offline tests, AppImage build, packaged-app smoke test and checksum; no release |
| Push or merge to `main` | Same checks; downloadable short-lived Actions artifact; no public Release |
| Push version tag `vMAJOR.MINOR.PATCH` (optional `-suffix`) | Same checks, then an official [GitHub Release](https://github.com/BenStein1/OpenAstroCC/releases) with `OpenAstroCC-x86_64.AppImage` and `.sha256` |
| Failed tests, packaging or smoke test | No release is published |

Versions beginning with `v0.` or having a prerelease suffix (for example
`v1.0.0-rc1`) are published as **pre-releases**. Other version tags produce
normal releases. Source archives are supplied by GitHub. Releases are not
automatically created for every `main` commit: that avoids publishing
unfinished changes.

## Make a release

1. Check the latest successful
   [AppImage workflow](https://github.com/BenStein1/OpenAstroCC/actions/workflows/appimage.yml).
   For a release, also validate the GUI and device behavior on actual A50 Gen 3
   hardware; automated tests cannot prove headset behavior.
2. Verify the version you want is committed to `main`, then create and push
   an annotated version tag:

   ```bash
   git switch main
   git pull --ff-only
   git tag -a v0.1.0 -m "OpenAstroCC v0.1.0"
   git push origin v0.1.0
   ```

3. GitHub Actions builds and tests the *tagged commit*. If green, its release
   job creates the download page with the AppImage and checksum and generates
   release notes from merged commits/PRs.
4. Download the release and verify its SHA-256 against the accompanying file.
   Test it on at least one Linux machine outside the build environment.

If the version's GitHub Release already exists, rerunning the release job
**refuses to overwrite the published assets**. Cut a new version for an
updated release. Never reuse or move a published tag.

## Packaging requirements and risks

- The build uses Python 3.11 and Ubuntu 22.04 to avoid packaging against a
  very new workstation glibc. Only **x86_64** is built today.
- The AppImage bundles Qt, PyQt6, app code, presets, and license notices.
- Some older AppImageLauncher installations cannot mount zstd-compressed
  AppImages; users may need to upgrade the launcher or extract/run the AppDir.
  See [AppImage troubleshooting](APPIMAGE.md).
- **Original factory Astro preset redistribution rights remain an unresolved
  release/legal check**; review this before inviting broad downloads. See
  [third-party notices](THIRD_PARTY_NOTICES.md).
- A successful CI build does not prove permanent on-device save, clean
  hotplug handling, or end-to-end 5.1 audio on every distro. See
  [feature acceptance](FEATURES.md).

## GitHub Actions permissions

The build job uses repository-content **read** access. Only the tag-gated
release job gets `contents: write`, to create the GitHub Release with the
automatic `GITHUB_TOKEN`. No personal access token or new secret is needed
under normal repository Actions settings. If GitHub disallows releases from
Actions, check **Settings → Actions → General → Workflow permissions** and
repository/org policy.

An Actions artifact is not a Release. Only the version tag starts the
publication step.

## Release automation troubleshooting

See [GitHub reliability](GITHUB-RELIABILITY.md) for GitHub-hosted minutes,
runner initialization, network issues and log retrieval. The latest successful
hosted run should always be checked before pushing a public tag.
