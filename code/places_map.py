import json,math,openpyxl,glob,re
from shapely.geometry import shape,MultiPolygon,Polygon
from shapely.ops import transform
R='raw/'
d=json.load(open('data.json'))
# region from GDHI workbooks
reg={}
for f in glob.glob(R+'gdhi/*.xlsx'):
    ws=openpyxl.load_workbook(f,read_only=True)['Table 3']
    for r in list(ws.iter_rows(values_only=True))[2:]:
        if r[1]: reg[r[1]]=r[0]
county={}
t=open(R+'nomis_census2021_extra_and_county_lookup.tsv').read().split('#####LOOKUP\n')[1]
for l in t.strip().split('\n')[1:]:
    p=l.split('\t'); county[p[2]]=p[1]
MET={}
for i in range(1,11): MET['E080000%02d'%i]='Greater Manchester'
for i in range(11,16): MET['E080000%02d'%i]='Merseyside'
for i in range(16,20): MET['E080000%02d'%i]='South Yorkshire'
for c in ['E08000021','E08000022','E08000023','E08000024','E08000037']: MET[c]='Tyne and Wear'
for i in range(25,32): MET['E080000%02d'%i]='West Midlands'
for i in range(32,37): MET['E080000%02d'%i]='West Yorkshire'
U={'Hartlepool':'County Durham','Stockton-on-Tees':'County Durham','Darlington':'County Durham','Middlesbrough':'North Yorkshire','Redcar and Cleveland':'North Yorkshire',
'Halton':'Cheshire','Warrington':'Cheshire','Blackburn with Darwen':'Lancashire','Blackpool':'Lancashire','Kingston upon Hull, City of':'East Riding of Yorkshire',
'North East Lincolnshire':'Lincolnshire','North Lincolnshire':'Lincolnshire','York':'North Yorkshire','Derby':'Derbyshire','Leicester':'Leicestershire','Nottingham':'Nottinghamshire',
'Telford and Wrekin':'Shropshire','Stoke-on-Trent':'Staffordshire','Bath and North East Somerset':'Somerset','North Somerset':'Somerset','South Gloucestershire':'Gloucestershire',
'Plymouth':'Devon','Torbay':'Devon','Swindon':'Wiltshire','Peterborough':'Cambridgeshire','Luton':'Bedfordshire','Southend-on-Sea':'Essex','Thurrock':'Essex','Medway':'Kent',
'Bracknell Forest':'Berkshire','West Berkshire':'Berkshire','Reading':'Berkshire','Slough':'Berkshire','Windsor and Maidenhead':'Berkshire','Wokingham':'Berkshire',
'Milton Keynes':'Buckinghamshire','Brighton and Hove':'East Sussex','Portsmouth':'Hampshire','Southampton':'Hampshire','Cheshire East':'Cheshire','Cheshire West and Chester':'Cheshire',
'Bedford':'Bedfordshire','Central Bedfordshire':'Bedfordshire','Bournemouth, Christchurch and Poole':'Dorset','North Northamptonshire':'Northamptonshire','West Northamptonshire':'Northamptonshire',
'Cumberland':'Cumbria','Westmorland and Furness':'Cumbria'}
NICE={'Kingston upon Hull, City of':'Hull','Herefordshire, County of':'Herefordshire','Bristol, City of':'Bristol','Rhondda Cynon Taf':'Rhondda Cynon Taf'}
REGN={'North East':'North East England','North West':'North West England','Yorkshire and The Humber':'Yorkshire and the Humber','East Midlands':'East Midlands','West Midlands':'West Midlands',
'East':'East of England','East of England':'East of England','London':'London','South East':'South East England','South West':'South West England'}
meta={}
for code,(name,nat) in d['places'].items():
    if nat=='E':
        if code.startswith('E09'): lab='London'
        else:
            cty=county.get(code) or MET.get(code) or U.get(name)
            r=REGN.get(reg.get(code,''),reg.get(code,''))
            lab=(cty+' · ' if cty and cty!=r else '')+r
    else: lab={'W':'Wales','S':'Scotland','N':'Northern Ireland'}[nat]
    meta[code]=[NICE.get(name,name),nat,lab]
miss=[c for c,m in meta.items() if m[1]=='E' and not m[2]]
print('missing',miss); print([meta[c] for c in ['E07000125','E08000003','E06000008','E09000022','E06000052','E06000010','W06000023','S12000017']])
# map
geo=json.load(open('repos/footpaths/data/lad.geojson'))
K=math.cos(math.radians(54.5))
def proj(x,y,z=None): return (x*K, -y)
paths={};allb=[]
for f in geo['features']:
    c=f['properties']['code']
    if c not in meta: continue
    g=transform(proj,shape(f['geometry']))
    polys=list(g.geoms) if isinstance(g,MultiPolygon) else [g]
    big=max(p.area for p in polys)
    keep=[p for p in polys if p.area>max(big*0.02,2e-5)]
    s=MultiPolygon(keep).simplify(0.006,preserve_topology=True)
    allb.append(s.bounds); paths[c]=s
minx=min(b[0] for b in allb);miny=min(b[1] for b in allb);maxx=max(b[2] for b in allb);maxy=max(b[3] for b in allb)
W=600;S=W/(maxx-minx);H=round((maxy-miny)*S)
def ps(geom):
    out=[]
    for p in (geom.geoms if isinstance(geom,MultiPolygon) else [geom]):
        pts=[(round((x-minx)*S),round((y-miny)*S)) for x,y in p.exterior.coords]
        out.append('M'+'L'.join(f'{x:g} {y:g}' for x,y in pts[:-1])+'Z')
    return ''.join(out)
mp={'w':W,'h':H,'p':{},'c':{},'b':{}}
for c,g in paths.items():
    mp['p'][c]=ps(g); rp=g.representative_point(); mp['c'][c]=[round((rp.x-minx)*S),round((rp.y-miny)*S)]; b=g.bounds; mp['b'][c]=[round((b[0]-minx)*S),round((b[1]-miny)*S),round((b[2]-minx)*S),round((b[3]-miny)*S)]
json.dump(mp,open('map.json','w'),separators=(',',':'))
json.dump(meta,open('meta.json','w'),ensure_ascii=False)
d['places']=meta
json.dump(d,open('data.json','w'),ensure_ascii=False,separators=(',',':'))
print('map',W,H,len(mp['p']),'missing map',[c for c in meta if c not in mp['p']])
