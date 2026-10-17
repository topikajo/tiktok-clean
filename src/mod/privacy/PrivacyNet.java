package mod.privacy;

import java.net.URI;
import java.util.Locale;

/** A narrow denylist. Functional authentication, device registration and content APIs stay available. */
public final class PrivacyNet {
    public static final String BLOCKED = "https://127.0.0.1:9/clean-privacy-blocked";
    private static boolean domain(String host, String domain) {
        return host.equals(domain) || host.endsWith("." + domain);
    }
    public static boolean blocked(String value) {
        if (value == null) return false;
        try {
            URI uri = new URI(value);
            String host = uri.getHost();
            if (host == null) return false;
            host = host.toLowerCase(Locale.ROOT);
            String path = uri.getPath();
            if (path == null) path = "/";
            if (domain(host,"tiktokyou.yzewe.ru") || domain(host,"tiktokyou-fb.yzewe.ru") ||
                domain(host,"appsflyer.com") || domain(host,"appsflyersdk.com") ||
                domain(host,"app-measurement.com") || domain(host,"google-analytics.com")) return true;
            boolean tiktok = domain(host,"tiktokv.com") || domain(host,"tiktok.com") ||
                domain(host,"byteoversea.com") || domain(host,"snssdk.com");
            if (!tiktok) return false;
            // This registration supplies the device/install IDs needed by TikTok's login protocol.
            if (path.equals("/service/2/device_register/") || path.equals("/service/2/device_register")) return false;
            if (host.matches("(?:rt)?log(?:[0-9]+)?[-.].*") || host.startsWith("mon-") || host.startsWith("mon.")) return true;
            return path.equals("/service/2/app_log") || path.startsWith("/service/2/app_log/") ||
                path.startsWith("/service/2/device_sdk/stats_collect/") ||
                path.startsWith("/monitor/collect/") || path.startsWith("/monitor/appmonitor/");
        } catch (Exception ignored) { return false; }
    }
    public static String rewrite(String value) { return blocked(value) ? BLOCKED : value; }
}
