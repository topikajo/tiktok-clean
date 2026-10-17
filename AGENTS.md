# TikTok Clean release workflow

Current profile: `scripts/build_you_privacy.py`, `src/mod/privacy`, input You 4.4 / 46.8.3. Older 47.x files are historical; do not mix their patches into this profile.

The user requested public updates at `topikajo/tiktok-clean` and uses GitHub Desktop with this checkout. Preserve this checkout and remote so commits and pushes remain visible there. Publish completed APK updates to GitHub Releases after validation. Do not create recurring tasks merely for this workflow.

For an APK change:

1. Increase VERSION and use the existing local signing key. Never print, stage or upload `tools/signing`, passwords, tokens, raw APK inputs or device/account data.
2. Build with `python scripts/build_you_privacy.py`; run `python scripts/test_privacy_jvm.py` and `python scripts/run_privacy_stress.py fixed`.
3. Use only the disposable TikTokAudit AVD, serial emulator-5580. Build normal, stress and updater probes with `scripts/build_you_probe.py`, `--stress`, `--updates`; install the release and run `scripts/test_you_android.py`.
4. Run `scripts/verify_you_privacy.py`, then `scripts/smoke_you_startup.py`, then `scripts/prepare_public_release.py`. Keep reports bound to the actual APK hash and source hashes. Update claims/docs to actual evidence.
5. Review staged files for secrets. Commit source/docs/tests, push main (GitHub Desktop is connected), then run `scripts/publish_github_release.py`. Consumer `clean-V` Releases contain only `ttc-arm8.apk` and the identical `ttc-arm64.apk` alias. Put JSON, hashes and reports in a separate `technical-V` prerelease, never alongside consumer APKs. Publish only after asset verification. Do not replace an already published release's APK bytes under the same version.
6. The updater reads `https://raw.githubusercontent.com/topikajo/tiktok-clean/updates/update.json`. Advance this separate technical branch only after the consumer APK is public and verified. The publisher uses an isolated generated checkout under `tools/update-channel`; do not switch the main checkout to that branch. Original build 2024608033 needs one manual upgrade or custom source change after this migration.

Current base contains arm64-v8a only. ARM8/ARM64 filenames are aliases, not different builds. Do not publish ARM7/ARM32 filenames unless their APK actually contains supported armeabi-v7a native code and has been checked separately. GitHub's automatic Source code archives are outside the uploaded asset list.

Retain red likes and core native functionality. After feed refresh select the first fresh video immediately; leave the previous video one reverse swipe away. No return button or old-video-first view.

The Android probes isolate the native bootstrap and use a test-only boot receiver. They do not establish real account login, live feed, comment stickers, physical devices or decoder/GPU performance. Never claim those tested based on compilation, component simulations or guest startup.
