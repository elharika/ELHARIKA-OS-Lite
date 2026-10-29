# Exact-model development product. Upstream licensing remains in inherited sources.
$(call inherit-product, device/samsung/v1awifi/lineage_v1awifi.mk)
PRODUCT_NAME := elharika_v1awifi
PRODUCT_DEVICE := v1awifi
PRODUCT_MODEL := SM-P900
PRODUCT_PACKAGES += ElharikaLauncherLite ElharikaPenTools
PRODUCT_LOCALES := en_US fr_FR ar_MA

# GitHub-hosted bring-up profile: reduce Android build intermediates and image size.
# Dexpreopt is intentionally disabled for development system-image builds; ART can
# compile code on-device after first boot. Re-enable for release/performance builds.
WITH_DEXPREOPT := false
PRODUCT_ART_TARGET_INCLUDE_DEBUG_BUILD := false

# Keep the initial bring-up image lean. These apps are not required to validate
# boot, display, touch, Wi-Fi, pen, audio, or core framework bring-up.
PRODUCT_PACKAGES -= Updater Gallery2 ThemePicker

# No Google package bundle or root package is added here.
# Upstream base apps and fingerprint still require review before a final release.
