import com.android.apksig.ApkVerifier;
import java.io.File;
import java.nio.file.*;
public class ApkCertificate {
 public static void main(String[] args)throws Exception {
  var result=new ApkVerifier.Builder(new File(args[0])).setMinCheckedPlatformVersion(24).build().verify();
  if(!result.isVerified() || result.getSignerCertificates().size()!=1)throw new IllegalArgumentException("Invalid source signing certificate");
  Files.write(Path.of(args[1]),result.getSignerCertificates().get(0).getEncoded());
 }
}
