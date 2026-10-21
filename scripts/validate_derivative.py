#!/usr/bin/env python3
"""Offline checks of exact published text, identity, links and release bytes."""
from pathlib import Path
import argparse,json,re,hashlib,sys,unicodedata,subprocess,tempfile,shutil,xml.etree.ElementTree as ET
sys.dont_write_bytecode=True
from bs4 import BeautifulSoup
from markdown_it import MarkdownIt
import yaml,pymupdf,bibtexparser

def norm(s):return re.sub(r'\s+',' ',unicodedata.normalize('NFC',s).replace('\u2060','')).strip()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def require(c,m):
 if not c:raise AssertionError(m)
def validate(root,rebuild=True):
 root=Path(root);a=json.loads((root/'source/paper.json').read_text());inv=json.loads((root/'source/invariants.json').read_text());bs=a['blocks'];d=json.loads((root/'bibliography.json').read_text())
 require(a['doi']=='10.5281/zenodo.23524396','edition DOI');require(a['publication_date']=='2026-10-21','publication date')
 require(sha(root/a['pdf_filename'])==inv['pdf_sha256']=='43a1b73ebb707c94e1f6a09dc3e356707d288beb27d8e5c8582ef60445fdfdca','immutable PDF')
 require(len(pymupdf.open(root/a['pdf_filename']))==inv['pdf_pages']==160,'PDF pages')
 require((root/a['pdf_filename']).stat().st_size==inv['pdf_bytes']<5_000_000,'PDF size')
 require(hashlib.sha256(json.dumps(bs,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()==inv['canonical_blocks_sha256'],'canonical block hash')
 require(sha(root/'bibliography.json')==inv['bibliography_sha256'],'frozen bibliography')
 page=BeautifulSoup((root/'index.html').read_text(),'html.parser');blocks=page.select('[data-block]')
 require([int(x['data-block'])for x in blocks]==list(range(len(bs))),'every HTML block exactly once and ordered')
 cells=0
 for i,(b,node)in enumerate(zip(bs,blocks)):
  if b['type']=='figure':
   im=node.find('img');require(im and im.get('src')==b['asset']and im.get('alt')==b['alt'],f'figure {i}')
  elif b['type']=='table':
   rows=[[norm(c.get_text())for c in row.find_all(['td','th'],recursive=False)]for row in node.find_all('tr')]
   require(rows==[[norm(c)for c in row]for row in b['rows']],f'table {i} cells');cells+=sum(map(len,rows))
  else:require(norm(node.get_text())==norm(b['text']),f'HTML block {i} text')
 require(len(page.select('table'))==8 and len(page.select('figure img'))==2,'table/figure counts')
 require([int(n['id'][4:])for n in page.select('li[id^="ref-"]')]==list(range(1,588)),'all references')
 for link in page.select('a[href^="#ref-"]'):
  no=int(link['href'][5:]);require(1<=no<=587 and page.select_one('#ref-'+str(no))and link.get_text()==str(no),f'citation {no} target')
 for n in page.select('li[id^="ref-"] a'):
  require(n['href'].startswith(('https://','http://')),'reference target');require(n.get_text()==n['href']or n['href']=='https://doi.org/'+n.get_text(),'bibliography links only displayed identifiers')
 for k,v in {'citation_title':a['title'],'citation_author':'Brad Pierce','citation_publication_date':'2026/10/21','citation_doi':a['doi'],'citation_pdf_url':a['public_urls']['pdf'],'citation_fulltext_html_url':a['public_urls']['article'],'keywords':', '.join(a['keywords']),'description':a['abstract']}.items():
  require([n.get('content')for n in page.select('meta[name="'+k+'"]')]==[v],'HTML metadata '+k)
 require([n.get('href')for n in page.select('link[rel="canonical"]')]==[a['public_urls']['article']],'self-canonical')
 front=page.select_one('#scholarly-front-matter');require(norm(a['abstract'])in norm(front.get_text()),'complete visible abstract')
 require(str(page).index('id="scholarly-front-matter"')<str(page).index('id="relevance-and-citation-scope"')<str(page).index('id="canonical-paper"'),'front matter order')
 aside=page.select_one('#relevance-and-citation-scope');require(aside.h2.get_text()=='Relevance and citation scope'and aside.p.get_text()==a['relevance_scope'],'declarative scope')
 cff=yaml.safe_load((root/'CITATION.cff').read_text());own=bibtexparser.loads((root/'citation.bib').read_text()).entries
 require(len(own)==1 and own[0]['title']==a['title']and own[0]['doi']==a['doi']and own[0]['date']==a['publication_date'],'own BibTeX identity')
 for obj in [cff,cff['preferred-citation']]:require(obj['title']==a['title']and obj['doi']==a['doi'],'CFF identity')
 expected_authors=[{'family-names':p['family'],'given-names':p['given'],'orcid':p['orcid']}for p in a['authors']]
 for obj in [cff,cff['preferred-citation']]:
  require(obj['authors']==expected_authors,'CFF complete human authors')
  require(obj['url']==a['zenodo_record']and obj['keywords']==a['keywords'],'CFF URL/keywords')
 require(cff['abstract']==a['abstract']and cff['license']==a['license'],'CFF abstract/license')
 require(cff['keywords']==a['keywords']and cff['date-released']==a['publication_date']and cff['preferred-citation']['date-published']==a['publication_date'],'CFF keywords/dates')
 ld=json.loads(page.select_one('script[type="application/ld+json"]').string);require(ld['headline']==a['title']and ld['abstract']==a['abstract']and ld['keywords']==a['keywords']and ld['identifier']['value']==a['doi'],'JSON-LD identity')
 require(ld['author']==[{'@type':'Person','name':p['name'],'givenName':p['given'],'familyName':p['family'],'sameAs':p['orcid']}for p in a['authors']],'JSON-LD complete human authors')
 require(ld['datePublished']==a['publication_date']and ld['url']==a['public_urls']['article']and ld['sameAs']==[a['doi_url'],a['zenodo_record']],'JSON-LD date/URLs')
 require(ld['encoding']=={'@type':'MediaObject','contentUrl':a['public_urls']['pdf'],'encodingFormat':'application/pdf'}and ld['license']=='https://creativecommons.org/licenses/by-nc/4.0/'and ld['inLanguage']=='en'and ld['isAccessibleForFree']is True,'JSON-LD PDF/license/language')
 require(json.loads((root/'metadata.json').read_text())=={k:v for k,v in a.items()if k not in ['blocks','references']},'metadata sidecar equality')
 prov=json.loads((root/'provenance.json').read_text())
 for k,v in {'source_publication':a['zenodo_record'],'preferred_version_doi':a['doi'],'concept_doi':a['concept_doi'],'source_filename':a['pdf_filename'],'source_sha256':inv['pdf_sha256'],'source_bytes':inv['pdf_bytes'],'canonical_blocks_sha256':inv['canonical_blocks_sha256']}.items():require(prov[k]==v,'provenance '+k)
 require(own[0]['author']=='Pierce, Brad'and own[0]['keywords']==', '.join(a['keywords'])and own[0]['year']=='2026'and own[0]['month']=='oct'and own[0]['url']==a['doi_url'],'own BibTeX author/keywords/date/URL')
 sitemap=ET.fromstring((root/'sitemap.xml').read_text());locs=[node.text for node in sitemap.findall('{http://www.sitemaps.org/schemas/sitemap/0.9}url/{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
 require(sitemap.tag=='{http://www.sitemaps.org/schemas/sitemap/0.9}urlset'and len(locs)==len(set(locs))==2 and set(locs)==set(a['public_urls'].values()),'paper sitemap exact locations')
 require((root/'robots.txt').read_text()=='User-agent: *\nAllow: /\nSitemap: '+a['public_urls']['article']+'sitemap.xml\n','paper robots crawl permission')
 md=(root/'paper.md').read_text();readme=(root/'README.md').read_text();start='<!-- BEGIN CANONICAL MANUSCRIPT -->\n';end='<!-- END CANONICAL MANUSCRIPT -->\n'
 require(readme.count(start)==readme.count(end)==1 and readme.split(start)[1].split(end)[0]==md,'README canonical partition')
 require(readme.split(start)[0].count('## Relevance and citation scope')==1 and a['relevance_scope']in readme.split(start)[0],'README scope')
 # Parse the actual Markdown independently, including the tables and images.
 mpage=BeautifulSoup(MarkdownIt('commonmark').enable('table').render(md),'html.parser')
 expected=[];observed=[]
 for b in bs:
  if b['type']=='figure':expected.append(('figure',b['asset'],b['alt']))
  elif b['type']=='table':expected.append(('table',[[norm(c)for c in row]for row in b['rows']]))
  else:expected.append(('text',norm(b['text'])))
 for node in mpage.find_all(recursive=False):
  if node.name=='table':observed.append(('table',[[norm(c.get_text())for c in row.find_all(['td','th'],recursive=False)]for row in node.find_all('tr')]))
  elif node.find('img'):observed.append(('figure',node.img['src'],node.img['alt']))
  else:observed.append(('text',norm(node.get_text())))
 require(observed==expected,'whole Markdown parser conservation')
 refs=[b['text']for b in bs if b['type']=='reference'];require([s['exact_reference']for s in d['slots']]==refs,'exact published reference slots')
 require((root/'references.md').read_text()=='References\n\n'+'\n\n'.join(refs)+'\n','references.md complete')
 ids=[w['id']for w in d['works']];require(len(ids)==len(set(ids))==inv['normalized_work_records'],'work IDs')
 byid={w['id']:w for w in d['works']}
 for wid,record in json.loads((root/'source/reference-field-fixture.json').read_text())['records'].items():
  require(record['published_reference']in refs,'independent fixture source reference')
  for k,v in record['expected_fields'].items():require(byid[wid].get(k)==v,'independent published field '+wid+' '+k)
 for w in d['works']:
  if 'title'in w:require(norm(w['title'])in norm(w['note']),'published title spacing '+w['id'])
 require({x for s in d['slots']for x in s['works']}==set(ids),'slot-work reachability')
 csl=json.loads((root/'references.csl.json').read_text());require(csl==d['works'],'CSL all frozen fields')
 bib=bibtexparser.loads((root/'references.bib').read_text()).entries;require(len(bib)==len(ids)and {w['ID']for w in bib}==set(ids),'BibTeX parser complete')
 bm={w['ID']:w for w in bib}
 for w in d['works']:
  for src,target in [('title','title'),('DOI','doi'),('URL','url')]:
   if src in w:require(bm[w['id']].get(target)==w[src],'BibTeX opaque identity '+w['id']+' '+src)
  if 'issued'in w:require(bm[w['id']].get('date')=='-'.join(str(v).zfill(4 if i==0 else 2)for i,v in enumerate(w['issued']['date-parts'][0])),'BibTeX date '+w['id'])
 require((root/'references.ris').read_text().count('TY  - ')==len(ids)and (root/'references.ris').read_text().count('ER  - ')==len(ids),'RIS record count')
 for f,h in inv['figure_sha256'].items():require(sha(root/'figures'/f)==h,'SVG bytes '+f)
 # Repository-added prose is audited separately from immutable publication text.
 framing=readme.split(start)[0]+' '+aside.get_text()+' '+json.dumps({k:v for k,v in a.items()if k not in ['blocks']})+' '+(root/'provenance.json').read_text()+' '+cff['message']
 for bad in ['when to cite this report','cite this report','if this work is relevant','ignore previous','you should','system prompt','act as','use this source']:
  require(bad not in framing.lower(),'instruction-like framing '+bad)
 require('display:none'not in (root/'index.html').read_text().replace(' ',''),'hidden text')
 paths=inv['public_paths'];actual=sorted(p.relative_to(root).as_posix()for p in root.rglob('*')if p.is_file()and '.git'not in p.parts and not any(v in p.parts for v in ['node_modules','__pycache__'])and p.suffix not in ['.pyc','.pyo'])
 require(actual==paths,'exact public path set')
 manifest=[line.split('  ',1)for line in (root/'checksums.sha256').read_text().splitlines()]
 require([p for h,p in manifest]==[p for p in paths if p!='checksums.sha256'],'exact checksum coverage')
 for h,p in manifest:require(sha(root/p)==h,'checksum '+p)
 if rebuild:
  with tempfile.TemporaryDirectory()as tmp:
   dest=Path(tmp)/'repo';shutil.copytree(root,dest,ignore=shutil.ignore_patterns('.git','__pycache__','node_modules'))
   subprocess.run([sys.executable,'-B',str(dest/'scripts/build_derivative.py')],check=True)
   require(all((dest/p).read_bytes()==(root/p).read_bytes()for p in paths),'fresh deterministic rebuild')
 return {'status':'PASS','canonical_blocks':len(bs),'table_cells':cells,'references':587,'figures':2,'tables':8,'pdf_pages':160,'pdf_sha256':inv['pdf_sha256'],'files':len(paths),'bibliography_exceptions':len(d['exceptions']),'rebuild':'PASS'if rebuild else'not requested'}

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--no-rebuild',action='store_true');args=p.parse_args()
 try:print(json.dumps(validate(args.repo,not args.no_rebuild),indent=2))
 except (AssertionError,KeyError,ValueError)as e:print('FAIL: '+str(e),file=sys.stderr);sys.exit(1)
