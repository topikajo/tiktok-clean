"""Move Clean 33 reports to a technical prerelease without rebuilding its APK.

Read-only plan by default; pass --apply to perform the user-requested migration.
Every original asset is backed up and verified before any remote mutation. An
interrupted run can be resumed with the same command. No main-branch files,
update feed, signing key, APK bytes or existing source tag are changed here.
"""

import argparse
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import time
import urllib.request


ROOT = pathlib.Path(__file__).resolve().parents[1]
GH = ROOT / "tools/gh/gh.exe"
REPO = "topikajo/tiktok-clean"
TAG = "clean-2024608033"
TECH_TAG = "technical-2024608033"
RELEASE_ID = 415668087
APK_ID = 649925516
APK_SIZE = 381670326
OLD_APK = "TikTokClean-arm64.apk"
ARM8 = "ttc-arm8.apk"
ARM64 = "ttc-arm64.apk"
APK_SHA = "f2f4befe66c6a9cae3c1bceb2d1c728d0ea8a9a62584d7e5379cd0972b39117c"
ORIGINAL_DIGESTS = {
    OLD_APK: APK_SHA,
    "build.json": "28ca369f4da9cc0bf4ec761c7f2e99f76e97cddd38eabd22d83f977c18aa9f0c",
    "verification.json": "9035b632ec15e381e0c1609af1baafd5fcdb374c5382129d4949d8b59f3ab39c",
    "stress.json": "480a371b97e534a3235edeac8ea8b388431979563085c09ea5c41098c2f78803",
    "SHA256SUMS.txt": "13c9aba31f7f5ddf8d404aaf5225d24305bc093f452d1b5ab7f868009be3ff43",
    "update.json": "68153a426f4d0618d041dd4629ebef0c9130ec2ae52741869de5814e77364888",
}
METADATA = tuple(name for name in ORIGINAL_DIGESTS if name != OLD_APK)
BACKUP = ROOT / "analysis/release-layout-backup" / TAG
ENDPOINT = f"repos/{REPO}"


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def run(*args):
    result = subprocess.run(
        [str(arg) for arg in args], cwd=ROOT, capture_output=True,
        text=True, encoding="utf8",
    )
    require(result.returncode == 0, result.stderr.strip() or "GitHub CLI failed")
    return result.stdout


def api(path, *, method="GET", payload=None, optional=False):
    args = [str(GH), "api", path, "--method", method]
    if payload is not None:
        # JSON stays in a file; neither quoting nor shell interpolation is used.
        requests = BACKUP / "api-input"
        requests.mkdir(parents=True, exist_ok=True)
        source = requests / f"{time.time_ns()}.json"
        source.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf8")
        args += ["--input", str(source)]
    result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, encoding="utf8")
    if optional and result.returncode and "HTTP 404" in result.stderr:
        return None
    require(result.returncode == 0, result.stderr.strip() or f"GitHub API failed: {method} {path}")
    return json.loads(result.stdout) if result.stdout.strip() else None


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verified_file(path, digest, size):
    return path.is_file() and path.stat().st_size == size and sha(path) == digest


def by_name(release):
    assets = release["assets"]
    result = {asset["name"]: asset for asset in assets}
    require(len(result) == len(assets), "Duplicate remote asset names")
    return result


def check_asset(asset, digest, size, name):
    require(asset["state"] == "uploaded", f"Incomplete remote asset: {name}")
    require(asset.get("digest") == "sha256:" + digest, f"Remote digest mismatch: {name}")
    require(asset["size"] == size, f"Remote size mismatch: {name}")


def release(tag):
    found = api(f"{ENDPOINT}/releases/tags/{tag}", optional=True)
    if found is not None:
        return found
    # A draft may not be returned by the by-tag endpoint.
    for page in range(1, 11):
        entries = api(f"{ENDPOINT}/releases?per_page=100&page={page}")
        match = next((item for item in entries if item["tag_name"] == tag), None)
        if match is not None:
            return match
        if len(entries) < 100:
            return None
    raise RuntimeError("Release listing exceeded the bounded pagination limit")


