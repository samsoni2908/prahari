package org.prahari.mobile;

import android.annotation.SuppressLint;
import android.content.Context;
import android.content.Intent;
import android.graphics.Bitmap;
import android.net.ConnectivityManager;
import android.net.NetworkInfo;
import android.net.Uri;
import android.os.Bundle;
import android.view.KeyEvent;
import android.view.View;
import android.webkit.CookieManager;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.ProgressBar;
import android.widget.TextView;
import androidx.appcompat.app.AppCompatActivity;
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout;

public class MainActivity extends AppCompatActivity {

    private WebView mWebView;
    private ProgressBar mProgressBar;
    private SwipeRefreshLayout mSwipeRefresh;
    private View mErrorContainer;
    private TextView mErrorText;

    // Configured target server URL (change for production deployment)
    private static final String DEFAULT_URL = "https://prahari.up.railway.app/login";
    private String mTargetUrl = DEFAULT_URL;

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        mWebView = findViewById(R.id.webview);
        mProgressBar = findViewById(R.id.progressBar);
        mSwipeRefresh = findViewById(R.id.swipeRefresh);
        mErrorContainer = findViewById(R.id.errorContainer);
        mErrorText = findViewById(R.id.errorText);

        // Determine server URL from build config or intent
        if (BuildConfig.SERVER_URL != null && !BuildConfig.SERVER_URL.isEmpty()) {
            mTargetUrl = BuildConfig.SERVER_URL;
        }
        mTargetUrl = mTargetUrl.replaceAll("[\"\'\\s]", "").trim();
        Uri target = Uri.parse(mTargetUrl);
        if (target.getHost() == null || (!"https".equalsIgnoreCase(target.getScheme())
                && !(BuildConfig.DEBUG && "http".equalsIgnoreCase(target.getScheme())
                && ("10.0.2.2".equals(target.getHost()) || "localhost".equals(target.getHost()))))) {
            showError("Invalid application URL. Release builds require HTTPS.");
            return;
        }

        // Enable Chrome remote debugging on debug builds
        if (BuildConfig.DEBUG) {
            WebView.setWebContentsDebuggingEnabled(true);
        }

        // Configure WebView
        mWebView.setBackgroundColor(0xFFFAF9F5);
        WebSettings webSettings = mWebView.getSettings();
        webSettings.setJavaScriptEnabled(true);
        webSettings.setDomStorageEnabled(true);
        webSettings.setDatabaseEnabled(true);
        webSettings.setUseWideViewPort(true);
        webSettings.setLoadWithOverviewMode(true);
        webSettings.setSupportZoom(false);
        webSettings.setBuiltInZoomControls(false);
        webSettings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        webSettings.setUserAgentString(webSettings.getUserAgentString() + " PrahariApp/" + BuildConfig.VERSION_NAME);
        webSettings.setAllowFileAccess(false);
        webSettings.setAllowContentAccess(false);
        webSettings.setCacheMode(WebSettings.LOAD_DEFAULT);

        // Same-origin session cookies; third-party cookies are not required.
        CookieManager cookieManager = CookieManager.getInstance();
        cookieManager.setAcceptCookie(true);
        cookieManager.setAcceptThirdPartyCookies(mWebView, false);

        // WebView Client
        mWebView.setWebViewClient(new WebViewClient() {
            @Override
            public void onPageStarted(WebView view, String url, Bitmap favicon) {
                mProgressBar.setVisibility(View.VISIBLE);
                mErrorContainer.setVisibility(View.GONE);
                mWebView.setVisibility(View.VISIBLE);
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                mProgressBar.setVisibility(View.GONE);
                mSwipeRefresh.setRefreshing(false);
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                if (request.isForMainFrame()) {
                    mProgressBar.setVisibility(View.GONE);
                    mSwipeRefresh.setRefreshing(false);
                    String desc = "";
                    if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.M && error != null) {
                        desc = " (" + error.getDescription() + ")";
                    }
                    showError("Unable to reach the PRAHARI server at " + mTargetUrl + desc + ". Check network connectivity.");
                }
            }

            @Override
            public void onReceivedHttpError(WebView view, WebResourceRequest request, android.webkit.WebResourceResponse errorResponse) {
                if (request.isForMainFrame() && errorResponse != null && errorResponse.getStatusCode() >= 400) {
                    mProgressBar.setVisibility(View.GONE);
                    mSwipeRefresh.setRefreshing(false);
                    showError("Server returned error " + errorResponse.getStatusCode() + " at " + mTargetUrl + ". Please verify backend status.");
                }
            }

            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                Uri trusted = Uri.parse(mTargetUrl);
                if (uri != null && uri.getHost() != null
                        && uri.getHost().equalsIgnoreCase(trusted.getHost())
                        && uri.getScheme() != null && uri.getScheme().equalsIgnoreCase(trusted.getScheme())
                        && uri.getPort() == trusted.getPort()) return false;
                // External links open in default browser
                if (uri != null && ("https".equalsIgnoreCase(uri.getScheme()) || "http".equalsIgnoreCase(uri.getScheme()))) {
                    try { startActivity(new Intent(Intent.ACTION_VIEW, uri)); } catch (Exception ignored) {}
                }
                return true;
            }
        });

        // WebChromeClient for progress bar and console logging
        mWebView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onProgressChanged(WebView view, int newProgress) {
                mProgressBar.setProgress(newProgress);
                if (newProgress >= 100) {
                    mProgressBar.setVisibility(View.GONE);
                } else {
                    mProgressBar.setVisibility(View.VISIBLE);
                }
            }

            @Override
            public boolean onConsoleMessage(android.webkit.ConsoleMessage consoleMessage) {
                if (BuildConfig.DEBUG) android.util.Log.d("PrahariApp", consoleMessage.message());
                return true;
            }
        });

        // Pull to refresh
        mSwipeRefresh.setOnRefreshListener(() -> mWebView.reload());
        mSwipeRefresh.setColorSchemeColors(0xFF2C5127, 0xFF15803D, 0xFFCFDDCE);

        // Retry button in error screen
        findViewById(R.id.btnRetry).setOnClickListener(v -> {
            mErrorContainer.setVisibility(View.GONE);
            mWebView.setVisibility(View.VISIBLE);
            mWebView.loadUrl(mTargetUrl);
        });

        // Initial load
        mWebView.loadUrl(mTargetUrl);
    }

    private void showError(String message) {
        mWebView.setVisibility(View.GONE);
        mErrorContainer.setVisibility(View.VISIBLE);
        if (mErrorText != null) {
            mErrorText.setText(message);
        }
    }

    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) {
        if (keyCode == KeyEvent.KEYCODE_BACK && mWebView.canGoBack()) {
            mWebView.goBack();
            return true;
        }
        return super.onKeyDown(keyCode, event);
    }
}
