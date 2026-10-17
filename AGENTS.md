# TikTok Clean release workflow

Current profile: `scripts/build_you_privacy.py`, `src/mod/privacy`, input You 4.4 / 46.8.3. Older 47.x files are historical; do not mix their patches into this profile.

The user requested public updates at `topikajo/tiktok-clean` and uses GitHub Desktop with this checkout. Preserve this checkout and remote so commits and pushes remain visible there. Publish completed APK updates to GitHub Releases after validation. Do not create recurring tasks merely for this workflow.

For an APK change:

1. Increase VERSION and use the existing local signing key. Never print, stage or upload `tools/signing`, passwords, tokens, raw APK inputs or device/account data.
2. Build with `python scripts/build_you_privacy.py`; run `python scripts/test_privacy_jvm.py` and `python scripts/run_privacy_stress.py fixed`.
3. Use only the disposable TikTokAudit AVD, serial emulator-5580. Build normal, stress and updater probes with `scripts/build_you_probe.py`, `--stress`, `--updates`; install the release and run `scripts/test_you_android.py`.
4. Run `scripts/verify_you_privacy.py`, then `scripts/smoke_you_startup.py`, then `scripts/prepare_public_release.py`. Keep reports bound to the actual APK hash and source hashes. Update claims/docs to actual evidence.
5. Review staged files for secrets. Commit source/docs/tests, push main (GitHub Desktop is connected), then run `scripts/publish_github_release.py`. It stages a draft with immutable APK URL and publishes only after asset verification. Do not replace an already published release's APK under the same version.

Retain red likes and core native functionality. After feed refresh select the first fresh video immediately; leave the previous video one reverse swipe away. No return button or old-video-first view.

The Android probes isolate the native bootstrap and use a test-only boot receiver. They do not establish real account login, live feed, comment stickers, physical devices or decoder/GPU performance. Never claim those tested based on compilation, component simulations or guest startup.
