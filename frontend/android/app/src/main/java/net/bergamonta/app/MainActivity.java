package net.bergamonta.app;

import android.os.Bundle;
import android.webkit.WebView;

import androidx.activity.OnBackPressedCallback;
import androidx.activity.OnBackPressedDispatcher;

import com.getcapacitor.BridgeActivity;

/**
 * Capacitor 8 no longer wires the system back gesture/button to the WebView,
 * so without this callback the default activity behavior finishes the app no
 * matter where the user is. Instead: navigate the WebView history back
 * (popstate -> SvelteKit renders the previous entry) and, only when there is
 * nothing left behind, move the task to the background (Spotify-style).
 */
public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(ThemeBarsPlugin.class);
        super.onCreate(savedInstanceState);

        OnBackPressedDispatcher dispatcher = getOnBackPressedDispatcher();
        dispatcher.addCallback(this, new OnBackPressedCallback(true) {
            @Override
            public void handleOnBackPressed() {
                WebView webView = bridge != null ? bridge.getWebView() : null;
                if (webView != null && webView.canGoBack()) {
                    webView.goBack();
                } else {
                    moveTaskToBack(true);
                }
            }
        });
    }
}
