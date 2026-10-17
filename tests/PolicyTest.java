import mod.clean.Policy;
import mod.clean.UpdateChannel;
public final class PolicyTest {
    static void check(boolean c,String m){if(!c)throw new AssertionError(m);}
    public static void main(String[] args){
        long now=1000000000L;
        check(Policy.due(true,"a","a",0,0,now),"enabled and due");
        check(!Policy.due(false,"a","a",0,0,now),"disabled");
        check(!Policy.due(true,"a","b",0,0,now),"account switch");
        check(!Policy.due(true,"","",0,0,now),"logged out");
        check(!Policy.due(true,"a","a",now-1000,0,now),"recent manual/send activity");
        check(!Policy.due(true,"a","a",0,1,now),"uncertain pending send");
        check(!Policy.due(true,"a","a",now+1000,0,now),"clock rollback");
        check(Policy.authorCanChange("c","c","a","a",5,2,1,true),"own message");
        check(!Policy.authorCanChange("c","c","a","b",5,2,1,true),"foreign author");
        check(!Policy.authorCanChange("c","other","a","a",5,2,1,true),"cross chat");
        check(!Policy.authorCanChange("c","c","a","a",0,2,1,true),"unacknowledged target");
        check(!Policy.authorCanChange("c","c","a","a",5,1,1,true),"replay");
        check(!Policy.authorCanChange("c","c","a","a",5,2,1,false),"non opted-in recipient");
        check(UpdateChannel.sameSigners(new byte[][]{{1,2},{3}},new byte[][]{{3},{1,2}}),"same signer set");
        check(!UpdateChannel.sameSigners(new byte[][]{{1,2}},new byte[][]{{1,3}}),"different signer");
        check(!UpdateChannel.sameSigners(new byte[0][],new byte[0][]),"unsigned rejected");
        System.out.println("PASS: 16 account, streak, message authorization and signer cases");
    }
}
