import React,{useEffect,useState} from 'react';
import './campaign-overview.css';

const labels={CMO:'CM',Research:'RE',Design:'DE',Implementation:'IM','Digital Marketing':'DM',Content:'CO',Analyst:'AN'};
const number=new Intl.NumberFormat();
const measured=n=>Number.isFinite(n)?number.format(n):'Unknown';

function Operations({run}){
 const [step,setStep]=useState(null);
 const messages=run?.messages||[];
 const live=run?.status==='working';
 useEffect(()=>setStep(null),[run?.id]);
 useEffect(()=>{
   if(step===null)return;
   const timer=setTimeout(()=>setStep(step+1<messages.length?step+1:null),2100);
   return ()=>clearTimeout(timer);
 },[step,messages.length]);
 const replay=step!==null;
 const trail=replay?messages.slice(0,step):messages;
 const plan=[...trail].reverse().find(m=>m.assignments);
 const current=live?run?.brief.active_task:null;
 const focus=replay?messages[step]?.role:current?.role;
 const roles=[...new Set(['CMO',...(plan?.assignments||[]).map(t=>t.role),...trail.map(m=>m.role),...(focus?[focus]:[]),'Analyst'])];
 const verdict=messages.at(-1)?.body?.split('\n')[0].trim();
 const status=replay?'Replaying saved handoffs':live?'Campaign running':run?.status==='failed'?'Run stopped':run?.status==='published'?'Published':verdict==='READY'?'Cleared for launch':verdict==='HOLD'?'Held for revision':run?.status||'Awaiting brief';
 return <section className="opsBoard" aria-label="Campaign operations"><header><div><small>CAMPAIGN OPERATIONS</small><h2>Agent workflow</h2></div><span className={'opsState '+(live?'active':'')}>{status}</span></header>
 <div className="agentGrid">{roles.map(role=>{
 const assigned=plan?.assignments.find(t=>t.role===role);
 const last=[...trail].reverse().find(m=>m.role===role);
 const working=focus===role;
 const done=!!last&&(role==='CMO'?last.decision||last===trail.at(-1):true);
 return <div className={'agentNode '+(working?'running':last?'finished':'')} key={role}>
 <div className="agentMark">{labels[role]||role.slice(0,2)}</div><strong>{role==='CMO'?'AI CMO':role}</strong><small>{working?(replay?'Recorded step':'Working'):done?'Handoff saved':last?(live||replay?'Supervising':'Handoff saved'):assigned?'Assigned':'Waiting'}</small>
 <span>{(working&&current?.provider)||last?.model?.split(' / ')[0]||assigned?.provider||'—'}</span></div>})}</div>
 <div className="opsFoot"><div><b>{replay?'Recorded handoff':live?'Current task':'Latest handoff'}</b><p>{replay?messages[step]?.body:live?current?.task||'Preparing campaign':messages.at(-1)?.body||'The CMO starts when a company brief is ready.'}</p></div>
 {!live&&messages.length>0&&<button type="button" onClick={()=>setStep(replay?null:0)}>{replay?'Stop replay':'Replay handoffs'}</button>}</div></section>;
}

function Website({report}){
 const pages=report?.crawl?.pages||[];
 const checked=pages.filter(p=>p.status===200&&p.partial===false);
 const checks=[['Page title',/ title elements$/],['Main heading',/ h1 elements$/],['Image alt attributes',/missing alt attributes/],['Indexing directive',/noindex directive/]];
 const results=checks.map(([label,issue])=>({label,passed:checked.filter(p=>!p.findings.some(f=>issue.test(f))).length}));
 const pass=results.reduce((n,r)=>n+r.passed,0);
 const score=checked.length?Math.round(100*pass/(checked.length*checks.length)):null;
 return <section className="auditBoard"><header><div><small>WEBSITE AUDIT</small><h2>Technical health</h2></div></header><div className="auditScore"><div className="scoreDial" style={{'--score':(score??0)+'%'}}><strong>{score??'—'}</strong></div><div><b>{score===null?'Awaiting a complete page':'Technical check pass rate'}</b><p>{pass} of {checked.length*4} checks passed across {checked.length} fully crawled HTML pages.</p></div></div>
 <div className="checkRows">{results.map(r=><div key={r.label}><span>{r.label}</span><progress max={checked.length||1} value={r.passed}/><small>{checked.length?r.passed+'/'+checked.length:'Unknown'}</small></div>)}</div>
 {pages.flatMap(p=>p.findings.map(f=><p className="auditIssue" key={p.url+f}><b>{new URL(p.url).pathname}</b> · {f}</p>))}</section>;
}

export default function CampaignOverview({ws}){
 const report=ws.seo?.report, search=report?.search_console;
 const rows=search?.status==='available'?search.rows||[]:[];
 const sum=k=>rows.length&&rows.every(r=>Number.isFinite(r[k]))?rows.reduce((n,r)=>n+r[k],0):null;
 const deliveries=ws.deliveries||[];
 const metricCards=[['Search clicks',sum('clicks'),'Returned query and page rows'],['Search impressions',sum('impressions'),'Returned query and page rows'],['Measured social posts',deliveries.filter(d=>d.metrics&&Object.keys(d.metrics).length).length,'In recent delivery history'],['Qualified conversions',null,'No connected conversion report']];
 return <div className="campaignOverview"><Operations run={ws.runs.find(r=>!r.brief.skill)}/><Website report={report}/>
 <section className="metricBoard"><header><div><small>CHANNEL ANALYTICS</small><h2>Marketing performance</h2></div>{search?.end&&<span>{search.start} – {search.end} · Search Console</span>}</header><div className="metricGrid">{metricCards.map(([name,value,basis])=><div key={name}><small>{name}</small><strong>{measured(value)}</strong><span>{basis}</span></div>)}</div><details className="channelDetails"><summary>Channel measurement detail</summary><dl>
 {['linkedin','facebook','instagram','mastodon'].map(network=>{const post=deliveries.find(d=>d.network===network&&d.metrics&&Object.keys(d.metrics).length);return <div key={network}><dt>{network}</dt><dd>{post?Object.entries(post.metrics).map(([k,v])=>k+' '+measured(v)).join(' · ')+' (latest measured post)':'Unknown'}</dd></div>})}
 <div><dt>Visits by channel</dt><dd>Unknown</dd></div><div><dt>Email performance</dt><dd>Unknown</dd></div></dl></details></section></div>
}
