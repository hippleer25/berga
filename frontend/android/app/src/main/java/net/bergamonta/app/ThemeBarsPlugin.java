package net.bergamonta.app;

import android.content.res.Configuration;
import android.graphics.Color;
import android.graphics.drawable.ColorDrawable;
import android.os.Build;
import android.view.View;
import android.view.Window;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

/**
 * Paints the native window area behind the system bars with the app theme
 * color. On Android 15+ the window is enforced edge-to-edge and Capacitor
 * pads the WebView natively (no viewport-fit=cover), so the deprecated
 * setNavigationBarColor is a no-op and the window background is what shows
 * behind the bars. On older Androids the classic window bar colors are set
 * directly. Capacitor's core SystemBars plugin resets the window/decor view
 * background to the Android theme color on every style change and
 * configuration change, so this plugin re-applies the saved color on load()
 * and handleOnConfigurationChanged, and the JS layer re-syncs right after
 * each SystemBars.setStyle call.
 */
@CapacitorPlugin(name = "ThemeBars")
public class ThemeBarsPlugin extends Plugin {

    private static int lastColor = Color.BLACK;

    @Override
    public void load() {
        applyColor(lastColor);
    }

    @Override
    protected void handleOnConfigurationChanged(Configuration newConfig) {
        super.handleOnConfigurationChanged(newConfig);
        // SystemBars repaints the decor view synchronously inside the same
        // configuration dispatch; queue after it.
        View decor = getActivity() != null ? getActivity().getWindow().getDecorView() : null;
        if (decor != null) {
            decor.post(() -> applyColor(lastColor));
        }
    }

    @PluginMethod
    public void setBackgroundColor(PluginCall call) {
        String hex = call.getString("color");
        final int color;
        try {
            color = Color.parseColor(hex);
        } catch (Exception e) {
            call.reject("Invalid color (expected #RRGGBB)");
            return;
        }
        lastColor = color;
        getActivity().runOnUiThread(() -> {
            applyColor(color);
            call.resolve();
        });
    }

    private void applyColor(int color) {
        Window window = getActivity() != null ? getActivity().getWindow() : null;
        if (window == null) return;
        window.setBackgroundDrawable(new ColorDrawable(color));
        window.getDecorView().setBackgroundColor(color);
        View webView = getBridge() != null ? getBridge().getWebView() : null;
        if (webView != null) {
            webView.setBackgroundColor(color);
            if (webView.getParent() instanceof View) {
                ((View) webView.getParent()).setBackgroundColor(color);
            }
        }
        if (Build.VERSION.SDK_INT < 35) {
            window.setStatusBarColor(color);
            window.setNavigationBarColor(color);
        }
        if (Build.VERSION.SDK_INT >= 29) {
            window.setNavigationBarContrastEnforced(false);
        }
    }
}
