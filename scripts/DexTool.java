import com.android.tools.smali.baksmali.*;
import com.android.tools.smali.smali.*;
import com.android.tools.smali.dexlib2.*;
import com.android.tools.smali.dexlib2.iface.*;
import com.android.tools.smali.dexlib2.iface.instruction.*;
import com.android.tools.smali.dexlib2.iface.reference.*;
import com.android.tools.smali.dexlib2.immutable.ImmutableDexFile;
import java.io.*;
import java.util.*;
import java.util.regex.Pattern;

/** Uses official smali/dexlib APIs bundled with JADX; no APK code is executed. */
public class DexTool {
  // Infer each input's opcode set from its DEX header. Patch classes use DEX 039.
  static final Opcodes OP = null;
  public static void main(String[] a) throws Exception {
    switch (a[0]) {
      case "references": {
        var container=DexFileFactory.loadDexContainer(new File(a[1]),OP);
        Pattern pattern=Pattern.compile(a[3]);
        try(PrintWriter out=new PrintWriter(new OutputStreamWriter(new FileOutputStream(a[2]),java.nio.charset.StandardCharsets.UTF_8))) {
          for(String name:container.getDexEntryNames())for(ClassDef c:container.getEntry(name).getDexFile().getClasses())for(Method m:c.getMethods()) {
            MethodImplementation impl=m.getImplementation();if(impl==null)continue;
            for(Instruction instruction:impl.getInstructions())if(instruction instanceof ReferenceInstruction reference&&reference.getReference() instanceof MethodReference method&&pattern.matcher(method.toString()).find())
              out.printf("%s\t%s\t%s%n",name,m.toString(),method.toString());
          }
        }
        break;
      }
      case "disassemble": {
        DexFile d= DexFileFactory.loadDexFile(a[1], OP);
        BaksmaliOptions o=new BaksmaliOptions(); o.apiLevel=28; o.debugInfo=true;
        List<String> filter=null;
        if(a.length>3){
          if(a[3].startsWith("@"))filter=Arrays.asList(new com.google.gson.Gson().fromJson(java.nio.file.Files.readString(java.nio.file.Path.of(a[3].substring(1))),String[].class));
          else filter=Arrays.asList(Arrays.copyOfRange(a,3,a.length));
        }
        if(!Baksmali.disassembleDexFile(d,new File(a[2]),4,o,filter))throw new IOException("disassembly failed");
        break;
      }
      case "assemble": {
        SmaliOptions o=new SmaliOptions(); o.apiLevel=28;o.jobs=4;o.outputDexFile=a[2];o.verboseErrors=true;
        if(!Smali.assemble(o,a[1]))throw new IOException("assembly failed");
        break;
      }
      case "merge": {
        DexFile original=DexFileFactory.loadDexFile(a[1],OP);
        Map<String,ClassDef> classes=new TreeMap<>();
        for(ClassDef c:original.getClasses())classes.put(c.getType(),c);
        for(int i=2;i<a.length-1;i++)for(ClassDef c:DexFileFactory.loadDexFile(a[i],OP).getClasses()) {
          classes.put(c.getType(),c);System.out.println("replace/add "+c.getType());
        }
        DexFileFactory.writeDexFile(a[a.length-1],new ImmutableDexFile(original.getOpcodes(),classes.values()));
        System.out.println("classes "+original.getClasses().size()+" -> "+classes.size());
        break;
      }
      case "scan": {
        var container=DexFileFactory.loadDexContainer(new File(a[1]),OP);
        Pattern strings=Pattern.compile("comment.*(?:sticker|gif)|(?:sticker|gif).*comment|https?://(?:[^/]*(?:mod|central|platinum|github|gitlab)|t\\.me)|aHR0cHM|TikTok-Mod",Pattern.CASE_INSENSITIVE);
        Pattern methods=Pattern.compile("^(?:Lme/tiktokupdatez/|Lcom/tiktok/plugin/|Lcom/aaaaaaa/)|^Landroid/telephony/TelephonyManager;->get(?:Sim|Network)|^Lcom/ss/android/ugc/aweme/feed/model/FeedItemList;->getItems|^Lcom/ss/android/ugc/aweme/feed/model/Aweme;->isAd");
        try(PrintWriter out=new PrintWriter(new OutputStreamWriter(new FileOutputStream(a[2]),java.nio.charset.StandardCharsets.UTF_8))) {
          long count=0;
          for(String dex:container.getDexEntryNames()) {
            for(ClassDef c:container.getEntry(dex).getDexFile().getClasses())for(Method m:c.getMethods()) {
              MethodImplementation impl=m.getImplementation();if(impl==null)continue;count++;
              int offset=0;
              for(Instruction i:impl.getInstructions()) {
                if(i instanceof ReferenceInstruction ri) {
                  Reference r=ri.getReference();
                  String text=r instanceof StringReference sr?sr.getString():r.toString();
                  if((r instanceof StringReference && strings.matcher(text).find())||(r instanceof MethodReference && methods.matcher(text).find()))
                    out.printf("%s\t%s\t%d\t%s\t%s%n",dex,m.toString(),offset,i.getOpcode().name(),text.replace("\n","\\n").replace("\t","\\t"));
                }
                offset+=i.getCodeUnits();
              }
            }
          }
          System.out.println("Scanned method implementations: "+count);
        }
        break;
      }
      case "find_strings": {
        var container=DexFileFactory.loadDexContainer(new File(a[1]),OP);
        Pattern pattern=Pattern.compile(a[3],Pattern.CASE_INSENSITIVE);
        try(PrintWriter out=new PrintWriter(new OutputStreamWriter(new FileOutputStream(a[2]),java.nio.charset.StandardCharsets.UTF_8))) {
          for(String name:container.getDexEntryNames())for(ClassDef c:container.getEntry(name).getDexFile().getClasses())for(Method m:c.getMethods()) {
            MethodImplementation impl=m.getImplementation();if(impl==null)continue;
            for(Instruction instruction:impl.getInstructions())if(instruction instanceof ReferenceInstruction reference&&reference.getReference() instanceof StringReference string&&pattern.matcher(string.getString()).find())
              out.printf("%s\t%s\t%s%n",name,m.toString(),string.getString().replace("\n","\\n").replace("\t","\\t"));
          }
        }
        break;
      }
      default: throw new IllegalArgumentException(a[0]);
    }
  }
}
