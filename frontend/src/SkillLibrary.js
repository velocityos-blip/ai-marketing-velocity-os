import React,{useState,useEffect} from 'react';
import {Link} from 'react-router-dom';

export default function SkillLibrary({apiCall}){
  const [skills,setSkills]=useState([]),[query,setQuery]=useState(''),[role,setRole]=useState(''),[busy,setBusy]=useState(''),[error,setError]=useState(''),[run,setRun]=useState(null);
  useEffect(()=>{apiCall('/api/marketing-skills').then(setSkills).catch(()=>setError('Could not load marketing skills.'))},[apiCall]);
  async function execute(slug){
    setBusy(slug);setRun(null);setError('');
    try{
      const result=await apiCall('/api/campaign-agents/run-skill',{method:'POST',headers:{'X-VOS-Client':'dashboard'},body:JSON.stringify({skill:slug})});
      setRun(result.id);
    }catch(e){try{setError(JSON.parse(e.message).detail)}catch{setError('Skill run failed. Check campaign activity before retrying.')}}
    finally{setBusy('')}
  }
  const visible=skills.filter(s=>(!role||s.role===role)&&[s.title,s.slug,s.method,...s.terms].join(' ').toLowerCase().includes(query.trim().toLowerCase()));
  return <section className="velocity skill-library"><header><p className="kicker">Marketing skills</p><h2>Agent playbooks</h2><p>Your campaign agents select skills from your brief. You can also run a skill on its own using one campaign credit.</p></header>
  <div className="vform formpair"><label>Find a skill<input type="search" placeholder="Try pricing or customer research" value={query} onChange={e=>setQuery(e.target.value)}/></label><label>Agent<select value={role} onChange={e=>setRole(e.target.value)}><option value="">All agents</option>{['CMO','Digital Marketing','Content','Analyst'].map(r=><option key={r}>{r}</option>)}</select></label></div>
  {error&&<p role="alert">{error}</p>}{run&&<p role="status">Skill run {run} complete. <Link to="/dashboard">View the result in campaign activity →</Link></p>}
  <p aria-live="polite">{skills.length?visible.length+' of '+skills.length+' skills':error?'':'Loading skills…'}</p>
  <div className="skill-list">{visible.map(s=><details key={s.slug}><summary>{s.title} <small>{s.role}</small></summary><p>{s.method}</p><h3>Deliverable</h3><p>{s.deliverable}</p><h3>Review criteria</h3><p>{s.review}</p><button className="vquiet" disabled={!!busy} onClick={()=>execute(s.slug)}>{busy===s.slug?'Running…':'Run with company brief'}</button></details>)}</div></section>
}