def source_commit(tag, *, optional=False):
    ref = api(f"{ENDPOINT}/git/ref/tags/{tag}", optional=optional)
    if ref is None:
        return None
    obj = ref["object"]
    for _ in range(10):
        require(re.fullmatch(r"[0-9a-f]{40}", obj["sha"]) is not None, "Invalid tag SHA")
        if obj["type"] == "commit":
            return obj["sha"]
        require(obj["type"] == "tag", "Tag does not resolve to a commit")
        obj = api(f"{ENDPOINT}/git/tags/{obj['sha']}")["object"]
    raise RuntimeError("Tag nesting exceeded the bounded limit")


def backup_original_assets(original):
    original_assets = by_name(original)
    require(set(original_assets) == set(ORIGINAL_DIGESTS), "Unexpected original asset set")
    for name, asset in original_assets.items():
        digest = ORIGINAL_DIGESTS[name]
        check_asset(asset, digest, asset["size"], name)
        target = BACKUP / name
        if verified_file(target, digest, asset["size"]):
            continue
        # Do not overwrite a corrupt or unexpectedly modified existing backup.
        require(not target.exists(), f"Existing backup does not match: {target}")
        part = target.with_name(target.name + ".part")
        if name == OLD_APK:
            candidates = [
                ROOT / "output/publish" / TAG / OLD_APK,
                ROOT / "output/TikTok_Clean_46.8.3_You_Privacy_ARM64.apk",
            ]
            local = next((p for p in candidates if verified_file(p, digest, asset["size"])), None)
            if local is not None:
                shutil.copyfile(local, part)
        if not verified_file(part, digest, asset["size"]):
            url = asset["browser_download_url"]
            require(url.startswith(f"https://github.com/{REPO}/releases/download/{TAG}/"), "Unexpected backup URL")
            # Retrying this read is safe; a partial file never counts as a backup.
            for attempt in range(3):
                try:
                    request = urllib.request.Request(url, headers={"User-Agent": "TikTokClean-layout-migration"})
                    with urllib.request.urlopen(request, timeout=60) as response, part.open("wb") as output:
                        shutil.copyfileobj(response, output, length=4 * 1024 * 1024)
                    require(verified_file(part, digest, asset["size"]), f"Backup verification failed: {name}")
                    break
                except Exception:
                    if attempt == 2:
                        raise
                    time.sleep(attempt + 1)
        require(verified_file(part, digest, asset["size"]), f"Backup verification failed: {name}")
        part.replace(target)
        print(f"Backed up and verified {name}", flush=True)


def assert_latest_unchanged(latest_id):
    latest = api(f"{ENDPOINT}/releases/latest")
    require(latest["id"] == latest_id, "Latest release changed; stop before further mutations")
    require(latest["tag_name"] != TECH_TAG, "Technical prerelease unexpectedly became latest")


