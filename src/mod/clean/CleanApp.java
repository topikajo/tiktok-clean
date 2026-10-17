package mod.clean;

import android.app.*;
import android.app.job.*;
import android.content.*;
import android.os.*;
import android.graphics.Color;
import android.view.*;
import android.widget.*;
import java.lang.ref.WeakReference;
import java.util.*;
import org.json.JSONObject;

public final class CleanApp implements Application.ActivityLifecycleCallbacks {
    public static Context context;
    private static boolean installed;
    private static WeakReference<Activity> chat=new WeakReference<Activity>(null);
    private static final Map<String,String> conversations=new HashMap<String,String>();
    static final Handler main=new Handler(Looper.getMainLooper());
    private static final String WRAPPER="clean_chat_controls";
    public static synchronized void install(Application app){
        if(installed)return;installed=true;context=app.getApplicationContext();app.registerActivityLifecycleCallbacks(new CleanApp());
        try{
            JobScheduler scheduler=(JobScheduler)context.getSystemService(Context.JOB_SCHEDULER_SERVICE);
            JobInfo info=new JobInfo.Builder(47141,new ComponentName(context,StreakJob.class)).setRequiredNetworkType(JobInfo.NETWORK_TYPE_ANY).setPeriodic(30*60*1000L).build();
            scheduler.schedule(info);
        }catch(Exception ignored){}
    }
    public static SharedPreferences prefs(){return context.getSharedPreferences("clean_preferences",Context.MODE_PRIVATE);}
    public static String key(String owner,String cid,String setting){return setting+"|"+owner+"|"+cid;}
    public static boolean paired(String owner,String cid){return prefs().getBoolean(key(owner,cid,"paired"),false);}
    public static boolean peer(String owner,String cid){return prefs().getBoolean(key(owner,cid,"peer"),false);}
    public static boolean hideAuto(String owner,String cid){return paired(owner,cid)&&peer(owner,cid)&&prefs().getBoolean(key(owner,cid,"hide"),false);}
    public static synchronized String conversationForPeer(String uid){String cid=conversations.get(NativeBridge.uid()+"|"+uid);return cid==null?"":cid;}
    public static synchronized void rememberSession(Object session,String cid){
        if(cid==null||cid.isEmpty()||context==null)return;
        try{String user=String.valueOf(NativeBridge.call(session,"getSingleChatFromUserId"));if(!user.isEmpty()&&!user.equals("null"))conversations.put(NativeBridge.uid()+"|"+user,cid);}catch(Exception ignored){}
    }
    public static void refreshChat(){main.post(new Runnable(){public void run(){Activity a=chat.get();if(a!=null&&!a.isFinishing())refreshViews(a.getWindow().getDecorView());}});}
    private static void refreshViews(View view){
        // Refresh SDK message lists after receiving paired-client edits/deletions.
        if(view.getClass().getName().contains("RecyclerView"))try{Object adapter=NativeBridge.call(view,"getAdapter");if(adapter!=null)NativeBridge.call(adapter,"notifyDataSetChanged");}catch(Exception ignored){}
        if(view instanceof ViewGroup){ViewGroup group=(ViewGroup)view;for(int i=0;i<group.getChildCount();i++)refreshViews(group.getChildAt(i));}
    }
    static int dp(Context c,int value){return Math.round(value*c.getResources().getDisplayMetrics().density);}
    static TextView button(final Activity a,String label){
        TextView view=new TextView(a);view.setText(label);view.setTextSize(13);view.setTextColor(Color.WHITE);view.setGravity(Gravity.CENTER);view.setPadding(dp(a,8),dp(a,8),dp(a,8),dp(a,8));view.setBackgroundColor(Color.rgb(254,44,85));return view;
    }
    static LinearLayout insertRow(Activity a,String tag){
        ViewGroup content=a.findViewById(android.R.id.content);if(content==null||content.getChildCount()==0)return null;
        View existing=content.findViewWithTag(tag);if(existing instanceof LinearLayout)return (LinearLayout)existing;
        View original=content.getChildAt(0);ViewGroup.LayoutParams params=original.getLayoutParams();content.removeView(original);
        FrameLayout wrapper=new FrameLayout(a);
        LinearLayout row=new LinearLayout(a);row.setTag(tag);row.setOrientation(LinearLayout.HORIZONTAL);
        final FrameLayout.LayoutParams originalParams=new FrameLayout.LayoutParams(-1,-1);originalParams.topMargin=dp(a,40);
        wrapper.addView(original,originalParams);wrapper.addView(row,new FrameLayout.LayoutParams(-1,-2,Gravity.TOP));content.addView(wrapper,0,params);
        final View child=original;row.addOnLayoutChangeListener(new View.OnLayoutChangeListener(){public void onLayoutChange(View v,int l,int t,int r,int b,int ol,int ot,int or,int ob){if(originalParams.topMargin!=b-t){originalParams.topMargin=b-t;child.setLayoutParams(originalParams);}}});return row;
    }
    void attachChat(final Activity a){
        chat=new WeakReference<Activity>(a);final LinearLayout row=insertRow(a,WRAPPER);if(row==null||row.getChildCount()!=0)return;
        final TextView auto=button(a,"🔥 Автоогонёк");final TextView messages=button(a,"Правка / удаление");
        row.addView(auto,new LinearLayout.LayoutParams(0,-2,1));row.addView(messages,new LinearLayout.LayoutParams(0,-2,1));
        auto.setOnClickListener(new View.OnClickListener(){public void onClick(View view){
            final String owner=NativeBridge.uid(),cid=NativeBridge.chatId(a);
            if(owner.isEmpty()||cid.isEmpty()){Toast.makeText(a,"Откройте личный чат после входа в аккаунт",Toast.LENGTH_LONG).show();return;}
            final boolean enabled=prefs().getBoolean(key(owner,cid,"auto"),false);
            new AlertDialog.Builder(a).setTitle("Автоогонёк").setMessage(enabled?"Выключить автоматическое поддержание серии в этом чате?":"Если вы давно не писали в этот чат, TikTok Clean отправит 🔥. Android может задерживать отправку в фоне. Серия также зависит от активности собеседника.").setNegativeButton("Отмена",null).setPositiveButton(enabled?"Выключить":"Включить",new DialogInterface.OnClickListener(){public void onClick(DialogInterface dialog,int which){
                prefs().edit().putBoolean(key(owner,cid,"auto"),!enabled).commit();auto.setText(!enabled?"🔥 Авто: включён":"🔥 Автоогонёк");StreakJob.tick();
            }}).show();
        }});
        messages.setOnClickListener(new View.OnClickListener(){public void onClick(View view){showMessages(a);}});
    }
    static void showMessages(final Activity a){
        final String owner=NativeBridge.uid(),cid=NativeBridge.chatId(a);
        if(owner.isEmpty()||cid.isEmpty()){Toast.makeText(a,"Откройте личный чат после входа в аккаунт",Toast.LENGTH_LONG).show();return;}
        if(!paired(owner,cid)||!peer(owner,cid)){
            final boolean enabled=paired(owner,cid);
            new AlertDialog.Builder(a).setTitle("Синхронизация мода").setMessage(enabled?"Ожидается включение режима у собеседника. Оба участника должны использовать TikTok Clean и включить режим в этом чате.":"Редактирование и скрытие сообщений будут видны только двум пользователям TikTok Clean. Исходные сообщения сохраняются на сервере TikTok. Включите режим у обоих участников.").setNegativeButton("Закрыть",null).setNeutralButton(enabled?"Выключить":"Позже",new DialogInterface.OnClickListener(){public void onClick(DialogInterface d,int w){if(enabled)prefs().edit().putBoolean(key(owner,cid,"paired"),false).putBoolean(key(owner,cid,"peer"),false).apply();}}).setPositiveButton("Включить / соединить",new DialogInterface.OnClickListener(){public void onClick(DialogInterface d,int w){
                prefs().edit().putBoolean(key(owner,cid,"paired"),true).commit();
                String request="{\"op\":\"hello\",\"nonce\":\""+UUID.randomUUID().toString()+"\"}";
                NativeBridge.send(owner,cid,"TikTok Clean: подключение синхронизации",Collections.singletonMap(MessageHooks.CONTROL,request),new NativeBridge.Completion(){public void finished(final boolean ok,final String error){main.post(new Runnable(){public void run(){Toast.makeText(a,ok?"Запрос отправлен. Собеседник должен включить режим у себя":error,Toast.LENGTH_LONG).show();}});}});
            }}).show();return;
        }
        final List<JSONObject> own=MessageHooks.ownMessages(owner,cid);
        if(own.isEmpty()){Toast.makeText(a,"Прокрутите чат до своего текстового сообщения и откройте список снова",Toast.LENGTH_LONG).show();return;}
        String[] labels=new String[own.size()];for(int i=0;i<labels.length;i++){String t=own.get(i).optString("text");labels[i]=t.length()>90?t.substring(0,90)+"…":t;}
        new AlertDialog.Builder(a).setTitle("Ваши сообщения — режим мода").setItems(labels,new DialogInterface.OnClickListener(){public void onClick(DialogInterface d,int index){
            final JSONObject message=own.get(index);
            new AlertDialog.Builder(a).setTitle("Действие с сообщением").setItems(new String[]{"Редактировать в моде у обоих","Скрыть в моде у обоих"},new DialogInterface.OnClickListener(){public void onClick(DialogInterface dialog,int action){
                if(action==1)performChange(a,owner,cid,message.optLong("id"),"",true);
                else{final EditText text=new EditText(a);text.setText(message.optString("text"));new AlertDialog.Builder(a).setTitle("Редактирование в моде").setView(text).setNegativeButton("Отмена",null).setPositiveButton("Сохранить",new DialogInterface.OnClickListener(){public void onClick(DialogInterface d,int w){String value=text.getText().toString();if(value.length()<=2000&&!value.trim().isEmpty())performChange(a,owner,cid,message.optLong("id"),value,false);}}).show();}
            }}).show();
        }}).setNeutralButton("Скрывать автоогоньки",new DialogInterface.OnClickListener(){public void onClick(DialogInterface d,int w){boolean hide=prefs().getBoolean(key(owner,cid,"hide"),false);prefs().edit().putBoolean(key(owner,cid,"hide"),!hide).apply();Toast.makeText(a,!hide?"Служебные огоньки скрыты в этом моде":"Служебные огоньки отображаются",Toast.LENGTH_LONG).show();refreshChat();}}).setPositiveButton("Отключить режим",new DialogInterface.OnClickListener(){public void onClick(DialogInterface d,int w){prefs().edit().putBoolean(key(owner,cid,"paired"),false).putBoolean(key(owner,cid,"peer"),false).apply();refreshChat();}}).setNegativeButton("Закрыть",null).show();
    }
    static void performChange(final Activity a,String owner,String cid,long id,String text,boolean delete){MessageHooks.change(owner,cid,id,text,delete,new NativeBridge.Completion(){public void finished(final boolean ok,final String error){main.post(new Runnable(){public void run(){Toast.makeText(a,ok?"Изменение синхронизировано между модами":error,Toast.LENGTH_LONG).show();refreshChat();}});}});}
    public void onActivityResumed(final Activity a){
        if(a.getClass().getName().equals("com.ss.android.ugc.aweme.im.sdk.chat.ui.singleactivity.ChatShellActivity")){main.post(new Runnable(){public void run(){if(!a.isFinishing())attachChat(a);}});}
        if(a.getClass().getName().equals("com.ss.android.ugc.aweme.setting.ui.SettingContainerActivity"))UpdateChannel.attach(a);
        StreakJob.tick();
    }
    public void onActivityCreated(Activity a,Bundle b){}public void onActivityStarted(Activity a){}public void onActivityPaused(Activity a){}public void onActivityStopped(Activity a){}public void onActivitySaveInstanceState(Activity a,Bundle b){}
    public void onActivityDestroyed(Activity a){if(chat.get()==a)chat=new WeakReference<Activity>(null);}
}
