package uz.finzanjir.app

import android.annotation.SuppressLint
import android.app.Activity
import android.content.Intent
import android.graphics.Color
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.view.ViewGroup
import android.webkit.RenderProcessGoneDetail
import android.webkit.SafeBrowsingResponse
import android.webkit.WebChromeClient
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.FrameLayout
import android.widget.TextView
import androidx.core.view.WindowCompat

/**
 * Thin Android client for the server-hosted FINZANJIR application.
 *
 * The UI, AI model, prompts, knowledge corpus and orchestration remain server-side.
 * Loading the hosted frontend means server deployments update the app without APK rebuilds.
 */
class MainActivity : Activity() {
    private lateinit var container: FrameLayout
    private lateinit var webView: WebView
    private var showingOfflinePage = false

    private val appUrl = "https://finzanjir-grounded-ai-7veo.onrender.com/"
    private val allowedHosts = setOf(
        "finzanjir-grounded-ai-7veo.onrender.com",
        "finzanjir-grounded-ai-api.onrender.com"
    )

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.statusBarColor = Color.rgb(18, 59, 99)
        window.navigationBarColor = Color.rgb(16, 44, 70)
        WindowCompat.setDecorFitsSystemWindows(window, true)

        container = FrameLayout(this)
        webView = WebView(this)
        container.addView(
            webView,
            FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT
            )
        )
        setContentView(container)

        webView.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            databaseEnabled = false
            allowFileAccess = false
            allowContentAccess = false
            javaScriptCanOpenWindowsAutomatically = false
            setSupportMultipleWindows(false)
            mixedContentMode = android.webkit.WebSettings.MIXED_CONTENT_NEVER_ALLOW
            cacheMode = android.webkit.WebSettings.LOAD_DEFAULT
        }

        webView.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(
                view: WebView?,
                request: WebResourceRequest?
            ): Boolean {
                val uri = request?.url ?: return true
                val scheme = uri.scheme ?: return true
                if (scheme == "https" && uri.host in allowedHosts) return false

                if (scheme == "https" || scheme == "http") {
                    return try {
                        startActivity(Intent(Intent.ACTION_VIEW, uri))
                        true
                    } catch (_: Exception) {
                        true
                    }
                }
                return true
            }

            override fun onPageStarted(view: WebView?, url: String?, favicon: android.graphics.Bitmap?) {
                showingOfflinePage = false
            }

            override fun onReceivedError(
                view: WebView?,
                request: WebResourceRequest?,
                error: WebResourceError?
            ) {
                if (request?.isForMainFrame == true) showOfflinePage()
            }

            override fun onReceivedHttpError(
                view: WebView?,
                request: WebResourceRequest?,
                errorResponse: android.webkit.WebResourceResponse?
            ) {
                if (request?.isForMainFrame == true &&
                    (errorResponse?.statusCode ?: 0) >= 500
                ) showOfflinePage()
            }

            override fun onRenderProcessGone(
                view: WebView?,
                detail: RenderProcessGoneDetail?
            ): Boolean {
                container.removeView(webView)
                webView.destroy()
                createWebView()
                showOfflinePage()
                return true
            }
        }
        webView.webChromeClient = WebChromeClient()

        if (savedInstanceState == null || !webView.restoreState(savedInstanceState).let { it != null }) {
            webView.loadUrl(appUrl)
        }
    }

    @SuppressLint("SetJavaScriptEnabled")
    private fun createWebView() {
        webView = WebView(this)
        webView.settings.javaScriptEnabled = true
        webView.settings.domStorageEnabled = true
        webView.settings.allowFileAccess = false
        webView.settings.allowContentAccess = false
        webView.settings.mixedContentMode = android.webkit.WebSettings.MIXED_CONTENT_NEVER_ALLOW
        webView.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(view: WebView?, request: WebResourceRequest?): Boolean {
                val uri = request?.url ?: return true
                if (uri.scheme == "https" && uri.host in allowedHosts) return false
                return true
            }
            override fun onReceivedError(view: WebView?, request: WebResourceRequest?, error: WebResourceError?) {
                if (request?.isForMainFrame == true) showOfflinePage()
            }
        }
        webView.webChromeClient = WebChromeClient()
        container.addView(webView, FrameLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.MATCH_PARENT
        ))
    }

    private fun showOfflinePage() {
        if (showingOfflinePage || !::webView.isInitialized) return
        showingOfflinePage = true
        val html = """
            <!doctype html><html lang="uz"><meta name="viewport" content="width=device-width,initial-scale=1">
            <meta charset="utf-8"><body style="margin:0;background:#f3f7fa;color:#16334a;font:16px system-ui;display:grid;min-height:100vh;place-items:center">
            <main style="max-width:420px;padding:28px;text-align:center">
            <div style="font-size:38px;font-weight:800;color:#123b63">FINZANJIR</div>
            <h2>Server bilan aloqa vaqtincha yo‘q</h2>
            <p>Internet yoki server javobini tekshiring. Ulanish tiklangach, qayta urinib ko‘ring.</p>
            <button onclick="location.href='$appUrl'" style="border:0;border-radius:12px;background:#123b63;color:white;padding:14px 22px;font-size:16px">Qayta ulanish</button>
            </main></body></html>
        """.trimIndent()
        webView.loadDataWithBaseURL(appUrl, html, "text/html", "UTF-8", null)
    }

    override fun onSaveInstanceState(outState: Bundle) {
        if (::webView.isInitialized && !showingOfflinePage) webView.saveState(outState)
        super.onSaveInstanceState(outState)
    }

    @Deprecated("Deprecated in Android API 33")
    override fun onBackPressed() {
        if (::webView.isInitialized && webView.canGoBack() && !showingOfflinePage) {
            webView.goBack()
        } else {
            super.onBackPressed()
        }
    }

    override fun onDestroy() {
        if (::webView.isInitialized) {
            container.removeView(webView)
            webView.destroy()
        }
        super.onDestroy()
    }
}
