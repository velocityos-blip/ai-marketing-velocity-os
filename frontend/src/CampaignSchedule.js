import React,{useState} from 'react';

const dayKey=d=>[d.getFullYear(),String(d.getMonth()+1).padStart(2,'0'),String(d.getDate()).padStart(2,'0')].join('-');
const clock=d=>[d.getHours(),d.getMinutes()].map(v=>String(v).padStart(2,'0')).join(':');
const dateOf=p=>new Date(p.due*1000);
const channel=p=>p.network==='private'?'Private draft':p.network;
export default function CampaignSchedule({ws,act,busy}){
 const [month,setMonth]=useState(()=>new Date(new Date().getFullYear(),new Date().getMonth(),1));
 const [day,setDay]=useState(dayKey(new Date())),[edit,setEdit]=useState(null),[when,setWhen]=useState(''),[draft,setDraft]=useState('');
 const posts=ws.calendar||[], selected=posts.filter(p=>dayKey(dateOf(p))===day);
 const drafts=ws.runs.filter(r=>r.status==='review'&&r.draft&&!posts.some(p=>p.run===r.id));
 const admin=ws.role==='admin';
 const active=ws.runs.filter(r=>r.status==='working'&&!r.brief.skill);
 const pending=active.flatMap(r=>{
   const plan=[...r.messages].reverse().find(m=>m.assignments);
   const current=r.brief.active_task;
   if(!plan||!current)return [];
   const work=[...plan.assignments,{role:'Analyst',instruction:'Check the draft and evidence'},{role:'CMO',instruction:'Make the release decision'}];
   const idx=work.findIndex(t=>t.role===current.role);
   if(current.role==='CMO'&&current.task.startsWith('Choose'))return [];
   return idx<0?[]:work.slice(idx+1).map(t=>({...t,run:r.id}));
 });
 function choose(value){setDay(value);setEdit(null);setDraft('');setWhen(value+'T10:00')}
 function move(delta){const next=new Date(month.getFullYear(),month.getMonth()+delta,1);setMonth(next);choose(dayKey(next))}
 function reschedule(post){setEdit(post);const d=dateOf(post);setWhen(dayKey(d)+'T'+clock(d))}
 function save(e){
   e.preventDefault();const d=new Date(when);
   const payload=edit?{id:edit.id,previous_due:edit.due}:{run:Number(draft)};
   act(edit?'reschedule-post':'plan-private',{...payload,due:Math.floor(d.getTime()/1000)},()=>{setMonth(new Date(d.getFullYear(),d.getMonth(),1));choose(dayKey(d))})
 }
 const days=new Date(month.getFullYear(),month.getMonth()+1,0).getDate();
 return <div className="scheduleLayout"><section className="opsBoard"><header><div><small>CAMPAIGN OPERATIONS</small><h2>Agent queue</h2></div></header>
 {active.map(r=><p key={r.id}><b>{r.brief.active_task?.role||'AI CMO'} · working</b><br/>{r.brief.active_task?.task||'Preparing the campaign'}</p>)}
 {pending.length>0&&<ol>{pending.map(t=><li key={t.run+t.role}><strong>{t.role}</strong><p>{t.instruction}</p></li>)}</ol>}
 {!pending.length&&<p>{active.length?'Waiting for the next assignment.':'No agent tasks are waiting.'}</p>}
 {ws.autopilot?.enabled&&ws.autopilot.due&&<p><b>Next campaign brief</b><br/>{new Date(ws.autopilot.due*1000).toLocaleString()}</p>}</section>
 <section className="auditBoard"><header><div><small>CONTENT SCHEDULE</small><h2>Publishing calendar</h2></div></header>
 <div className="monthNav"><button aria-label="Previous month" onClick={()=>move(-1)}>‹</button><strong>{month.toLocaleString(undefined,{month:'long',year:'numeric'})}</strong><button aria-label="Next month" onClick={()=>move(1)}>›</button></div>
 <div className="monthGrid">{['Su','Mo','Tu','We','Th','Fr','Sa'].map(w=><small key={w}>{w}</small>)}{Array.from({length:month.getDay()},(_,i)=><span key={'blank'+i}/>)}{Array.from({length:days},(_,i)=>{const d=new Date(month.getFullYear(),month.getMonth(),i+1),key=dayKey(d),count=posts.filter(p=>dayKey(dateOf(p))===key&&p.state!=='cancelled').length;return <button key={key} aria-label={d.toLocaleDateString()+' · '+count+' posts'} aria-pressed={key===day} onClick={()=>choose(key)}>{i+1}{count>0&&<b>{count}</b>}</button>})}</div>
 <h3>{new Date(day+'T12:00').toLocaleDateString(undefined,{weekday:'long',month:'short',day:'numeric'})}</h3>
 {selected.map(p=><div className="postSlot" key={p.id}><strong>{clock(dateOf(p))} · {channel(p)}</strong><small>{p.state}</small><p>{p.draft}</p>{admin&&p.state==='scheduled'&&<div className="actions"><button disabled={busy} onClick={()=>reschedule(p)}>Change date</button><button disabled={busy} onClick={()=>act('cancel-post',{id:p.id,previous_due:p.due},()=>setEdit(null))}>Cancel post</button></div>}</div>)}
 {!selected.length&&<p>No posts on this date.</p>}
 {admin&&!edit&&drafts.length>0&&<label>Plan a private draft<select value={draft} onChange={e=>{setDraft(e.target.value);setWhen(day+'T10:00')}}><option value="">Choose campaign</option>{drafts.map(r=><option key={r.id} value={r.id}>Campaign {r.id} · {r.draft.slice(0,45)}</option>)}</select></label>}
 {admin&&(edit||draft)&&<form className="vform" onSubmit={save}><label>Scheduled time ({Intl.DateTimeFormat().resolvedOptions().timeZone})<input type="datetime-local" required value={when} onChange={e=>setWhen(e.target.value)}/></label><button disabled={busy}>{edit?'Save new date':'Schedule private draft'}</button></form>}
 </section></div>;
}
