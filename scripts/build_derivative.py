#!/usr/bin/env python3
"""Offline deterministic representation of one frozen published survey."""
from pathlib import Path
import json,html,re,argparse,hashlib,yaml,sys
sys.dont_write_bytecode=True
from export_bibliography import export

def trim(s):return s.rstrip('.,;:!?')
def links(s,citations=True):
 spans=[]
 for m in re.finditer(r'https?://\S+',s):
  u=trim(m[0]);spans.append((m.start(),m.start()+len(u),u))
 for m in re.finditer(r'(?<![\w/])(10\.\d{4,9}/\S+)',s):
  u=trim(m[1]);start=m.start(1)
  if not any(a<=start<b for a,b,_ in spans):spans.append((start,start+len(u),'https://doi.org/'+u))
 if citations:
  for m in re.finditer(r'\[(\d+)\]',s):
   for n in re.finditer(r'\d+',m[1]):spans.append((m.start()+1+n.start(),m.start()+1+n.end(),f'#ref-{int(n[0])}'))
 out='';pos=0
 for a,b,target in sorted(spans):
  if a<pos:continue
  out+=html.escape(s[pos:a])+f'<a href="{html.escape(target,quote=True)}">{html.escape(s[a:b])}</a>';pos=b
 return out+html.escape(s[pos:])

def block(b,i):
 attr=f' data-block="{i}"';s=b.get('text','');typ=b['type']
 if typ=='table':return '<table'+attr+'><thead><tr>'+''.join('<th scope="col">'+links(c)+'</th>'for c in b['rows'][0])+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+links(c)+'</td>'for c in row)+'</tr>'for row in b['rows'][1:])+'</tbody></table>'
 if typ=='figure':return f'<figure{attr}><img src="{b["asset"]}" alt="{html.escape(b["alt"],quote=True)}"></figure>'
 if typ=='reference':return f'<li{attr} id="ref-{b["number"]}" value="{b["number"]}">'+links(s,False)+'</li>'
 if i==0:return '<h1'+attr+'>'+html.escape(s)+'</h1>'
 if i==1:return '<p class="author"'+attr+'>'+html.escape(s)+'</p>'
 if i==2:return '<p class="date">Manuscript date: <span'+attr+'>'+html.escape(s)+'</span></p>'
 if typ=='heading':return f'<h{min(b["level"]+1,6)}{attr}>'+html.escape(s)+f'</h{min(b["level"]+1,6)}>'
 if s.startswith('Keywords:'):return '<p class="keywords"'+attr+'><em>Keywords:</em>'+html.escape(s[len('Keywords:'):])+'</p>'
 return '<p'+attr+'>'+links(s)+'</p>'

def markdown(blocks):
 lines=[]
 def inline(s):return re.sub(r'([\\`*_{}\[\]])',r'\\\1',s).replace('<','&lt;').replace('>','&gt;')
 for i,b in enumerate(blocks):
  if b['type']=='table':
   row=lambda r:'| '+' | '.join(inline(c).replace('|','\\|').replace('\n','<br>')for c in r)+' |'
   lines.append('\n'.join([row(b['rows'][0]),row(['---']*len(b['rows'][0]))]+[row(r)for r in b['rows'][1:]]))
  elif b['type']=='figure':lines.append(f'![{inline(b["alt"])}]({b["asset"]})')
  else:lines.append(('# 'if i==0 else '#'*(min(b['level']+1,6))+' 'if b['type']=='heading'else '')+inline(b['text']))
 return '\n\n'.join(lines)+'\n'