def ensure_technical_release(commit, original):
    existing_commit = source_commit(TECH_TAG, optional=True)
    if existing_commit is None:
        api(f"{ENDPOINT}/git/refs", method="POST", payload={"ref": "refs/tags/" + TECH_TAG, "sha": commit})
    else:
        require(existing_commit == commit, "Technical tag points to a different source commit")
    require(source_commit(TECH_TAG) == commit, "Technical tag verification failed")
    technical = release(TECH_TAG)
    notes = (
        f"Архив технических файлов сборки {TAG}. APK для установки находятся в "
        f"[основном выпуске](https://github.com/{REPO}/releases/tag/{TAG}).\n\n"
        "Все пять файлов сохранены побайтно. update.json и SHA256SUMS.txt — исторический "
        "снимок до переименования APK; старое имя TikTokClean-arm64.apk в них не изменялось. "
        "Этот архив не является текущим каналом обновлений.\n"
    )
    if technical is None:
        technical = api(f"{ENDPOINT}/releases", method="POST", payload={
            "tag_name": TECH_TAG, "target_commitish": commit,
            "name": "Технический архив · 2024608033", "body": notes,
            "draft": True, "prerelease": True, "make_latest": "false",
        })
    require(technical["prerelease"], "Existing technical release is not marked prerelease")
    current = by_name(technical)
    require(set(current) <= set(METADATA), "Unexpected asset in technical release")
    sizes = {name: by_name(original)[name]["size"] for name in METADATA}
    for name in METADATA:
        if name in current:
            check_asset(current[name], ORIGINAL_DIGESTS[name], sizes[name], name)
        else:
            require(technical["draft"], f"Published technical archive lacks {name}; refusing to modify its contents")
            run(GH, "release", "upload", TECH_TAG, "--repo", REPO, BACKUP / name)
    technical = api(f"{ENDPOINT}/releases/{technical['id']}")
    current = by_name(technical)
    require(set(current) == set(METADATA), "Technical archive asset set mismatch")
    for name in METADATA:
        check_asset(current[name], ORIGINAL_DIGESTS[name], sizes[name], name)
        if technical["draft"]:
            api(f"{ENDPOINT}/releases/assets/{current[name]['id']}", method="PATCH", payload={
                "name": name, "label": "Архив: исходный файл без изменений",
            })
    if technical["draft"]:
        technical = api(f"{ENDPOINT}/releases/{technical['id']}", method="PATCH", payload={
            "draft": False, "prerelease": True, "make_latest": "false", "body": notes,
        })
    require(not technical["draft"] and technical["prerelease"], "Technical archive publication failed")
    return technical


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Perform the reviewed migration; default prints a read-only plan")
    args = parser.parse_args()
    current = release(TAG)
    require(current is not None and current["id"] == RELEASE_ID, "Unexpected consumer release")
    require(not current["draft"] and not current["prerelease"], "Consumer release must remain a published stable release")
    require(not current.get("immutable", False), "GitHub release immutability prevents this migration")
    latest = api(f"{ENDPOINT}/releases/latest")
    require(latest["tag_name"] != TECH_TAG, "Technical archive must not be latest")
    commit = source_commit(TAG)
    current_assets = by_name(current)
    require(set(current_assets) <= set(ORIGINAL_DIGESTS) | {ARM8, ARM64}, "Unexpected consumer asset set")
    original_file = BACKUP / "original-release.json"
    if original_file.exists():
        original = json.loads(original_file.read_text(encoding="utf8"))
    else:
        require(set(current_assets) == set(ORIGINAL_DIGESTS), "Original snapshot is missing after migration started")
        original = current
    require(original["id"] == RELEASE_ID and original["tag_name"] == TAG, "Wrong original backup release")
    original_assets = by_name(original)
    require(set(original_assets) == set(ORIGINAL_DIGESTS), "Incomplete original release snapshot")
    require(original_assets[OLD_APK]["id"] == APK_ID and original_assets[OLD_APK]["size"] == APK_SIZE, "Original APK identity changed")
    for name, digest in ORIGINAL_DIGESTS.items():
        check_asset(original_assets[name], digest, original_assets[name]["size"], name)
    for name, asset in current_assets.items():
        if name in METADATA:
            check_asset(asset, ORIGINAL_DIGESTS[name], original_assets[name]["size"], name)
        else:
            check_asset(asset, APK_SHA, APK_SIZE, name)
    print(json.dumps({
        "apply": args.apply, "release": current["html_url"], "source_commit": commit,
        "backup": str(BACKUP), "technical_tag": TECH_TAG,
        "consumer_apks": [ARM8, ARM64], "apk_sha256": APK_SHA,
        "preserve_latest": latest["tag_name"], "metadata_to_move": list(METADATA),
    }, ensure_ascii=False, indent=2), flush=True)
    if not args.apply:
        return
    BACKUP.mkdir(parents=True, exist_ok=True)
    if not original_file.exists():
        # Exclusive creation preserves the initial release metadata on every retry.
        with original_file.open("x", encoding="utf8") as output:
            json.dump(original, output, ensure_ascii=False, indent=2)
            output.write("\n")
    backup_original_assets(original)
    technical = ensure_technical_release(commit, original)
    assert_latest_unchanged(latest["id"])
    current = api(f"{ENDPOINT}/releases/{RELEASE_ID}")
    current_assets = by_name(current)
    original_apk = next((a for a in current["assets"] if a["id"] == APK_ID), None)
    require(original_apk is not None and original_apk["name"] in (OLD_APK, ARM8), "Original APK asset disappeared or was replaced")
    check_asset(original_apk, APK_SHA, APK_SIZE, original_apk["name"])
    if original_apk["name"] == OLD_APK:
        require(ARM8 not in current_assets, "Short APK name already belongs to a different asset")
        api(f"{ENDPOINT}/releases/assets/{APK_ID}", method="PATCH", payload={"name": ARM8, "label": ""})
    elif original_apk.get("label"):
        api(f"{ENDPOINT}/releases/assets/{APK_ID}", method="PATCH", payload={"name": ARM8, "label": ""})
    current_assets = by_name(api(f"{ENDPOINT}/releases/{RELEASE_ID}"))
    if ARM64 not in current_assets:
        staging = BACKUP / "aliases"
        staging.mkdir(exist_ok=True)
        alias = staging / ARM64
        if not alias.exists():
            try:
                os.link(BACKUP / OLD_APK, alias)
            except OSError:
                shutil.copyfile(BACKUP / OLD_APK, alias)
        require(verified_file(alias, APK_SHA, APK_SIZE), "Local alias differs from original APK")
        run(GH, "release", "upload", TAG, "--repo", REPO, alias)
    current_assets = by_name(api(f"{ENDPOINT}/releases/{RELEASE_ID}"))
    for name in (ARM8, ARM64):
        require(name in current_assets, f"Missing consumer APK: {name}")
        check_asset(current_assets[name], APK_SHA, APK_SIZE, name)
    notes = (
        f"[Скачать ttc-arm8.apk](https://github.com/{REPO}/releases/download/{TAG}/{ARM8}) · "
        f"[Скачать ttc-arm64.apk](https://github.com/{REPO}/releases/download/{TAG}/{ARM64})\n\n"
        "ARM8 и ARM64 — два имени одного и того же APK; достаточно скачать любой один. "
        "ARM7/32-bit не поддерживается текущей основой You 4.4 / TikTok 46.8.3.\n\n"
        "Сохранены подпись и содержимое ранее опубликованного APK. "
        f"[Отчёты и исторические метаданные](https://github.com/{REPO}/releases/tag/{TECH_TAG}) вынесены отдельно.\n\n"
        "Для канала обновлений этой сборки потребуется один раз установить следующую сборку Clean 34 "
        "или указать долгим нажатием на строку обновления в настройках HTTPS-источник: "
        f"https://raw.githubusercontent.com/{REPO}/updates/update.json .\n\n"
        "Реальные аккаунты, живая лента и физические устройства пока не проверены. "
        "Перед удалением чужого TikTok сохраните черновики.\n"
    )
    api(f"{ENDPOINT}/releases/{RELEASE_ID}", method="PATCH", payload={"body": notes})
    # Verify the published copy immediately before each authorized removal.
    for name in METADATA:
        archived = by_name(api(f"{ENDPOINT}/releases/{technical['id']}"))
        require(name in archived, f"Technical copy missing before deletion: {name}")
        check_asset(archived[name], ORIGINAL_DIGESTS[name], original_assets[name]["size"], name)
        require(verified_file(BACKUP / name, ORIGINAL_DIGESTS[name], original_assets[name]["size"]), f"Backup missing before deletion: {name}")
        consumer = by_name(api(f"{ENDPOINT}/releases/{RELEASE_ID}"))
        if name in consumer:
            check_asset(consumer[name], ORIGINAL_DIGESTS[name], original_assets[name]["size"], name)
            api(f"{ENDPOINT}/releases/assets/{consumer[name]['id']}", method="DELETE")
    final = api(f"{ENDPOINT}/releases/{RELEASE_ID}")
    final_assets = by_name(final)
    require(set(final_assets) == {ARM8, ARM64}, "Consumer release still has unexpected assets")
    require(final_assets[ARM8]["id"] == APK_ID, "The original APK asset was replaced")
    for name in (ARM8, ARM64):
        check_asset(final_assets[name], APK_SHA, APK_SIZE, name)
    assert_latest_unchanged(latest["id"])
    result = {"release": final["html_url"], "technical": technical["html_url"],
              "apk_sha256": APK_SHA, "source_commit": commit, "latest_unchanged": latest["tag_name"],
              "assets": {name: asset["browser_download_url"] for name, asset in final_assets.items()}}
    (BACKUP / "migration-result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
