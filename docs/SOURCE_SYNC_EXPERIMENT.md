# Free-worker Android 11 source-sync experiment

Workflow `android11-sync-probe.yml` executes a real source sync on the standard ubuntu-22.04 GitHub runner. It does not rent a worker, build Android, download proprietary stock firmware or flash anything.

It initializes the recorded Android 11 candidate manifest commit, overlays the 11 pinned hardware repositories after removing conflicting platform entries, and requests shallow/current-branch fetches with four jobs. Git Repo is cloned from its official upstream; the actual tool revision is recorded. Subproject branches are fully captured with `repo manifest -r` only if sync succeeds.

A monitor stops the process group when free disk falls below 12 GiB or 30 minutes elapse. The job has an outer 40-minute limit. Logs and resource samples are retained as an artifact for seven days. No aggressive runner-directory deletion or paid configuration is used.

Interpret results precisely:

- SYNC_COMPLETE: sources downloaded within this attempt's limits, not that they compile or enough output space remains.
- SYNC_ERROR: inspect the actual network/repository error; this does not establish insufficient hardware.
- DISK_RESERVE_REACHED: this particular attempt exhausted the permitted source-space budget.
- TIME_BUDGET_REACHED: the bounded experiment stopped before completion, not proof a longer run would fail.

Source bytes are ephemeral on the hosted runner and are not uploaded as a huge artifact. This is a measurement experiment. After a successful feasibility result, source sync and compilation must be combined into a single job or use an explicitly reviewed persistence mechanism. No complete platform build is claimed from this workflow.
