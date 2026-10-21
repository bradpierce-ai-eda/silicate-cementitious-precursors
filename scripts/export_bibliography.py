#!/usr/bin/env python3
"""Deterministic exports from frozen bibliography.json; no network enrichment."""
from pathlib import Path
import json,re,argparse
def export(root):
 OUT=Path(root);dataset=json.loads((OUT/'bibliography.json').read_text());works=dataset['works']
 def esc(s):return str(s).replace('\\','\\textbackslash{}').replace('{','\\{').replace('}','\\}')
 bib=[];ris=[]
 for w in works:
  fields={'note':w['note'],'key':w['id']}
  if 'title'in w:fields['title']=w['title']
  if w.get('author'):fields['author']=' and '.join((n['family']+', '+n['given']) if 'family'in n else '{'+n['literal']+'}' for n in w['author'])
  for k,t in [('DOI','doi'),('URL','url'),('page','pages')]:
   if k in w:fields[t]=w[k]
  for k,t in [('container-title','journal'),('volume','volume'),('issue','number')]:
   if k in w:fields[t]=w[k]
  if 'article-locator'in w:fields['eid']=w['article-locator']
  if w['type']=='patent':fields['number']=w['number']
  fields['note']='Source type: '+w['type']+'. '+fields['note']
  if 'issue'in w:fields['note']+=' Issue: '+w['issue']+'.'
  for field in ['published-online','published-print']:
   if field in w:fields['note']+=' '+field+': '+'-'.join(str(v) for v in w[field]['date-parts'][0])+'.'
  if 'number'in w:fields['note']+=' Publication identifier: '+w['number']+'.'
  if 'issued'in w:fields['year']=str(w['issued']['date-parts'][0][0])
  if 'issued'in w:fields['date']='-'.join(str(v).zfill(4 if i==0 else 2) for i,v in enumerate(w['issued']['date-parts'][0]))
  if 'title-translation'in w:fields['annote']=w['title-translation'];fields['note']+=' English title: '+w['title-translation']
  # Opaque DOI/URL fields are literal; prose braces only protect source punctuation.
  # Classic BibTeX lacks patent/standard/dataset/webpage types. Retain these as
  # misc with an explicit source-type note; CSL is the richer typed authority.
  entry='article' if w['type'] in ['article-journal','article-magazine']and w.get('title')and w.get('container-title') else 'inproceedings' if w['type']=='paper-conference'and w.get('title')and w.get('container-title') else 'misc'
  if entry=='inproceedings'and 'journal'in fields:fields['booktitle']=fields.pop('journal')
  if entry=='article'and 'number'in fields and 'volume'not in fields:fields.pop('number')
  bib.append('@'+entry+'{'+w['id']+',\n'+',\n'.join('  '+k+' = {'+(v if k in ['doi','url','author'] else esc(v))+'}' for k,v in fields.items())+'\n}')
  ris_type={'article-journal':'JOUR','article-magazine':'MGZN','paper-conference':'CONF','patent':'PAT','thesis':'THES','report':'RPRT','webpage':'ELEC'}.get(w['type'],'GEN')
  rr=['TY  - '+ris_type,'ID  - '+w['id'],'N1  - Source type: '+w['type']+'.']
  if 'issue'in w:rr.append('N1  - Issue: '+w['issue']+'.')
  if 'title'in w:rr.append('TI  - '+w['title'])
  for n in w.get('author',[]):rr.append('AU  - '+(n['family']+', '+n['given'] if 'family'in n else n['literal']+','))
  if 'issued'in w:rr.append('PY  - '+str(w['issued']['date-parts'][0][0]))
  if 'issued'in w:rr.append('DA  - '+'-'.join(str(v).zfill(4 if i==0 else 2) for i,v in enumerate(w['issued']['date-parts'][0])))
  for k,t in [('DOI','DO'),('URL','UR'),('note','N1')]:
   if k in w:rr.append(t+'  - '+w[k])
  for k,t in [('container-title','JO'),('volume','VL'),('issue','IS')]:
   if k in w:rr.append(t+'  - '+w[k])
  if 'page'in w:
   ends=re.split('[–-]',w['page']);rr.append('SP  - '+ends[0])
   if len(ends)>1:rr.append('EP  - '+ends[-1])
  if 'article-locator'in w:
   rr.append('SP  - '+w['article-locator']);rr.append('N1  - Article identifier: '+w['article-locator'])
  if 'number'in w:
   rr.append('M1  - '+w['number']);rr.append('N1  - Publication identifier: '+w['number'])
  if 'title-translation'in w:rr.append('N1  - English title: '+w['title-translation'])
  rr.append('ER  - ');ris.append('\n'.join(rr))
 (OUT/'references.bib').write_text('\n\n'.join(bib)+'\n');(OUT/'references.ris').write_text('\n\n'.join(ris)+'\n')

 (OUT/'references.csl.json').write_text(json.dumps(works,ensure_ascii=False,indent=2))
 (OUT/'references.md').write_text('References\n\n'+'\n\n'.join(s['exact_reference'] for s in dataset['slots'])+'\n')
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1]);export(parser.parse_args().repo)
