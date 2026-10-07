from __future__ import annotations
import sqlite3
from pathlib import Path
import pandas as pd
import streamlit as st
from dotenv import dotenv_values
from car_deal_finder.scan import run_scan, load_config
from car_deal_finder.db import init_db
from car_deal_finder.chainsaws import init_chainsaw_db, scan_chainsaws

ROOT=Path(__file__).parent; DB=ROOT/'cars.db'; ENV=ROOT/'.env'
st.set_page_config(page_title='Deal & Hidden Gem Finder',page_icon='🔎',layout='wide')
init_db(); init_chainsaw_db()

SOURCE_LABELS={
    'bazos_sk':'Bazoš SK','bazos_cz':'Bazoš CZ','autobazar_eu':'Autobazar.EU','otomoto_pl':'OTOMOTO PL',
    'hasznaltauto_hu':'Használtautó HU','willhaben_at':'willhaben AT','autoscout24_at':'AutoScout24 AT','mobile_de':'mobile.de',
    'chainsaw_bazos_sk':'Bazoš SK','chainsaw_bazos_cz':'Bazoš CZ'
}

def money(v):
    try:return f'{float(v):,.0f} €'.replace(',',' ')
    except:return '—'

def _numcol(df,c):
    if c in df.columns:df[c]=pd.to_numeric(df[c],errors='coerce')

def _q(series,q,default,cap=None):
    s=pd.to_numeric(series,errors='coerce').dropna()
    v=float(s.quantile(q)) if len(s) else float(default)
    if cap is not None:v=min(v,cap)
    return max(v,1)

@st.cache_data(ttl=15)
def load_all():
    con=sqlite3.connect(DB)
    cars=pd.read_sql_query('SELECT * FROM listings WHERE COALESCE(is_vehicle,1)=1',con)
    saws=pd.read_sql_query('SELECT * FROM chainsaws',con)
    runs=pd.read_sql_query('''SELECT r.* FROM source_runs r JOIN (SELECT source,MAX(id) id FROM source_runs GROUP BY source) x ON r.id=x.id ORDER BY r.source''',con)
    con.close();return cars,saws,runs

def save_env(updates):
    vals=dict(dotenv_values(ENV)) if ENV.exists() else {}; vals.update(updates)
    ENV.write_text('\n'.join(f'{k}={v or ""}' for k,v in vals.items())+'\n',encoding='utf-8')

def car_table(data,height=620):
    cols=['interesting_score','deal_score','rare_score','special_score','scarcity_score','hidden_gem_score','repair_score','discount_pct','peer_count','price_eur','market_price_eur','title','make','model','year','mileage_km','views','engine_signature','body_style','source','location','posted_at','interesting_reason','rare_reason','repair_reason','ai_note','url']
    labels={'interesting_score':'⭐','deal_score':'🔥 Deal','rare_score':'💎 Rare','special_score':'✨ Special','scarcity_score':'Scarcity','hidden_gem_score':'Hidden','repair_score':'🛠 Repair','discount_pct':'Pod trhom %','peer_count':'Porovnaní','price_eur':'Cena €','market_price_eur':'Trh €','title':'Názov','make':'Značka','model':'Model','year':'Rok','mileage_km':'km','views':'Videnia','engine_signature':'Motor','body_style':'Karoséria','source':'Zdroj','location':'Lokalita','posted_at':'Pridané','interesting_reason':'Prečo','rare_reason':'Rare dôkaz','repair_reason':'Oprava','ai_note':'AI','url':'Inzerát'}
    d=data[[c for c in cols if c in data.columns]].copy().rename(columns=labels)
    if 'Zdroj' in d:d['Zdroj']=d['Zdroj'].map(lambda x:SOURCE_LABELS.get(x,x))
    st.dataframe(d,use_container_width=True,hide_index=True,height=height,column_config={
        'Inzerát':st.column_config.LinkColumn('Inzerát',display_text='Otvoriť'),'Cena €':st.column_config.NumberColumn(format='%.0f €'),'Trh €':st.column_config.NumberColumn(format='%.0f €'),
        'Pod trhom %':st.column_config.NumberColumn(format='%.1f %%'),'⭐':st.column_config.ProgressColumn(min_value=0,max_value=100,format='%.0f'),
        '🔥 Deal':st.column_config.NumberColumn(format='%.0f'),'💎 Rare':st.column_config.NumberColumn(format='%.0f'),'✨ Special':st.column_config.NumberColumn(format='%.0f'),
        'km':st.column_config.NumberColumn(format='%d'),'Videnia':st.column_config.NumberColumn(format='%d')})

