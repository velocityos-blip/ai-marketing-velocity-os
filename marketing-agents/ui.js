const $=id=>document.getElementById(id);
let mode='signup', state;
function authMode(m){mode=m;$('companyLabel').hidden=m==='login';$('auth').elements.company.required=m==='signup';$('authSubmit').textContent=m==='login'?'Sign in':'Create workspace';$('auth').elements.password.autocomplete=m==='login'?'current-password':'new-password';for(const v of ['signup','login'])$(v+'Tab').setAttribute('aria-pressed',String(v===m))}
$('signupTab').onclick=()=>authMode('signup');$('loginTab').onclick=()=>authMode('login');authMode(mode);
function el(tag,text,cls){const e=document.createElement(tag);if(text!=null)e.textContent=text;if(cls)e.className=cls;return e}
function btn(text,fn){const b=el('button',text);b.onclick=()=>fn(b);return b}
function form(id,route,convert=x=>x){$(id).onsubmit=async e=>{e.preventDefault();const f=e.currentTarget;const ok=await act(route(),convert(Object.fromEntries(new FormData(f))),f.querySelector('button'));if(ok)f.reset()}}
async function act(path,data,button){
 button.disabled=true;$('notice').textContent=path==='run'?'Agents are preparing your campaign…':'Saving…';
 try{const r=await fetch('/api/'+path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});const x=await r.json();if(!r.ok)throw Error(x.error);await load();$('notice').textContent='';return true}
 catch(e){$('notice').textContent=e.message;try{await load()}catch{}return false}finally{button.disabled=false}
}
form('auth',()=>mode);form('run',()=>'run',x=>({...x,budget:Number(x.budget)}));form('member',()=>'member');form('connect',()=>'connect');
$('logout').onclick=()=>act('logout',{},$('logout'));$('disconnect').onclick=()=>act('disconnect',{},$('disconnect'));
async function load(){
 const res=await fetch('/api/state');if(!res.ok)throw Error('Could not load your workspace.');state=await res.json();
 $('welcome').hidden=state.signedIn;$('workspace').hidden=$('logout').hidden=!state.signedIn;
 if(!state.signedIn){$('runs').replaceChildren();return}
 const admin=state.role==='admin';$('companyName').textContent=state.company;$('usage').textContent=state.tier.toUpperCase()+'  ·  '+state.used+' of '+state.limit+' runs this month  ·  '+state.role+'  ·  Company #'+state.companyId;
 $('settings').hidden=!admin;$('connected').textContent=state.social?'Connected: @'+state.social+' on mastodon.social':'No publishing account connected.';$('disconnect').hidden=!state.social;
 const feed=$('runs');feed.replaceChildren();if(!state.runs.length)feed.append(el('p','Your first campaign and agent handoffs will appear here.'));
 for(const r of state.runs){const a=el('article');feed.append(a);a.append(el('span',r.status,'pill'),el('p','#'+r.id+' · '+r.created+' UTC'),el('h2',r.brief.goal),el('p',r.brief.audience+' · Budget: USD '+r.brief.budget));
 for(const m of r.messages){const d=el('details');d.append(el('summary',m.role+' · '+m.model),el('p',m.body,'output'));a.append(d)}
 if(r.draft){a.append(el('h3','Social post'));if(admin&&r.status==='review'){const t=el('textarea');t.value=r.draft;t.maxLength=500;t.setAttribute('aria-label','Post to approve');a.append(t,btn('Approve edited post',b=>act('approve',{id:r.id,draft:t.value},b)))}else a.append(el('p',r.draft,'output'))}
 if(r.status==='approved'&&admin&&state.social){const social=state.social;a.append(btn('Publish to @'+social+' on mastodon.social',b=>act('publish',{id:r.id,social},b)))}
 if(r.receipt)a.append(el('p','Published: '+r.receipt));
 }}
load().catch(e=>$('notice').textContent=e.message);
