import React,{useState} from 'react';
import {Link,useLocation} from 'react-router-dom';
import './workspace.css';

export const workspaceSections=[
 ['overview','Overview','◫'],['campaigns','Campaigns','▤'],['agents','AI team','◈'],
 ['calendar','Publishing calendar','▦'],['analytics','Analytics','▥'],['website','Website & SEO','◎'],
 ['integrations','Integrations','⊞'],['settings','Company settings','⚙']
];
const secondary=[['/ai-tools','Skills library','◇'],['/tasks','Team tasks','☷'],['/team','Members','♙'],['/subscription','Billing','▣']];
export default function WorkspaceShell({user,logout,children}){
 const location=useLocation(),[open,setOpen]=useState(false);
 const section=new URLSearchParams(location.search).get('view')||'overview';
 const title=location.pathname==='/dashboard'?(workspaceSections.find(s=>s[0]===section)?.[1]||'Overview'):secondary.find(s=>s[0]===location.pathname)?.[1]||'Workspace';
 return <div className="velocity workspaceShell">
 <a className="skipWorkspace" href="#workspace-content">Skip to content</a>
 {open&&<button className="workspaceScrim" aria-label="Close navigation" onClick={()=>setOpen(false)}/>}
 <aside className={'workspaceSidebar '+(open?'isOpen':'')}>
 <Link to="/dashboard" className="workspaceLogo" onClick={()=>setOpen(false)}><span>V</span><div>Velocity OS<small>MARKETING WORKSPACE</small></div></Link>
 <nav aria-label="Workspace navigation"><p>WORKSPACE</p>{workspaceSections.map(([key,label,icon])=><Link key={key} to={'/dashboard?view='+key} aria-current={location.pathname==='/dashboard'&&section===key?'page':undefined} onClick={()=>setOpen(false)}><span aria-hidden="true">{icon}</span>{label}</Link>)}
 <p>ORGANIZATION</p>{secondary.map(([url,label,icon])=><Link key={url} to={url} aria-current={location.pathname===url?'page':undefined} onClick={()=>setOpen(false)}><span aria-hidden="true">{icon}</span>{label}</Link>)}</nav>
 <div className="workspaceIdentity"><strong>{user?.full_name||user?.name||'Your account'}</strong><small>{user?.email}</small><div><a href="https://github.com/velocityos-blip/vos" target="_blank" rel="noreferrer">GitHub ↗</a><button onClick={logout}>Sign out</button></div></div>
 </aside>
 <div className="workspaceBody"><header className="workspaceTopbar"><button className="workspaceMenu" aria-label="Open navigation" aria-expanded={open} onClick={()=>setOpen(!open)}>☰</button><span>Workspace <b>/</b> <strong>{title}</strong></span><Link to="/dashboard?view=settings">Manage automation →</Link></header>
 <main id="workspace-content" className="workspaceContent" tabIndex={-1}>{children}</main></div>
 </div>;
}
