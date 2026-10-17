import pathlib,zipfile,json
p=pathlib.Path('analysis/avd');a=p/'TikTokAudit.avd';a.mkdir(parents=True,exist_ok=True)
s=pathlib.Path('C:/Users/robot/.android/avd/Medium_Phone.avd/config.ini').read_text()
updates={'AvdId':'TikTokAudit','avd.ini.displayname':'TikTok Audit Disposable','image.sysdir.1':'C:/Users/robot/AppData/Local/Android/Sdk/system-images/android-36.1/google_apis_playstore/x86_64/','hw.ramSize':'4096','hw.gpu.mode':'swiftshader_indirect','fastboot.forceColdBoot':'yes','fastboot.forceFastBoot':'no','hw.lcd.width':'1080','hw.lcd.height':'2400','hw.camera.back':'none','hw.camera.front':'none'}
d=dict(l.split('=',1) for l in s.splitlines() if '=' in l);d.update(updates)
(a/'config.ini').write_text('\n'.join(k+'='+v for k,v in d.items())+'\n')
(p/'TikTokAudit.ini').write_text('avd.ini.encoding=UTF-8\npath='+str(a.resolve())+'\ntarget=android-36.1\n')
print(a.resolve())
