package org.elharika.pen;
import android.app.*;import android.os.*;import android.content.*;import android.graphics.*;import android.graphics.pdf.PdfDocument;import android.net.Uri;import android.view.*;import android.widget.*;import android.util.AtomicFile;import java.io.*;

public class MainActivity extends Activity {
 InkView ink; TextView status;
 void btn(LinearLayout row,int id,Runnable r){Button b=new Button(this);b.setText(id);b.setOnClickListener(v->r.run());row.addView(b);}
 @Override public void onCreate(Bundle b){super.onCreate(b);
  LinearLayout root=new LinearLayout(this);root.setOrientation(1);
  HorizontalScrollView scroll=new HorizontalScrollView(this);LinearLayout bar=new LinearLayout(this);scroll.addView(bar);root.addView(scroll);
  ink=new InkView(this);android.content.SharedPreferences prefs=getPreferences(0);ink.finger=prefs.getBoolean("finger",false);ink.gamma=prefs.getFloat("gamma",1);ink.base=prefs.getFloat("base",7);ink.buttonEraser=prefs.getBoolean("button",true);
  btn(bar,R.string.undo,()->ink.undo());btn(bar,R.string.clear,()->new AlertDialog.Builder(this).setMessage(R.string.confirm).setPositiveButton(R.string.yes,(d,w)->{ink.clear();save();}).setNegativeButton(R.string.no,null).show());
  btn(bar,R.string.export,()->export(10,"image/png","note.png"));btn(bar,R.string.pdf,()->export(11,"application/pdf","note.pdf"));
  btn(bar,R.string.import_image,()->{Intent i=new Intent(Intent.ACTION_OPEN_DOCUMENT);i.setType("image/*");i.addCategory(Intent.CATEGORY_OPENABLE);startActivityForResult(i,12);});btn(bar,R.string.tools,()->options());
  status=new TextView(this);status.setText(R.string.note);root.addView(status);root.addView(ink,new LinearLayout.LayoutParams(-1,0,1));setContentView(root);
  try{AtomicFile f=new AtomicFile(new File(getFilesDir(),"note.json"));ink.decode(new String(f.readFully(),"UTF-8"));}catch(FileNotFoundException ignored){}catch(Exception e){toast(R.string.error);}
  File image=new File(getFilesDir(),"background.png");if(image.exists())ink.background=BitmapFactory.decodeFile(image.toString());
 }
 void options(){LinearLayout l=new LinearLayout(this);l.setOrientation(1);
  CheckBox f=new CheckBox(this);f.setText(R.string.finger);f.setChecked(ink.finger);f.setOnCheckedChangeListener((v,c)->ink.finger=c);l.addView(f);
  CheckBox b=new CheckBox(this);b.setText(R.string.button);b.setChecked(ink.buttonEraser);b.setOnCheckedChangeListener((v,c)->ink.buttonEraser=c);l.addView(b);
  TextView t=new TextView(this);t.setText(R.string.pressure);l.addView(t);SeekBar s=new SeekBar(this);s.setMax(150);s.setProgress((int)((ink.gamma-0.5f)*100));s.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener(){public void onProgressChanged(SeekBar v,int p,boolean u){ink.gamma=.5f+p/100f;}public void onStartTrackingTouch(SeekBar v){}public void onStopTrackingTouch(SeekBar v){}});l.addView(s);
  TextView info=new TextView(this);info.setText(ink.telemetry);l.addView(info);new AlertDialog.Builder(this).setTitle(R.string.tools).setView(l).setPositiveButton(android.R.string.ok,(d,w)->save()).show();
 }
 void export(int code,String mime,String name){Intent i=new Intent(Intent.ACTION_CREATE_DOCUMENT);i.setType(mime);i.addCategory(Intent.CATEGORY_OPENABLE);i.putExtra(Intent.EXTRA_TITLE,name);startActivityForResult(i,code);}
 void toast(int s){Toast.makeText(this,s,Toast.LENGTH_LONG).show();}
 @Override protected void onActivityResult(int request,int result,Intent data){super.onActivityResult(request,result,data);if(result!=RESULT_OK||data==null||data.getData()==null)return;Uri u=data.getData();
  try{
   if(request==12){try(InputStream in=getContentResolver().openInputStream(u)){BitmapFactory.Options o=new BitmapFactory.Options();o.inJustDecodeBounds=true;BitmapFactory.decodeStream(in,null,o);int sample=1;while(o.outWidth/sample>2048||o.outHeight/sample>2048)sample*=2;o.inSampleSize=sample;o.inJustDecodeBounds=false;try(InputStream in2=getContentResolver().openInputStream(u)){Bitmap image=BitmapFactory.decodeStream(in2,null,o);if(image==null)throw new IOException("Invalid image");ink.background=image;ink.invalidate();}}save();return;}
   int w=1600,h=Math.max(1,Math.round(w*(float)ink.getHeight()/Math.max(1,ink.getWidth())));
   try(OutputStream out=getContentResolver().openOutputStream(u)){
    if(out==null)throw new IOException("Output unavailable");
    if(request==10){Bitmap image=Bitmap.createBitmap(w,h,Bitmap.Config.ARGB_8888);ink.drawPage(new Canvas(image),w,h);if(!image.compress(Bitmap.CompressFormat.PNG,100,out))throw new IOException("PNG failed");image.recycle();}
    else if(request==11){PdfDocument doc=new PdfDocument();try{PdfDocument.Page p=doc.startPage(new PdfDocument.PageInfo.Builder(w,h,1).create());try{ink.drawPage(p.getCanvas(),w,h);}finally{doc.finishPage(p);}doc.writeTo(out);}finally{doc.close();}}
   }toast(R.string.saved);
  }catch(Exception e){toast(R.string.error);}
 }
 void save(){
  ink.finishStroke();getPreferences(0).edit().putBoolean("finger",ink.finger).putBoolean("button",ink.buttonEraser).putFloat("gamma",ink.gamma).putFloat("base",ink.base).apply();
  AtomicFile f=new AtomicFile(new File(getFilesDir(),"note.json"));FileOutputStream out=null;
  try{out=f.startWrite();out.write(ink.encode().getBytes("UTF-8"));f.finishWrite(out);}catch(Exception e){if(out!=null)f.failWrite(out);toast(R.string.error);}
  File bg=new File(getFilesDir(),"background.png");if(ink.background!=null){AtomicFile a=new AtomicFile(bg);FileOutputStream s=null;try{s=a.startWrite();if(!ink.background.compress(Bitmap.CompressFormat.PNG,100,s))throw new IOException();a.finishWrite(s);}catch(Exception e){if(s!=null)a.failWrite(s);toast(R.string.error);}}else if(bg.exists())bg.delete();
 }
 @Override protected void onPause(){save();super.onPause();}
}
