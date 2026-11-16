import React, { useCallback, useEffect, useState } from 'react';

const fieldStyle = 'block border rounded px-3 py-2 w-full';
const buttonStyle = 'bg-primary-600 text-white rounded px-4 py-2 disabled:opacity-50';

export default function CampaignDesk({ api }) {
  const [workspace, setWorkspace] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState('');
  const load = useCallback(async () => {
    const response = await api.get('/api/campaign-agents');
    setWorkspace(response.data);
  }, [api]);
  useEffect(() => {
    load().catch(e => setError(e.response?.data?.detail || 'Could not load campaigns.'));
  }, [load]);

  async function act(action, data, form) {
    setBusy(action);
    setError('');
    try {
      await api.post('/api/campaign-agents/' + action, data, { headers: { 'X-VOS-Client': 'dashboard' } });
      form?.reset();
    } catch (e) {
      setError(e.response?.data?.detail || 'Request interrupted. Check campaign activity before trying again.');
    } finally {
      try { await load(); } catch { setError('Could not refresh campaign activity. Reload your dashboard.'); }
      setBusy('');
    }
  }
  function submit(event, action, extra = {}) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = Object.fromEntries(new FormData(form));
    if (action === 'run') data.budget = Number(data.budget);
    act(action, { ...data, ...extra }, form);
  }
  const admin = workspace?.role === 'admin';
  return <section aria-labelledby="agents-title" className="bg-white rounded-xl shadow-md p-6 mb-8">
    <h2 id="agents-title" className="text-2xl font-bold">Campaign agents</h2>
    {error && <p role="alert" className="text-red-700 my-3">{error}</p>}
    {workspace && <>
      <p className="my-3">{workspace.company} · {workspace.used} of {workspace.limit} campaign runs this month</p>
      <form onSubmit={e => submit(e, 'run')} className="grid md:grid-cols-2 gap-4">
        {[['goal','Campaign goal',600],['audience','Target audience',200],['offer','Product or offer',200]].map(([key,label,max]) =>
          <label key={key}>{label}<input required name={key} maxLength={max} className={fieldStyle}/></label>)}
        <label>Budget (USD)<input name="budget" type="number" min="0" max="100000000" step="1" defaultValue="0" required className={fieldStyle}/></label>
        <button className={buttonStyle} disabled={!!busy || workspace.used >= workspace.limit}>{busy === 'run' ? 'Agents are working…' : 'Run campaign'}</button>
      </form>
      {admin && <details className="mt-5"><summary>Publishing account</summary>
        <p>{workspace.social ? '@'+workspace.social+' on mastodon.social' : 'Connect a mastodon.social account to publish approved posts.'}</p>
        {workspace.social && <button disabled={!!busy} onClick={() => act('disconnect', {})}>Disconnect</button>}
        <form className="my-2 flex gap-3" onSubmit={e => submit(e, 'connect')}>
          <label>Access token<input className={fieldStyle} type="password" name="token" autoComplete="off" required /></label>
          <button disabled={!!busy}>Verify account</button></form></details>}
      <h3 className="text-lg font-semibold mt-6">Campaign activity</h3>
      {!workspace.runs.length && <p>Your campaigns will appear here.</p>}
      {workspace.runs.map(run => <article className="border-t py-4" key={run.id}>
        <h4 className="font-semibold">{run.brief.goal}</h4><p>{run.status} · {run.created} UTC</p>
        {run.messages.map(message => <details className="my-2" key={message.role}><summary>{message.role} · {message.model}</summary>
          <p className="whitespace-pre-wrap">{message.body}</p></details>)}
        {admin && run.status === 'review' ? <form onSubmit={e => submit(e, 'approve', {id: run.id})}>
          <label>Post for approval<textarea className={fieldStyle} name="draft" required maxLength={500} defaultValue={run.draft}/></label>
          <button className={buttonStyle} disabled={!!busy}>Approve post</button></form> : <p>{run.draft}</p>}
        {admin && workspace.social && run.status === 'approved' && <button disabled={!!busy} onClick={() => act('publish',{id:run.id,social:workspace.social})}>Publish to @{workspace.social}</button>}
        {run.receipt && <p>Published at {run.receipt}</p>}
      </article>)}
    </>}
  </section>;
}
