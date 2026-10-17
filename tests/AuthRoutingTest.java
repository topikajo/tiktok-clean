import mod.clean.AuthRouting;
public final class AuthRoutingTest {
    static int cases;
    static void check(boolean value,String message){if(!value)throw new AssertionError(message);cases++;}
    public static void main(String[] args){
        check("google_web".equals(AuthRouting.providerOverride("google")),"Google uses registered browser provider");
        check("google_web".equals(AuthRouting.providerOverride("google_onetap")),"Google credential alias uses browser provider");
        check("google_web".equals(AuthRouting.providerOverride("google_web")),"explicit Google browser alias");
        for(String platform:new String[]{null,"email","phone","username","facebook","line","kakaotalk","passkey","unknown"})check(AuthRouting.providerOverride(platform)==null,"original resolver retained for "+platform);
        System.out.println("PASS: "+cases+" Google routing and non-Google preservation cases");
    }
}
