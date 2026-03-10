[app]
# App identity
title = Construction Manager Pro
package.name = constructionpro
package.domain = org.construction

# Source
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,db
source.exclude_dirs = tests, bin, .buildozer, __pycache__, dist, build

# Version
version = 1.0

# Requirements — keep reportlab/openpyxl for export_utils.py
requirements = python3==3.11,kivy==2.3.0,kivymd==1.2.0,sqlite3,reportlab,openpyxl,pillow

# Orientation
orientation = portrait

# Android permissions
android.permissions = WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE, INTERNET

# Android API
android.api = 33
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a

# Icon / Presplash (add your own icon.png / presplash.png here)
# icon.filename = %(source.dir)s/icon.png
# presplash.filename = %(source.dir)s/presplash.png

# Leave debug for now (use 'release' when signing for Play Store)
# android.release_artifact = aab

[buildozer]
log_level = 2
warn_on_root = 1
