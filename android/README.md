# FINZANJIR Android client

Application label: **Finzanjir sun’iy ongi**  
Application ID: `uz.finzanjir.app`

## Architecture

This is a thin native Android WebView client. It loads the hosted FINZANJIR frontend from:

- `https://finzanjir-grounded-ai-7veo.onrender.com/`

The hosted frontend calls the shared API:

- `https://finzanjir-grounded-ai-api.onrender.com`

The Android package does not embed provider API keys, model weights, prompts, the knowledge corpus, or risk-engine logic. Those remain on the server. Backend AI/model/knowledge changes therefore become available without rebuilding the APK. Frontend changes are available after the Render static-site deployment completes.

## Build

The GitHub Actions workflow `.github/workflows/android-apk.yml` builds a debug APK on changes to this directory and on manual dispatch. Download the artifact named `finzanjir-suniy-ongi-debug-apk` from the workflow run.

Local build requirements: JDK 17, Android SDK platform 35/build tools 35, Gradle 8.9.

```sh
gradle -p android assembleDebug
```

APK output:

```
android/app/build/outputs/apk/debug/app-debug.apk
```

## Update behavior

- Server AI, prompts, retrieval, knowledge, detectors and API changes: no APK rebuild required.
- Hosted frontend changes: Render redeploy updates the app's next page load; no APK rebuild required.
- Native Android changes, app icon, permissions, or offline/native features: rebuild APK required.

## Network and security

- HTTPS only; cleartext HTTP disabled.
- Only the FINZANJIR frontend and API hosts are kept inside the app.
- Other web links open outside the app.
- WebView file/content access is disabled and mixed content is blocked.
- No API keys or provider credentials are stored in the APK.
- The offline page provides a retry action; the app does not claim the service is available when it cannot connect.

The current backend remains a synthetic prototype. This APK does not enable real bank integrations, cross-bank exchange, or authoritative financial decisions. A debug APK is suitable for controlled installation/testing; Play Store publication requires a privately managed release signing key and a separate release validation.
