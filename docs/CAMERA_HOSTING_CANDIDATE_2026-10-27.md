# Split camera hosting candidate — hardware unverified

The existing pinned common device product already installs android.hardware.camera.provider@2.4-impl.exynos5420, android.hardware.camera.provider@2.4-service, camera.device@1.0-impl.exynos5420 and camera.universal5420. CameraProvider.cpp (Git blob bb0030030931446bd79926745ba3bdddbe7ed8bc) explicitly implements CAMERA_DEVICE_API_VERSION_1_0 and creates a V1_0 CameraDevice. HAL1 support is retained.

TARGET_HAS_LEGACY_CAMERA_HAL1 previously selected CameraService inside mediaserver (NO_CAMERA_SERVER, camera_in_mediaserver_defaults overrides cameraserver). It also included legacy-common/public/legacy-camera-hal1/mediaserver.te, conflicting with the platform cameraserver ownership assertions. The candidate sets this hosting flag false and retains the existing HAL1 provider and libraries. No platform neverallow is disabled or edited. This changes process hosting and requires runtime validation: proprietary camera buffers, preview, still capture, recording and process isolation may expose compatibility problems.

Evidence: frameworks/av commit 7db8eb3de32436269109f8168d24f19d90cb24ce, device policy commit 02f04d2b0a57f1c7435dc9f2ce8fac2640b38782 legacy-common/sepolicy.mk, common device commit b018612a7939d3a4ab8900e3d03ac1ca608546a0. Build defaults inspected in vendor/lineage lineage-18.1; fresh CI source regeneration must confirm selection.

Actual local checkpolicy replay used run 40406491838 inputs plus the previous init restriction, removed only the conditional legacy HAL1 policy section from both expanded inputs, and reported two remaining failures (cbd sysfs_sec_switch write and hal_sensors_default sysfs_input write). This is NOT a completed source-generated policy build. Three camera patch regression tests and the two preceding init tests passed locally. Entire project suite runs in CI.

Required validation: regenerate policy from source; inspect installed init services and selected camera binaries; compile boot/system; test both cameras, preview, photo, recording, sleep/wake, and multimedia alongside pen use on SM-P900. All hardware checks remain NOT TESTED. Not approved for flashing.
