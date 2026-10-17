package mod.privacy;
public final class PrivacyRuntime {
    public static final Preferences preferences=new Preferences();
    public static Preferences prefs(){return preferences;}
    public static final class Preferences {
        public volatile boolean enabled=true;
        public boolean getBoolean(String key,boolean fallback){return enabled;}
    }
}
