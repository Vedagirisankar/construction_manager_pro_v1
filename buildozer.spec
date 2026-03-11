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

# Requirements — removed sqlite3 (built-in), removed python3 version pin
requirements = kivy==2.3.0,kivymd==1.2.0,reportlab,openpyxl,pillow

# Orientation
orientation = portrait

# Android permissions
android.permissions = WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE, INTERNET

# Android API
android.api = 33
android.minapi = 24
android.ndk = 25b
android.sdk = 33
android.build_tools_version = 33.0.2
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True

# Icon / Presplash
# icon.filename = %(source.dir)s/icon.png
# presplash.filename = %(source.dir)s/presplash.png

[buildozer]
log_level = 2
warn_on_root = 1
