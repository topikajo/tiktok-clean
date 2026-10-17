package mod.privacy;
import java.lang.reflect.*;
import java.lang.ref.WeakReference;
import java.util.*;

/** Version-specific hooks for You 4.4 / TikTok 46.8.3. Keeps one displayed FYP video in RAM. */
public final class NativeRefresh {
    private static Object last;
    private static String lastId="",owner="";
    private static float percent;
    private static WeakReference<Object> cell=new WeakReference<Object>(null);
    private static WeakReference<Object> active=new WeakReference<Object>(null);
    private static boolean inFyp;
    private static final Map<Object,Snapshot> pending=new WeakHashMap<Object,Snapshot>();
    private static final Map<Object,Arrival> arrivals=new WeakHashMap<Object,Arrival>();
    private static String restoreId="";
    private static float restorePercent;
    static final class Snapshot {
        final Object aweme;final String owner;final float percent;final WeakReference<Object> pager;
        Snapshot(Object aweme,String owner,float percent,Object pager){this.aweme=aweme;this.owner=owner;this.percent=percent;this.pager=new WeakReference<Object>(pager);}
    }
    static final class Arrival {
        final RefreshPolicy.Selection selection;final String owner;final long expires;
        Arrival(String previous,String fresh,String owner){selection=new RefreshPolicy.Selection(previous,fresh);this.owner=owner;expires=android.os.SystemClock.elapsedRealtime()+10000;}
    }
    public static Object call(Object target,String name,Object...args)throws Exception {
        return CachedReflect.call(target,name,args);
    }
    public static Object field(Object target,String name)throws Exception {
        return CachedReflect.field(target,name);
    }
    public static String id(Object aweme) {
        if(aweme==null)return "";try{Object value=call(aweme,"getAid");return value==null?"":String.valueOf(value);}catch(Exception ignored){return "";}
    }
    private static String account() {
        try {
            ClassLoader loader=NativeRefresh.class.getClassLoader();
            Class<?> manager=loader.loadClass("com.ss.android.ugc.aweme.framework.services.ServiceManager");
            Object service=call(call(manager,"get"),"getService",loader.loadClass("com.ss.android.ugc.aweme.IAccountService"));
            Object user=call(service,"LJIIJJI");
            Object uid=call(user,"getCurUserId");String value=uid==null?"":String.valueOf(uid);
            return value.isEmpty() || value.equals("0")?"guest":value;
        }catch(Exception ignored){return null;}
    }
    public static synchronized void selected(Object selected) {
        try {
            String event=String.valueOf(call(selected,"getEventType"));
            active=new WeakReference<Object>(selected);
            inFyp=event.equals("homepage_hot") || event.equals("homepage_for_you");
            FrameActions.resumed(null);
            if(!inFyp)return;
            Object aweme=field(selected,"LLJJJJLIIL");String aid=id(aweme),who=account();
            if(who==null || aid.isEmpty() || Boolean.TRUE.equals(call(aweme,"isAd"))) {
                last=null;lastId="";percent=0;restoreId="";cell=new WeakReference<Object>(null);pending.clear();arrivals.clear();return;
            }
            if(!owner.equals(who)){last=null;lastId="";percent=0;restoreId="";pending.clear();arrivals.clear();}
            if(!lastId.equals(aid))percent=0;
            owner=who;last=aweme;lastId=aid;cell=new WeakReference<Object>(selected);
        }catch(Exception ignored){}
    }
    public static synchronized void progress(Object selected,float value) {
        if(inFyp && selected==cell.get() && !Float.isNaN(value) && value>=0 && value<=100)percent=value;
    }
    public static synchronized boolean current(Object selected){return selected==active.get();}
    public static synchronized void userNavigation(){arrivals.clear();}
    public static synchronized void begin(Object model) {
        pending.remove(model);
        try {
            if(((Number)field(model,"mListQueryType")).intValue()!=1 || !inFyp || last==null ||
               !PrivacyRuntime.prefs().getBoolean("retain_last",true) || !owner.equals(account()))return;
            Object selected=cell.get();
            Object pager=selected==null?null:call(call(call(selected,"sw2"),"Ic"),"bc1");
            // Do not change the response unless the matching pager can select its fresh item.
            if(pager==null)return;
            arrivals.remove(pager);
            pending.put(model,new Snapshot(last,owner,percent,pager));
        }catch(Exception ignored){}
    }
    public static synchronized void finish(Object model) {
        Snapshot snapshot=pending.remove(model);if(snapshot==null)return;
        try {
            if(!PrivacyRuntime.prefs().getBoolean("retain_last",true))return;
            if(!snapshot.owner.equals(account()))return;
            if(((Number)field(model,"mListQueryType")).intValue()!=1)return;
            if(Boolean.TRUE.equals(field(model,"mIsNewDataEmpty")))return;
            Object data=field(model,"mData");
            List<?> items=(List<?>)call(data,"getItems");
            List<?> retained=RefreshPolicy.retain(items,snapshot.aweme,new RefreshPolicy.Id(){public String of(Object a){return id(a);}},true,true);
            if(retained==items)return;
            Object pager=snapshot.pager.get();if(pager==null)return;
            if(retained.size()<2 || id(retained.get(1)).isEmpty())return;
            arrivals.put(pager,new Arrival(id(snapshot.aweme),id(retained.get(1)),snapshot.owner));
            call(data,"setItems",retained);
            restoreId=id(snapshot.aweme);restorePercent=snapshot.percent;
        }catch(Exception ignored){}
    }
    /** Hook the native pager's common selector before it dispatches page selection or renders. */
    public static synchronized int initialIndex(Object pager,int requested) {
        Arrival arrival=arrivals.get(pager);if(arrival==null)return requested;
        if(android.os.SystemClock.elapsedRealtime()>arrival.expires || !arrival.owner.equals(account())) {
            arrivals.remove(pager);return requested;
        }
        try {
            Object adapter=call(pager,"getAdapter");
            if(((Number)call(adapter,"getCount")).intValue()<2)return requested;
            int index=arrival.selection.index(requested,id(call(adapter,"getItem",0)),id(call(adapter,"getItem",1)),true);
            if(arrival.selection.consumed())arrivals.remove(pager);
            return index;
        }catch(Exception ignored){return requested;}
    }
    public static void firstFrame(Object selected) {
        final float position;
        synchronized(NativeRefresh.class) {
            if(!arrivals.isEmpty() && inFyp && selected==cell.get())try {
                Object pager=call(call(call(selected,"sw2"),"Ic"),"bc1");
                Arrival arrival=arrivals.get(pager);
                if(arrival!=null && ((Number)call(pager,"getCurrentItem")).intValue()==1) {
                    arrival.selection.displayed(id(field(selected,"LLJJJJLIIL")));
                    if(arrival.selection.consumed())arrivals.remove(pager);
                }
            }catch(Exception ignored){}
            if(restoreId.isEmpty() || !inFyp || selected!=cell.get())return;
            try {
                if(!id(field(selected,"LLJJJJLIIL")).equals(restoreId) || !owner.equals(account()))return;
            }catch(Exception ignored){return;}
            position=Math.max(0,Math.min(99.5f,restorePercent));
            restoreId="";
        }
        try {
            Object ability=call(call(selected,"sw2"),"De2");
            // The native player API seeks in percent, retaining its duration and buffering logic.
            // Do not hold our monitor while entering player callbacks.
            call(ability,"zT0",position);
        }catch(Exception ignored){}
    }
}
