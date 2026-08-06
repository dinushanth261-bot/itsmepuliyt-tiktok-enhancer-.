[app]
title = TikTok Enhancer
package.name = tiktok_enhancer
package.domain = com.itsmepuliyt
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,html,css,js,json,txt
version = 1.0.0
requirements = python3,flask,flask-cors,gunicorn,requests,jinja2,markupsafe,werkzeug,itsdangerous

orientation = portrait
fullscreen = 0
android.permissions = INTERNET, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE

[buildozer]
log_level = 2
warn_on_root = 1