def top_cards(data,n=6):
    if data.empty:
        st.info('Momentálne nič neprešlo prísnym výberom. To je zámer – radšej nič ako bežné autá vydávajúce sa za hidden gem.')
        return
    data=data.sort_values('interesting_score',ascending=False).head(n)
    for start in range(0,len(data),3):
        cols=st.columns(3)
        for col,(_,r) in zip(cols,data.iloc[start:start+3].iterrows()):
            with col:
                with st.container(border=True):
                    st.markdown(f"### {float(r.get('interesting_score') or 0):.0f}/100 · {str(r.get('title') or 'Bez názvu')[:78]}")
                    a,b,c=st.columns(3); a.metric('Cena',money(r.get('price_eur')))
                    b.metric('km','—' if pd.isna(r.get('mileage_km')) else f"{int(r.get('mileage_km')):,}".replace(',',' '))
                    c.metric('Videnia','—' if pd.isna(r.get('views')) else str(int(r.get('views'))))
                    reason=r.get('interesting_reason') or r.get('rare_reason') or r.get('repair_reason') or 'Silný kandidát.'
                    st.caption(str(reason)[:480])
                    st.caption(f"Deal {float(r.get('deal_score') or 0):.0f} · Rare {float(r.get('rare_score') or 0):.0f} · Special {float(r.get('special_score') or 0):.0f} · peers {int(r.get('peer_count') or 0)}")
                    if r.get('url'):st.link_button('Otvoriť inzerát',r.get('url'),use_container_width=True)

def saw_table(data):
    cols=['opportunity_score','repair_score','price_eur','brand','title','views','repair_estimate_min_eur','repair_estimate_max_eur','repair_risk','repair_reason','source','location','posted_at','url']
    labels={'opportunity_score':'⭐ Oprava','repair_score':'Repair','price_eur':'Cena €','brand':'Značka','title':'Názov','views':'Videnia','repair_estimate_min_eur':'Oprava min €','repair_estimate_max_eur':'Oprava max €','repair_risk':'Riziko','repair_reason':'Prečo','source':'Zdroj','location':'Lokalita','posted_at':'Pridané','url':'Inzerát'}
    d=data[[c for c in cols if c in data.columns]].copy().rename(columns=labels)
    if 'Zdroj' in d:d['Zdroj']=d['Zdroj'].map(lambda x:SOURCE_LABELS.get(x,x))
    st.dataframe(d,use_container_width=True,hide_index=True,height=620,column_config={'Inzerát':st.column_config.LinkColumn('Inzerát',display_text='Otvoriť'),'Cena €':st.column_config.NumberColumn(format='%.0f €'),'Oprava min €':st.column_config.NumberColumn(format='%.0f €'),'Oprava max €':st.column_config.NumberColumn(format='%.0f €'),'⭐ Oprava':st.column_config.ProgressColumn(min_value=0,max_value=100,format='%.0f')})

st.title('🔎 Deal & Hidden Gem Finder v0.5')
st.caption('Prísny režim: diely/kolesá sa pred scoringom zahadzujú, deal potrebuje aspoň 8 porovnateľných áut a Rare sekcia vyžaduje konkrétny dôkaz – samotné RS/GTI alebo nezvyčajná kombinácia slov nestačí.')

cars,saws,runs=load_all()
main_cars,main_saws,settings=st.tabs(['🚗 Autá','🪚 Pokazené motorové píly','⚙️ Nastavenia'])

