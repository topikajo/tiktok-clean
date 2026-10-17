"""Prepare genuine ARMv7 aliases and separate technical reports without publishing."""
import hashlib,json,pathlib,shutil,zipfile
root=pathlib.Path(__file__).resolve().parents[1]
def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def load(name):return json.loads((root/'release'/name).read_text(encoding='utf8'))
def write(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

def main():
    build=load('arm32-build.json');checks=load('arm32-android-checks.json');startup=load('arm32-startup.json')
    apk=pathlib.Path(build['file']);digest=sha(apk)
    assert digest==build['sha256']==checks['apk_sha256']==startup['apk_sha256']
    assert build['abis']==['armeabi-v7a'] and build['native_libraries_byte_identical_to_official']
    assert build['signature_verified'] and build['zip_16k_alignment_verified']
    assert checks['actual_32bit_process_verified'] and checks['results']['privacy_update']['passed'] and checks['results']['legacy_bindings']['passed']
    for name,expected in build['source_sha256s'].items():assert sha(root/name)==expected,name
    for name,expected in checks['test_source_sha256'].items():assert sha(root/name)==expected,name
    with zipfile.ZipFile(apk) as z:
        libs=[n for n in z.namelist() if n.startswith('lib/') and not n.endswith('/')]
        assert libs and all(n.startswith('lib/armeabi-v7a/') for n in libs)
    consumer='clean-'+str(load('update.json')['versionCode']);technical='technical-arm32-'+str(build['versionCode'])
    folder=root/'output/publish'/technical;folder.mkdir(parents=True,exist_ok=True)
    for name in ('ttc-arm7.apk','ttc-arm32.apk'):
        if not (folder/name).exists() or sha(folder/name)!=digest:shutil.copyfile(apk,folder/name)
    experimental=not startup['normal_startup_verified'] or not build['physical_device_verified']
    feed={'packageName':'com.zhiliaoapp.musically','versionCode':build['versionCode'],'versionName':'47.1.4 Clean ARM7',
          'sha256':digest,'apkUrls':['https://github.com/topikajo/tiktok-clean/releases/download/'+consumer+'/ttc-arm7.apk'],
          'notes':'Отдельная ARMv7-сборка на основе 47.1.4. Проверка на физическом телефоне требуется.'}
    write(folder/'update-arm32.json',feed)
    public_build=dict(build)
    for key in ('file','source','upstream'):public_build[key]=pathlib.Path(public_build[key]).name
    public_checks=dict(checks);public_checks.pop('serial',None)
    write(folder/'build-arm32.json',public_build);write(folder/'android-checks-arm32.json',public_checks);write(folder/'startup-arm32.json',startup)
    (folder/'SHA256SUMS-arm32.txt').write_text(''.join(digest+'  '+name+'\n' for name in ('ttc-arm7.apk','ttc-arm32.apk')),encoding='utf8')
    distribution={'consumer_tag':consumer,'technical_tag':technical,'versionCode':build['versionCode'],'baseVersion':build['baseVersion'],
                  'sha256':digest,'size':apk.stat().st_size,'experimental':experimental,'normal_startup_verified':startup['normal_startup_verified'],
                  'physical_device_verified':False,'assets':['ttc-arm7.apk','ttc-arm32.apk']}
    write(root/'release/arm32-distribution.json',distribution)
    (folder/'technical-notes.md').write_text('ARMv7 / 32-bit · отдельная основа TikTok 47.1.4, код '+str(build['versionCode'])+'.\n\n'
        'Здесь только технические файлы. APK: [основной выпуск](https://github.com/topikajo/tiktok-clean/releases/tag/'+consumer+'). '
        'ARM7 и ARM32 — одинаковые файлы. Библиотеки совпадают с официальной 32-битной основой.\n\n'
        '61 проверка установленного APK и 100 000 обращений к SDK-модели прошли в 32-битном процессе с изолированным Application. '
        'Это не проверка реального входа, живой ленты или GPU. Состояние обычного запуска описано в startup-arm32.json; физический телефон не проверен.\n',encoding='utf8')
    (folder/'consumer-notes.md').write_text('Выберите **один** APK под свой телефон:\n\n'
        '- **ttc-arm8.apk / ttc-arm64.apk** — одна 64-битная сборка, основа You 4.4 / TikTok 46.8.3. Для современных Pixel и Poco.\n'
        '- **ttc-arm7.apk / ttc-arm32.apk** — одна настоящая 32-битная сборка ARMv7, отдельная основа TikTok 47.1.4; Android 6+. '
        '**Экспериментальная: физический ARMv7-телефон ещё не проверен.**\n\n'
        'В каждой паре файлы идентичны; два файла скачивать не нужно. x86 не поддерживается. '
        'У ARM32 отдельный канал обновлений; клиент отклоняет APK другой архитектуры.\n\n'
        'ARM64: при обновлении ленты первый новый ролик показывается сразу, прошлый доступен обратным свайпом; сохранение кадра на паузе; '
        'сохранены загрузки и выбор качества из You. ARM32: фильтрация рекламных роликов, отключение найденной Java-аналитики и рекламного ID, '
        'обновления во «Входящих». Сохранение прошлого ролика и кадра на ARM32 пока не перенесены; функции You там отсутствуют.\n\n'
        'Обе сборки: отключены найденные сторонние каналы обновлений, подпись и хеш загружаемого APK проверяются; установка только по нажатию. '
        'Точка во «Входящих» остаётся до проверенной загрузки. Найденные системные запросы разрешений привязаны к действию пользователя.\n\n'
        'Проверки: ARM64 — 45 JVM-правил, 100 000 сценариев ленты, 100 000 циклов уведомлений, установленный APK и гостевой запуск. '
        'ARM32 — 61 проверка установленного APK, 100 000 обращений к модели видео. '
        'На ARM32 Android 11 x86-транслятор падает в ICU одинаково у мода и нетронутого оригинала; это ограничивает проверку обычного запуска. '
        'Реальный вход, живая лента и физические устройства не проверены; модели нагрузки не измеряют FPS/GPU.\n\n'
        'Отчёты: [ARM64](https://github.com/topikajo/tiktok-clean/releases/tag/technical-'+consumer.removeprefix('clean-')+'), '
        '[ARM32 и его исходники](https://github.com/topikajo/tiktok-clean/releases/tag/'+technical+'). '
        'Встроенные GitHub-архивы Source code скачивать для установки не нужно.\n\n'
        'Сохраните черновики перед удалением прежнего приложения. Переход ARM32 → ARM64 может потребовать удаления из-за разных versionCode. '
        'Для Clean 2024608033 один раз установите ARM64 вручную или смените источник на '
        '`https://raw.githubusercontent.com/topikajo/tiktok-clean/updates/update.json`.\n',encoding='utf8')
    (root/'analysis/arm32-public-release-path.txt').write_text(str(folder),encoding='utf8')
    print(json.dumps(distribution,indent=2))
if __name__=='__main__':main()
