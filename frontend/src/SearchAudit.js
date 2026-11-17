import React,{useEffect,useRef,useState} from 'react';
const headers={'X-VOS-Client':'dashboard'};
export default function SearchAudit({seo,admin,api,load}){
  const [busy,setBusy]=useState(false),[error,setError]=useState('');
  const handled=useRef(false);
  useEffect(()=>{
    const p=new URLSearchParams(window.location.search);
    if(handled.current||!p.has('state')||sessionStorage.getItem('vos-gsc-state')!==p.get('state'))return;
    handled.current=true;sessionStorage.removeItem('vos-gsc-state');window.history.replaceState(null,'',window.location.pathname);
    if(!p.has('code')){setError('Google authorization was cancelled.');return}
    setBusy(true);
    api.post('/api/search-audit/finish',{state:p.get('state'),code:p.get('code')},{headers}).then(load)
      .catch(e=>setError(e.response?.data?.detail||'Could not connect Google.')).finally(()=>setBusy(false));
  },[api,load]);
  async function action(op,data={}){
    setBusy(true);setError('');
    try{
      const result=await api.post('/api/search-audit/'+op,data,{headers});
      if(op==='start'){
        sessionStorage.removeItem('vos-connect-network');
        sessionStorage.setItem('vos-gsc-state',new URL(result.data.url).searchParams.get('state'));
        window.location.assign(result.data.url);
      }else await load();
    }catch(e){setError(e.response?.data?.detail||'Could not update website settings.')}
    finally{setBusy(false)}
  }
  if(!seo)return null;
  const report=seo.report;
  return <section className="panel run"><h2>Website and search performance</h2><p>VOS checks up to six public pages weekly and uses the findings in scheduled campaigns. Connect Google to add search queries, clicks and impressions to the agents’ brief.</p>
    {admin&&<form className="vform" key={seo.site} onSubmit={e=>{e.preventDefault();action('save',{site:e.currentTarget.elements.site.value})}}>
      <label>Company website<input name="site" defaultValue={seo.site} placeholder="https://company.com" required/></label><div className="actions"><button className="vquiet" disabled={busy}>Save website</button></div></form>}
    {seo.site&&<><p>{seo.site} · {seo.property?'Search Console connected to '+seo.property:seo.available?'Search Console disconnected':'Google OAuth app setup required'}</p>
    {admin&&<div className="actions">{seo.property?<button disabled={busy} onClick={()=>action('disconnect')}>Disconnect Google</button>:<button className="vquiet" disabled={busy||!seo.available} onClick={()=>action('start')}>Connect Google Search Console</button>}<button disabled={busy} onClick={()=>action('remove')}>Stop website audits</button></div>}
    {report?<details><summary>Latest audit · {new Date(report.checked*1000).toLocaleDateString()} · {report.crawl.pages.length} pages</summary><p>{report.crawl.status}. Search Console: {report.search_console.status}.</p>
    {report.crawl.pages.map(p=><p key={p.url}>{p.url} · {p.status} · {p.findings.join(', ')||'No issues in sampled checks'}</p>)}
    {report.search_console.rows?.map((r,i)=><p key={i}>{r.keys.join(' · ')} · {r.clicks} clicks · {r.impressions} impressions</p>)}</details>:<p role="status">First audit queued.</p>}</>}
    {error&&<p role="alert">{error}</p>}</section>
}
