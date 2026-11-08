package org.elharika.oneui;

import android.content.Context;
import android.content.SharedPreferences;
import org.json.JSONArray;
import org.json.JSONObject;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/** Persistent home pages, folders and dock. The system launcher is never modified. */
final class HomeStore {
    static final int PAGES = 3;
    static final int MAX_PAGE = 24;
    static final int MAX_DOCK = 8;
    private final SharedPreferences pref;
    final List<List<Item>> pages = new ArrayList<>();
    final List<Item> dock = new ArrayList<>();

    static final class Item {
        String kind = "app";
        String component = "";
        String label = "";
        final List<String> members = new ArrayList<>();
        Item() {}
        static Item app(String component){Item i=new Item();i.component=component;return i;}
        static Item folder(String title,String a,String b){
            Item i=new Item();i.kind="folder";i.label=title;
            i.members.add(a);i.members.add(b);return i;
        }
        boolean folder(){return "folder".equals(kind);}
        JSONObject json(){
            JSONObject j=new JSONObject();
            try{
                j.put("kind",kind);j.put("component",component);j.put("label",label);
                JSONArray a=new JSONArray();for(String v:members)a.put(v);j.put("members",a);
            }catch(Exception ignored){}
            return j;
        }
        static Item parse(JSONObject j){
            Item i=new Item();
            i.kind=j.optString("kind","app");
            i.component=j.optString("component","");
            i.label=j.optString("label","");
            JSONArray arr=j.optJSONArray("members");
            if(arr!=null)for(int k=0;k<arr.length();k++){
                String id=arr.optString(k,"");if(!id.isEmpty())i.members.add(id);
            }
            return i;
        }
    }
    HomeStore(Context c){
        pref=c.getSharedPreferences("elharika_oneui_home",Context.MODE_PRIVATE);
        for(int p=0;p<PAGES;p++)pages.add(new ArrayList<>());
        load();
    }
    int theme(){return pref.getInt("theme",0);}
    void theme(int v){pref.edit().putInt("theme",v).apply();}
    int iconSize(){return pref.getInt("icon_size",62);}
    void iconSize(int v){pref.edit().putInt("icon_size",Math.max(42,Math.min(82,v))).apply();}
    int widgetId(){return pref.getInt("widget_id",-1);}
    void widgetId(int id){pref.edit().putInt("widget_id",id).apply();}
    void clearWidget(){pref.edit().remove("widget_id").apply();}
    void load(){
        try{
            JSONArray a=new JSONArray(pref.getString("home","[]"));
            for(int p=0;p<Math.min(PAGES,a.length());p++){
                JSONArray page=a.optJSONArray(p);
                if(page==null)continue;
                for(int k=0;k<Math.min(MAX_PAGE,page.length());k++){
                    JSONObject o=page.optJSONObject(k);
                    if(o!=null)pages.get(p).add(Item.parse(o));
                }
            }
            JSONArray ds=new JSONArray(pref.getString("dock","[]"));
            for(int k=0;k<Math.min(MAX_DOCK,ds.length());k++){
                JSONObject o=ds.optJSONObject(k);
                if(o!=null)dock.add(Item.parse(o));
            }
        }catch(Exception ignored){}
    }
    void save(){
        JSONArray all=new JSONArray();
        for(List<Item> list:pages){
            JSONArray page=new JSONArray();for(Item i:list)page.put(i.json());all.put(page);
        }
        JSONArray d=new JSONArray();for(Item i:dock)d.put(i.json());
        pref.edit().putString("home",all.toString()).putString("dock",d.toString()).apply();
    }
    boolean empty(){
        for(List<Item> p:pages)if(!p.isEmpty())return false;
        return true;
    }
    boolean containsHome(String id) {
        for(List<Item> page:pages)for(Item item:page){
            if(!item.folder() && item.component.equals(id))return true;
            if(item.folder() && item.members.contains(id))return true;
        }
        return false;
    }
    boolean containsDock(String id) {
        for(Item item:dock)if(item.component.equals(id))return true;
        return false;
    }
    boolean addHome(String id,int page){
        if(containsHome(id))return false;
        List<Item> target=pages.get(Math.max(0,Math.min(PAGES-1,page)));
        if(target.size()>=MAX_PAGE)return false;
        target.add(Item.app(id));save();return true;
    }
    boolean addDock(String id){
        if(containsDock(id)||dock.size()>=MAX_DOCK)return false;
        dock.add(Item.app(id));save();return true;
    }
    void remove(String id, boolean fromDock){
        if(fromDock) dock.removeIf(i->i.component.equals(id));
        else for(List<Item> list:pages){
            for(int p=list.size()-1;p>=0;p--){
                Item item=list.get(p);
                if(item.folder()){
                    item.members.remove(id);
                    if(item.members.isEmpty())list.remove(p);
                    else if(item.members.size()==1)list.set(p,Item.app(item.members.get(0)));
                }else if(item.component.equals(id))list.remove(p);
            }
        }
        save();
    }
    void removeAt(int page,int index){
        if(page>=0&&page<PAGES&&index>=0&&index<pages.get(page).size()){
            pages.get(page).remove(index);save();
        }
    }
    boolean relocate(int srcPage,int from,int destPage,int to){
        if(srcPage<0||srcPage>=PAGES||destPage<0||destPage>=PAGES)return false;
        List<Item> source=pages.get(srcPage),target=pages.get(destPage);
        if(from<0||from>=source.size())return false;
        if(destPage!=srcPage&&target.size()>=MAX_PAGE)return false;
        if(to>=0&&to<target.size()&&(srcPage!=destPage||from!=to)){
            Item moving=source.get(from),receiver=target.get(to);
            if(!moving.folder()&&!receiver.folder()&&!moving.component.equals(receiver.component)){
                target.set(to,Item.folder("Folder",receiver.component,moving.component));
                source.remove(from);save();return true;
            }
            if(!moving.folder()&&receiver.folder()&&!receiver.members.contains(moving.component)){
                receiver.members.add(moving.component);
                source.remove(from);save();return true;
            }
        }
        Item v=source.remove(from);
        if(srcPage==destPage&&from<to)to--;
        target.add(Math.max(0,Math.min(to,target.size())),v);
        save();return true;
    }
    boolean movePage(int page,int at){
        if(page<0||page>=PAGES||at<0||at>=pages.get(page).size())return false;
        int next=(page+1)%PAGES;
        if(pages.get(next).size()>=MAX_PAGE)return false;
        pages.get(next).add(pages.get(page).remove(at));save();return true;
    }
    void renameFolder(int page,int at,String name){
        if(page<0||page>=PAGES||at<0||at>=pages.get(page).size())return;
        Item i=pages.get(page).get(at);
        if(i.folder()&&!name.trim().isEmpty()){i.label=name.trim();save();}
    }
    void initialize(List<String> initial){
        if(pref.getBoolean("initialized",false))return;
        if(empty()){
            for(int k=0;k<Math.min(18,initial.size());k++){
                pages.get(k/9).add(Item.app(initial.get(k)));
            }
            for(int k=0;k<Math.min(6,initial.size());k++)dock.add(Item.app(initial.get(k)));
        }
        pref.edit().putBoolean("initialized",true).apply();
        save();
    }
}
