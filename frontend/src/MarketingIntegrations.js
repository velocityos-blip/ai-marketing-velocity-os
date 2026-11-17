import React,{useEffect,useRef,useState} from 'react';

const descriptions={ga4:'Active users, sessions, engaged sessions, key events and revenue.',bing:'Clicks and impressions from your verified Bing site.',clarity:'Sessions, scroll depth and engagement from the last 24 hours.',youtube:'Channel views, subscribers and public videos.',x:'Followers, following and post counts.',tiktok:'Followers, likes and videos.',pinterest:'Account reach and audience metrics where available.',threads:'Profile follower count.'};
const credentials={bing:'Bing Webmaster API key',clarity:'Clarity Data Export token',threads:'Threads insights access token'};
const headers={'X-VOS-Client':'dashboard'};
const label=k=>k.replaceAll('_',' ').replace(/([a-z])([A-Z])/g,'$1 $2');
export default function MarketingIntegrations({ws,api,load}){
 const [busy,setBusy]=useState(false),[message,setMessage]=useState(''),handled=useRef(false);
 useEffect(()=>{
   const saved=sessionStorage.getItem('vos-metrics-return');
   if(!saved||handled.current)return;
   const p=new URLSearchParams(window.location.search),{source,state}=JSON.parse(saved);
   if(state!==p.get('state'))return;
   handled.current=true;sessionStorage.removeItem('vos-metrics-return');
   window.history.replaceState(null,'',window.location.pathname);
   if(!p.get('code')){setMessage('Authorization was cancelled.');return}
   setBusy(true);
   api.post('/api/marketing-integrations/finish',{source,state,code:p.get('code')},{headers}).then(load)
     .catch(e=>setMessage(e.response?.data?.detail||'Connection failed.')).finally(()=>setBusy(false));
 },[api,load]);
 async function action(op,source,fields={}){
   setBusy(true);setMessage('');
   try{
     const {data}=await api.post('/api/marketing-integrations/'+op,{source,...fields},{headers});
     if(data.url){
       sessionStorage.removeItem('vos-connect-network');sessionStorage.removeItem('vos-gsc-state');
       sessionStorage.setItem('vos-metrics-return',JSON.stringify({source,state:new URL(data.url).searchParams.get('state')}));
       window.location.assign(data.url);return
     }
     await load();
   }catch(e){setMessage(e.response?.data?.detail||'Connection failed.')}finally{setBusy(false)}
 }
 return <section className="metricBoard metricIntegrations"><header><div><small>READ-ONLY CONNECTIONS</small><h2>Analytics and social profiles</h2></div></header>
 {message&&<p role="alert">{message}</p>}
 <div className="integrationGrid">{(ws.integrations||[]).map(r=><article key={r.source}><strong>{r.name}</strong><small>{r.connected?r.problem?'Sync needs attention':'Connected':r.available?'Ready to connect':'Provider app setup required'}</small><p>{descriptions[r.source]}</p>
 {r.connected&&<><b>{r.report.account}</b><p>{r.report.period} · Last synced {new Date(r.checked*1000).toLocaleDateString()}</p>{Object.keys(r.report.metrics).length?<dl>{Object.entries(r.report.metrics).map(([k,v])=><div key={k}><dt>{label(k)}</dt><dd>{v.toLocaleString()}</dd></div>)}</dl>:<p>No measurements returned. Baseline unknown.</p>}</>}
 {ws.role==='admin'&&(r.connected?<button disabled={busy} onClick={()=>action('disconnect',r.source)}>Disconnect {r.name}</button>:r.available&&<details><summary>Connect {r.name}</summary><form className="vform" onSubmit={e=>{e.preventDefault();const f=e.currentTarget,fields=Object.fromEntries(new FormData(f));if(f.elements.key)f.elements.key.value='';action(credentials[r.source]?'connect':'start',r.source,fields)}}>
 {r.source==='ga4'&&<label>GA4 property ID<input required name="target" inputMode="numeric" pattern="[0-9]+"/></label>}
 {r.source==='bing'&&<label>Verified Bing site URL<input required name="target" type="url" defaultValue={ws.seo?.site}/></label>}
 {credentials[r.source]&&<label>{credentials[r.source]}<input required type="password" autoComplete="off" name="key"/></label>}
 <button disabled={busy}>{credentials[r.source]?'Verify and connect':'Continue to provider'}</button></form></details>)}</article>)}</div></section>;
}
