[app]
title = H&M 德扑值守
package.name = pokerduty
package.domain = com.hm
source.dir = .
source.include_exts = py,png,jpg,jpeg,json
version = 2.3.3
requirements = python3,kivy==2.3.0,plyer
orientation = portrait
fullscreen = 0
android.permissions = READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE
android.api = 31
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a
android.accept_sdk_license = True
android.allow_backup = True
p4a.bootstrap = sdl2
p4a.branch = v2024.01.21
[buildozer]
log_level = 2
warn_on_root = 1
