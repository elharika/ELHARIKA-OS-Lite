package org.elharika.pen;
public final class StrokeMath {
 private StrokeMath() {}
 public static float width(float p,float base,float gamma) {
  if(Float.isNaN(p)||Float.isInfinite(p)) p=0;
  p=Math.max(0,Math.min(1,p));
  return base*(0.15f+0.85f*(float)Math.pow(p,gamma));
 }
}
