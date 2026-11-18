import React, { useCallback, useEffect, useState } from 'react';
import {Link,useSearchParams} from 'react-router-dom';
import {workspaceSections} from './WorkspaceShell';
import MarketingIntegrations from "./MarketingIntegrations";
import CampaignSchedule from "./CampaignSchedule";
import CampaignOverview from './CampaignOverview';
import SearchAudit from './SearchAudit';
import SocialChannels,{Results} from './SocialChannels';
const stamp=t=>new Date(t*1000).toLocaleString(undefined,{dateStyle:'medium',timeStyle:'short'});
export default function CampaignDesk({api}){
 const [params]=useSearchParams();
 const view=workspaceSections.some(s=>s[0]===params.get('view'))?params.get('view'):'overview';
 const visible=(...names)=>names.includes(view);
 const [query,setQuery]=useState('');
 const [status,setStatus]=useState('all');
 const [ws,setWs]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[editing,setEditing]=useState(false);
 const load=useCallback(async()=>setWs((await api.get('/api/campaign-agents')).data),[api]);
 useEffect(()=>{const refresh=()=>load().catch(()=>setError('Could not load your workspace. Refresh to try again.'));refresh();const id=setInterval(()=>{if(!document.hidden)refresh()},5000);return ()=>clearInterval(id)},[load]);
 async function act(op,data,done){setBusy(true);setError('');try{await api.post('/api/campaign-agents/'+op,data,{headers:{'X-VOS-Client':'dashboard'}});await load();done?.()}catch(e){setError(e.response?.data?.detail || 'Could not save the change. Please try again.')}finally{setBusy(false)}}
 if(!ws)return <p role="status">{error||'Loading your workspace…'}</p>;
 const profile=ws.autopilot, admin=ws.role==='admin', previous=profile?.brief||ws.runs[0]?.brief||{};
 function configure(e){e.preventDefault();const f=Object.fromEntries(new FormData(e.currentTarget));act('configure',{...f,budget:Number(f.budget),destination:f.autopublish?ws.social:null},()=>setEditing(false))}
 return <><p className="kicker">{ws.company}</p><div className="desktitle"><h1>{workspaceSections.find(s=>s[0]===view)[1]}</h1><span className="tag">{profile?.enabled?'Automation on':profile?'Paused':'Setup'}</span></div>
 {error&&<p className="notice" role="alert">{error}</p>}
 {view==='overview'&&<div className="workspaceSummary">{[
 ['Campaigns',ws.runs.filter(r=>!r.brief.skill).length,'campaigns'],
 ['Scheduled posts',(ws.calendar||[]).filter(p=>p.state==='scheduled'&&p.network!=='private').length,'calendar'],
 ['Working agents',ws.runs.filter(r=>r.status==='working').length,'agents'],
 ['Connected sources',(ws.integrations||[]).filter(r=>r.connected).length+(ws.channels||[]).filter(r=>r.label).length+(ws.seo?.property?1:0),'integrations']
 ].map(([label,value,to])=><Link key={to} to={'/dashboard?view='+to}><small>{label}</small><strong>{value}<span>↗</span></strong></Link>)}</div>}
 <div hidden={!visible('overview','analytics','agents')} className={'overviewView overview-'+view}><CampaignOverview ws={ws}/></div>
 {view==='analytics'&&<section className="metricBoard"><h2>Connected reports</h2>{(ws.integrations||[]).some(r=>r.connected)?<div className="integrationGrid">{ws.integrations.filter(r=>r.connected).map(r=><article key={r.source}><strong>{r.name}</strong><p>{r.report.account} · {r.report.period}</p>{r.problem&&<p role="status">{r.problem}</p>}<dl>{Object.entries(r.report.metrics).map(([k,v])=><div key={k}><dt>{k.replace(/([a-z])([A-Z])/g,'$1 $2').replaceAll('_',' ')}</dt><dd>{v.toLocaleString()}</dd></div>)}</dl>{!Object.keys(r.report.metrics).length&&<p>Measurements unknown</p>}</article>)}</div>:<p>Connect analytics sources to see their measured results here.</p>}<Link to="/dashboard?view=integrations">Manage connections →</Link></section>}
 <div hidden={!visible("calendar","agents")} className={"scheduleView schedule-"+view}><CampaignSchedule ws={ws} act={act} busy={busy}/></div>
 <div hidden={!visible("settings")}><div className="deskgrid"><section className="panel"><h2>{profile&&!editing?'Company brief':'Brief your AI CMO'}</h2>
 {admin&&(!profile||editing)?<form className="vform" onSubmit={configure}>
 {[['offer','What do you sell?','Inventory software for independent shops',200],['audience','Who do you want to reach?','Independent florists',200],['goal','What should the campaign achieve?','Book 10 demos in 30 days',600]].map(([k,label,hint,max])=><label key={k}>{label}<input name={k} required maxLength={max} defaultValue={previous[k]} placeholder={hint}/></label>)}
 <div className="formpair"><label>Planning budget (USD)<input name="budget" type="number" min="0" max="100000000" step="1" required defaultValue={previous.budget||0}/></label><label>Campaign frequency<select name="cadence" defaultValue={profile?.cadence||'weekly'}><option value="weekly">Every week</option><option value="once">Once</option></select></label></div>
 {ws.social&&<label className="check"><input type="checkbox" name="autopublish" defaultChecked={profile?.destination===ws.social}/> Automatically publish posts cleared by the Analyst to @{ws.social}</label>}
 <small>The first campaign starts immediately. Your budget guides planning; this workflow uses organic social.</small>
 <div className="actions"><button className="vprimary" disabled={busy}>{profile?.enabled?'Save changes':'Start automation'} →</button>{editing&&<button type="button" onClick={()=>setEditing(false)}>Cancel</button>}</div></form>:
 profile?<><h3>{profile.brief.goal}</h3><p>{profile.brief.offer} · {profile.brief.audience}</p><dl><dt>Frequency</dt><dd>{profile.cadence==='weekly'?'Weekly':'One campaign'}</dd><dt>Budget</dt><dd>USD {profile.brief.budget}</dd><dt>Delivery</dt><dd>{profile.destination?'Auto-publish to @'+profile.destination:ws.channels?.some(c=>c.label)?'Connected channels':'Save drafts'}</dd></dl>{admin&&<div className="actions"><button className="vquiet" onClick={()=>setEditing(true)}>{profile.enabled?'Edit brief':'Resume automation'}</button>{!!profile.enabled&&<button disabled={busy} onClick={()=>act('pause',{})}>Pause</button>}</div>}</>:<p>A company admin can activate automation here.</p>}
 </section><aside className="panel control"><h2>CMO status</h2><p aria-live="polite">{profile?.note||'Waiting for the company brief.'}</p>
 <dl><dt>Next campaign</dt><dd>{profile?.due?stamp(profile.due):'None scheduled'}</dd><dt>Runs this month</dt><dd>{ws.used} / {ws.limit}</dd></dl>
 {admin&&<details><summary>Publishing connection</summary><p>{ws.social?'Connected to @'+ws.social:'Connect Mastodon to enable automatic publishing. You can also keep drafts private.'}</p><form className="vform" onSubmit={e=>{e.preventDefault();const f=e.currentTarget;act('connect',{token:f.elements.token.value},()=>f.reset())}}><label>Mastodon.social token<input name="token" type="password" required autoComplete="off"/></label><button className="vquiet" disabled={busy}>Connect account</button></form>{ws.social&&<button onClick={()=>act('disconnect',{})} disabled={busy}>Disconnect</button>}</details>}</aside></div></div>
 <div hidden={!visible("website")}><SearchAudit seo={ws.seo} admin={admin} api={api} load={load}/></div>
 <div hidden={!visible("integrations")}><MarketingIntegrations ws={ws} api={api} load={load}/>
 <SocialChannels api={api} ws={ws} load={load}/></div>
 <div hidden={!visible("overview","campaigns")}><div className="runhead"><h2 className="feedtitle">{view==="overview"?"Recent campaigns":"Campaign activity"}</h2><Link to="/ai-tools">Explore agent skills ↗</Link></div>{!ws.runs.length&&<p className="empty">Your agents’ work will appear here as each handoff finishes.</p>}
 {view==='campaigns'&&<div className="campaignFilters"><label>Search campaigns<input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Goal, draft or campaign number"/></label><label>Status<select value={status} onChange={e=>setStatus(e.target.value)}><option value="all">All statuses</option>{[...new Set(ws.runs.map(r=>r.status))].map(s=><option key={s}>{s}</option>)}</select></label></div>}
 {ws.runs.filter(r=>(view==='overview'||status==='all'||r.status===status)&&(view==='overview'||!query||[r.id,r.brief.goal,r.draft].join(' ').toLowerCase().includes(query.toLowerCase()))).slice(0,view==='overview'?3:50).map(r=><article className="panel run" key={r.id}><div className="runhead"><small>Campaign {r.id} · {r.created} UTC</small><span className="tag">{r.status}</span></div><h3>{r.brief.skill ? r.brief.skill.replace(/-/g," "):r.brief.goal}</h3>
 {view!=="overview"&&r.messages.some(m=>m.assignments)&&<section><h4>CMO assignments</h4><ul>{[...r.messages].reverse().find(m=>m.assignments).assignments.map(t=><li key={t.type}><strong>{t.role}</strong> · {t.provider}<p>{t.instruction}</p></li>)}</ul></section>}
 {view!=="overview"&&r.messages.at(-1)?.decision&&<section><h4>CMO decision</h4><p>{r.messages.at(-1).body}</p></section>}
 {r.draft&&<blockquote>{r.draft}</blockquote>}<details><summary>Agent handoffs ({r.messages.length})</summary>{r.messages.map((m,i)=><div className="handoff" key={i}><strong>{m.role}</strong><small>{m.model}{m.skill && " · "+m.skill}</small><p>{m.body}</p></div>)}</details>
 {admin&&r.status==='review'&&<details><summary>Edit and approve manually</summary><form className="vform" onSubmit={e=>{e.preventDefault();act('approve',{id:r.id,draft:e.currentTarget.elements.copy.value})}}><label>Post<textarea name="copy" defaultValue={r.draft} maxLength={500} required/></label><button disabled={busy} className="vquiet">Approve post</button></form></details>}
 {admin&&r.status==='approved'&&ws.social&&<button className="vquiet" disabled={busy} onClick={()=>act('publish',{id:r.id,social:ws.social})}>Publish to @{ws.social}</button>}
 <Results deliveries={ws.deliveries} id={r.id}/>
 {r.receipt&&<p>Published at {r.receipt}</p>}</article>)}{view==="overview"&&<Link className="vquiet" to="/dashboard?view=campaigns">View all campaigns →</Link>}</div></>
}
