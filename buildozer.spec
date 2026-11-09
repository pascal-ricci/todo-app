[app]
title = To-Do Simple
package.name = todosimple
package.domain = org.pascal
source.dir = .
source.exts = py,png,jpg,kv,atlas,json
version = 1.0
requirements = python3,kivy,pip,requests,android
orientation = portrait
fullscreen = 0
android.permissions = INTERNET, ACCESS_NETWORK_STATE
icon.filename = %(source.dir)s/icone_todo.png
# (int) Target Android API, should be as high as possible.
android.api = 33

# (int) Minimum API your APK will support.
android.minapi = 21
