import csv,io,json,re,statistics,openpyxl,math
from collections import defaultdict
# R: folder of downloaded source files (Nomis CSVs, ONS workbooks, Electoral Commission CSV)
# P: clones of my footpaths and sun-and-rain-uk study repos
R='raw/'; P='repos/'
EXCL={'E09000001','E06000053'}  # City of London, Isles of Scilly (tiny)
# ---------- places: 2023 LADs from mid-2025 population ----------
parts={}
for sec in open(R+'nomis_population_ashe.csv').read().split('#####')[1:]:
    k,body=sec.split('\n',1); parts[k.strip()]=list(csv.DictReader(io.StringIO(body)))
places={}; pop={}
for r in parts['POP']:
    c=r['GEOGRAPHY_CODE']
    if c in EXCL: continue
    places[c]=r['GEOGRAPHY_NAME']; pop[c]=float(r['OBS_VALUE'])
POPYEAR=parts['POP'][0]['DATE_NAME']
def nation(c): return {'E':'England','W':'Wales','S':'Scotland','N':'Northern Ireland'}[c[0]]
cats=[]
def add(id,group,label,q,unit,fmt,source,year,vals,link=None,dp=0,note=None,lower=False):
    v={c:round(x,dp) if dp else round(x) for c,x in vals.items() if c in places and x is not None and not (isinstance(x,float) and math.isnan(x))}
    cats.append(dict(id=id,group=group,label=label,q=q,unit=unit,fmt=fmt,source=source,year=str(year),link=link,dp=dp,note=note,v=v))
    print(f'{id:14s} n={len(v):3d} yr={year} min={min(v.items(),key=lambda x:x[1])} max={max(v.items(),key=lambda x:x[1])}')
# ---------- 2022 -> 2023 merges ----------
MERGE={'E06000063':['E07000026','E07000028','E07000029'],'E06000064':['E07000027','E07000030','E07000031'],
 'E06000065':['E07000163','E07000164','E07000165','E07000166','E07000167','E07000168','E07000169'],
 'E06000066':['E07000187','E07000188','E07000189','E07000246']}
OLD2NEW={o:n for n,os in MERGE.items() for o in os}
# ---------- census ----------
cen=defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
dens={}
for sec in open(R+'nomis_census2021_lad2022.tsv').read().split('#####')[1:]:
    head,body=sec.split('\n',1); k=head.split('\t')[0]
    for l in body.strip().split('\n'):
        p=l.split('\t')
        if k=='TS006':
            dens[p[0]]=float(p[1]); continue
        c=OLD2NEW.get(p[0],p[0]); cen[k][c][p[1]]+=float(p[2])
def share(tab,num,den=None):
    out={}
    for c,d in cen[tab].items():
        tot=[v for kk,v in d.items() if kk.startswith('Total')][0] if den is None else sum(d[x] for x in den)
        n=sum(d[x] for x in (num if isinstance(num,list) else [num]))
        out[c]=100*n/tot
    return out
CS='Census 2021, ONS (via Nomis)'; CL='https://www.nomisweb.co.uk/sources/census_2021'
# area & density
area=defaultdict(float)
for old,dn in dens.items():
    p21=[v for kk,v in cen['TS001'][OLD2NEW.get(old,old)].items()] # placeholder
for old,dn in dens.items():
    pass
# compute area per old LAD from TS001 by old code: need old pops -> re-read
oldpop={}
for sec in open(R+'nomis_census2021_lad2022.tsv').read().split('#####')[1:]:
    head,body=sec.split('\n',1)
    if head.startswith('TS001'):
        for l in body.strip().split('\n'):
            p=l.split('\t')
            if p[1].startswith('Total'): oldpop[p[0]]=float(p[2])
for old,dn in dens.items():
    if old in oldpop and dn>0: area[OLD2NEW.get(old,old)]+=oldpop[old]/dn
