package org.elharika.oneui;

import android.app.Activity;
import android.app.AlertDialog;
import android.appwidget.AppWidgetHost;
import android.appwidget.AppWidgetHostView;
import android.appwidget.AppWidgetManager;
import android.appwidget.AppWidgetProviderInfo;
import android.content.ComponentName;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.ClipData;
import android.content.pm.PackageManager;
import android.content.pm.ResolveInfo;
import android.content.res.Configuration;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.Drawable;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.BatteryManager;
import android.os.Bundle;
import android.provider.Settings;
import android.text.Editable;
import android.text.TextWatcher;
import android.util.TypedValue;
import android.view.DragEvent;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.view.ViewGroup;
import android.widget.BaseAdapter;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.GridView;
import android.widget.HorizontalScrollView;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextClock;
import android.widget.TextView;
import android.widget.Toast;
import org.json.JSONObject;
import java.text.DateFormat;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/**
 * Tablet home with persistent pages, native app shortcuts, folders and widgets.
 * Original ELHARIKA Launcher and Launcher Pro stay installed as safe alternatives.
 * Note: the system-wide One UI taskbar / DeX require firmware, not a Home app.
 */
public final class MainActivity extends Activity {
    private static final int REQ_PICK_WIDGET=8101;
    private static final int REQ_BIND_WIDGET=8102;
    private static final int WIDGET_HOST_ID=9441;
    private final ArrayList<App> installed=new ArrayList<>();
    private final Map<String,App> apps=new HashMap<>();
    private HomeStore store;
    private AppWidgetHost widgetHost;
    private FrameLayout root, drawerLayer;
    private LinearLayout mainColumn;
    private View wallpaper;
    private boolean drawerOpen=false, editMode=false, dragInProgress=false;
    private int currentPage=0, palette=0;
    private float gestureStartX,gestureStartY;
    private String drawerQuery="";
    private GridView homeGrid;
    private int ink=Color.WHITE;
    private int lightInk=0xFFD6E9FF;
    private int glass=0x55212B58;
    private int bright=0xFFDAE7FF;

    private static final class App {
        final String id,label;
        final Drawable icon;
        final ComponentName component;
        App(String id,String label,Drawable icon,ComponentName component){
            this.id=id;this.label=label;this.icon=icon;this.component=component;
        }
    }

