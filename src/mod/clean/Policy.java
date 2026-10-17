package mod.clean;

/** Pure rules shared by the UI and background job. */
public final class Policy {
    public static final long INTERVAL=20L*60*60*1000;
    public static boolean due(boolean enabled,String owner,String current,long last,long pending,long now) {
        return enabled&&owner!=null&&!owner.isEmpty()&&owner.equals(current)&&pending==0&&now>=last&&now-last>=INTERVAL;
    }
    public static boolean authorCanChange(String cid,String targetCid,String author,String targetAuthor,long id,long revision,long previous,boolean enabled) {
        return enabled&&cid!=null&&cid.equals(targetCid)&&author!=null&&!author.isEmpty()&&author.equals(targetAuthor)&&id>0&&revision>previous;
    }
}
