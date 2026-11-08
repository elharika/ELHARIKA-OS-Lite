package org.elharika.launcher.pro;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.content.pm.ResolveInfo;
import android.content.res.Configuration;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.Drawable;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Bundle;
import android.provider.Settings;
import android.text.Editable;
import android.text.TextWatcher;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.view.inputmethod.InputMethodManager;
import android.widget.BaseAdapter;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.GridView;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextClock;
import android.widget.TextView;
import android.widget.Toast;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;

/**
 * ELHARIKA Launcher Pro – Android 11 tablet-first home screen.
 * Standalone package keeps the original ROM launcher untouched and selectable.
 * No network, accessibility, overlay, root, data-migration or privileged permissions.
 */
public final class MainActivity extends Activity {
    private final List<AppEntry> installed = new ArrayList<>();
    private final List<AppEntry> displayed = new ArrayList<>();
    private SharedPreferences prefs;
    private Set<String> favorites = new HashSet<>();
    private GridView grid;
    private BaseAdapter adapter;
    private TextView countLabel;
    private TextView favoritesLabel;
    private LinearLayout dock;
    private EditText search;
    private TextView allTab, favoritesTab;
    private boolean dark;
    private boolean favoritesOnly;
    private String filter = "";
    private int foreground, secondary, cardColor, accent, background;

