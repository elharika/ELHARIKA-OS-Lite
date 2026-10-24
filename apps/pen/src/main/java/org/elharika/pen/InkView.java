package org.elharika.pen;
import android.content.Context;
import android.graphics.*;
import android.view.*;
import org.json.*;
import java.util.*;

public final class InkView extends View {
 static final class Dot { float x,y,p; Dot(float a,float b,float c){x=a;y=b;p=c;} }
 static final class Stroke { boolean erase; float base,gamma; ArrayList<Dot> points=new ArrayList<>(); }
 final ArrayList<Stroke> strokes=new ArrayList<>();
 final Paint paint=new Paint(3);
 static final int MAX_STROKES=2000, MAX_POINTS=100000, MAX_TEXT=12000000;
 int pointCount=0;
 final PorterDuffXfermode clearMode=new PorterDuffXfermode(PorterDuff.Mode.CLEAR);
 Stroke current; int pointer=-1;
 boolean finger=false,buttonEraser=true; float base=7,gamma=1;
 Bitmap background; float hoverX=-1,hoverY=-1;
 String telemetry="No pen events yet";
 public InkView(Context c){super(c);setBackgroundColor(Color.WHITE);setSaveEnabled(false);}
 void drawPage(Canvas c,int w,int h){
  c.drawColor(Color.WHITE);
  if(background!=null)c.drawBitmap(background,null,new Rect(0,0,w,h),paint);
  paint.setStyle(Paint.Style.STROKE);paint.setStrokeCap(Paint.Cap.ROUND);paint.setStrokeJoin(Paint.Join.ROUND);
  boolean hasEraser=false;for(Stroke s:strokes)if(s.erase){hasEraser=true;break;}
  int layer=hasEraser?c.saveLayer(0,0,w,h,null):-1;
  try {
  for(Stroke s:strokes){
   paint.setXfermode(s.erase?clearMode:null);
   paint.setColor(Color.rgb(21,40,60));
   Dot last=null;
   for(Dot d:s.points){
    paint.setStrokeWidth(StrokeMath.width(d.p,s.base,s.gamma));
    if(last==null)c.drawPoint(d.x*w,d.y*h,paint);
    else c.drawLine(last.x*w,last.y*h,d.x*w,d.y*h,paint);
    last=d;
   }
  }
  } finally {paint.setXfermode(null);if(layer>=0)c.restoreToCount(layer);}
 }
 @Override protected void onDraw(Canvas c){super.onDraw(c);drawPage(c,getWidth(),getHeight());
  if(hoverX>=0){paint.setColor(Color.GRAY);paint.setStyle(Paint.Style.STROKE);paint.setStrokeWidth(1);c.drawCircle(hoverX,hoverY,9,paint);}
 }
 @Override public boolean onHoverEvent(MotionEvent e){
  if(e.getToolType(0)==MotionEvent.TOOL_TYPE_STYLUS){hoverX=e.getActionMasked()==MotionEvent.ACTION_HOVER_EXIT?-1:e.getX();hoverY=e.getY();telemetry="Hover; button="+e.getButtonState();invalidate();return true;}
  return super.onHoverEvent(e);
 }
 boolean eligible(MotionEvent e,int i){int t=e.getToolType(i);return t==MotionEvent.TOOL_TYPE_STYLUS||t==MotionEvent.TOOL_TYPE_ERASER||(finger&&t==MotionEvent.TOOL_TYPE_FINGER);}
 void point(MotionEvent e,int i,int history){
  float x=history<0?e.getX(i):e.getHistoricalX(i,history),y=history<0?e.getY(i):e.getHistoricalY(i,history),p=history<0?e.getPressure(i):e.getHistoricalPressure(i,history);
  if(pointCount>=MAX_POINTS){telemetry="Page limit reached; export or clear before continuing";return;}
  if(!Float.isFinite(x)||!Float.isFinite(y)||!Float.isFinite(p))return;
  pointCount++;
  current.points.add(new Dot(x/Math.max(1,getWidth()),y/Math.max(1,getHeight()),p));
  telemetry="tool="+e.getToolType(i)+" pressure="+p+" buttons="+e.getButtonState()+" eventTime="+e.getEventTime();
 }
 @Override public boolean onTouchEvent(MotionEvent e){
  int a=e.getActionMasked(),idx=e.getActionIndex();
  if(a==MotionEvent.ACTION_CANCEL){if(current!=null){pointCount-=current.points.size();strokes.remove(current);}current=null;pointer=-1;invalidate();return true;}
  if((a==MotionEvent.ACTION_DOWN||a==MotionEvent.ACTION_POINTER_DOWN)&&pointer<0&&eligible(e,idx)){
   if(strokes.size()>=MAX_STROKES||pointCount>=MAX_POINTS)return true;
   pointer=e.getPointerId(idx);current=new Stroke();current.base=base;current.gamma=gamma;
   current.erase=e.getToolType(idx)==MotionEvent.TOOL_TYPE_ERASER||(buttonEraser&&(e.getButtonState()&MotionEvent.BUTTON_STYLUS_PRIMARY)!=0);
   if(current.erase)current.base*=4;
   strokes.add(current);point(e,idx,-1);
  }else if(current!=null){
   int i=e.findPointerIndex(pointer);
   if(i>=0){
    if(a==MotionEvent.ACTION_MOVE){for(int h=0;h<e.getHistorySize();h++)point(e,i,h);point(e,i,-1);}
    if((a==MotionEvent.ACTION_UP||a==MotionEvent.ACTION_POINTER_UP)&&idx==i){point(e,i,-1);current=null;pointer=-1;}
   }
  }
  invalidate();return true;
 }
 void finishStroke(){current=null;pointer=-1;}
 void undo(){finishStroke();if(!strokes.isEmpty())pointCount-=strokes.remove(strokes.size()-1).points.size();invalidate();}
 void clear(){finishStroke();strokes.clear();pointCount=0;background=null;invalidate();}
 String encode() throws JSONException {
  JSONArray all=new JSONArray();for(Stroke s:strokes){JSONArray pts=new JSONArray();for(Dot d:s.points)pts.put(new JSONArray().put(d.x).put(d.y).put(d.p));all.put(new JSONObject().put("erase",s.erase).put("base",s.base).put("gamma",s.gamma).put("points",pts));}
  return new JSONObject().put("version",1).put("strokes",all).toString();
 }
 static float checked(double value,float min,float max)throws JSONException{
  if(Double.isNaN(value)||Double.isInfinite(value)||value<min||value>max)throw new JSONException("Invalid stroke value");
  return (float)value;
 }
 void decode(String text)throws JSONException{
  if(text.length()>MAX_TEXT)throw new JSONException("Note too large");
  JSONObject root=new JSONObject(text);if(root.getInt("version")!=1)throw new JSONException("version");
  JSONArray all=root.getJSONArray("strokes");
  if(all.length()>MAX_STROKES)throw new JSONException("Too many strokes");
  ArrayList<Stroke> parsed=new ArrayList<>();int count=0;
  for(int i=0;i<all.length();i++){
   JSONObject j=all.getJSONObject(i);Stroke s=new Stroke();s.erase=j.getBoolean("erase");
   s.base=checked(j.getDouble("base"),0.1f,256);s.gamma=checked(j.getDouble("gamma"),0.1f,4);
   JSONArray pts=j.getJSONArray("points");
   if(pts.length()>MAX_POINTS-count)throw new JSONException("Too many points");
   count+=pts.length();
   for(int k=0;k<pts.length();k++){
    JSONArray d=pts.getJSONArray(k);
    s.points.add(new Dot(checked(d.getDouble(0),-16,16),checked(d.getDouble(1),-16,16),checked(d.getDouble(2),0,16)));
   }
   parsed.add(s);
  }
  finishStroke();strokes.clear();strokes.addAll(parsed);pointCount=count;invalidate();
 }
}
