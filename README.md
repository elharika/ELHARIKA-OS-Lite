# ELHARIKA OS Lite — application CI

Target OS project: Samsung SM-P900 / v1awifi. This repository seed builds only the two Java Android apps. It does NOT build or publish a ROM, boot image, kernel, or recovery. Full platform and vendor integration remain incomplete.

On main push or manual dispatch, GitHub Actions records actual CPU, disk and RAM, installs API30 and build-tools30.0.3, builds both apps with JDK17, verifies APK signatures through the build script, and uploads artifacts and logs for seven days. No private signing key is uploaded. Each run generates a fresh development key, so APKs from separate runs cannot necessarily update one another. Export notes before uninstalling any previous version.

No paid runner is selected. Private repository minutes can count toward the account allowance; check account billing controls. Source uses standard ubuntu-22.04. This CI file has not yet run on GitHub. Local builds previously succeeded with the same SDK and JDK major version; this is not hardware verification.

The standard runner is not assumed sufficient for an entire Android source build. A large runner alone will not resolve the incomplete device port. No GApps or root components are included in these apps.
