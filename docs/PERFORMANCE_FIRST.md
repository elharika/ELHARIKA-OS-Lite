# ELHARIKA OS Lite — performance-first design (SM-P900)

Hardware: Exynos 5420, Mali-T628 MP6, 3 GB RAM, 2560x1600 display. The objective is smooth everyday UI, not a high benchmark score.

## Initial design choices

- Start with minimal apps, no bundled GApps, no root and no heavyweight launcher.
- Shorten window, transition and animator animation scales to 0.5x for perceived responsiveness.
- Consider 768 MiB ZRAM only after confirming kernel support, compression choice, memory pressure and CPU cost; benchmark against disabled ZRAM.
- Do not hardcode CPU clocks, overclock, disable thermal throttling, or blindly change low-memory-killer thresholds.
- Keep display at native resolution until graphics stability and readability are measured.
- Do not force GPU acceleration or unsupported Mali flags: the community Android 11 Exynos5420 port reports GPU driver hangs under some graphics-intensive workloads.
- Evaluate light web browsing, PDF reading, note-taking and stylus responsiveness. Google services are optional and should be installed only if needed.

## Test criteria before any release

1. Cold boot time (3 repeats).
2. Launcher smoothness and dropped frames during app switching.
3. Idle memory and memory pressure during 5-app multitasking.
4. Browser scroll/pinch stability for 20 minutes.
5. PDF annotation and S Pen latency.
6. Wi-Fi reconnection, audio, sleep/wake and charging.
7. Battery drain and surface temperature under sustained browsing.

No benchmarks or actual device tests have been performed. The JSON profile is documentation only; it is not applied to Android build outputs.
