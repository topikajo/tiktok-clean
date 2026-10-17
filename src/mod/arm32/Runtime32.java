package mod.arm32;

import android.app.*;
import android.content.*;
import android.content.pm.PackageManager;
import android.os.*;
import android.view.*;
import android.widget.*;
import java.lang.ref.WeakReference;
import java.lang.reflect.*;
import java.util.Arrays;

/** Local permission UX. Stores no touch history, account IDs or usage events. */
public final class Runtime32 implements Application.ActivityLifecycleCallbacks {
    public static final Handler main = new Handler(Looper.getMainLooper());
    private static Application app;
    private static volatile long actionAt;
    private static volatile WeakReference<Activity> foreground = new WeakReference<Activity>(null);
    public static synchronized void install(Application application) {
        if (app != null) return;
        app = application;
        application.registerActivityLifecycleCallbacks(new Runtime32());
    }
    public static SharedPreferences prefs() { return app.getSharedPreferences("clean_privacy",0); }
    public static Activity foregroundActivity() { return foreground.get(); }
    public static void noteAction(Activity activity) {
        if (foreground.get() == activity && !activity.isFinishing()) actionAt = SystemClock.elapsedRealtime();
    }
    public static boolean canRequest(Activity activity, String[] permissions) {
        // Native startup notification prompts on the main feed are suppressed. The explicit controls below work everywhere.
        if (permissions != null && Arrays.asList(permissions).contains("android.permission.POST_NOTIFICATIONS") && activity!=null) {
            String name=activity.getClass().getName().toLowerCase(java.util.Locale.ROOT);
            if (!name.contains("setting") && !name.contains("notification")) return false;
        }
        return activity != null && !activity.isFinishing() &&
            PermissionPolicy.allow(permissions,SystemClock.elapsedRealtime(),actionAt,foreground.get() == activity);
    }
    private static int[] denied(String[] permissions) {
        int[] result = new int[permissions == null ? 0 : permissions.length];
        Arrays.fill(result,PackageManager.PERMISSION_DENIED);return result;
    }
    public static void request(final Activity activity, final String[] permissions, final int code) {
        if (canRequest(activity,permissions)) { activity.requestPermissions(permissions,code);return; }
        if (activity != null) main.post(new Runnable(){public void run(){
            if (!activity.isFinishing()) activity.onRequestPermissionsResult(code,permissions,denied(permissions));
        }});
    }
    public static void requestFragment(final android.app.Fragment fragment, final String[] permissions, final int code) {
        if (canRequest(fragment.getActivity(),permissions)) { fragment.requestPermissions(permissions,code);return; }
        main.post(new Runnable(){public void run(){fragment.onRequestPermissionsResult(code,permissions,denied(permissions));}});
    }
    public static void requestSupport(final Object fragment, final String[] permissions, final int code) {
        try {
            Activity activity = (Activity)fragment.getClass().getMethod("getActivity").invoke(fragment);
            if (canRequest(activity,permissions)) {
                fragment.getClass().getMethod("requestPermissions",String[].class,int.class).invoke(fragment,permissions,code);return;
            }
            main.post(new Runnable(){public void run(){try {
                fragment.getClass().getMethod("onRequestPermissionsResult",int.class,String[].class,int[].class)
                    .invoke(fragment,code,permissions,denied(permissions));
            } catch (ReflectiveOperationException ignored) {}}});
        } catch (ReflectiveOperationException e) { throw new IllegalStateException("Permission callback unavailable",e); }
    }
    private static final class Touch implements InvocationHandler {
        final WeakReference<Activity> activity; final Window.Callback delegate;
        float downX,downY;boolean down;
        Touch(Activity activity, Window.Callback delegate) {this.activity=new WeakReference<Activity>(activity);this.delegate=delegate;}
        public Object invoke(Object proxy, Method method, Object[] args) throws Throwable {
            Activity a=activity.get();
            if (a!=null && args!=null && args.length>0) {
                if (method.getName().equals("dispatchTouchEvent") && args[0] instanceof MotionEvent) {
                    MotionEvent event=(MotionEvent)args[0];int action=event.getActionMasked();
                    if(action==MotionEvent.ACTION_DOWN){down=true;downX=event.getX();downY=event.getY();}
                    if(action==MotionEvent.ACTION_UP){
                        int slop=ViewConfiguration.get(a).getScaledTouchSlop();
                        if(down && Math.abs(event.getX()-downX)<slop && Math.abs(event.getY()-downY)<slop)noteAction(a);
                        down=false;
                    }
                    if(action==MotionEvent.ACTION_CANCEL)down=false;
                }
                if (method.getName().equals("dispatchKeyEvent") && args[0] instanceof KeyEvent) {
                    KeyEvent key=(KeyEvent)args[0];
                    if (key.getAction()==KeyEvent.ACTION_DOWN && (key.getKeyCode()==KeyEvent.KEYCODE_ENTER ||
                        key.getKeyCode()==KeyEvent.KEYCODE_DPAD_CENTER)) {noteAction(a);}
                }
            }
            try{return method.invoke(delegate,args);}catch(InvocationTargetException e){throw e.getCause();}
        }
    }
    private static void watch(Activity activity) {
        Window window=activity.getWindow(); if (window==null) return;
        Window.Callback original=window.getCallback(); if (original==null) return;
        if (Proxy.isProxyClass(original.getClass()) && Proxy.getInvocationHandler(original) instanceof Touch) return;
        window.setCallback((Window.Callback)Proxy.newProxyInstance(Window.Callback.class.getClassLoader(),
            new Class<?>[]{Window.Callback.class},new Touch(activity,original)));
    }
    public static TextView button(Context context,String text) {
        Button button=new Button(context);button.setText(text);button.setAllCaps(false);return button;
    }
    public static LinearLayout insertRow(Activity activity,String tag) {
        ViewGroup content=activity.findViewById(android.R.id.content);
        if(content==null || content.getChildCount()==0)return null;
        View old=content.findViewWithTag(tag);if(old instanceof LinearLayout)return (LinearLayout)old;
        View original=content.getChildAt(0);ViewGroup.LayoutParams params=original.getLayoutParams();
        content.removeView(original);LinearLayout wrapper=new LinearLayout(activity);wrapper.setOrientation(1);
        LinearLayout row=new LinearLayout(activity);row.setOrientation(1);row.setTag(tag);
        wrapper.addView(row,new LinearLayout.LayoutParams(-1,-2));
        wrapper.addView(original,new LinearLayout.LayoutParams(-1,0,1));content.addView(wrapper,0,params);return row;
    }
    public static LinearLayout settingsView(final Activity activity) {
        LinearLayout row=new LinearLayout(activity);row.setOrientation(1);
        TextView text=new TextView(activity);text.setPadding(24,12,24,12);
        text.setText("TikTok Clean ARM7 / 32-bit\nОтключены найденные Java-каналы аналитики и рекламный ID.\nTikTok получает запросы для входа, ленты и общения.");row.addView(text);
        addPermission(row,activity,"Камера","android.permission.CAMERA");
        addPermission(row,activity,"Микрофон","android.permission.RECORD_AUDIO");
        addPermission(row,activity,"Поиск друзей по контактам","android.permission.READ_CONTACTS");
        if(Build.VERSION.SDK_INT>=33)addPermission(row,activity,"Уведомления","android.permission.POST_NOTIFICATIONS");
        return row;
    }
    private static void attachPrivacy(final Activity activity) {
        ViewGroup root=activity.findViewById(android.R.id.content);if(root==null||root.findViewWithTag("arm32_privacy")!=null)return;
        View target=root.findViewWithTag("clean_update_row");if(!(target instanceof LinearLayout))return;
        TextView button=button(activity,"Приватность и разрешения");button.setTag("arm32_privacy");((LinearLayout)target).addView(button);
        button.setOnClickListener(new View.OnClickListener(){public void onClick(View v){new AlertDialog.Builder(activity).setTitle("TikTok Clean ARM7").setView(settingsView(activity)).setPositiveButton("Закрыть",null).show();}});
    }
    private static void addPermission(LinearLayout row,final Activity activity,String label,final String permission) {
        TextView view=button(activity,label);row.addView(view);
        view.setOnClickListener(new View.OnClickListener(){public void onClick(View v){
            noteAction(activity);
            if(PermissionPolicy.allow(new String[]{permission},SystemClock.elapsedRealtime(),actionAt,foreground.get()==activity))
                activity.requestPermissions(new String[]{permission},0x6341);
        }});
    }
    public void onActivityResumed(final Activity activity) {
        foreground=new WeakReference<Activity>(activity);watch(activity);
        main.post(new Runnable(){public void run(){if(!activity.isFinishing()) {
            watch(activity);
            UpdateChannel.onResume(activity);
            if(activity.getClass().getName().equals("com.ss.android.ugc.aweme.setting.ui.SettingContainerActivity")){UpdateChannel.attach(activity);attachPrivacy(activity);}
        }}});
    }
    public void onActivityPaused(Activity activity) {if(foreground.get()==activity)foreground=new WeakReference<Activity>(null);}
    public void onActivityCreated(Activity activity,Bundle state) {}
    public void onActivityStarted(Activity activity) {}
    public void onActivityStopped(Activity activity) {}
    public void onActivitySaveInstanceState(Activity activity,Bundle state) {}
    public void onActivityDestroyed(Activity activity) {}
}
