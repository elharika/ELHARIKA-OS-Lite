package org.elharika.oneui;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.LinearGradient;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.RadialGradient;
import android.graphics.Shader;
import android.view.View;

/** Lightweight original soft-wave tablet wallpaper (no proprietary Samsung assets). */
final class WaveWallpaper extends View {
    private int theme;
    private final Paint p = new Paint(Paint.ANTI_ALIAS_FLAG);
    WaveWallpaper(Context ctx,int theme){super(ctx);this.theme=theme;setLayerType(View.LAYER_TYPE_SOFTWARE,null);}
    void theme(int value){theme=value;invalidate();}
    @Override protected void onDraw(Canvas c){
        int w=getWidth(),h=getHeight();if(w==0||h==0)return;
        int[] palette;
        if(theme==1) palette=new int[]{Color.rgb(44,31,107),Color.rgb(112,77,189),Color.rgb(201,136,190)};
        else if(theme==2) palette=new int[]{Color.rgb(75,79,150),Color.rgb(235,136,140),Color.rgb(255,204,169)};
        else palette=new int[]{Color.rgb(28,49,133),Color.rgb(65,98,211),Color.rgb(127,188,236)};
        p.setShader(new LinearGradient(0,0,w,h,palette,null,Shader.TileMode.CLAMP));
        c.drawRect(0,0,w,h,p);p.setShader(null);
        p.setShader(new RadialGradient(w*.08f,h*.13f,w*.85f,new int[]{0x66C9E8FF,0x25FFFFFF,0x00FFFFFF},null,Shader.TileMode.CLAMP));
        c.drawCircle(w*.08f,h*.13f,w*.85f,p);p.setShader(null);
        Path v=new Path();
        v.moveTo(w*.39f,-h*.08f);
        v.cubicTo(w*.72f,h*.12f,w*.65f,h*.51f,w*1.06f,h*.65f);
        v.lineTo(w*1.03f,h*1.04f);v.lineTo(w*.43f,h*1.04f);
        v.cubicTo(w*.15f,h*.67f,w*.47f,h*.37f,w*.39f,-h*.08f);
        v.close();
        int wave=theme==2?0x55FFD6BC:theme==1?0x556E8CEA:0x5579D0FF;
        p.setColor(wave);p.setShader(null);c.drawPath(v,p);
        Path bottom=new Path();
        bottom.moveTo(0,h*.81f);
        bottom.cubicTo(w*.19f,h*.59f,w*.30f,h*.95f,w*.51f,h*.82f);
        bottom.cubicTo(w*.70f,h*.70f,w*.83f,h*.88f,w,h*.78f);
        bottom.lineTo(w,h);bottom.lineTo(0,h);bottom.close();
        p.setColor(theme==2?0x66F9CAD3:0x666673D9);c.drawPath(bottom,p);
        p.setShader(new RadialGradient(w*.86f,h*.16f,w*.46f,
            new int[]{0x55FFFFFF,0x00FFFFFF},null,Shader.TileMode.CLAMP));
        c.drawCircle(w*.86f,h*.16f,w*.46f,p);p.setShader(null);
    }
}
