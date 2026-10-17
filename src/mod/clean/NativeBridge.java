package mod.clean;

import android.app.Activity;
import java.lang.reflect.*;
import java.util.*;

/** Bindings verified against the original 47.1.4 DEX, rather than private HTTP endpoints. */
public final class NativeBridge {
    private static volatile Object userService;
    public interface Completion { void finished(boolean success, String error); }
    public static Object call(Object object, String name, Object... args) throws Exception {
        Class<?> type=object instanceof Class?(Class<?>)object:object.getClass();
        for(Method method:type.getMethods()) if(method.getName().equals(name)&&method.getParameterTypes().length==args.length) {
            Class<?>[] params=method.getParameterTypes();boolean compatible=true;
            for(int i=0;i<args.length;i++)if(args[i]!=null&&!params[i].isPrimitive()&&!params[i].isInstance(args[i]))compatible=false;
            if(!compatible)continue;
            method.setAccessible(true);return method.invoke(object instanceof Class?null:object,args);
        }
        throw new NoSuchMethodException(type.getName()+"."+name);
    }
    public static String uid() {
        try {
            Object users=userService;
            if(users==null){Object service=Class.forName("com.ss.android.ugc.aweme.AccountService").getConstructor().newInstance();users=call(service,"LJIIJ");userService=users;}
            if(!Boolean.TRUE.equals(call(users,"isLogin")))return "";
            String id=String.valueOf(call(users,"getCurUserId"));
            return "0".equals(id)||"null".equals(id)?"":id;
        }catch(Exception failure){return "";}
    }
    public static String chatId(Activity activity) {
        try {
            Object params=activity.getIntent().getSerializableExtra("key_enter_chat_params");
            if(params==null)return "";
            Object group=call(params,"getGroupId");if(group instanceof String&&!((String)group).isEmpty())return "";
            Object session=call(params,"getSessionId");
            if(session instanceof String&&!((String)session).isEmpty())return (String)session;
            String user=String.valueOf(call(params,"getUserId"));
            return CleanApp.conversationForPeer(user);
        }catch(Exception ignored){return "";}
    }
    public static void send(final String owner, final String cid, String text, Map<String,String> ext, final Completion completion) {
        try {
            if(owner==null||owner.isEmpty()||!owner.equals(uid())||cid==null||cid.isEmpty())throw new IllegalStateException("Нет активного аккаунта или чата");
            Object content=call(Class.forName("com.ss.android.ugc.aweme.im.message.content.TextContent"),"obtain",text);
            Object builder=call(Class.forName("X.0qFC"),"LIZ");
            if(builder==null||builder.getClass().getName().equals("X.0qAm"))throw new IllegalStateException("SDK чатов ещё не готов");
            call(builder,"LIZIZ",cid);call(builder,"LIZLLL",content);
            call(builder,"LJIIZILJ",ext==null?Collections.<String,String>emptyMap():ext);
            call(builder,"LJIIIIZZ",ext==null?Collections.<String,String>emptyMap():ext);
            call(builder,"LJIIL","clean_mod");
            Class<?> callback=Class.forName("X.0BVW");
            Object proxy=Proxy.newProxyInstance(callback.getClassLoader(),new Class<?>[]{callback},new InvocationHandler(){
                private boolean done;
                public Object invoke(Object proxy,Method method,Object[] args) {
                    if(method.getDeclaringClass()==Object.class) {
                        if(method.getName().equals("toString"))return "CleanMessageCallback";
                        if(method.getName().equals("hashCode"))return System.identityHashCode(proxy);
                        if(method.getName().equals("equals"))return proxy==args[0];
                    }
                    if(!done&&method.getName().equals("LIZIZ")){done=true;completion.finished(true,"");}
                    else if(!done&&method.getName().equals("LJ")){done=true;completion.finished(false,"TikTok не отправил сообщение");}
                    return null;
                }
            });
            if(!owner.equals(uid()))throw new IllegalStateException("Аккаунт изменился");
            call(builder,"LJFF",proxy);
        }catch(Exception error){completion.finished(false,"Не удалось отправить сообщение");}
    }
}