add('density','People','Population density','more people per square kilometre','people per km²','int','Mid-'+POPYEAR+' population estimates and Census 2021 land area, ONS',POPYEAR,{c:pop[c]/area[c] for c in area if c in pop},'https://www.ons.gov.uk/peoplepopulationandcommunity/populationandmigration/populationestimates')
add('pop','People','Population','more people','people','int','Mid-year population estimates, ONS (via Nomis)',POPYEAR,pop,'https://www.ons.gov.uk/peoplepopulationandcommunity/populationandmigration/populationestimates')
# median age
def med_age(d):
    ages=[]
    for kk,v in d.items():
        m=re.match(r'Aged (\d+) years?$',kk)
        if m: ages.append((int(m.group(1)),v))
        elif kk=='Aged under 1 year': ages.append((0,v))
        elif kk=='Aged 100 years and over': ages.append((100,v))
    ages.sort(); tot=sum(v for _,v in ages); half=tot/2; cum=0
    for a,v in ages:
        if cum+v>=half: return a+(half-cum)/v
        cum+=v
add('medage','People','Median age','an older population (higher median age)','years','1',CS,2021,{c:med_age(d) for c,d in cen['TS007'].items()},CL,dp=1)
add('bornabroad','People','Born outside the UK','more people born outside the UK','%','pct',CS,2021,{c:100-share('TS004','Europe: United Kingdom')[c] for c in cen['TS004']},CL,dp=1)
add('norelig','People','No religion','more people with no religion','%','pct',CS,2021,share('TS030','No religion'),CL,dp=1)
add('degree','People','Degree-level qualifications','more people with a degree or equivalent (Level 4+)','%','pct',CS,2021,share('TS067','Level 4 qualifications or above'),CL,dp=1)
add('vgood','People','Very good health','more people in very good health','%','pct',CS,2021,share('TS037','Very good health'),CL,dp=1)
add('veterans','People','Armed forces veterans','more armed forces veterans (share of adults)','%','pct',CS,2021,share('TS071',['Previously served in UK regular armed forces','Previously served in UK reserve armed forces','Previously served in both regular and reserve UK armed forces']),CL,dp=1)
add('married','People','Married or civil partnership','more adults married or in a civil partnership','%','pct',CS,2021,share('TS002','Married or in a registered civil partnership'),CL,dp=1)
add('outright','Homes','Homes owned outright','more homes owned outright, with no mortgage','%','pct',CS,2021,share('TS054','Owned: Owns outright'),CL,dp=1)
add('nocar','Homes','Households with no car','more households without a car or van','%','pct',CS,2021,share('TS045','No cars or vans in household'),CL,dp=1)
add('wfh','Work','Working from home','more workers mainly working from home (March 2021)','%','pct',CS,2021,share('TS061','Work mainly at or from home'),CL,dp=1)
add('detached','Homes','Detached houses','more homes that are detached houses','%','pct',CS,2021,share('TS044','Detached'),CL,dp=1)
add('bigbeds','Homes','Homes with 4+ bedrooms','more homes with four or more bedrooms','%','pct',CS,2021,share('TS050','4 or more bedrooms'),CL,dp=1)
add('noheat','Homes','No central heating','more homes with no central heating','%','pct',CS,2021,share('TS046','No central heating'),CL,dp=1)
def hhsize(d):
    n=0;h=0
    for kk,v in d.items():
        m=re.match(r'(\d+)( or more)? (?:person|people) in household',kk)
        if m: k=int(m.group(1)); n+=k*v; h+=v if k>0 else 0
    return n/h
