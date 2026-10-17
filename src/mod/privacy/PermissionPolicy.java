package mod.privacy;

import java.util.Arrays;
import java.util.HashSet;
import java.util.Set;

/** No permission is reported as granted. Requests need a recent foreground user action. */
public final class PermissionPolicy {
    public static final long ACTION_WINDOW_MS = 5000;
    private static final Set<String> ALLOWED = new HashSet<String>(Arrays.asList(
        "android.permission.CAMERA", "android.permission.RECORD_AUDIO", "android.permission.READ_CONTACTS",
        "android.permission.POST_NOTIFICATIONS", "android.permission.READ_MEDIA_IMAGES",
        "android.permission.READ_MEDIA_VIDEO", "android.permission.READ_MEDIA_VISUAL_USER_SELECTED",
        "android.permission.READ_EXTERNAL_STORAGE", "android.permission.WRITE_EXTERNAL_STORAGE",
        "android.permission.BLUETOOTH_SCAN", "android.permission.BLUETOOTH_CONNECT",
        "android.permission.BLUETOOTH_ADVERTISE"));
    public static boolean allow(String[] permissions, long now, long actionAt, boolean foreground) {
        if (!foreground || actionAt <= 0 || now < actionAt || now - actionAt > ACTION_WINDOW_MS ||
            permissions == null || permissions.length == 0) return false;
        for (String permission : permissions) if (!ALLOWED.contains(permission)) return false;
        return true;
    }
}
