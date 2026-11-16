import React, {useEffect,useRef,useState} from 'react';

const names={linkedin:'LinkedIn',instagram:'Instagram',facebook:'Facebook'};
const marks={linkedin:'in',instagram:'◎',facebook:'f'};
const headers={'X-VOS-Client':'dashboard'};
export default function SocialChannels({api,ws,load}){
 const [message,setMessage]=useState(''),[pending,setPending]=useState(null),[busy,setBusy]=useState(false);
 const handled=useRef(false);
 useEffect(()=>{
   if(handled.current)return;
   const params=new URLSearchParams(window.location.search);
   const network=sessionStorage.getItem('vos-connect-network');
   if(!network||!params.has('state'))return;
   handled.current=true;
   sessionStorage.removeItem('vos-connect-network');
   window.history.replaceState(null,'',window.location.pathname);
   if(!params.get('code')){setMessage('Authorization was cancelled.');return}
   setBusy(true);
   api.post('/api/social/finish',{network,state:params.get('state'),code:params.get('code')},{headers})
    .then(({data})=>data.choices.length?setPending({network,choices:data.choices}):setMessage('No eligible company accounts were returned. Check your provider role and permissions.'))
    .catch(e=>setMessage(e.response?.data?.detail||'Authorization failed.')).finally(()=>setBusy(false));
 },[api]);
 async function action(network,op,key){
   setBusy(true);setMessage('');
   try{
     const {data}=await api.post('/api/social/'+op,{network,key},{headers});
     if(op==='start'){sessionStorage.setItem('vos-connect-network',network);window.location.assign(data.url);return}
     setPending(null);await load();
   }catch(e){setMessage(e.response?.data?.detail||'Unable to update this account.')}
   finally{setBusy(false)}
 }
 return <section className="channels"><h2>Publishing channels</h2><p>Connect a company account to publish cleared campaigns and collect performance automatically.</p>
 <div className="networkgrid">{(ws.channels||[]).map(c=><section className={'network '+c.network} key={c.network}><div className="networkhead"><span aria-hidden="true">{marks[c.network]}</span><strong>{names[c.network]}</strong></div>
 <small>{c.problem||c.label||(c.available?'Ready to connect':'Provider setup required')}</small>{ws.role==='admin'&&<div>{(!c.label||c.problem)&&<button disabled={busy||!c.available} onClick={()=>action(c.network,'start')}>{c.label?'Reconnect':'Connect account'} ↗</button>}
 {c.label&&<button disabled={busy} onClick={()=>action(c.network,'disconnect')}>Disconnect</button>}</div>}</section>)}</div>
 {message&&<p role="status">{message}</p>}{pending&&<section className="panel"><h3>Choose a {names[pending.network]} destination</h3><p>Enable automatic publishing and analytics for the selected account.</p>{pending.choices.map(c=><button className="vquiet" disabled={busy} key={c.key} onClick={()=>action(pending.network,'select',c.key)}>Enable for {c.label}</button>)}</section>}</section>
}
export function Results({deliveries,id}){
 const posts=(deliveries||[]).filter(p=>p.run===id);
 if(!posts.length)return null;
 return <section className="results"><h4>Channel results</h4>{posts.map(p=><div key={p.network}><strong>{names[p.network]}</strong> · {p.status}<p>{p.metrics?Object.entries(p.metrics).map(([k,v])=>k+': '+v).join(' · '):p.remote?'Awaiting first measurement':''}</p></div>)}</section>
}
