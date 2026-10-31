#!/usr/bin/env python3
"""Compatibility entry point for the pinned SM-P900 Android 11 manifest generator."""
from prepare_sync_manifest_impl import REQUIRED_PLATFORM_PROJECTS, overlay, main

__all__ = ['REQUIRED_PLATFORM_PROJECTS', 'overlay', 'main']

if __name__ == '__main__':
    main()