add('hhsize','Homes','Average household size','bigger households on average','people','1',CS,2021,{c:hhsize(d) for c,d in cen['TS017'].items()},CL,dp=2)
add('cycle','Work','Cycling to work','more workers who cycle to work','%','pct',CS,2021,share('TS061','Bicycle'),CL,dp=1)
add('selfemp','Work','Self-employed','more self-employed adults','%','pct',CS,2021,share('TS066',['Economically active (excluding full-time students):In employment:Self-employed with employees','Economically active (excluding full-time students):In employment:Self-employed without employees']),CL,dp=1)
add('retired','People','Retired','more retired adults','%','pct',CS,2021,share('TS066','Economically inactive: Retired'),CL,dp=1)
add('longcommute','Work','Long commutes (60 km+)','more workers commuting 60 km or more','%','pct',CS,2021,share('TS058','60km and over'),CL,dp=1)
# ---------- money ----------
add('pay','Money','Median full-time pay','higher median full-time pay','£ a year','gbp','Annual Survey of Hours and Earnings (resident analysis), ONS (via Nomis)',parts['ASHE'][0]['DATE_NAME'],{r['GEOGRAPHY_CODE']:float(r['OBS_VALUE']) for r in parts['ASHE'] if r['OBS_VALUE'] and r['OBS_STATUS_NAME']=='Normal Value'},'https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/earningsandworkinghours/bulletins/annualsurveyofhoursandearnings/latest')
g=json.load(open(R+'gdhi.json'))
add('gdhi','Money','Household income per person','higher disposable household income per person','£ a year','gbp','Regional gross disposable household income, ONS',g['year'],{c:v[1] for c,v in g['d'].items()},'https://www.ons.gov.uk/economy/regionalaccounts/grossdisposablehouseholdincome')
wb=openpyxl.load_workbook(R+'afford.xlsx',read_only=True)
def afft(sn):
    rows=list(wb[sn].iter_rows(values_only=True)); h=rows[1]; last=max(i for i,x in enumerate(h) if x and str(x).startswith('Year ending') or (x and re.match(r'^\d{4}$',str(x))))
    return h[last],{r[2]:r[last] for r in rows[2:] if r[2] and isinstance(r[last],(int,float))}
y,hp=afft('5a'); add('house','Money','Median house price','a higher median house price','£','gbp','House price statistics for small areas, ONS',re.sub(r'\D','',str(y))[-4:],hp,'https://www.ons.gov.uk/peoplepopulationandcommunity/housing/datasets/ratioofhousepricetoresidencebasedearningslowerquartileandmedian',note='Year ending September')
y,ra=afft('5c'); add('afford','Money','House price to earnings ratio','less affordable homes (higher price-to-earnings ratio)','× earnings','1','Housing affordability in England and Wales, ONS',re.sub(r'\D','',str(y))[-4:],ra,'https://www.ons.gov.uk/peoplepopulationandcommunity/housing/datasets/ratioofhousepricetoresidencebasedearningslowerquartileandmedian',dp=1)
# ---------- high street ----------
ub=defaultdict(dict)
for r in csv.DictReader(open(R+'nomis_ukbc_local_units.csv')): ub[r['INDUSTRY_NAME'].split(' : ')[0]][r['GEOGRAPHY_CODE']]=float(r['OBS_VALUE'])
UY=parts['UKBC'][0]['DATE_NAME']; US='UK Business Counts (local units), ONS (via Nomis)'; UL='https://www.nomisweb.co.uk/datasets/idbr'
for sic,id,label,q in [('56302','pubs','Pubs and bars','more pubs and bars per person'),('56103','takeaways','Takeaways','more takeaways per person'),('96020','hair','Hairdressers and beauty salons','more hairdressers and beauty salons per person'),('55100','hotels','Hotels','more hotels per person')]:
    add(id,'High street',label+' per 10,000 people',q,'per 10,000 people','1',US,UY,{c:1e4*v/pop[c] for c,v in ub[sic].items() if c in pop},UL,dp=1)
# ---------- life expectancy & wellbeing ----------
wb=openpyxl.load_workbook(R+'le.xlsx',read_only=True)
le=defaultdict(dict); per=None
rows=wb['1'].iter_rows(min_row=7,values_only=True)
latest='2021 to 2023'
for r in rows:
    if r[0]==latest and r[7]==1 and r[2]=='Local Areas': le[r[5]][r[3]]=r[9]