    @Override public void onCreate(Bundle b){
        super.onCreate(b);
        store=new HomeStore(this);
        palette=store.theme();
        widgetHost=new AppWidgetHost(this,WIDGET_HOST_ID);
        getWindow().setStatusBarColor(0xFF273869);
        getWindow().setNavigationBarColor(0xFF192B57);
        loadApps();
        List<String> preferred=new ArrayList<>();
        for(App a:installed)preferred.add(a.id);
        store.initialize(preferred);
        render();
    }
    @Override protected void onStart(){
        super.onStart();
        try{widgetHost.startListening();}catch(Exception ignored){}
    }
    @Override protected void onStop(){
        try{widgetHost.stopListening();}catch(Exception ignored){}
        super.onStop();
    }
    @Override protected void onResume(){
        super.onResume();
        if(root!=null && !drawerOpen){
            loadApps();
            render();
        }
    }
    @Override protected void onNewIntent(Intent intent){
        super.onNewIntent(intent);
        closeDrawer();
        if(currentPage!=0){currentPage=0;render();}
    }
    private int d(float dp){return Math.round(getResources().getDisplayMetrics().density*dp);}
    private int sp(float s){return Math.round(s);}
    private boolean wide(){
        Configuration c=getResources().getConfiguration();
        return c.orientation==Configuration.ORIENTATION_LANDSCAPE&&c.screenWidthDp>=650;
    }
    private GradientDrawable shape(int color,int rad){
        GradientDrawable g=new GradientDrawable();
        g.setColor(color);g.setCornerRadius(d(rad));return g;
    }
    private GradientDrawable border(int color,int radius,int line){
        GradientDrawable g=shape(color,radius);
        g.setStroke(d(1),line);return g;
    }
    private TextView text(String txt,int size,boolean heavy,int color){
        TextView t=new TextView(this);
        t.setText(txt);
        t.setTextSize(TypedValue.COMPLEX_UNIT_SP,size);
        t.setTextColor(color);
        t.setGravity(Gravity.CENTER_VERTICAL);
        if(heavy)t.setTypeface(Typeface.create("sans-serif-medium",Typeface.NORMAL));
        return t;
    }
    private LinearLayout column(){LinearLayout l=new LinearLayout(this);l.setOrientation(1);return l;}
    private LinearLayout row(){LinearLayout l=new LinearLayout(this);l.setOrientation(0);l.setGravity(Gravity.CENTER_VERTICAL);return l;}
    private LinearLayout.LayoutParams lp(int w,int h,int left,int top,int right,int bottom){
        LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(w,h);
        p.setMargins(d(left),d(top),d(right),d(bottom));return p;
    }
    private TextView pill(String label,Runnable run){
        TextView t=text(label,14,true,ink);
        t.setGravity(Gravity.CENTER);t.setPadding(d(13),d(8),d(13),d(8));
        t.setBackground(border(0x59324480,18,0x558DAAE8));
        t.setOnClickListener(v->run.run());return t;
    }
    private void loadApps(){
        installed.clear();apps.clear();
        PackageManager pm=getPackageManager();
        Intent i=new Intent(Intent.ACTION_MAIN);i.addCategory(Intent.CATEGORY_LAUNCHER);
        List<ResolveInfo> ri=pm.queryIntentActivities(i,0);
        HashSet<String> known=new HashSet<>();
        for(ResolveInfo item:ri){
            if(item.activityInfo==null || getPackageName().equals(item.activityInfo.packageName))continue;
            ComponentName component=new ComponentName(item.activityInfo.packageName,item.activityInfo.name);
            String id=component.flattenToString();
            if(!known.add(id))continue;
            try {
                App app=new App(id,item.loadLabel(pm).toString(),item.loadIcon(pm),component);
                installed.add(app);apps.put(id,app);
            }catch(Exception ignored){}
        }
        installed.sort(Comparator.comparingInt(this::priority).thenComparing(a->a.label.toLowerCase(Locale.getDefault())));
    }
    private int priority(App app){
        String key=(app.component.getPackageName()+" "+app.label).toLowerCase(Locale.ROOT);
        if(key.contains("setting"))return 1;
        if(key.contains("files")||key.contains("file manager"))return 2;
        if(key.contains("browser")||key.contains("chrome"))return 3;
        if(key.contains("camera"))return 4;
        if(key.contains("gallery")||key.contains("photo"))return 5;
        if(key.contains("calendar"))return 6;
        if(key.contains("clock"))return 7;
        if(key.contains("calculator"))return 8;
        return 20;
    }
    private void render(){
        drawerOpen=false;
        ink=Color.WHITE;lightInk=0xFFE1EAFE;
        root=new FrameLayout(this);
        wallpaper=new WaveWallpaper(this,palette);
        root.addView(wallpaper,new FrameLayout.LayoutParams(-1,-1));
        mainColumn=column();
        mainColumn.setPadding(d(wide()?28:15),d(13),d(wide()?28:15),d(10));
        root.addView(mainColumn,new FrameLayout.LayoutParams(-1,-1));
        setContentView(root);
        renderTopBar();
        renderHomeBody();
        renderBottom();
    }
    private void renderTopBar(){
        LinearLayout top=row();
        TextView brand=text("ELHARIKA  •  ONE UI EDITION",wide()?18:15,true,ink);
        brand.setShadowLayer(d(2),0,d(1),0x66393D76);
        top.addView(brand,new LinearLayout.LayoutParams(0,d(53),1));
        top.addView(pill(editMode?getString(R.string.done):"✎  "+getString(R.string.edit),()->{
            editMode=!editMode;render();
        }),lp(-2,-2,0,0,8,0));
        top.addView(pill("⚙",this::showCustomize),lp(-2,-2,0,0,0,0));
        mainColumn.addView(top,lp(-1,d(54),0,0,0,4));
    }
    private void renderHomeBody(){
        LinearLayout area=new LinearLayout(this);
        boolean landscape=wide();
        area.setOrientation(landscape?0:1);
        mainColumn.addView(area,new LinearLayout.LayoutParams(-1,0,1));
        LinearLayout left=column();
        int sideWidth=landscape?getResources().getConfiguration().screenWidthDp/3:0;
        LinearLayout.LayoutParams leftParams=landscape
            ?lp(d(Math.min(sideWidth,340)),-1,0,0,18,0)
            :lp(-1,d(234),0,4,0,8);
        area.addView(left,leftParams);
        renderWidgetArea(left);

        LinearLayout right=column();
        LinearLayout.LayoutParams rightParams=landscape
            ?new LinearLayout.LayoutParams(0,-1,1)
            :new LinearLayout.LayoutParams(-1,0,1);
        area.addView(right,rightParams);

        LinearLayout rightTitle=row();
        TextView current=text(getString(R.string.home)+"   "+(currentPage+1)+"/"+HomeStore.PAGES,16,true,ink);
        rightTitle.addView(current,new LinearLayout.LayoutParams(0,d(44),1));
        rightTitle.addView(pill("＋",()->showDrawer()),lp(-2,-2,0,0,8,0));
        rightTitle.addView(pill("☷",this::showDrawer),lp(-2,-2,0,0,0,0));
        right.addView(rightTitle,lp(-1,d(48),0,0,0,4));

        List<HomeStore.Item> onPage=store.pages.get(currentPage);
        if(onPage.isEmpty()){
            TextView hint=text(getString(R.string.empty_home),15,false,lightInk);
            hint.setGravity(Gravity.CENTER);hint.setBackground(shape(0x33202F66,24));
            right.addView(hint,new LinearLayout.LayoutParams(-1,0,1));
        }else{
            homeGrid=new GridView(this);
            homeGrid.setNumColumns(landscape?6:4);
            homeGrid.setHorizontalSpacing(d(4));homeGrid.setVerticalSpacing(d(2));
            homeGrid.setStretchMode(GridView.STRETCH_COLUMN_WIDTH);
            homeGrid.setSelector(android.R.color.transparent);
            homeGrid.setPadding(0,d(2),0,d(2));
            homeGrid.setClipToPadding(false);
            homeGrid.setAdapter(new BaseAdapter(){
                public int getCount(){return onPage.size();}
                public Object getItem(int position){return onPage.get(position);}
                public long getItemId(int p){return p;}
                public View getView(int p,View v,ViewGroup parent){
                    HomeStore.Item item=onPage.get(p);
                    return homeCell(item,p);
                }
            });
            homeGrid.setOnItemClickListener((parent,v,pos,id)->openItem(onPage.get(pos)));
            homeGrid.setOnItemLongClickListener((parent,v,pos,id)->{
                if(editMode){
                    dragInProgress=true;
                    v.startDragAndDrop(ClipData.newPlainText("elharika-item",currentPage+":"+pos),
                        new View.DragShadowBuilder(v),null,0);
                }else showHomeMenu(onPage.get(pos),pos);
                return true;
            });
            homeGrid.setOnDragListener((v,event)->{
                if(event.getAction()==DragEvent.ACTION_DROP&&event.getClipData()!=null){
                    String[] split=event.getClipData().getItemAt(0).coerceToText(this).toString().split(":");
                    if(split.length==2){
                        try{
                            int srcPage=Integer.parseInt(split[0]),index=Integer.parseInt(split[1]);
                            store.relocate(srcPage,index,currentPage,store.pages.get(currentPage).size());
                            render();
                        }catch(Exception ignored){}
                    }
                    return true;
                }
                if(event.getAction()==DragEvent.ACTION_DRAG_ENDED)dragInProgress=false;
                return true;
            });
            right.addView(homeGrid,new LinearLayout.LayoutParams(-1,0,1));
        }
        renderPager(right);
    }
    private void renderWidgetArea(LinearLayout parent){
        LinearLayout card=column();
        card.setPadding(d(18),d(18),d(18),d(14));
        card.setBackground(border(0x49304489,25,0x4AFFFFFF));
        parent.addView(card,new LinearLayout.LayoutParams(-1,-1));
        LinearLayout top=row();
        TextView daily=text(getString(R.string.widgets).toUpperCase(Locale.getDefault()),12,true,0xFFD4E1FF);
        top.addView(daily,new LinearLayout.LayoutParams(0,d(31),1));
        top.addView(pill("＋",this::pickWidget),lp(-2,-2,0,0,0,0));
        card.addView(top);

        int id=store.widgetId();
        if(id>=0){
            AppWidgetProviderInfo info=AppWidgetManager.getInstance(this).getAppWidgetInfo(id);
            if(info!=null){
                try{
                    AppWidgetHostView view=widgetHost.createView(this,id,info);
                    view.setAppWidget(id,info);
                    card.addView(view,new LinearLayout.LayoutParams(-1,0,1));
                    TextView remove=text("✕",13,true,ink);
                    remove.setGravity(Gravity.END);
                    remove.setOnClickListener(v->{
                        widgetHost.deleteAppWidgetId(id);store.clearWidget();render();
                    });
                    card.addView(remove,lp(-1,d(28),0,0,0,0));
                    return;
                }catch(Exception ignored){}
            }else{store.clearWidget();}
        }
        TextClock clock=new TextClock(this);
        clock.setFormat24Hour("HH:mm");clock.setFormat12Hour("h:mm");
        clock.setTextSize(TypedValue.COMPLEX_UNIT_SP,wide()?57:43);
        clock.setTypeface(Typeface.create("sans-serif-light",Typeface.NORMAL));
        clock.setTextColor(ink);
        card.addView(clock,lp(-1,d(wide()?87:68),0,4,0,0));
        TextClock date=new TextClock(this);
        date.setFormat24Hour("EEEE, d MMMM");
        date.setFormat12Hour("EEEE, d MMMM");
        date.setTextSize(TypedValue.COMPLEX_UNIT_SP,15);
        date.setTextColor(lightInk);
        card.addView(date,lp(-1,d(29),0,0,0,12));

        LinearLayout row=row();
        row.setPadding(d(13),d(8),d(13),d(8));
        row.setBackground(shape(0x453A60A1,17));
        int percent=batteryPercent();
        TextView status=text("◉  "+(percent<0?"—":percent+"%")+"   •   "+installed.size()+" apps",14,true,ink);
        row.addView(status);
        card.addView(row,lp(-1,d(44),0,0,0,10));
        TextView hint=text(getString(R.string.drawer_hint),12,false,0xFFCADBFF);
        hint.setGravity(Gravity.CENTER);
        card.addView(hint,lp(-1,-2,0,0,0,0));
    }
    private int batteryPercent(){
        Intent i=registerReceiver(null,new IntentFilter(Intent.ACTION_BATTERY_CHANGED));
        if(i==null)return -1;
        int level=i.getIntExtra(BatteryManager.EXTRA_LEVEL,-1),scale=i.getIntExtra(BatteryManager.EXTRA_SCALE,-1);
        return scale>0&&level>=0?(level*100/scale):-1;
    }
    private void renderPager(LinearLayout container){
        LinearLayout dots=row();dots.setGravity(Gravity.CENTER);
        for(int k=0;k<HomeStore.PAGES;k++){
            final int page=k;
            TextView dot=text(k==currentPage?"●":"•",k==currentPage?23:20,true,ink);
            dot.setGravity(Gravity.CENTER);
            dot.setAlpha(k==currentPage?1f:.48f);
            dot.setOnClickListener(v->{currentPage=page;render();});
            dots.addView(dot,lp(d(28),d(34),0,0,0,0));
        }
        container.addView(dots,lp(-1,d(37),0,5,0,0));
    }
    private View iconView(App app,int size){
        ImageView v=new ImageView(this);
        if(app!=null)v.setImageDrawable(app.icon);
        v.setScaleType(ImageView.ScaleType.FIT_CENTER);
        v.setLayoutParams(new LinearLayout.LayoutParams(d(size),d(size)));
        return v;
    }
    private View homeCell(HomeStore.Item item,int index){
        LinearLayout cell=column();cell.setGravity(Gravity.TOP|Gravity.CENTER_HORIZONTAL);
        cell.setPadding(d(2),d(9),d(2),d(6));
        if(editMode)cell.setBackground(border(0x353E5DA6,17,0x668BC6FF));
        if(item.folder()){
            FrameLayout folder=new FrameLayout(this);
            folder.setBackground(shape(0xBCEAF2FF,18));
            LinearLayout miniature=row();miniature.setGravity(Gravity.CENTER);
            int count=0;
            for(String id:item.members){
                App a=apps.get(id);
                if(a!=null){
                    miniature.addView(iconView(a,20),lp(d(20),d(20),1,0,1,0));
                    if(++count==3)break;
                }
            }
            folder.addView(miniature,new FrameLayout.LayoutParams(d(store.iconSize()),d(store.iconSize()),Gravity.CENTER));
            cell.addView(folder,lp(d(store.iconSize()),d(store.iconSize()),0,0,0,6));
        }else cell.addView(iconView(apps.get(item.component),store.iconSize()),
            lp(d(store.iconSize()),d(store.iconSize()),0,0,0,6));
        String label=item.folder()?item.label:(apps.containsKey(item.component)?apps.get(item.component).label:"App");
        TextView name=text(label,12,false,ink);
        name.setMaxLines(2);
        name.setEllipsize(android.text.TextUtils.TruncateAt.END);
        name.setGravity(Gravity.CENTER);
        name.setShadowLayer(d(3),0,d(1),0x990F2050);
        cell.addView(name,lp(-1,d(36),0,0,0,0));
        cell.setOnDragListener((v,event)->{
            if(event.getAction()==DragEvent.ACTION_DROP&&editMode&&event.getClipData()!=null){
                try{
                    String[] t=event.getClipData().getItemAt(0).coerceToText(this).toString().split(":");
                    if(t.length==2){
                        int fromPage=Integer.parseInt(t[0]),from=Integer.parseInt(t[1]);
                        store.relocate(fromPage,from,currentPage,index);dragInProgress=false;render();
                    }
                }catch(Exception ignored){}
                return true;
            }
            if(event.getAction()==DragEvent.ACTION_DRAG_ENDED)dragInProgress=false;
            return true;
        });
        return cell;
    }
    private void renderBottom(){
        LinearLayout bar=row();bar.setGravity(Gravity.CENTER_VERTICAL);
        bar.setPadding(d(13),d(5),d(13),d(5));
        bar.setBackground(border(0x7F172853,27,0x5DFFFFFF));
        LinearLayout.LayoutParams barParams=lp(-1,d(84),0,6,0,0);
        mainColumn.addView(bar,barParams);
        TextView appsBtn=text("☷",29,true,ink);
        appsBtn.setGravity(Gravity.CENTER);appsBtn.setBackground(shape(0x59426FC7,18));
        appsBtn.setOnClickListener(v->showDrawer());
        bar.addView(appsBtn,lp(d(64),d(61),0,0,11,0));
        HorizontalScrollView scroll=new HorizontalScrollView(this);
        scroll.setHorizontalScrollBarEnabled(false);
        LinearLayout slots=row();
        for(HomeStore.Item item:store.dock){
            App app=apps.get(item.component);
            if(app==null)continue;
            LinearLayout slot=column();slot.setGravity(Gravity.CENTER);
            slot.addView(iconView(app,47),lp(d(47),d(47),0,0,0,0));
            TextView title=text(app.label,10,false,ink);
            title.setMaxLines(1);title.setGravity(Gravity.CENTER);
            title.setEllipsize(android.text.TextUtils.TruncateAt.END);
            slot.addView(title,lp(d(74),d(20),0,0,0,0));
            slot.setOnClickListener(v->launch(app));
            slot.setOnLongClickListener(v->{showDockMenu(app);return true;});
            slots.addView(slot,lp(d(79),d(71),0,0,4,0));
        }
        scroll.addView(slots);
        bar.addView(scroll,new LinearLayout.LayoutParams(0,-1,1));
        TextView settings=text("⚙",26,false,ink);
        settings.setGravity(Gravity.CENTER);
        settings.setOnClickListener(v->launchIntent(new Intent(Settings.ACTION_SETTINGS)));
        bar.addView(settings,lp(d(52),d(61),3,0,0,0));
    }
    private void openItem(HomeStore.Item item){
        if(item.folder())showFolder(item);
        else{App app=apps.get(item.component);if(app!=null)launch(app);}
    }
    private void launch(App app){
        Intent i=new Intent(Intent.ACTION_MAIN);
        i.addCategory(Intent.CATEGORY_LAUNCHER);
        i.setComponent(app.component);
        i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK|Intent.FLAG_ACTIVITY_RESET_TASK_IF_NEEDED);
        launchIntent(i);
    }
    private void launchIntent(Intent intent){
        try{startActivity(intent);}
        catch(Exception e){Toast.makeText(this,"Cannot open app",Toast.LENGTH_SHORT).show();}
    }
    private void showHomeMenu(HomeStore.Item item,int index){
        if(item.folder()){
            String[] choices={getString(R.string.rename_folder),getString(R.string.move_page),getString(R.string.remove_home)};
            new AlertDialog.Builder(this).setTitle(item.label).setItems(choices,(d,which)->{
                if(which==0)renameFolder(index,item);
                else if(which==1){store.movePage(currentPage,index);render();}
                else{store.removeAt(currentPage,index);render();}
            }).show();
        }else{
            App app=apps.get(item.component);if(app==null)return;
            String[] choices={getString(R.string.move_page),getString(R.string.create_folder),
                getString(R.string.remove_home),getString(R.string.app_info)};
            new AlertDialog.Builder(this).setTitle(app.label).setItems(choices,(d,which)->{
                if(which==0){if(!store.movePage(currentPage,index))toast("Page full");render();}
                if(which==1)chooseFolderPartner(index);
                if(which==2){store.remove(app.id,false);render();}
                if(which==3)appInfo(app);
            }).show();
        }
    }
    private void showDockMenu(App app){
        String[] choices={getString(R.string.remove_dock),getString(R.string.app_info)};
        new AlertDialog.Builder(this).setTitle(app.label).setItems(choices,(d,which)->{
            if(which==0){store.remove(app.id,true);render();}
            else appInfo(app);
        }).show();
    }
    private void showFolder(HomeStore.Item folder){
        ArrayList<String> labels=new ArrayList<>(),ids=new ArrayList<>();
        for(String cmp:folder.members){
            App a=apps.get(cmp);
            if(a!=null){labels.add(a.label);ids.add(cmp);}
        }
        new AlertDialog.Builder(this).setTitle("▦  "+folder.label)
            .setItems(labels.toArray(new String[0]),(d,pos)->{
                App a=apps.get(ids.get(pos));if(a!=null)launch(a);
            }).setNegativeButton(R.string.done,null).show();
    }
    private void renameFolder(int index,HomeStore.Item folder){
        EditText input=new EditText(this);input.setSingleLine(true);input.setText(folder.label);
        new AlertDialog.Builder(this).setTitle(R.string.rename_folder)
            .setView(input).setPositiveButton(R.string.done,(d,w)->{
                store.renameFolder(currentPage,index,input.getText().toString());render();
            }).setNegativeButton(R.string.cancel,null).show();
    }
    private void chooseFolderPartner(int from){
        List<HomeStore.Item> page=store.pages.get(currentPage);
        ArrayList<Integer> indexes=new ArrayList<>();ArrayList<String> choices=new ArrayList<>();
        for(int i=0;i<page.size();i++){
            if(i==from)continue;
            HomeStore.Item item=page.get(i);
            App a=apps.get(item.component);
            choices.add(item.folder()?item.label:a!=null?a.label:"App");
            indexes.add(i);
        }
        if(choices.isEmpty()){toast("Add another app to this page first");return;}
        new AlertDialog.Builder(this).setTitle(R.string.create_folder)
            .setItems(choices.toArray(new String[0]),(d,k)->{
                store.relocate(currentPage,from,currentPage,indexes.get(k));render();
            }).show();
    }
    private void appInfo(App app){
        launchIntent(new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
            Uri.parse("package:"+app.component.getPackageName())));
    }
    private void toast(String s){Toast.makeText(this,s,Toast.LENGTH_SHORT).show();}
    private void showCustomize(){
        String[] options={getString(R.string.ocean),getString(R.string.violet),
            getString(R.string.peach),"Icons 48dp","Icons 62dp","Icons 72dp",
            getString(R.string.pick_widget),getString(R.string.settings)};
        new AlertDialog.Builder(this).setTitle(R.string.personalize)
            .setItems(options,(dialog,pos)->{
                if(pos<=2){palette=pos;store.theme(pos);render();}
                else if(pos<=5){store.iconSize(pos==3?48:pos==4?62:72);render();}
                else if(pos==6)pickWidget();
                else launchIntent(new Intent(Settings.ACTION_SETTINGS));
            }).setNegativeButton(R.string.cancel,null).show();
    }
    private void showDrawer(){
        if(drawerOpen)return;
        drawerOpen=true;
        drawerLayer=new FrameLayout(this);
        drawerLayer.setBackgroundColor(0xB4091738);
        root.addView(drawerLayer,new FrameLayout.LayoutParams(-1,-1));
        LinearLayout panel=column();
        panel.setPadding(d(wide()?32:15),d(14),d(wide()?32:15),d(16));
        panel.setBackground(border(0xF21E315A,30,0x6DFFFFFF));
        FrameLayout.LayoutParams frame=new FrameLayout.LayoutParams(-1,-1);
        frame.setMargins(d(12),d(15),d(12),d(9));
        drawerLayer.addView(panel,frame);

        LinearLayout header=row();
        header.addView(text(getString(R.string.apps),24,true,ink),new LinearLayout.LayoutParams(0,d(52),1));
        header.addView(pill("✕",this::closeDrawer),lp(-2,-2,0,0,0,0));
        panel.addView(header);
        EditText query=new EditText(this);
        query.setSingleLine(true);query.setTextSize(TypedValue.COMPLEX_UNIT_SP,16);
        query.setTextColor(ink);query.setHintTextColor(0xFFAEC6EB);
        query.setHint("⌕   "+getString(R.string.search));
        query.setPadding(d(20),d(12),d(20),d(12));
        query.setBackground(border(0x8A334879,19,0x669DC2FA));
        panel.addView(query,lp(-1,d(55),0,8,0,14));

        GridView grid=new GridView(this);
        grid.setNumColumns(wide()?8:5);
        grid.setHorizontalSpacing(d(8));grid.setVerticalSpacing(d(11));
        grid.setStretchMode(GridView.STRETCH_COLUMN_WIDTH);
        grid.setClipToPadding(false);
        grid.setPadding(0,d(7),0,d(16));
        grid.setSelector(android.R.color.transparent);
        ArrayList<App> visible=new ArrayList<>(installed);
        BaseAdapter a=new BaseAdapter(){
            public int getCount(){return visible.size();}
            public Object getItem(int i){return visible.get(i);}
            public long getItemId(int i){return i;}
            public View getView(int i,View old,ViewGroup parent){
                App app=visible.get(i);
                LinearLayout card=column();card.setGravity(Gravity.CENTER);
                card.setPadding(d(3),d(8),d(3),d(6));
                card.addView(iconView(app,store.iconSize()),lp(d(store.iconSize()),d(store.iconSize()),0,0,0,5));
                TextView title=text(app.label,12,false,ink);
                title.setGravity(Gravity.CENTER);title.setMaxLines(2);
                title.setEllipsize(android.text.TextUtils.TruncateAt.END);
                card.addView(title,lp(-1,d(35),0,0,0,0));
                return card;
            }
        };
        grid.setAdapter(a);
        grid.setOnItemClickListener((parent,view,pos,id)->launch(visible.get(pos)));
        grid.setOnItemLongClickListener((parent,view,pos,id)->{
            App app=visible.get(pos);
            String[] opts={getString(R.string.add_home),getString(R.string.add_dock),getString(R.string.app_info)};
            new AlertDialog.Builder(this).setTitle(app.label)
                .setItems(opts,(dialog,choice)->{
                    if(choice==0){if(!store.addHome(app.id,currentPage))toast("Already added or page full");closeDrawer();render();}
                    if(choice==1){if(!store.addDock(app.id))toast("Already pinned or dock full");closeDrawer();render();}
                    if(choice==2)appInfo(app);
                }).show();
            return true;
        });
        panel.addView(grid,new LinearLayout.LayoutParams(-1,0,1));
        TextView note=text("＋  "+getString(R.string.add_home)+"  •  Long press any app",12,false,lightInk);
        note.setGravity(Gravity.CENTER);
        panel.addView(note,lp(-1,d(34),0,0,0,0));
        query.addTextChangedListener(new TextWatcher(){
            public void beforeTextChanged(CharSequence s,int start,int count,int after){}
            public void onTextChanged(CharSequence s,int start,int before,int count){
                drawerQuery=s.toString();
                visible.clear();
                String q=drawerQuery.trim().toLowerCase(Locale.getDefault());
                for(App app:installed)if(app.label.toLowerCase(Locale.getDefault()).contains(q))visible.add(app);
                a.notifyDataSetChanged();
            }
            public void afterTextChanged(Editable e){}
        });
        if(!drawerQuery.isEmpty())query.setText(drawerQuery);
    }
    private void closeDrawer(){
        if(!drawerOpen)return;
        drawerOpen=false;drawerQuery="";
        if(drawerLayer!=null && drawerLayer.getParent()!=null)root.removeView(drawerLayer);
        drawerLayer=null;
    }
    private void pickWidget(){
        try{
            int id=widgetHost.allocateAppWidgetId();
            Intent pick=new Intent(AppWidgetManager.ACTION_APPWIDGET_PICK);
            pick.putExtra(AppWidgetManager.EXTRA_APPWIDGET_ID,id);
            startActivityForResult(pick,REQ_PICK_WIDGET);
        }catch(Exception ex){toast("Widget picker not available on this ROM");}
    }
    @Override protected void onActivityResult(int request,int result,Intent data){
        super.onActivityResult(request,result,data);
        if(request==REQ_PICK_WIDGET||request==REQ_BIND_WIDGET){
            int id=data!=null?data.getIntExtra(AppWidgetManager.EXTRA_APPWIDGET_ID,-1):-1;
            if(result!=RESULT_OK||id<0){if(id>=0)widgetHost.deleteAppWidgetId(id);return;}
            AppWidgetProviderInfo info=AppWidgetManager.getInstance(this).getAppWidgetInfo(id);
            if(info==null){widgetHost.deleteAppWidgetId(id);return;}
            if(request==REQ_PICK_WIDGET){
                try{
                    if(!AppWidgetManager.getInstance(this).bindAppWidgetIdIfAllowed(id,info.provider)){
                        Intent bind=new Intent(AppWidgetManager.ACTION_APPWIDGET_BIND);
                        bind.putExtra(AppWidgetManager.EXTRA_APPWIDGET_ID,id);
                        bind.putExtra(AppWidgetManager.EXTRA_APPWIDGET_PROVIDER,info.provider);
                        startActivityForResult(bind,REQ_BIND_WIDGET);
                        return;
                    }
                }catch(Exception ex){widgetHost.deleteAppWidgetId(id);toast("Widget requires permission");return;}
            }
            if(store.widgetId()>=0)widgetHost.deleteAppWidgetId(store.widgetId());
            store.widgetId(id);render();
        }
    }
    @Override public boolean dispatchTouchEvent(MotionEvent event){
        if(event.getActionMasked()==MotionEvent.ACTION_DOWN){
            gestureStartX=event.getX();gestureStartY=event.getY();
        }else if(event.getActionMasked()==MotionEvent.ACTION_UP&&!dragInProgress){
            float dx=event.getX()-gestureStartX,dy=event.getY()-gestureStartY;
            if(!drawerOpen && dy<-d(100) && Math.abs(dy)>Math.abs(dx)*1.5){
                showDrawer();return true;
            }
            if(drawerOpen && dy>d(115)&&Math.abs(dy)>Math.abs(dx)*1.7){
                closeDrawer();return true;
            }
            if(!drawerOpen&&Math.abs(dx)>d(110)&&Math.abs(dx)>Math.abs(dy)*1.4){
                currentPage=(currentPage+(dx<0?1:HomeStore.PAGES-1))%HomeStore.PAGES;
                render();return true;
            }
        }
        return super.dispatchTouchEvent(event);
    }
    @Override public void onBackPressed(){
        if(drawerOpen){closeDrawer();return;}
        if(editMode){editMode=false;render();return;}
        if(currentPage!=0){currentPage=0;render();return;}
        // Home launcher stays visible.
    }
}