    private static final class AppEntry {
        final ComponentName component;
        final String label;
        final Drawable icon;
        AppEntry(ComponentName component, String label, Drawable icon) {
            this.component = component; this.label = label; this.icon = icon;
        }
        String id() { return component.flattenToString(); }
    }

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        prefs = getSharedPreferences("launcher_pro_v1", MODE_PRIVATE);
        dark = prefs.getBoolean("dark", true);
        favorites = new HashSet<>(prefs.getStringSet("favorites", Collections.emptySet()));
        getWindow().setStatusBarColor(Color.rgb(8,14,28));
        getWindow().setNavigationBarColor(Color.rgb(8,14,28));
        getWindow().getDecorView().setSystemUiVisibility(0);
        render();
    }

    private int dp(float n) { return Math.round(n * getResources().getDisplayMetrics().density); }
    private int color(String s) { return Color.parseColor(s); }
    private GradientDrawable rounded(int c, float radius) {
        GradientDrawable d = new GradientDrawable();
        d.setColor(c); d.setCornerRadius(dp(radius)); return d;
    }
    private GradientDrawable outline(int c, float radius, int border) {
        GradientDrawable d = rounded(c, radius);
        d.setStroke(dp(1), border); return d;
    }
    private LinearLayout column() {
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        return box;
    }
    private LinearLayout row() {
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.HORIZONTAL);
        box.setGravity(Gravity.CENTER_VERTICAL);
        return box;
    }
    private TextView text(String value, int sp, int clr, boolean bold) {
        TextView t = new TextView(this);
        t.setText(value); t.setTextColor(clr); t.setTextSize(TypedValue.COMPLEX_UNIT_SP, sp);
        if (bold) t.setTypeface(Typeface.create("sans-serif-medium", Typeface.NORMAL));
        t.setGravity(Gravity.CENTER_VERTICAL);
        return t;
    }
    private LinearLayout.LayoutParams margins(int w, int h, int l, int t, int r, int b) {
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(w,h);
        p.setMargins(dp(l),dp(t),dp(r),dp(b)); return p;
    }
    private TextView chip(String label, Runnable click) {
        TextView t = text(label, 13, foreground, true);
        t.setGravity(Gravity.CENTER);
        t.setPadding(dp(16),dp(9),dp(16),dp(9));
        t.setBackground(outline(cardColor, 14, dark?color("#32415D"):color("#C5D4E7")));
        t.setOnClickListener(v -> click.run());
        t.setFocusable(true); return t;
    }
    private void palette() {
        accent = color("#2DE2CF");
        foreground = dark ? color("#F6FAFF") : color("#172440");
        secondary = dark ? color("#A4B5CF") : color("#536783");
        background = dark ? color("#0B1223") : color("#EDF4FC");
        cardColor = dark ? color("#17233C") : Color.WHITE;
    }
    private boolean landscape() {
        Configuration c = getResources().getConfiguration();
        return c.screenWidthDp >= 700 && c.orientation == Configuration.ORIENTATION_LANDSCAPE;
    }
    private void render() {
        palette();
        LinearLayout root=column();
        root.setPadding(dp(landscape()?26:16),dp(12),dp(landscape()?26:16),dp(12));
        GradientDrawable bg = new GradientDrawable(GradientDrawable.Orientation.TL_BR,
                dark?new int[]{color("#091222"),color("#102345"),color("#172444")}
                    :new int[]{color("#EFF8FF"),color("#DAEEFF"),color("#EFF4FF")});
        root.setBackground(bg);
        setContentView(root);

        LinearLayout top=row();
        TextView brand=text("◆  ELHARIKA  /  OS LITE", 18, foreground, true);
        top.addView(brand,new LinearLayout.LayoutParams(0,dp(52),1));
        TextView theme=chip(dark?"☀  "+getString(R.string.light_theme):"☾  "+getString(R.string.dark_theme),
            () -> { dark=!dark; prefs.edit().putBoolean("dark",dark).apply(); render(); });
        top.addView(theme,margins(-2,-2,4,0,8,0));
        top.addView(chip("⚙  "+getString(R.string.settings),
            () -> safeStart(new Intent(Settings.ACTION_SETTINGS))),margins(-2,-2,0,0,0,0));
        root.addView(top);

        boolean wide=landscape();
        LinearLayout workspace = new LinearLayout(this);
        workspace.setOrientation(wide?LinearLayout.HORIZONTAL:LinearLayout.VERTICAL);
        root.addView(workspace,new LinearLayout.LayoutParams(-1,0,1));

        LinearLayout overview=column();
        overview.setPadding(dp(22),dp(22),dp(22),dp(18));
        overview.setBackground(outline(cardColor, 22, dark?color("#2D3B59"):color("#D0DFEF")));
        LinearLayout.LayoutParams overviewParams=wide?
            new LinearLayout.LayoutParams(0,-1,0.36f):new LinearLayout.LayoutParams(-1,-2);
        overviewParams.setMargins(0,dp(14),dp(wide?12:0),dp(wide?0:12));
        workspace.addView(overview,overviewParams);

        TextView eyebrow=text(getString(R.string.welcome),13,accent,true);
        overview.addView(eyebrow,margins(-1,dp(24),0,0,0,5));
        TextView hero=text(getString(R.string.hero),wide?28:23,foreground,true);
        hero.setMaxLines(2);
        overview.addView(hero,margins(-1,-2,0,0,0,7));
        TextView subtitle=text(getString(R.string.subtitle),13,secondary,false);
        subtitle.setMaxLines(3);
        overview.addView(subtitle,margins(-1,-2,0,0,0,wide?30:12));
        TextClock clock = new TextClock(this);
        clock.setFormat24Hour("HH:mm"); clock.setFormat12Hour("h:mm");
        clock.setTextSize(TypedValue.COMPLEX_UNIT_SP,wide?54:42);
        clock.setTypeface(Typeface.create("sans-serif-light",Typeface.NORMAL));
        clock.setTextColor(foreground);
        overview.addView(clock,margins(-1,-2,0,0,0,0));
        TextClock date = new TextClock(this);
        date.setFormat12Hour("EEEE, d MMMM"); date.setFormat24Hour("EEEE, d MMMM");
        date.setTextSize(TypedValue.COMPLEX_UNIT_SP,14);
        date.setTextColor(secondary);
        overview.addView(date,margins(-1,-2,0,0,0,16));

        LinearLayout totals=row();
        countLabel=text("0",15,foreground,true);
        favoritesLabel=text("0",15,foreground,true);
        totals.addView(summaryTile(getString(R.string.installed),countLabel),new LinearLayout.LayoutParams(0,dp(83),1));
        totals.addView(summaryTile(getString(R.string.favorites),favoritesLabel),margins(dp(wide?128:140),dp(83),10,0,0,0));
        overview.addView(totals,margins(-1,dp(83),0,0,0,12));

        TextView dockTitle=text(getString(R.string.quick_access),15,foreground,true);
        overview.addView(dockTitle,margins(-1,dp(28),0,0,0,6));
        ScrollView dockScroll=new ScrollView(this);
        dockScroll.setFillViewport(false);
        dock=column();
        dockScroll.addView(dock);
        overview.addView(dockScroll,wide?new LinearLayout.LayoutParams(-1,0,1):
            new LinearLayout.LayoutParams(-1,dp(90)));
        if (wide) overview.addView(text(getString(R.string.hint),12,secondary,false),
            margins(-1,-2,0,10,0,0));

        LinearLayout appsPane=column();
        appsPane.setPadding(dp(18),dp(14),dp(18),dp(10));
        appsPane.setBackground(outline(cardColor,22,dark?color("#2D3B59"):color("#D0DFEF")));
        LinearLayout.LayoutParams appsParams=wide?new LinearLayout.LayoutParams(0,-1,0.64f):
            new LinearLayout.LayoutParams(-1,0,1);
        appsParams.setMargins(dp(wide?12:0),dp(wide?14:0),0,0);
        workspace.addView(appsPane,appsParams);

        LinearLayout heading=row();
        heading.addView(text(getString(R.string.all_apps),21,foreground,true),
            new LinearLayout.LayoutParams(0,dp(42),1));
        heading.addView(chip(getString(R.string.manage),
            () -> safeStart(new Intent(Settings.ACTION_APPLICATION_SETTINGS))),
            margins(-2,-2,0,0,0,0));
        appsPane.addView(heading,margins(-1,dp(45),0,0,0,7));

        search=new EditText(this);
        search.setSingleLine(true);
        search.setTextSize(TypedValue.COMPLEX_UNIT_SP,14);
        search.setTextColor(foreground);
        search.setHintTextColor(secondary);
        search.setHint("⌕   "+getString(R.string.search));
        search.setPadding(dp(18),dp(11),dp(18),dp(11));
        search.setBackground(outline(background,16,dark?color("#34476A"):color("#CBDCEA")));
        appsPane.addView(search,margins(-1,dp(50),0,0,0,12));
        search.setText(filter);
        search.addTextChangedListener(new TextWatcher(){
            public void beforeTextChanged(CharSequence s,int st,int count,int after){}
            public void onTextChanged(CharSequence s,int st,int before,int count){filter=s.toString(); applyFilter();}
            public void afterTextChanged(Editable e){}
        });

        LinearLayout tabs=row();
        allTab=chip(getString(R.string.all_apps),()->{favoritesOnly=false;applyFilter();});
        favoritesTab=chip("★  "+getString(R.string.favorites),()->{favoritesOnly=true;applyFilter();});
        tabs.addView(allTab,margins(-2,-2,0,0,10,0));
        tabs.addView(favoritesTab,margins(-2,-2,0,0,0,0));
        appsPane.addView(tabs,margins(-1,-2,0,0,0,5));

        grid=new GridView(this);
        grid.setNumColumns(wide?4:3);
        grid.setHorizontalSpacing(dp(9));
        grid.setVerticalSpacing(dp(12));
        grid.setStretchMode(GridView.STRETCH_COLUMN_WIDTH);
        grid.setClipToPadding(false);
        grid.setPadding(0,dp(10),0,dp(14));
        adapter=new BaseAdapter(){
            public int getCount(){return displayed.size();}
            public Object getItem(int position){return displayed.get(position);}
            public long getItemId(int position){return position;}
            public View getView(int pos,View convert,ViewGroup parent){return appCell(displayed.get(pos));}
        };
        grid.setAdapter(adapter);
        grid.setOnItemClickListener((p,v,position,id)->openApp(displayed.get(position)));
        grid.setOnItemLongClickListener((p,v,position,id)->{showAppMenu(displayed.get(position));return true;});
        appsPane.addView(grid,new LinearLayout.LayoutParams(-1,0,1));
        refreshInstalled();
    }
    private View summaryTile(String title,TextView value) {
        LinearLayout panel=column();
        panel.setGravity(Gravity.CENTER_VERTICAL);
        panel.setPadding(dp(14),dp(8),dp(8),dp(8));
        panel.setBackground(rounded(background,13));
        panel.addView(value);
        panel.addView(text(title,12,secondary,false));
        return panel;
    }
    private View appCell(AppEntry item) {
        LinearLayout card=column();
        card.setGravity(Gravity.CENTER);
        card.setPadding(dp(5),dp(10),dp(5),dp(9));
        card.setBackground(rounded(background,15));
        ImageView img=new ImageView(this);
        img.setImageDrawable(item.icon);
        img.setScaleType(ImageView.ScaleType.FIT_CENTER);
        card.addView(img,margins(dp(53),dp(53),0,0,0,5));
        String label=item.label;
        TextView title=text(label,12,foreground,true);
        title.setGravity(Gravity.CENTER);
        title.setMaxLines(2);
        title.setEllipsize(android.text.TextUtils.TruncateAt.END);
        card.addView(title,new LinearLayout.LayoutParams(-1,dp(35)));
        if(favorites.contains(item.id())){
            TextView star=text("★",11,accent,true);
            star.setGravity(Gravity.CENTER);
            card.addView(star,margins(-1,dp(15),0,0,0,0));
        }
        card.setContentDescription(item.label);
        return card;
    }
    private void refreshInstalled() {
        installed.clear();
        PackageManager pm=getPackageManager();
        Intent intent=new Intent(Intent.ACTION_MAIN);
        intent.addCategory(Intent.CATEGORY_LAUNCHER);
        List<ResolveInfo> candidates=pm.queryIntentActivities(intent,0);
        HashSet<String> seen=new HashSet<>();
        for(ResolveInfo ri:candidates){
            if(ri.activityInfo==null || getPackageName().equals(ri.activityInfo.packageName))continue;
            ComponentName c=new ComponentName(ri.activityInfo.packageName,ri.activityInfo.name);
            if(!seen.add(c.flattenToString()))continue;
            try{
                installed.add(new AppEntry(c,ri.loadLabel(pm).toString(),ri.loadIcon(pm)));
            }catch(RuntimeException ignore){}
        }
        installed.sort(Comparator.comparing(a->a.label.toLowerCase(Locale.getDefault())));
        applyFilter();
    }
    private void applyFilter() {
        displayed.clear();
        String q=filter.trim().toLowerCase(Locale.getDefault());
        for(AppEntry item:installed) {
            if(favoritesOnly && !favorites.contains(item.id()))continue;
            if(!q.isEmpty() && !item.label.toLowerCase(Locale.getDefault()).contains(q))continue;
            displayed.add(item);
        }
        if(adapter!=null)adapter.notifyDataSetChanged();
        if(countLabel!=null) countLabel.setText(String.valueOf(installed.size()));
        if(favoritesLabel!=null) favoritesLabel.setText(String.valueOf(favorites.size()));
        if(allTab!=null) allTab.setAlpha(favoritesOnly?.5f:1f);
        if(favoritesTab!=null) favoritesTab.setAlpha(favoritesOnly?1f:.5f);
        updateDock();
    }
    private void updateDock() {
        if(dock==null)return;
        dock.removeAllViews();
        int count=0;
        for(AppEntry app:installed){
            if(!favorites.contains(app.id()))continue;
            if(count++>=7)break;
            LinearLayout tile=row();
            tile.setPadding(dp(10),dp(6),dp(8),dp(6));
            tile.setBackground(rounded(background,11));
            ImageView img=new ImageView(this);
            img.setImageDrawable(app.icon);
            tile.addView(img,margins(dp(30),dp(30),0,0,9,0));
            TextView label=text(app.label,13,foreground,true);
            label.setSingleLine(true);
            label.setEllipsize(android.text.TextUtils.TruncateAt.END);
            tile.addView(label,new LinearLayout.LayoutParams(0,dp(36),1));
            tile.setOnClickListener(v->openApp(app));
            tile.setOnLongClickListener(v->{showAppMenu(app);return true;});
            dock.addView(tile,margins(-1,dp(46),0,0,0,5));
        }
        if(count==0){
            TextView empty=text(getString(R.string.no_favorites),13,secondary,false);
            dock.addView(empty,margins(-1,-2,0,5,0,0));
        }
    }
    private void showAppMenu(AppEntry app){
        final boolean saved=favorites.contains(app.id());
        final String[] actions={saved?getString(R.string.remove_favorite):getString(R.string.add_favorite),
            getString(R.string.app_info),getString(R.string.cancel)};
        new AlertDialog.Builder(this).setTitle(app.label).setItems(actions,(dialog,which)->{
            if(which==0){
                if(saved)favorites.remove(app.id());else favorites.add(app.id());
                prefs.edit().putStringSet("favorites",new HashSet<>(favorites)).apply();
                applyFilter();
            }else if(which==1){
                Intent i=new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                    Uri.parse("package:"+app.component.getPackageName()));
                safeStart(i);
            }
        }).show();
    }
    private void openApp(AppEntry app){
        Intent i=new Intent(Intent.ACTION_MAIN);
        i.addCategory(Intent.CATEGORY_LAUNCHER);
        i.setComponent(app.component);
        i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK|Intent.FLAG_ACTIVITY_RESET_TASK_IF_NEEDED);
        safeStart(i);
    }
    private void safeStart(Intent i){
        try{startActivity(i);}
        catch(Exception e){Toast.makeText(this,R.string.launch_error,Toast.LENGTH_SHORT).show();}
    }
    @Override protected void onResume(){super.onResume();if(prefs!=null && grid!=null)refreshInstalled();}
    @Override public void onBackPressed(){
        if(!filter.isEmpty()){
            filter="";if(search!=null)search.setText("");
            return;
        }
        if(favoritesOnly){favoritesOnly=false;applyFilter();return;}
        // The Home screen must not close unexpectedly when the user presses Back.
    }
}