def build(root):
 root=Path(root);a=json.loads((root/'source/paper.json').read_text());bs=a['blocks'];u=a['public_urls'];e=html.escape
 meta={'citation_title':a['title'],'citation_author':'Brad Pierce','citation_publication_date':a['publication_date'].replace('-','/'),'citation_doi':a['doi'],'citation_pdf_url':u['pdf'],'citation_fulltext_html_url':u['article'],'keywords':', '.join(a['keywords']),'description':a['abstract'],'robots':'index,follow'}
 ld={'@context':'https://schema.org','@type':'ScholarlyArticle','headline':a['title'],'author':[{'@type':'Person','name':'Brad Pierce','givenName':'Brad','familyName':'Pierce','sameAs':a['authors'][0]['orcid']}],'datePublished':a['publication_date'],'identifier':{'@type':'PropertyValue','propertyID':'DOI','value':a['doi']},'url':u['article'],'sameAs':[a['doi_url'],a['zenodo_record']],'encoding':{'@type':'MediaObject','contentUrl':u['pdf'],'encodingFormat':'application/pdf'},'abstract':a['abstract'],'keywords':a['keywords'],'license':'https://creativecommons.org/licenses/by-nc/4.0/','isAccessibleForFree':True,'inLanguage':'en','publisher':{'@type':'Organization','name':'Zenodo'}}
 css='body{font:15px/1.45 Arial,sans-serif;max-width:1120px;margin:18px auto;padding:0 16px;color:#171717}h1{font-size:24px;line-height:1.15;margin:0 0 8px}h2{font-size:20px;margin:22px 0 8px}h3{font-size:17px;margin:18px 0 6px}p{margin:7px 0}.author{font-size:19px;margin:6px 0}.date{font-size:13px;margin:3px 0}a{color:#165a82;overflow-wrap:anywhere}table{border-collapse:collapse;width:100%;font-size:14px;margin:12px 0}td,th{border:1px solid #aaa;padding:7px;vertical-align:top;overflow-wrap:anywhere}th{background:#e8edf0}img{max-width:100%;height:auto}figure{margin:16px 0}.keywords{font-size:13px}aside{border-top:1px solid #ccc;margin:18px 0;padding-top:8px}aside h2{font-size:18px;margin-top:6px}.references{list-style:none;padding:0}.references li{padding-left:2em;text-indent:-2em;margin:8px 0;font-size:14px}footer{margin-top:22px;font-size:13px}@media(max-width:600px){body{font-size:13px;line-height:1.4;margin:10px auto;padding:0 12px}h1{font-size:20px;line-height:1.1}.author{font-size:17px}h2{font-size:18px;margin:14px 0 6px}table{display:block;overflow-x:auto}}'
 head='<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>'+e(a['title'])+' — Brad Pierce</title>\n'
 head+='\n'.join(f'<meta name="{k}" content="{e(v,quote=True)}">'for k,v in meta.items())
 head+='\n'+''.join(f'<meta property="{k}" content="{e(v,quote=True)}">'for k,v in {'og:title':a['title'],'og:description':a['abstract'],'og:type':'article','og:url':u['article']}.items())
 head+=f'<link rel="canonical" href="{u["article"]}"><script type="application/ld+json">'+json.dumps(ld,ensure_ascii=False).replace('</',r'<\/')+'</script><style>'+css+'</style></head><body><article>'
 front=''
 for i,b in enumerate(bs[:7]):
  if i==2:front+='<p class="date">Publication date: <time datetime="'+a['publication_date']+'">21 October 2026</time></p>\n'
  front+=block(b,i)+'\n'
 aside='<aside id="relevance-and-citation-scope"><h2>Relevance and citation scope</h2><p>'+links(a['relevance_scope'],False)+'</p><p>'+links(a['preferred_citation'],False)+'</p><p>This static full-text representation is a derivative of the Zenodo publication of record.</p><p><a href="silicate-cementitious-precursors.pdf">PDF</a> · <a href="'+a['zenodo_record']+'">Zenodo record</a> · <a href="citation.bib">Paper citation (BibTeX)</a> · <a href="references.bib">Source bibliography (BibTeX)</a> · <a href="references.ris">RIS</a> · <a href="references.csl.json">CSL-JSON</a></p></aside>'
 rest=[];opened=False
 for i,b in enumerate(bs[7:],7):
  if b['type']!='reference'and opened:rest.append('</ol>');opened=False
  if b['type']=='reference'and not opened:rest.append('<ol class="references">');opened=True
  rest.append(block(b,i))
 if opened:rest.append('</ol>')
 source=head+'<header id="scholarly-front-matter">'+front+'</header>'+aside+'<div id="canonical-paper">'+'\n'.join(rest)+'</div></article><footer>© 2026 Brad Pierce · <a href="https://creativecommons.org/licenses/by-nc/4.0/">CC BY-NC 4.0</a></footer></body></html>\n'
 (root/'index.html').write_text(source)
 paper=markdown(bs);(root/'paper.md').write_text(paper)
 prefix='# '+a['title']+'\n\nBrad Pierce · Published 21 October 2026 · [Preprint]\n\n'+a['preferred_citation']+'\n\nThe DOI-linked Zenodo edition is the publication of record. This repository contains its complete machine-readable derivative and citation files.\n\n## Relevance and citation scope\n\n'+a['relevance_scope']+'\n\n'
 (root/'README.md').write_text(prefix+'<!-- BEGIN CANONICAL MANUSCRIPT -->\n'+paper+'<!-- END CANONICAL MANUSCRIPT -->\n')
 human=[{'family-names':'Pierce','given-names':'Brad','orcid':a['authors'][0]['orcid']}]
 preferred={'type':'generic','status':'preprint','title':a['title'],'authors':human,'doi':a['doi'],'date-published':a['publication_date'],'year':2026,'url':a['zenodo_record'],'publisher':{'name':'Zenodo'},'keywords':a['keywords'],'notes':'Published preprint; the version DOI identifies the publication of record.'}
 cff={'cff-version':'1.2.0','message':'Bibliographic identity of the DOI-linked Zenodo preprint, the publication of record.','type':'dataset','title':a['title'],'authors':human,'doi':a['doi'],'date-released':a['publication_date'],'url':a['zenodo_record'],'abstract':a['abstract'],'keywords':a['keywords'],'license':a['license'],'preferred-citation':preferred}
 # CFF's top-level type describes this data/text repository; preferred-citation identifies the paper.
 (root/'CITATION.cff').write_text(yaml.safe_dump(cff,allow_unicode=True,sort_keys=False))
 own='@misc{pierce_silicate_2026,\n  author = {Pierce, Brad},\n  title = {'+a['title']+'},\n  year = {2026},\n  month = {oct},\n  date = {2026-10-21},\n  doi = {'+a['doi']+'},\n  url = {'+a['doi_url']+'},\n  keywords = {'+', '.join(a['keywords'])+'},\n  note = {Preprint. Zenodo. Published 21 October 2026}\n}\n'
 (root/'citation.bib').write_text(own)
 (root/'metadata.json').write_text(json.dumps({k:v for k,v in a.items()if k not in ['blocks','references']},ensure_ascii=False,indent=2)+'\n')
 (root/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+e(u[k])+'</loc></url>'for k in ['article','pdf'])+'</urlset>\n')
 (root/'robots.txt').write_text('User-agent: *\nAllow: /\nSitemap: '+u['article']+'sitemap.xml\n')
 export(root)
 inv=json.loads((root/'source/invariants.json').read_text());paths=inv.get('public_paths')
 if paths:
  (root/'checksums.sha256').write_text(''.join(hashlib.sha256((root/p).read_bytes()).hexdigest()+'  '+p+'\n'for p in paths if p!='checksums.sha256'))

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1]);build(parser.parse_args().repo)
