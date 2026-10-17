package mod.privacy;
import java.lang.reflect.*;
import java.util.*;

/** Bounded metadata only: never retains a video, Activity, account or receiver instance. */
public final class CachedReflect {
    private static final Class<?>[] EMPTY=new Class<?>[0];
    private static final Object[] EMPTY_VALUES=new Object[0];
    private static final class NullArgument {}
    private static final class Key {
        final Class<?> owner;final String name;final Class<?>[] arguments;final int hash;final boolean staticOnly;
        Key(Class<?> owner,String name,Object[] values,boolean staticOnly){
            this.owner=owner;this.name=name;this.staticOnly=staticOnly;arguments=values.length==0?EMPTY:new Class<?>[values.length];
            int n=31*(31*owner.hashCode()+name.hashCode())+(staticOnly?1:0);
            for(int i=0;i<values.length;i++){arguments[i]=values[i]==null?NullArgument.class:values[i].getClass();n=31*n+arguments[i].hashCode();}hash=n;
        }
        public int hashCode(){return hash;}
        public boolean equals(Object value){if(!(value instanceof Key))return false;Key k=(Key)value;return owner==k.owner&&staticOnly==k.staticOnly&&name.equals(k.name)&&Arrays.equals(arguments,k.arguments);}
    }
    private static final Map<Key,Method> methods=new LinkedHashMap<Key,Method>(64,.75f,true){
        protected boolean removeEldestEntry(Map.Entry<Key,Method> e){return size()>256;}
    };
    private static final Map<Key,Field> fields=new LinkedHashMap<Key,Field>(32,.75f,true){
        protected boolean removeEldestEntry(Map.Entry<Key,Field> e){return size()>128;}
    };
    private static Class<?> boxed(Class<?> t) {
        if(!t.isPrimitive())return t;
        if(t==int.class)return Integer.class;if(t==float.class)return Float.class;if(t==boolean.class)return Boolean.class;
        if(t==long.class)return Long.class;if(t==double.class)return Double.class;if(t==short.class)return Short.class;
        if(t==byte.class)return Byte.class;if(t==char.class)return Character.class;return Void.class;
    }
    private static int score(Class<?> expected,Class<?> actual) {
        if(actual==NullArgument.class)return expected.isPrimitive()?-1:20;
        Class<?> type=boxed(expected);if(type==actual)return expected.isPrimitive()?1:0;
        if(type.isAssignableFrom(actual)) {
            // Prefer a narrow interface/class to Object for inherited SDK overloads.
            if(type==Object.class)return 15;
            int depth=1;for(Class<?> c=actual.getSuperclass();c!=null;c=c.getSuperclass(),depth++)if(c==type)return depth;
            return 2;
        }
        if(expected.isPrimitive()&&expected!=boolean.class) {
            List<Class<?>> numeric=Arrays.<Class<?>>asList(Byte.class,Short.class,Integer.class,Long.class,Float.class,Double.class);
            int from=numeric.indexOf(actual),to=numeric.indexOf(type);
            if(actual==Character.class)from=2;
            if(from>=0&&to>from)return 5+to-from;
            if(actual==Character.class&&type==Integer.class)return 5;
        }
        return -1;
    }
    private static boolean narrower(Method a,Method b) {
        Class<?>[] x=a.getParameterTypes(),y=b.getParameterTypes();boolean better=false;
        for(int i=0;i<x.length;i++){Class<?> xx=boxed(x[i]),yy=boxed(y[i]);if(!yy.isAssignableFrom(xx))return false;better|=xx!=yy;}
        return better||(!a.isBridge()&&b.isBridge());
    }
    public static Object call(Object receiver,String name,Object... values)throws Exception {
        if(receiver==null)throw new NullPointerException("receiver");
        Class<?> type=receiver instanceof Class?(Class<?>)receiver:receiver.getClass();Key key=new Key(type,name,values,receiver instanceof Class);Method method;
        synchronized(methods){method=methods.get(key);}
        if(method==null) {
            int best=Integer.MAX_VALUE;boolean ambiguous=false;
            for(Method candidate:type.getMethods()) {
                if(!candidate.getName().equals(name)||candidate.getParameterTypes().length!=values.length ||
                   (receiver instanceof Class&&!Modifier.isStatic(candidate.getModifiers())))continue;
                Class<?>[] types=candidate.getParameterTypes();int total=0;boolean valid=true;
                for(int i=0;i<types.length;i++){int n=score(types[i],key.arguments[i]);if(n<0){valid=false;break;}total+=n;}
                if(!valid)continue;
                if(total<best){method=candidate;best=total;ambiguous=false;}
                else if(total==best) {
                    if(narrower(candidate,method)){method=candidate;ambiguous=false;}
                    else if(!narrower(method,candidate)&&!Arrays.equals(types,method.getParameterTypes()))ambiguous=true;
                }
            }
            if(method==null||ambiguous)throw new NoSuchMethodException(type.getName()+"."+name+(ambiguous?" (ambiguous)":""));
            method.setAccessible(true);synchronized(methods){methods.put(key,method);}
        }
        return method.invoke(receiver instanceof Class?null:receiver,values);
    }
    public static Object field(Object receiver,String name)throws Exception {
        if(receiver==null)throw new NullPointerException("receiver");
        Key key=new Key(receiver.getClass(),name,EMPTY_VALUES,false);Field found;
        synchronized(fields){found=fields.get(key);}
        if(found==null) {
            for(Class<?> type=receiver.getClass();type!=null;type=type.getSuperclass())try{found=type.getDeclaredField(name);break;}catch(NoSuchFieldException ignored){}
            if(found==null)throw new NoSuchFieldException(name);
            found.setAccessible(true);synchronized(fields){fields.put(key,found);}
        }
        return found.get(receiver);
    }
}
