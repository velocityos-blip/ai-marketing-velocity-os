import React, { useState } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import CampaignDesk from './CampaignDesk';
import './experience.css';

const repository = 'https://github.com/velocityos-blip/vos';
export const roles = [
  ['CMO','Strategy','Sets the direction and delegates the brief.'],
  ['Digital Marketing','Channels','Designs the channel experiment and success metric.'],
  ['Content','Studio','Writes a post for your audience and offer.'],
  ['Analyst','Review','Reviews the copy and flags issues before publication.']
];
export function Github(){return <a className="repo" href={repository} target="_blank" rel="noreferrer">GitHub ↗</a>}
function Header({user,logout}){return <header className="vbar"><Link to="/" className="wordmark"><i aria-hidden="true">V</i>Velocity OS</Link><nav><Github/>{user?<><Link to="/team">Team</Link><button onClick={logout}>Sign out</button></>:<Link to="/login">Sign in</Link>}</nav></header>}
export function Home({user}){
  if(user)return <Navigate to="/dashboard" replace/>;
  return <div className="velocity"><Header/><main className="vwrap"><div className="vhero"><div>
    <p className="kicker">Open-source marketing automation</p><h1>Your marketing team<br/><em>on autopilot.</em></h1>
    <p className="lede">Tell us what you sell, who you serve, and what you want to achieve. Four agents turn that brief into a campaign and keep it running on your schedule.</p>
    <div className="actions"><Link className="vprimary" to="/register">Set up my workspace <span>→</span></Link><a href={repository}>Explore the source ↗</a></div></div>
    <aside className="flight"><div className="orbitfield" aria-hidden="true"><i/><i/><i/><b>V</b></div><div className="flighthead"><span>Campaign workflow</span><span className="signal">Weekly example</span></div>
    <div className="briefsample"><small>COMPANY BRIEF</small><strong>Book demos for a florist inventory app</strong></div>
    <ol>{roles.map(([name,stage],i)=><li key={name}><b>{String(i+1).padStart(2,'0')}</b><strong>{name}</strong><span>{stage}</span></li>)}</ol>
    <div className="flightfoot">Output <strong>Organic campaign + social post</strong></div></aside></div>
    <section className="vsteps"><div><h2>One company brief</h2><p>Save your audience, offer, goal, and budget once.</p></div><div><h2>A team that follows through</h2><p>Your agents work in the background, even after you close the dashboard.</p></div><div><h2>Your publishing rules</h2><p>Choose which company accounts receive reviewed campaigns and track post performance from your workspace.</p></div></section></main><Footer/></div>
}
function Footer(){return <footer className="vfoot"><span>Velocity OS</span><a href={repository}>Source code on GitHub ↗</a></footer>}
export function Account({mode,auth,basePath}){
 const signup=mode==='register', navigate=useNavigate(),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 if(auth.user)return <Navigate to="/dashboard" replace/>;
 async function submit(e){e.preventDefault();const data=Object.fromEntries(new FormData(e.currentTarget));setBusy(true);setError('');
 try{if(signup)await auth.register(data.email,data.password,data.name,data.company);else await auth.login(data.email,data.password);navigate('/dashboard')}
 catch(err){const msg=err.response?.data?.detail;setError(typeof msg==='string'?msg:'Check your details and try again.')}finally{setBusy(false)}}
 return <div className="velocity"><Header/><main className="account"><p className="kicker">Company workspace</p><h1>{signup?'Set up your team.':'Welcome back.'}</h1><p>{signup?'Create your workspace, then give your agents their brief.':'Sign in to see your campaigns and automation settings.'}</p>
 <form onSubmit={submit} className="vform">{signup&&<><label>Your name<input name="name" required autoComplete="name"/></label><label>Company name<input name="company" required maxLength="80" autoComplete="organization"/></label></>}
 <label>Work email<input type="email" name="email" required autoComplete="username"/></label><label>Password<input type="password" name="password" required minLength={signup?12:1} autoComplete={signup?'new-password':'current-password'}/></label>
 {error&&<p role="alert">{error}</p>}<button disabled={busy} className="vprimary">{busy?'Please wait…':signup?'Create workspace →':'Sign in →'}</button></form>
 <button className="vquiet" onClick={()=>{window.location.href='https://auth.emergentagent.com/?redirect='+encodeURIComponent(window.location.origin+basePath+'/dashboard')}}>Continue with Google</button>
 <p>{signup?'Already registered? ':'New to VOS? '}<Link to={signup?'/login':'/register'}>{signup?'Sign in':'Create a workspace'}</Link></p></main><Footer/></div>
}
export function Desk({auth,api}){return <CampaignDesk api={api}/>}
