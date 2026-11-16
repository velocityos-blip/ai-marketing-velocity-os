import React, { useCallback, useEffect, useState } from 'react';
const stamp=t=>new Date(t*1000).toLocaleString(undefined,{dateStyle:'medium',timeStyle:'short'});
export default function CampaignDesk({api}){
 const [ws,setWs]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[editing,setEditing]=useState(false);
 const load=useCallback(async()=>setWs((await api.get('/api/campaign-agents')).data),[api]);
 useEffect(()=>{const refresh=()=>load().catch(()=>setError('Could not load your workspace. Refresh to try again.'));refresh();const id=setInterval(()=>{if(!document.hidden)refresh()},5000);return ()=>clearInterval(id)},[load]);
 async function act(op,data,done){setBusy(true);setError('');try{await api.post('/api/campaign-agents/'+op,data,{headers:{'X-VOS-Client':'dashboard'}});await load();done?.()}catch(e){setError(e.response?.data?.detail || 'Could not save the change. Please try again.')}finally{setBusy(false)}}
 if(!ws)return <p role="status">{error||'Loading your workspace…'}</p>;
 const profile=ws.autopilot, admin=ws.role==='admin', previous=profile?.brief||ws.runs[0]?.brief||{};
 function configure(e){e.preventDefault();const f=Object.fromEntries(new FormData(e.currentTarget));act('configure',{...f,budget:Number(f.budget),destination:f.autopublish?ws.social:null},()=>setEditing(false))}
 return <><p className="kicker">{ws.company}</p><div className="desktitle"><h1>Campaign workspace</h1><span className="tag">{profile?.enabled?'Automation on':profile?'Paused':'Setup'}</span></div>
 {error&&<p className="notice" role="alert">{error}</p>}
 <div className="deskgrid"><section className="panel"><h2>{profile&&!editing?'Company brief':'Give your agents a brief'}</h2>
 {admin&&(!profile||editing)?<form className="vform" onSubmit={configure}>
 {[['offer','What do you sell?','Inventory software for independent shops',200],['audience','Who do you want to reach?','Independent florists',200],['goal','What should the campaign achieve?','Book 10 demos in 30 days',600]].map(([k,label,hint,max])=><label key={k}>{label}<input name={k} required maxLength={max} defaultValue={previous[k]} placeholder={hint}/></label>)}
 <div className="formpair"><label>Planning budget (USD)<input name="budget" type="number" min="0" max="100000000" step="1" required defaultValue={previous.budget||0}/></label><label>Campaign frequency<select name="cadence" defaultValue={profile?.cadence||'weekly'}><option value="weekly">Every week</option><option value="once">Once</option></select></label></div>
 {ws.social&&<label className="check"><input type="checkbox" name="autopublish" defaultChecked={profile?.destination===ws.social}/> Automatically publish posts cleared by the Analyst to @{ws.social}</label>}
 <small>The first campaign starts immediately. Your budget guides planning; this workflow uses organic social.</small>
 <div className="actions"><button className="vprimary" disabled={busy}>{profile?.enabled?'Save changes':'Start automation'} →</button>{editing&&<button type="button" onClick={()=>setEditing(false)}>Cancel</button>}</div></form>:
 profile?<><h3>{profile.brief.goal}</h3><p>{profile.brief.offer} · {profile.brief.audience}</p><dl><dt>Frequency</dt><dd>{profile.cadence==='weekly'?'Weekly':'One campaign'}</dd><dt>Budget</dt><dd>USD {profile.brief.budget}</dd><dt>Delivery</dt><dd>{profile.destination?'Auto-publish to @'+profile.destination:'Save drafts'}</dd></dl>{admin&&<div className="actions"><button className="vquiet" onClick={()=>setEditing(true)}>{profile.enabled?'Edit brief':'Resume automation'}</button>{!!profile.enabled&&<button disabled={busy} onClick={()=>act('pause',{})}>Pause</button>}</div>}</>:<p>A company admin can activate automation here.</p>}
 </section><aside className="panel control"><h2>Automation status</h2><p aria-live="polite">{profile?.note||'Waiting for the company brief.'}</p>
 <dl><dt>Next campaign</dt><dd>{profile?.due?stamp(profile.due):'None scheduled'}</dd><dt>Runs this month</dt><dd>{ws.used} / {ws.limit}</dd></dl>
 {admin&&<details><summary>Publishing connection</summary><p>{ws.social?'Connected to @'+ws.social:'Connect Mastodon to enable automatic publishing. You can also keep drafts private.'}</p><form className="vform" onSubmit={e=>{e.preventDefault();const f=e.currentTarget;act('connect',{token:f.elements.token.value},()=>f.reset())}}><label>Mastodon.social token<input name="token" type="password" required autoComplete="off"/></label><button className="vquiet" disabled={busy}>Connect account</button></form>{ws.social&&<button onClick={()=>act('disconnect',{})} disabled={busy}>Disconnect</button>}</details>}</aside></div>
 <h2 className="feedtitle">Campaign activity</h2>{!ws.runs.length&&<p className="empty">Your agents’ work will appear here as each handoff finishes.</p>}
 {ws.runs.map(r=><article className="panel run" key={r.id}><div className="runhead"><small>Campaign {r.id} · {r.created} UTC</small><span className="tag">{r.status}</span></div><h3>{r.brief.goal}</h3>
 {r.draft&&<blockquote>{r.draft}</blockquote>}<details><summary>Agent handoffs ({r.messages.length}/4)</summary>{r.messages.map(m=><div className="handoff" key={m.role}><strong>{m.role}</strong><small>{m.model}</small><p>{m.body}</p></div>)}</details>
 {admin&&r.status==='review'&&<details><summary>Edit and approve manually</summary><form className="vform" onSubmit={e=>{e.preventDefault();act('approve',{id:r.id,draft:e.currentTarget.elements.copy.value})}}><label>Post<textarea name="copy" defaultValue={r.draft} maxLength={500} required/></label><button disabled={busy} className="vquiet">Approve post</button></form></details>}
 {admin&&r.status==='approved'&&ws.social&&<button className="vquiet" disabled={busy} onClick={()=>act('publish',{id:r.id,social:ws.social})}>Publish to @{ws.social}</button>}
 {r.receipt&&<p>Published at {r.receipt}</p>}</article>)}</>
}
