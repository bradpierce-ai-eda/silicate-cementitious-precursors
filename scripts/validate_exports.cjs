const fs=require('fs'),path=require('path');
const {Cite}=require('@citation-js/core');require('@citation-js/plugin-bibtex');require('@citation-js/plugin-csl');require('@citation-js/plugin-ris');
const root=path.resolve(process.argv[2]||path.join(__dirname,'..'));
const frozen=JSON.parse(fs.readFileSync(path.join(root,'bibliography.json'),'utf8'));
const issues=[];let count=0;
const canon=x=>Array.isArray(x)?x.map(canon):x&&typeof x==='object'?Object.fromEntries(Object.keys(x).sort().map(k=>[k,canon(x[k])])):x;
function check(file,id,field,actual,expected){count++;if(JSON.stringify(canon(actual))!==JSON.stringify(canon(expected)))issues.push({file,id,field,actual,expected});}
const display=n=>n.literal||[n.family,n.given].filter(Boolean).join(', ');
for(const file of ['references.bib','references.csl.json','references.ris']){
 const data=new Cite(fs.readFileSync(path.join(root,file),'utf8')).data;
 const byId=Object.fromEntries(data.map(r=>[r.id,r]));
 check(file,'all','IDs',Object.keys(byId).sort(),frozen.works.map(w=>w.id).sort());
 check(file,'all','record count',data.length,frozen.works.length);
 for(const w of frozen.works){const a=byId[w.id];if(!a)continue;
  for(const k of ['title','DOI','URL','container-title','volume'])check(file,w.id,k,a[k]??null,w[k]??null);
  check(file,w.id,'unparsed author identity',(a.author||[]).map(display),(w.author||[]).map(display));
  check(file,w.id,'publication-date precision',a.issued?.['date-parts']||null,w.issued?.['date-parts']||null);
  if(w.page)check(file,w.id,'page/locator',String(a.page||a['page-first']||'').replace(/[–—]/g,'-'),w.page.replace(/[–—]/g,'-'));
  const note=Array.isArray(a.note)?a.note.join(' '):a.note||'';
  if(w.issue)check(file,w.id,'issue retained in native field or explicit note',a.issue===w.issue||note.includes('Issue: '+w.issue+'.'),true);
  check(file,w.id,'exact published slot in note',note.includes(w.note),true);
 }
}
const a=JSON.parse(fs.readFileSync(path.join(root,'source/paper.json'),'utf8'));
const own=new Cite(fs.readFileSync(path.join(root,'citation.bib'),'utf8')).data;
check('citation.bib','own','count',own.length,1);
for(const[k,v]of Object.entries({title:a.title,DOI:a.doi,URL:a.doi_url}))check('citation.bib','own',k,own[0][k],v);
check('citation.bib','own','date',own[0].issued?.['date-parts'],[[2026,10,21]]);
check('citation.bib','own','actual human author',own[0].author,[{given:'Brad',family:'Pierce'}]);
console.log(JSON.stringify({status:issues.length?'FAIL':'PASS',works:frozen.works.length,formats:3,field_checks:count,issues,limitations:['Bibliographic names without verified structured splits remain unparsed literal names; no corporate status or surname decomposition is inferred.','Conservative document types and absent metadata remain explicit; exact publication references and qualifications are retained.']},null,2));
process.exitCode=issues.length?1:0;