add('lef','Health','Life expectancy (women)','longer life expectancy for women','years','1','Life expectancy for local areas of Great Britain, ONS','2021–23',le['Female'],'https://www.ons.gov.uk/peoplepopulationandcommunity/healthandsocialcare/healthandlifeexpectancies',dp=1)
add('lem','Health','Life expectancy (men)','longer life expectancy for men','years','1','Life expectancy for local areas of Great Britain, ONS','2021–23',le['Male'],'https://www.ons.gov.uk/peoplepopulationandcommunity/healthandsocialcare/healthandlifeexpectancies',dp=1)
wb=openpyxl.load_workbook(R+'wellb.xlsx',read_only=True)
def wbt(sn):
    rows=list(wb[sn].iter_rows(values_only=True)); h=rows[12]; col=[i for i,x in enumerate(h) if x and 'April 2022 to March 2023' in str(x) and 'accuracy' not in str(x)][0]
    return {r[1]:r[col] for r in rows[13:] if r[1] and isinstance(r[col],(int,float))}
WS='Annual personal well-being estimates, ONS (Annual Population Survey); score out of 10'; WL='https://www.ons.gov.uk/peoplepopulationandcommunity/wellbeing'
add('lifesat','Health','Life satisfaction','more satisfied people (average life satisfaction)','out of 10','2',WS,'2022–23',wbt('1 Life satisfaction means'),WL,dp=2)
add('happy','Health','Happiness','happier people (average happiness score)','out of 10','2',WS,'2022–23',wbt('7 Happiness means'),WL,dp=2)
# ---------- EU referendum ----------
EUMAP={'E06000028':'E06000058','E06000029':'E06000058','E07000048':'E06000058','E07000049':'E06000059','E07000050':'E06000059','E07000051':'E06000059','E07000052':'E06000059','E07000053':'E06000059','E07000201':'E07000245','E07000204':'E07000245','E07000205':'E07000244','E07000206':'E07000244','E07000190':'E06000066','E07000191':'E06000066','E07000004':'E06000060','E07000005':'E06000060','E07000006':'E06000060','E07000007':'E06000060','E07000150':'E06000061','E07000152':'E06000061','E07000153':'E06000061','E07000156':'E06000061','E07000151':'E06000062','E07000154':'E06000062','E07000155':'E06000062','E08000020':'E08000037','E06000048':'E06000057','E07000097':'E07000242','E07000101':'E07000243','E07000100':'E07000240','E07000104':'E07000241','S12000015':'S12000047','S12000024':'S12000048','S12000046':'S12000049','S12000044':'S12000050'}
EUMAP.update(OLD2NEW)
lv=defaultdict(float); vv=defaultdict(float); un=[]
for r in csv.DictReader(open(R+'EU-referendum-result-data.csv')):
    c=EUMAP.get(r['Area_Code'],r['Area_Code'])
    if c not in places: un.append(r['Area']); continue
    lv[c]+=float(r['Leave']); vv[c]+=float(r['Valid_Votes'])
print('EU unmatched',un)
add('leave','Politics','Leave vote in the EU referendum','a higher Leave vote in the 2016 EU referendum','%','pct','EU referendum results, Electoral Commission',2016,{c:100*lv[c]/vv[c] for c in vv},'https://www.electoralcommission.org.uk/research-reports-and-data/our-reports-and-data-past-elections-and-referendums/eu-referendum',dp=1,note='Councils merged since 2016 are combined')
eut={}
for r in csv.DictReader(open(R+'EU-referendum-result-data.csv')):
    c=EUMAP.get(r['Area_Code'],r['Area_Code'])
    if c in places: eut.setdefault(c,[0,0]); eut[c][0]+=float(r['Votes_Cast']); eut[c][1]+=float(r['Electorate'])
