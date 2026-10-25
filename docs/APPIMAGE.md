# Linux AppImage release

This repository builds a real, self-contained **x86_64 AppImage** (Python 3,
PyQt6, Qt libraries, A50 presets, license texts, hardware-settings GUI and
audio detector). It is intended for users whose Astro A50 Gen 3 is detected as
USB `9886:0015`. No vendor binaries or firmware are packaged.

## Build on Linux (Ubuntu 22.04+ recommended)

```bash
bash scripts/build_appimage_local.sh
```

That command creates a private build virtual environment under
`build/appimage-venv/`, installs pinned PyQt6/PyInstaller dependencies and
builds the complete AppImage without changing the system Python installation.
On a preconfigured build host, `bash scripts/build_appimage.sh` works directly.

The script also requires `curl` and the corresponding graphical libraries
available on the host. It downloads the current maintained x86_64
`appimagetool` from its official GitHub project, and creates:

- `dist/OpenAstroCC-x86_64.AppImage`
- `dist/OpenAstroCC-x86_64.AppImage.sha256`

For a CI-tested download, open **GitHub Actions → Build OpenAstroCC
AppImage → successful run → Artifacts → OpenAstroCC-x86_64**. The
`.github/workflows/appimage.yml` workflow runs offline tests, packages the
real executable, performs an offscreen AppImage smoke test, and uploads the
files as an artifact. Downloading the artifact doesn't publish a public
release automatically.

## Running

```bash
chmod +x OpenAstroCC-x86_64.AppImage
./OpenAstroCC-x86_64.AppImage
```

No system Python or PyQt6 installation is required. The application can also
be launched from a desktop integration tool. Test the packaged offline GUI
with a compatible JSON backup if one is available:

```bash
QT_QPA_PLATFORM=offscreen APPIMAGE_EXTRACT_AND_RUN=1 \
  ./OpenAstroCC-x86_64.AppImage --snapshot evidence/a50-baseline.json --smoke
```

AppImage requires a reasonably modern glibc Linux system; this CI bundle is
built on Ubuntu 22.04. FUSE is not required when using
`APPIMAGE_EXTRACT_AND_RUN=1`, though startup is slower.

## Writable data and audio setup

The packaged image is read-only. Custom `.astroeq` files save in
`$XDG_DATA_HOME/astro-a50-linux/presets`
(default `~/.local/share/astro-a50-linux/presets`), never inside its
squashfs archive. EQ labels are local at
`$XDG_CONFIG_HOME/astro-a50-linux/eq-names.json`; transaction backups go
under `$XDG_STATE_HOME/astro-a50-linux/backups`. In a *writable Git checkout*,
custom profiles instead save to `presets/custom/`.

The bottom-right **About** button opens **Audio setup…** (orange). The
standalone A50 detector runs as a subcommand of the packaged application,
previews the actual device and proposed WirePlumber config, then requires
explicit confirmation before any installation. It will refuse to overwrite
conflicting existing A50 routing rules. It does **not** fix USB permissions
automatically, restart audio services, change system defaults, or touch the
headset firmware. A login restart and host-specific permissions may still
be needed after review.

## License and attributions

Application source is **GPL-3.0-only** (see [LICENSE](../LICENSE)); it permits
commercial use and GPL-compliant redistribution. It does **not** impose a
noncommercial condition, because GPL PyQt6 cannot be redistributed under
that additional restriction without a different licensing arrangement.

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for PyQt6, SIP, Qt,
Python, PyInstaller, PipeWire, WirePlumber, original vendor EQ data and
attributions. The built AppImage also includes the full GPL, LGPL, Python,
PyInstaller and MIT license texts plus the *actual installed wheel copyright
and license files* with a component/version manifest. These are part of the
AppImage, not internet-only links.

**Vendor EQ data:** Distribution permissions for Astro-authored original
presets have not independently been verified. Review this before public
distribution. Keeping firmware and proprietary Windows app binaries out of
the package is intentional.

## AppImageLauncher compatibility

If appimagetool fails with "Squashfs image uses (null) compression", that is a host AppImageLauncher compatibility issue with newer zstd-compressed AppImages, not a PyInstaller problem. The build script first attempts APPIMAGELAUNCHER_DISABLE=1 and APPIMAGE_EXTRACT_AND_RUN=1. If that still fails, the script locates the validated embedded SquashFS image and extracts appimagetool with unsquashfs (requires the distro's squashfs-tools package), then runs its extracted AppRun. This does not disable the host AppImageLauncher or change system settings.

A finished AppImage can also trigger incompatibility in an older AppImageLauncher. Update that tool or disable its integration outside this build; do not modify desktop binfmt rules automatically.
