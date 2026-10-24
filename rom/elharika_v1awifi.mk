# Exact-model development product. Upstream licensing remains in inherited sources.
$(call inherit-product, device/samsung/v1awifi/lineage_v1awifi.mk)
PRODUCT_NAME := elharika_v1awifi
PRODUCT_DEVICE := v1awifi
PRODUCT_MODEL := SM-P900
PRODUCT_PACKAGES += ElharikaLauncherLite ElharikaPenTools
PRODUCT_LOCALES := en_US fr_FR ar_MA
# No Google package bundle or root package is added here.
# Upstream base apps and fingerprint still require review before a final release.