add('turnout','Politics','EU referendum turnout','a higher turnout in the 2016 EU referendum','%','pct','EU referendum results, Electoral Commission',2016,{c:100*a/b for c,(a,b) in eut.items()},'https://www.electoralcommission.org.uk/research-reports-and-data/our-reports-and-data-past-elections-and-referendums/eu-referendum',dp=1)
# ---------- land and weather ----------
from shapely.geometry import shape,Point
from shapely import STRtree
from pyproj import Transformer,Geod
geo=json.load(open(P+'footpaths/data/lad.geojson'))
polys=[];codes=[]
for f in geo['features']:
    polys.append(shape(f['geometry'])); codes.append(f['properties']['code'])
geod=Geod(ellps='WGS84')
add('area','Land','Area','a bigger area','km²','int','ONS council boundaries (December 2023)',2023,{c:abs(geod.geometry_area_perimeter(p)[0])/1e6 for c,p in zip(codes,polys)},'https://geoportal.statistics.gov.uk/')
tr=Transformer.from_crs(27700,4326,always_xy=True); tree=STRtree(polys)
acc=defaultdict(lambda: defaultdict(float)); cells=[]
for r in csv.DictReader(open(P+'sun-and-rain-uk/data/cells_5km.csv')):
    lon,lat=tr.transform(float(r['e_km'])*1000,float(r['n_km'])*1000); w=float(r['land_km2'])
    vals={'sun':float(r['sun_1991_2020']),'rain':float(r['rain_1991_2020']),'jul':float(r['tmax_Jul']),'jan':float(r['tmax_Jan'])}
    cells.append((lon,lat,vals))
    if w<=0: continue
    pt=Point(lon,lat)
    for i in tree.query(pt):
        if polys[i].contains(pt):
            a=acc[codes[i]]; a['w']+=w
            for k,v in vals.items(): a[k]+=w*v
            break
for c,p in zip(codes,polys):
    if c[0] in 'EWS' and acc[c]['w']<25:  # small councils: use cells near the centre
        rp=p.representative_point()
        near=sorted(cells,key=lambda x:(x[0]-rp.x)**2+((x[1]-rp.y)*1.6)**2)[:2]
        acc[c]={'w':1,**{k:sum(n[2][k] for n in near)/2 for k in near[0][2]}}
MS='HadUK-Grid climate averages 1991–2020, Met Office (5 km grid, averaged over each council)'; ML='https://www.metoffice.gov.uk/research/climate/maps-and-data/data/haduk-grid/haduk-grid'
add('sun','Weather','Sunshine','more hours of sunshine a year','hours a year','int',MS,'1991–2020',{c:a['sun']/a['w'] for c,a in acc.items() if a['w']},ML)
add('rain','Weather','Rainfall','more rain a year','mm a year','int',MS,'1991–2020',{c:a['rain']/a['w'] for c,a in acc.items() if a['w']},ML)
add('july','Weather','July afternoons','warmer July afternoons (average daily high)','°C','1',MS,'1991–2020',{c:a['jul']/a['w'] for c,a in acc.items() if a['w']},ML,dp=1)
add('jan','Weather','January afternoons','milder January afternoons (average daily high)','°C','1',MS,'1991–2020',{c:a['jan']/a['w'] for c,a in acc.items() if a['w']},ML,dp=1)
fp=json.load(open(P+'footpaths/data/lad.json')); cols=fp['cols']
add('paths','Land','Public rights of way','more miles of public footpath and bridleway per square mile','miles per sq mile','2','Council rights of way data via rowmaps.com; The Footpath Capital study',2026,{r[0]:r[cols.index('prow_mi')]/r[cols.index('area_sqmi')] for r in fp['rows'] if r[cols.index('area_sqmi')] and r[0][0] in 'EW' and r[cols.index('prow_mi')]/r[cols.index('area_sqmi')]>=0.05},'https://maps.tristanhotham.com/footpaths/',dp=2,note='Inner London boroughs have no definitive map and are left out')
# ---------- output ----------
out={'places':{c:[n,c[0]] for c,n in places.items()},'cats':cats}
json.dump(out,open('data.json','w'),ensure_ascii=False,separators=(',',':'))
print('cats',len(cats),'places',len(places))