with main_cars:
    b1,b2,b3=st.columns([1,1,4])
    with b1:quick=st.button('⚡ Rýchly scan áut',use_container_width=True)
    with b2:deep=st.button('🧭 Hlboký scan áut',use_container_width=True)
    if quick or deep:
        with st.spinner('Skenujem autá...'):
            res=run_scan('deep' if deep else 'quick'); st.session_state['car_scan']=res; load_all.clear(); st.rerun()
    if cars.empty:
        st.info('Zatiaľ bez áut. Spusti Hlboký scan.')
    else:
        for c in ['interesting_score','deal_score','rare_score','special_score','scarcity_score','hidden_gem_score','repair_score','discount_pct','peer_count','price_eur','market_price_eur','mileage_km','views','year']:_numcol(cars,c)
        m1,m2,m3,m4=st.columns(4)
        m1.metric('Celé autá',len(cars)); m2.metric('🔥 Skutočné dealy',int(((cars.deal_score.fillna(0)>=65)&(cars.peer_count.fillna(0)>=8)).sum()))
        m3.metric('💎 Wow/Rare',int((cars.rare_score.fillna(0)>=70).sum())); m4.metric('⭐ Top nálezy',int((cars.interesting_score.fillna(0)>=60).sum()))
        st.subheader('🏆 Len silné nálezy')
        strong=cars[(cars.interesting_score.fillna(0)>=60) & cars.price_eur.notna()].copy(); top_cards(strong,6)

        with st.expander('🔎 Filtre',expanded=True):
            a,b,c,d=st.columns(4)
            with a:
                srcs=sorted(cars.source.dropna().unique()); src_sel=st.multiselect('Zdroj',srcs,default=list(srcs),format_func=lambda x:SOURCE_LABELS.get(x,x))
                makes=sorted(cars.make.dropna().astype(str).unique()); make_sel=st.multiselect('Značka',makes,default=[])
            with b:
                p_default=int(max(5000,_q(cars.price_eur,.99,50000,150000)))
                pmin=st.number_input('Cena od €',min_value=0,max_value=5000000,value=0,step=500)
                pmax=st.number_input('Cena do €',min_value=0,max_value=5000000,value=p_default,step=1000,help='Predvolený strop je 99. percentil (max. 150 000 €), takže jeden extrémny inzerát neroztiahne filter.')
            with c:
                km_default=int(max(50000,_q(cars.mileage_km,.99,300000,600000)))
                kmmin=st.number_input('km od',min_value=0,max_value=3000000,value=0,step=5000)
                kmmax=st.number_input('km do',min_value=0,max_value=3000000,value=km_default,step=10000)
                include_unknown_km=st.checkbox('Zahrnúť bez km',True)
            with d:
                v_default=int(max(100,_q(cars.views,.99,1500,10000)))
                vmin=st.number_input('Videnia od',min_value=0,max_value=10000000,value=0,step=10)
                vmax=st.number_input('Videnia do',min_value=0,max_value=10000000,value=v_default,step=100)
                include_unknown_views=st.checkbox('Zahrnúť bez videní',True)
                query=st.text_input('Text',placeholder='napr. V12, cabrio, diplomat...')
        f=cars[cars.source.isin(src_sel)].copy()
        if make_sel:f=f[f.make.isin(make_sel)]
        f=f[f.price_eur.isna() | f.price_eur.between(pmin,pmax)]
        km_mask=f.mileage_km.between(kmmin,kmmax); v_mask=f.views.between(vmin,vmax)
        if include_unknown_km:km_mask|=f.mileage_km.isna()
        if include_unknown_views:v_mask|=f.views.isna()
        f=f[km_mask & v_mask]
        if query.strip():
            blob=f.title.fillna('')+' '+f.description.fillna('')+' '+f.rare_reason.fillna('')+' '+f.ai_note.fillna('')
            f=f[blob.str.contains(query.strip(),case=False,regex=False)]

        t1,t2,t3,t4,t5=st.tabs(['⭐ TOP','🔥 FAKT DEAL','💎 WOW / RARE','🛠 Opraviteľné','📋 Všetky celé autá'])
        with t1:car_table(f[f.interesting_score.fillna(0)>=60].sort_values('interesting_score',ascending=False))
        with t2:
            st.caption('Zobrazí sa iba auto s minimálne 8 porovnateľnými kusmi a silným cenovým rozdielom. Kolesá/diely sem už nejdú.')
            x=f[(f.deal_score.fillna(0)>=65)&(f.peer_count.fillna(0)>=8)&(f.discount_pct.fillna(0)>=12)].sort_values('deal_score',ascending=False); car_table(x)
        with t3:
            st.caption('Prísna sekcia. Bežné RS/GTI/AMG označenie samo o sebe nestačí. Musí existovať konkrétny special/rarity dôkaz alebo veľmi vzácna konfigurácia podporená ďalším signálom.')
            x=f[f.rare_score.fillna(0)>=70].sort_values(['rare_score','special_score','scarcity_score'],ascending=False); car_table(x)
        with t4:
            x=f[(f.repair_score.fillna(0)>=55)&(f.deal_score.fillna(0)>=35)].sort_values(['repair_margin_eur','repair_score'],ascending=False,na_position='last'); car_table(x)
        with t5:car_table(f.sort_values('first_seen',ascending=False))

