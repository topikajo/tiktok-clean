package mod.privacy;
import java.util.*;

/** Pure retention rule, tested separately from TikTok's SDK. No mutation of response lists. */
public final class RefreshPolicy {
    public interface Id { String of(Object value); }
    /** Initial refresh transaction. Release on the first fresh frame or user navigation. */
    public static final class Selection {
        private final String previous, fresh;
        private boolean consumed;
        public Selection(String previous,String fresh){this.previous=previous;this.fresh=fresh;}
        public synchronized int index(int requested,String first,String second,boolean sameAccount) {
            if(consumed || requested!=0 || !sameAccount || previous==null || fresh==null ||
               previous.isEmpty() || fresh.isEmpty() || previous.equals(fresh) ||
               !previous.equals(first) || !fresh.equals(second))return requested;
            return 1;
        }
        public synchronized boolean consumed(){return consumed;}
        public synchronized void displayed(String id){if(fresh!=null && fresh.equals(id))consumed=true;}
        public synchronized void release(){consumed=true;}
    }
    public static List<?> retain(List<?> incoming,Object last,Id ids,boolean refresh,boolean sameAccount) {
        if(!refresh || !sameAccount || last==null || incoming==null || incoming.isEmpty())return incoming;
        String id=ids.of(last);if(id==null || id.isEmpty())return incoming;
        ArrayList<Object> result=new ArrayList<Object>();result.add(last);
        for(Object item:incoming)if(item==null || !id.equals(ids.of(item)))result.add(item);
        return result;
    }
}
