package mod.clean;

import android.content.*;
import android.database.Cursor;
import android.database.sqlite.*;
import org.json.JSONObject;
import java.util.*;

/** Paired-client display changes. The original server message is never claimed to be erased. */
public final class MessageHooks {
    static final String CONTROL="clean_ctl_v1",AUTO="clean_auto_streak";
    private static Db db;
    static class Db extends SQLiteOpenHelper {
        Db(Context c){super(c,"clean_messages.db",null,1);}
        public void onCreate(SQLiteDatabase d){
            d.execSQL("CREATE TABLE seen(owner TEXT,cid TEXT,id INTEGER,author TEXT,body TEXT,created INTEGER,PRIMARY KEY(owner,cid,id))");
            d.execSQL("CREATE TABLE changes(owner TEXT,cid TEXT,id INTEGER,author TEXT,rev INTEGER,deleted INTEGER,text TEXT,PRIMARY KEY(owner,cid,id,author))");
        }
        public void onUpgrade(SQLiteDatabase d,int old,int next){throw new IllegalStateException("Migration required");}
    }
    static synchronized SQLiteDatabase database() {
        if(CleanApp.context==null)return null;
        if(db==null)db=new Db(CleanApp.context);
        return db.getWritableDatabase();
    }
    static String string(Object m,String method)throws Exception{return String.valueOf(NativeBridge.call(m,method));}
    static long number(Object m,String method)throws Exception{return ((Number)NativeBridge.call(m,method)).longValue();}
    @SuppressWarnings("unchecked") static Map<String,String> extras(Object m)throws Exception {
        Object ext=NativeBridge.call(m,"getExt");return ext instanceof Map?(Map<String,String>)ext:Collections.<String,String>emptyMap();
    }
    public static String render(Object message,String original) {
        if(CleanApp.context==null)return original;
        try {
            String owner=NativeBridge.uid(),cid=string(message,"getConversationId"),author=string(message,"getSender");
            long id=number(message,"getMsgId");
            if(owner.isEmpty()||cid.isEmpty()||id<=0||original==null)return original;
            boolean paired=CleanApp.paired(owner,cid),auto=CleanApp.prefs().getBoolean(CleanApp.key(owner,cid,"auto"),false);
            if(!paired&&!auto)return original;
            Map<String,String> ext=extras(message);
            if(ext.containsKey(CONTROL)){consume(owner,cid,author,ext.get(CONTROL));return original;}
            rememberSend(message,owner,cid,author,ext);
            if(!paired)return original;
            SQLiteDatabase d=database();if(d==null)return original;
            ContentValues seen=new ContentValues();seen.put("owner",owner);seen.put("cid",cid);seen.put("id",id);seen.put("author",author);seen.put("body",original);seen.put("created",number(message,"getCreatedAt"));
            d.insertWithOnConflict("seen",null,seen,SQLiteDatabase.CONFLICT_REPLACE);
            try(Cursor row=d.rawQuery("SELECT author,deleted,text FROM changes WHERE owner=? AND cid=? AND id=? AND author=?",new String[]{owner,cid,Long.toString(id),author})){
                if(row.moveToFirst()&&author.equals(row.getString(0))){
                    if(row.getInt(1)!=0)return new JSONObject(original).put("text","Сообщение скрыто автором").toString();
                    return new JSONObject(original).put("text",row.getString(2)).put("rich_text_infos",new org.json.JSONArray()).toString();
                }
            }
        }catch(Exception ignored){}
        return original;
    }
    public static boolean deleted(Object message,boolean original) {
        if(CleanApp.context==null)return original;
        if(original)return true;
        try {
            String owner=NativeBridge.uid(),cid=string(message,"getConversationId"),author=string(message,"getSender");
            if(owner.isEmpty())return false;
            boolean paired=CleanApp.paired(owner,cid),auto=CleanApp.prefs().getBoolean(CleanApp.key(owner,cid,"auto"),false);
            if(!paired&&!auto)return false;
            Map<String,String> ext=extras(message);
            rememberSend(message,owner,cid,author,ext);
            if(ext.containsKey(CONTROL)){
                if(CleanApp.paired(owner,cid)){consume(owner,cid,author,ext.get(CONTROL));return true;}
                return false;
            }
            if("1".equals(ext.get(AUTO))&&CleanApp.hideAuto(owner,cid))return true;
            if(!paired)return false;
            SQLiteDatabase d=database();if(d==null)return false;
            try(Cursor row=d.rawQuery("SELECT author,deleted FROM changes WHERE owner=? AND cid=? AND id=? AND author=?",new String[]{owner,cid,Long.toString(number(message,"getMsgId")),author})){
                return row.moveToFirst()&&author.equals(row.getString(0))&&row.getInt(1)!=0;
            }
        }catch(Exception ignored){return false;}
    }
    public static int deletedInt(Object message,int original){return original!=0?original:deleted(message,false)?1:0;}
    static synchronized void consume(final String owner,final String cid,final String author,String body)throws Exception {
        if(body==null||body.length()>8192||!CleanApp.paired(owner,cid))return;
        JSONObject op=new JSONObject(body);String kind=op.optString("op");
        if(kind.equals("hello")||kind.equals("ack")){
            if(owner.equals(author))return;
            if(!CleanApp.peer(owner,cid)){CleanApp.prefs().edit().putBoolean(CleanApp.key(owner,cid,"peer"),true).apply();CleanApp.refreshChat();}
            if(kind.equals("hello")){
                final String nonce=op.optString("nonce","legacy");if(!nonce.matches("[a-zA-Z0-9-]{1,64}"))return;
                String key="ack|"+owner+"|"+cid+"|"+author+"|"+nonce;
                // Rendering a carrier repeatedly must never generate repeated replies.
                if(!CleanApp.prefs().getBoolean(key,false)&&CleanApp.prefs().edit().putBoolean(key,true).commit()){
                    final String ack=new JSONObject().put("op","ack").put("nonce",nonce).toString();
                    CleanApp.main.post(new Runnable(){public void run(){
                        if(CleanApp.paired(owner,cid)&&owner.equals(NativeBridge.uid()))NativeBridge.send(owner,cid,"TikTok Clean: синхронизация подключена",Collections.singletonMap(CONTROL,ack),new NativeBridge.Completion(){public void finished(boolean ok,String error){if(!ok)CleanApp.prefs().edit().putString(CleanApp.key(owner,cid,"status"),error).apply();}});
                    }});
                }
            }
            return;
        }
        if(!kind.equals("edit")&&!kind.equals("delete"))return;
        long id=op.optLong("id"),rev=op.optLong("rev");String text=op.optString("text");
        if(id<=0||rev<=0||text.length()>2000)return;
        SQLiteDatabase d=database();if(d==null)return;
        long previous=0;boolean deleted=false;
        try(Cursor row=d.rawQuery("SELECT author,rev,deleted FROM changes WHERE owner=? AND cid=? AND id=? AND author=?",new String[]{owner,cid,Long.toString(id),author})){
            if(row.moveToFirst()){
                if(!author.equals(row.getString(0)))return;previous=row.getLong(1);deleted=row.getInt(2)!=0;
            }
        }
        // Unknown targets remain pending; their authors are checked when they are rendered.
        try(Cursor row=d.rawQuery("SELECT author FROM seen WHERE owner=? AND cid=? AND id=?",new String[]{owner,cid,Long.toString(id)})){
            if(row.moveToFirst()&&!Policy.authorCanChange(cid,cid,author,row.getString(0),id,rev,previous,true))return;
        }
        if(rev<=previous||deleted&&!kind.equals("delete"))return;
        ContentValues value=new ContentValues();value.put("owner",owner);value.put("cid",cid);value.put("id",id);value.put("author",author);value.put("rev",rev);value.put("deleted",deleted||kind.equals("delete")?1:0);value.put("text",kind.equals("delete")?"":text);
        d.insertWithOnConflict("changes",null,value,SQLiteDatabase.CONFLICT_REPLACE);CleanApp.refreshChat();
    }
    public static List<JSONObject> ownMessages(String owner,String cid) {
        List<JSONObject> result=new ArrayList<>();SQLiteDatabase d=database();if(d==null)return result;
        try(Cursor rows=d.rawQuery("SELECT s.id,s.body,c.text FROM seen s LEFT JOIN changes c ON c.owner=s.owner AND c.cid=s.cid AND c.id=s.id AND c.author=s.author WHERE s.owner=? AND s.cid=? AND s.author=? AND COALESCE(c.deleted,0)=0 ORDER BY s.created DESC LIMIT 80",new String[]{owner,cid,owner})){
            while(rows.moveToNext())try{
                JSONObject body=new JSONObject(rows.getString(1));
                String text=rows.isNull(2)?body.optString("text"):rows.getString(2);
                if(body.has("text")&&!text.trim().isEmpty())result.add(new JSONObject().put("id",rows.getLong(0)).put("text",text));
            }catch(Exception ignored){}
        }return result;
    }
    public static void change(final String owner,final String cid,final long id,final String text,final boolean remove,final NativeBridge.Completion callback) {
        try {
            if(!owner.equals(NativeBridge.uid())||!CleanApp.paired(owner,cid)||!CleanApp.peer(owner,cid))throw new IllegalStateException();
            try(Cursor row=database().rawQuery("SELECT author FROM seen WHERE owner=? AND cid=? AND id=?",new String[]{owner,cid,Long.toString(id)})){if(!row.moveToFirst()||!owner.equals(row.getString(0)))throw new SecurityException("Not own message");}
            final long rev=Math.max(System.currentTimeMillis(),CleanApp.prefs().getLong(CleanApp.key(owner,cid,"revision"),0)+1);
            CleanApp.prefs().edit().putLong(CleanApp.key(owner,cid,"revision"),rev).commit();
            final String data=new JSONObject().put("op",remove?"delete":"edit").put("id",id).put("rev",rev).put("text",text).toString();
            NativeBridge.send(owner,cid,remove?"TikTok Clean: сообщение скрыто":"TikTok Clean: сообщение изменено",Collections.singletonMap(CONTROL,data),new NativeBridge.Completion(){public void finished(boolean ok,String error){
                if(ok)try{consume(owner,cid,owner,data);}catch(Exception ignored){}callback.finished(ok,error);
            }});
        }catch(Exception failure){callback.finished(false,"Для синхронизации оба участника должны включить режим мода в чате");}
    }
    static void rememberSend(Object message,String owner,String cid,String author,Map<String,String> ext)throws Exception {
        if(!owner.equals(author)||ext.containsKey(CONTROL)||number(message,"getMsgId")<=0||!Boolean.TRUE.equals(NativeBridge.call(message,"isSuccessStatus")))return;
        long time=number(message,"getCreatedAt");if(time<100000000000L)time*=1000;else if(time>100000000000000L)time/=1000;
        if(time>System.currentTimeMillis()+5*60*1000L)return;
        if("1".equals(ext.get(AUTO))){
            long pending=CleanApp.prefs().getLong(CleanApp.key(owner,cid,"pending"),0);
            if(pending>0&&time>=pending-2*60*1000L)CleanApp.prefs().edit().putLong(CleanApp.key(owner,cid,"pending"),0).putLong(CleanApp.key(owner,cid,"last"),time).apply();
        }else if(time>CleanApp.prefs().getLong(CleanApp.key(owner,cid,"manual"),0))CleanApp.prefs().edit().putLong(CleanApp.key(owner,cid,"manual"),time).apply();
    }
}