with main_saws:
    st.subheader('🪚 Pokazené motorové píly na opravu')
    st.caption('Má vlastný scan a vlastné skóre. Hľadá celé píly, nie reťaze/lišta/karburátory ako samostatné diely. Uprednostňuje opraviteľné závady: palivo, karburátor, iskra, štartér, mazanie, spojka.')
    s1,s2,s3=st.columns([1,1,4])
    with s1:sq=st.button('⚡ Rýchly scan píl',use_container_width=True)
    with s2:sd=st.button('🧭 Hlboký scan píl',use_container_width=True)
    if sq or sd:
        with st.spinner('Skenujem pokazené motorové píly...'):
            stats=scan_chainsaws(load_config(),'deep' if sd else 'quick'); st.session_state['saw_scan']=stats; load_all.clear(); st.rerun()
    if saws.empty:st.info('Zatiaľ bez výsledkov. Spusti scan píl.')
    else:
        for c in ['opportunity_score','repair_score','price_eur','views','repair_estimate_min_eur','repair_estimate_max_eur']:_numcol(saws,c)
        a,b,c=st.columns(3)
        with a:
            brands=sorted(saws.brand.dropna().astype(str).unique()); bsel=st.multiselect('Značka píly',brands,default=[])
        with b:
            spmax=int(max(100,_q(saws.price_eur,.99,500,2000))); spmin=st.number_input('Píla cena od €',0,10000,0,10); spmaxv=st.number_input('Píla cena do €',0,10000,spmax,20)
        with c:
            minscore=st.slider('Min. skóre opraviteľnosti',0,100,55); srch=st.text_input('Hľadať v pílach',placeholder='MS 261, Husqvarna, bez iskry...')
        sf=saws.copy()
        if bsel:sf=sf[sf.brand.isin(bsel)]
        sf=sf[sf.price_eur.isna() | sf.price_eur.between(spmin,spmaxv)]
        sf=sf[sf.opportunity_score.fillna(0)>=minscore]
        if srch.strip():sf=sf[(sf.title.fillna('')+' '+sf.description.fillna('')).str.contains(srch.strip(),case=False,regex=False)]
        saw_table(sf.sort_values('opportunity_score',ascending=False))

with settings:
    st.markdown('### Zdroje / AI')
    cfg=load_config(); enabled=[SOURCE_LABELS.get(k,k) for k,v in cfg.get('sources',{}).items() if v.get('enabled')]
    st.write('Zapnuté auto zdroje: '+', '.join(enabled))
    st.info('Mobile.de je vypnuté, kým nemáš samostatné API credentials. Bežný web login nie je Search API login.')
    env=dict(dotenv_values(ENV)) if ENV.exists() else {}
    with st.form('env'):
        oa=st.text_input('OPENAI_API_KEY (voliteľné)',value=env.get('OPENAI_API_KEY',''),type='password')
        om=st.text_input('OPENAI_MODEL',value=env.get('OPENAI_MODEL',''),placeholder='model dostupný v tvojom API účte')
        aim=st.selectbox('AI_ANALYSIS_MODE',['top','all'],index=1 if env.get('AI_ANALYSIS_MODE')=='all' else 0,help='all = AI skontroluje každý nový inzerát samostatne; môže to stáť viac API kreditu.')
        if st.form_submit_button('Uložiť'):
            save_env({'OPENAI_API_KEY':oa,'OPENAI_MODEL':om,'AI_ANALYSIS_MODE':aim});st.success('Uložené.')
    st.caption('Bez API funguje lokálna analýza každého inzerátu. S režimom all je AI druhá kontrolná vrstva na každom novom aute.')
