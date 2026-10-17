package mod.clean;

import android.content.Intent;

/** Use TikTok's existing browser OAuth provider for a personally re-signed APK. */
public final class AuthRouting {
    private AuthRouting() {}
    /** Null means keep the original provider resolver for this platform. */
    public static String providerOverride(String platform) {
        return "google".equals(platform)||"google_onetap".equals(platform)||"google_web".equals(platform)?"google_web":null;
    }
    /** Route the Google credential-manager alias through the regular third-party controller. */
    public static void normalizeIntent(Intent intent) {
        if(intent==null)return;
        String platform=intent.getStringExtra("platform");
        if("google_onetap".equals(platform)||"google_web".equals(platform))intent.putExtra("platform","google");
    }
}
