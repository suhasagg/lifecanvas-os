// LifeCanvasOS web client entry: authentication, routing and event delegation.
import { $, $$, api, post, put, del, esc, toast, state, city, country, openDrawer, closeDrawer, cardDetail, errorBox, loading, pill, ago, clock, empty } from './js/core.js';
import { budgetHtml, PAGES, NAMES, setTab, studio, actions, actionDraft, connections, circles, assistant, orchestra, memory, planner, travel, label } from './js/pages.js';
import { startRun, followRun, loadRun, runHtml, decide, approvalHtml } from './js/runs.js';

// ---------------------------------------------------------------------------------------------- auth
function authScreen(mode = 'login', error = '') {
  const reg = mode === 'register';
  $('#shell').classList.add('hidden');
  const box = $('#auth');
  box.classList.remove('hidden');
  box.innerHTML = `<div class="authcard"><div class="brand"><div class="logo">✳</div><div>life<span>canvas.</span><small>OS · SUNSHINE EDITION</small></div></div>
    <h1>${reg ? 'Create your workspace' : 'Welcome back, sunshine'}</h1><p class="small">Your plans, memory and approvals are private to your account.</p>
    ${error ? `<div class="errorbox" role="alert"><p>${esc(error)}</p></div>` : ''}
    <form id="authform" data-mode="${mode}">${reg ? '<div class="field"><label for="a-name">Name</label><input id="a-name" autocomplete="name" maxlength="60" required></div>' : ''}
    <div class="field"><label for="a-email">Email</label><input id="a-email" type="email" autocomplete="email" required maxlength="254"></div>
    <div class="field"><label for="a-pass">Password${reg ? ' (8+ characters)' : ''}</label><input id="a-pass" type="password" autocomplete="${reg ? 'new-password' : 'current-password'}" required minlength="${reg ? 8 : 1}" maxlength="200"></div>
    <button class="primary wide">${reg ? 'Create account ↗' : 'Sign in ↗'}</button></form>
    <p class="small center">${reg ? 'Already have an account?' : 'New here?'} <button class="linkbtn" data-authmode="${reg ? 'login' : 'register'}">${reg ? 'Sign in' : 'Create an account'}</button></p></div>
    <div class="authart" aria-hidden="true"></div>`;
  $(reg ? '#a-name' : '#a-email').focus();
}

async function boot() {
  try {
    state.boot = await api('bootstrap');
  } catch (e) {
    if (e.status === 401) return authScreen();
    $('#auth').classList.remove('hidden');
    $('#auth').innerHTML = `<div class="authcard">${errorBox(e, 'data-reload')}</div>`;
    return;
  }
  state.user = state.boot.user;
  $('#auth').classList.add('hidden');
  $('#shell').classList.remove('hidden');
  $('#username').textContent = state.user.name;
  $('#useremail').textContent = state.user.email;
  $('#avatar').textContent = state.user.name.slice(0, 2).toUpperCase();
  const home = (state.boot.preferences.home_city || []).slice(-1)[0] || state.boot.profile?.city || localStorage.getItem('lc-city') || '';
  $('#city').value = home;
  $('#country').value = localStorage.getItem('lc-country') || '';
  badges();
  go(location.hash.slice(1) in PAGES ? location.hash.slice(1) : 'today');
}

function badges() {
  const c = state.boot.provider_counts;
  const live = (c.connected_verified || 0) + (c.configured_unverified || 0);
  $('#modetext').textContent = `${live} live sources · ${c.configuration_required || 0} need setup`;
  $('#mode').classList.toggle('live', live > 0);
  const b = $('#pendingbadge');
  b.textContent = state.boot.pending_approvals;
  b.classList.toggle('hidden', !state.boot.pending_approvals);
}
async function refreshBadges() { try { state.boot = await api('bootstrap'); badges(); } catch { /* handled by the auth listener */ } }

// ---------------------------------------------------------------------------------------------- routing
async function go(page, { focus = true } = {}) {
  if (!(page in PAGES)) page = 'today';
  state.page = page;
  state.stream?.close();
  $$('#nav button, #nav2 button').forEach(b => b.classList.toggle('active', b.dataset.page === page));
  $('#crumb').textContent = NAMES[page];
  document.title = `${NAMES[page]} — LifeCanvasOS`;
  if (location.hash.slice(1) !== page) history.replaceState(null, '', '#' + page);
  const view = $('#view');
  view.innerHTML = PAGES[page].html();
  if (focus) window.scrollTo(0, 0);
  try { await PAGES[page].load?.(); } catch (e) { if (state.page === page && e.status !== 401) view.insertAdjacentHTML('beforeend', errorBox(e, `data-go="${page}"`)); }
}

// ---------------------------------------------------------------------------------------------- flows
async function runFromConcierge(q) {
  if (state.page !== 'assistant') await go('assistant');
  const chat = $('#chat');
  chat.insertAdjacentHTML('beforeend', `<div class="bubble user">${esc(q)}</div><div class="bubble" id="waiting"><span class="pulse">✦</span> Planning and dispatching specialists… <button class="linkbtn" id="cancelwait">Cancel</button></div>`);
  chat.scrollTop = chat.scrollHeight;
  $('#askbtn').disabled = true;
  $('#answer').innerHTML = '';
  try {
    const started = await post('runs', { goal: q, city: city(), country: country(), workflow: 'auto', thread_id: state.thread });
    state.thread = started.thread_id;
    $('#cancelwait').dataset.cancel = started.run_id;
    const out = await followRun(started.run_id, { traceEl: $('#trace'), pipelineEl: $('#pipeline') });
    if (state.page !== 'assistant' || !out) return;
    $('#waiting')?.remove();
    chat.insertAdjacentHTML('beforeend', `<div class="bubble">${esc(out.run.result?.summary || 'The run ended without an answer.')}</div>`);
    chat.scrollTop = chat.scrollHeight;
    $('#answer').innerHTML = runHtml(out.run, out.actions);
    assistant.load();
  } catch (e) {
    const w = $('#waiting');
    if (w) w.outerHTML = errorBox(e);
  } finally { if ($('#askbtn')) $('#askbtn').disabled = false; }
}

async function runFromOrchestra(q, workflow) {
  if (state.page !== 'orchestra') await go('orchestra');
  if (workflow) $('#workflow').value = workflow;
  $('#runq').value = q;
  const out = $('#orchestraout');
  out.innerHTML = `<div class="panel">${loading('Supervisor is planning; specialists will run in parallel…')}</div>`;
  $('#runbtn').disabled = true;
  try {
    const r = await startRun(q, { workflow: $('#workflow').value, strategy: $('#strategy').value, traceEl: $('#trace'), pipelineEl: $('#pipeline') });
    if (state.page === 'orchestra' && r) { out.innerHTML = runHtml(r.run, r.actions); orchestra.history(); }
  } catch (e) { out.innerHTML = errorBox(e); } finally { if ($('#runbtn')) $('#runbtn').disabled = false; }
}

async function openRun(id) {
  const target = state.page === 'assistant' ? '#answer' : '#orchestraout';
  if (!$(target)) await go('orchestra');
  const box = $(target) || $('#orchestraout');
  box.innerHTML = `<div class="panel">${loading('Loading run…')}</div>`;
  try {
    const r = await loadRun(id);
    box.innerHTML = runHtml(r.run, r.actions);
    box.scrollIntoView({ behavior: 'smooth', block: 'start' });
    if (r.run.status === 'running' && $('#trace')) followRun(id, { traceEl: $('#trace'), pipelineEl: $('#pipeline'), onFinish: o => { if (document.contains(box)) box.innerHTML = runHtml(o.run, o.actions); } });
  } catch (e) { box.innerHTML = errorBox(e); }
}

async function proposeAndShow(items, box) {
  box.innerHTML = loading('Validating and creating the approval request…');
  try {
    const out = await post('actions/propose', { items });
    const rejected = out.rejected.map(r => `<div class="notice error"><strong>${esc(label(r.kind))}</strong> was not proposed: ${esc(r.reason)}</div>`).join('');
    box.innerHTML = rejected + (out.actions.length ? approvalHtml(out.actions) : '');
    refreshBadges();
    return out;
  } catch (e) { box.innerHTML = errorBox(e); return null; }
}

const localIso = v => { const d = new Date(v); const off = -d.getTimezoneOffset(), p = n => String(Math.floor(Math.abs(n))).padStart(2, '0'); return `${v.length === 16 ? v + ':00' : v}${off >= 0 ? '+' : '-'}${p(off / 60)}:${p(off % 60)}`; };

// ---------------------------------------------------------------------------------------------- events
document.addEventListener('lc:unauthenticated', () => { if (state.user) { state.user = null; authScreen('login', 'Your session ended. Sign in again.'); } });
document.addEventListener('lc:refresh-badges', refreshBadges);
window.addEventListener('hashchange', () => { const p = location.hash.slice(1); if (state.user && p in PAGES && p !== state.page) go(p); });
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') closeDrawer();
  if (e.key === 'Enter' && e.target.matches?.('.card')) openDrawer(cardDetail(state.lastCards.get(e.target.dataset.card)));
});
$('#city').addEventListener('change', () => { localStorage.setItem('lc-city', city()); if (['today', 'dining'].includes(state.page)) go(state.page); });
$('#country').addEventListener('change', () => localStorage.setItem('lc-country', country()));

document.addEventListener('submit', async e => {
  e.preventDefault();
  const f = e.target;
  try {
    if (f.id === 'authform') {
      const reg = f.dataset.mode === 'register';
      f.querySelector('button').disabled = true;
      try { await post(reg ? 'auth/register' : 'auth/login', { email: $('#a-email').value, password: $('#a-pass').value, name: reg ? $('#a-name').value : '' }); await boot(); }
      catch (err) { authScreen(f.dataset.mode, err.message); }
    }
    if (f.id === 'heroform') runFromConcierge(new FormData(f).get('query'));
    if (f.id === 'askform') { const q = $('#askq').value.trim(); $('#askq').value = ''; if (q) runFromConcierge(q); }
    if (f.id === 'discoverform') PAGES[f.dataset.page].search();
    if (f.id === 'travelform') travel.search();
    if (f.id === 'planform') { await post('plans', { title: $('#planname').value, starts: $('#plandate').value, kind: 'idea', data: { provider: 'Personal idea' } }); toast('Added to My plans'); go('planner', { focus: false }); }
    if (f.id === 'budgetform') {
      const plans = (await api('plans')).plans;
      const cards = plans.map(x => ({ title: x.title, kind: x.kind, price: x.data?.price ?? null, currency: x.data?.currency || '', provider: x.data?.provider || '', url: x.data?.url || '', score: x.data?.score || 0 }));
      $('#budgetout').innerHTML = budgetHtml(await post('budget/plan', { budget: Number($('#budgetamount').value), currency: $('#budgetcurrency').value, per_category: Number($('#budgetper').value), cards }));
    }
    if (f.id === 'prefform') { await post('memory/preferences', { kind: $('#prefkind').value, value: $('#prefvalue').value }); toast('Preference remembered'); await refreshBadges(); go('memory', { focus: false }); }
    if (f.id === 'recallform') {
      const d = await api('memory/recall?q=' + encodeURIComponent($('#recallq').value));
      $('#recallout').innerHTML = d.matches.length ? d.matches.map(m => `<div class="flowrow"><div class="num">${Math.round(m.similarity * 100)}</div><div><strong>${esc(m.layer)} · ${esc(m.key)}</strong><p>${esc(m.content)}</p></div></div>`).join('') + '<p class="small">Number = cosine similarity × 100 from the local embedding index.</p>' : '<p class="small">Nothing relevant is stored for that query.</p>';
    }
    if (f.id === 'screenform') {
      const d = await post('security/screen', { text: $('#screenq').value });
      $('#screenout').innerHTML = `<div class="notice ${d.verdict.blocked ? 'error' : 'ok'}">${d.verdict.blocked ? 'Blocked — matched: ' + esc(d.verdict.rules.join(', ').replace(/_/g, ' ')) : 'No injection pattern matched.'}</div><pre class="preview">${esc(d.redacted)}</pre><p class="small">Secrets, emails, phone and card numbers are redacted before anything is stored.</p>`;
    }
  } catch (err) { if (err.status !== 401) toast(err.message, 'bad'); }
});

document.addEventListener('change', e => {
  const t = e.target;
  if (t.id === 'batchtarget') actions.fields();
  if (t.id === 'threadpick') { state.thread = t.value; if (t.value) assistant.showThread(t.value); else go('assistant'); }
  if (t.id === 'f-sort' || t.id === 'f-diet' || t.id === 'f-sport') PAGES[state.page].search?.();
});
document.addEventListener('input', e => {
  const v = e.target.closest?.('.variant');
  if (v && e.target.dataset.field === 'text') v.querySelector('[data-count]').textContent = e.target.value.length;
});

document.addEventListener('click', async e => {
  const el = e.target.closest('button, a, .card, [data-close]');
  if (!el) return;
  const d = el.dataset;
  try {
    if (d.close !== undefined) return closeDrawer();
    if (el.matches('.card') && !e.target.closest('button, a')) return openDrawer(cardDetail(state.lastCards.get(d.card)));
    if (el.tagName === 'A') return;
    if (d.authmode) return authScreen(d.authmode);
    if (d.reload !== undefined) return location.reload();
    if (el.id === 'signout') { await post('auth/logout'); return location.reload(); }  // reload drops every in-memory draft before another account signs in
    if (d.page) return go(d.page);
    if (d.dest) { $('#t-dest').value = d.dest; return travel.search(); }
    if (d.go) { if (d.tabgo) setTab(d.go, d.tabgo); return go(d.go); }
    if (d.tab) { setTab(state.page, d.tab); return go(state.page, { focus: false }); }
    if (d.detail) return openDrawer(cardDetail(state.lastCards.get(d.detail)));
    if (d.save) {
      const c = state.lastCards.get(d.save);
      await post('plans', { title: c.title, kind: c.kind, starts: (c.when || '').slice(0, 16), data: { provider: c.provider, url: c.url, where: c.where, image: c.image, retrieved_at: c.retrieved_at, price: c.price, currency: c.currency, score: c.score || 0 } });
      el.textContent = '✓ Saved'; el.disabled = true;
      return toast('Saved to My plans');
    }
    if (el.id === 'help') return openDrawer(`<span class="label">How it works</span><h2>LifeCanvasOS in one minute</h2><ol class="claims"><li><strong>Ask or browse.</strong> Each workspace calls a specialist agent that searches live providers. Every result names its source and when it was retrieved.</li><li><strong>Honest states.</strong> If a provider is not connected you see “configuration required” — never sample data.</li><li><strong>Memory you control.</strong> Stated preferences personalise ranking. Review or delete everything under Memory & safety.</li><li><strong>You approve actions.</strong> Posts, emails, calendar entries and tasks wait in the Action center until you approve the exact content.</li><li><strong>Bookings stay with providers.</strong> Ticketing, table and travel apps open as handoffs; availability and price are confirmed there.</li></ol>`);

    // concierge / orchestrator
    if (d.ask) return runFromConcierge(d.ask);
    if (d.run) return runFromOrchestra(d.run, d.workflow);
    if (d.workflowpick) { $('#workflow').value = d.workflowpick; const w = state.boot.workflows.find(x => x.id === d.workflowpick); toast(`${w.label}: ${w.about}`); return $('#runq').focus(); }
    if (el.id === 'runbtn') { const q = $('#runq').value.trim(); if (!q) return toast('Describe what you would like to do.'); return runFromOrchestra(q); }
    if (el.id === 'newthread') { state.thread = ''; return go('assistant'); }
    if (d.openrun) return openRun(d.openrun);
    if (d.cancel) { await post(`runs/${d.cancel}/cancel`); return toast('Cancelling the run…'); }
    if (d.resume) { await post(`runs/${d.resume}/resume`); toast('Resuming from the last checkpoint…'); if (state.page !== 'orchestra') await go('orchestra'); const o = await followRun(d.resume, { traceEl: $('#trace'), pipelineEl: $('#pipeline') }); if (o && $('#orchestraout')) { $('#orchestraout').innerHTML = runHtml(o.run, o.actions); orchestra.history(); } return; }
    if (d.checkpoints) {
      const c = await api(`runs/${d.checkpoints}/checkpoints`);
      return openDrawer(`<span class="label">Persistent checkpoints</span><h2>Run ${esc(d.checkpoints.slice(0, 8))}</h2><p class="small">Each row is a saved graph state in the SQLite checkpointer. A run resumes from the newest one after an approval, a restart or a cancel.</p>${c.checkpoints.map(x => `<div class="flowrow"><div class="num">${esc(x.step ?? '·')}</div><div><strong>${esc(x.next.join(', ') || 'end of graph')}</strong><p>${esc(x.source || '')} · ${esc(clock(x.created))}${x.interrupts ? ' · <span class="pill warn">interrupt</span>' : ''}</p></div></div>`).join('') || empty('No checkpoints')}`);
    }

    // approvals
    if (d.approve !== undefined || d.rejectall !== undefined) {
      const out = await decide(el, d.approve !== undefined);
      if (!out) return;
      toast(d.approve !== undefined ? 'Decision recorded.' : 'Rejected. Nothing was sent.');
      if (state.page === 'actions') return go('actions', { focus: false });
      if (out.run_id && (state.page === 'assistant' || state.page === 'orchestra')) return openRun(out.run_id);
      const box = el.closest('.approval');
      if (box) box.outerHTML = approvalHtml(out.actions);
      return;
    }
    if (d.execute) { el.disabled = true; const a = await post(`actions/${d.execute}/execute`); toast(a.note || `Action ${a.status}`); refreshBadges(); return state.page === 'actions' ? go('actions', { focus: false }) : null; }
    if (d.ledger) {
      const l = await api(`actions/${d.ledger}/ledger`);
      return openDrawer(`<span class="label">Execution ledger</span><h2>${esc(l.action.platform)} ${pill(l.action.status)}</h2><p class="small">Digest <code>${esc(l.action.digest)}</code></p><pre class="preview">${esc(JSON.stringify(l.action.payload, null, 2))}</pre>${l.ledger.map((x, i) => `<div class="flowrow"><div class="num">${i + 1}</div><div><strong>${esc(x.state.replace(/_/g, ' '))}</strong><p>${esc(clock(x.created * 1000))}${x.detail ? ' · ' + esc(x.detail.slice(0, 160)) : ''}</p></div></div>`).join('')}`);
    }
    if (el.id === 'batchadd') {
      const kind = $('#batchtarget').value, payload = {};
      $$('[data-bf]').forEach(i => { const v = i.value.trim(); if (i.dataset.bf === 'tracks') payload.tracks = v.split('\n').map(x => x.trim()).filter(Boolean); else if (v || ['text', 'title', 'name'].includes(i.dataset.bf)) payload[i.dataset.bf] = v; });
      actionDraft.push({ kind, payload, summary: `${label(kind)} action` });
      actions.fields();
      return actions.draft();
    }
    if (d.dropbatch !== undefined) { actionDraft.splice(+d.dropbatch, 1); return actions.draft(); }
    if (el.id === 'batchreview') {
      if (!actionDraft.length) return toast('Add at least one action to the batch.');
      const out = await post('actions/propose', { items: actionDraft });
      if (out.rejected.length) toast(`${out.rejected.length} refused: ${out.rejected[0].reason}`, 'bad');
      if (out.actions.length) actionDraft.length = 0;
      refreshBadges();
      return go('actions', { focus: false });
    }

    // creator studio
    if (d.target) { const p = studio.state.platforms; p.has(d.target) ? p.delete(d.target) : p.add(d.target); el.classList.toggle('selected'); return studio.extra(); }
    if (el.id === 'draftbtn') {
      const topic = $('#topic').value.trim();
      if (topic.length < 2) return toast('Add a topic to write about.');
      if (!studio.state.platforms.size) return toast('Choose at least one platform.');
      const out = $('#studioout');
      el.disabled = true;
      out.innerHTML = loading('Researching sources, drafting and adapting for each platform…');
      try {
        const r = await post('create', { topic, notes: $('#notes').value, tone: $('#tone').value, platforms: [...studio.state.platforms], to: $('#s-to')?.value || '', channel: $('#s-channel')?.value || '', image_url: $('#s-image')?.value || '', skip_research: $('#skipresearch').checked });
        studio.state.result = r;
        if (state.page === 'studio') out.innerHTML = studio.render(r);
      } catch (err) { out.innerHTML = errorBox(err); } finally { el.disabled = false; }
      return;
    }
    if (el.id === 'sendapproval') {
      const r = studio.state.result;
      const items = $$('.variant').filter(v => v.querySelector('[data-include]').checked).map(v => {
        const variant = r.creative.variants[+v.dataset.variant], payload = { ...variant.payload };
        v.querySelectorAll('[data-field]').forEach(i => { payload[i.dataset.field] = i.value; });
        return { kind: variant.platform, payload, summary: `${variant.format} — ${r.creative.draft.title.slice(0, 80)}` };
      });
      if (!items.length) return toast('Tick at least one variant to include.');
      return proposeAndShow(items, $('#studioout'));
    }

    // plans
    if (d.removeplan) { await del('plans/' + d.removeplan); return go('planner', { focus: false }); }
    if (d.plancal) { $('#caltitle').value = d.title; $('#calloc').value = d.where; if (d.starts.length >= 16) $('#calstart').value = d.starts.replace(' ', 'T').slice(0, 16); return $('#calstart').focus(); }
    if (el.id === 'calendarbtn') {
      if (!$('#caltitle').value.trim() || !$('#calstart').value || !$('#calend').value) return toast('Add a title, start and end.');
      return proposeAndShow([{ kind: 'google_calendar', summary: `Calendar event: ${$('#caltitle').value}`, payload: { title: $('#caltitle').value, start: localIso($('#calstart').value), end: localIso($('#calend').value), location: $('#calloc').value } }], $('#planapproval'));
    }
    if (el.id === 'taskbtn') { if (!$('#tasktitle').value.trim()) return toast('Add a task title.'); return proposeAndShow([{ kind: $('#taskapp').value, summary: `Task: ${$('#tasktitle').value}`, payload: { title: $('#tasktitle').value } }], $('#planapproval')); }

    // circles
    if (el.id === 'matchbtn') return circles.match();
    if (el.id === 'meetupcreate') {
      const options = $('#m-options').value.split('\n').map(l => l.split('|').map(x => x.trim())).filter(p => p[0]).map(p => ({ title: p[0], date: p[1] || '', cost_per_person: p[2] ? Number(p[2]) : null, currency: localStorage.getItem('lc-currency') || '', tags: (p[3] || '').split(',').map(x => x.trim()).filter(Boolean) }));
      const invitees = [...$('#m-invitees').selectedOptions].map(o => o.value);
      if (!options.length || !invitees.length) return toast('Add at least one option and choose a connection to invite.');
      await post('meetups', { title: $('#m-title').value || 'Meetup', options, invitees, constraints: circles.limits('m-') });
      toast('Sent. The agents will agree once everyone shares their limits.');
      return circles.meetups((await api('meetups')).meetups);
    }
    if (d.meetuplimits) { await post(`meetups/${d.meetuplimits}/constraints`, { constraints: circles.limits(`j-${d.meetuplimits}-`) }); return circles.meetups((await api('meetups')).meetups); }
    if (d.meetupconfirm) { await post(`meetups/${d.meetupconfirm}/confirm`); toast('Confirmed for you.'); return circles.meetups((await api('meetups')).meetups); }
    if (el.id === 'refreshinbox') return circles.inbox(await api('community/connections'));
    if (el.id === 'saveprofile') {
      await put('community/profile', { display_name: $('#pname').value, city: $('#pcity').value, interests: $('#pinterests').value.split(',').map(x => x.trim()).filter(Boolean), bio: $('#pbio').value, discoverable: $('#optin').checked, adult_confirmed: $('#adult').checked });
      return toast($('#optin').checked ? 'Profile saved. You are discoverable to other members.' : 'Profile saved. You are not discoverable.');
    }
    if (d.call) { const c = await post('community/call', { user_id: d.call }); return openDrawer(`<span class="label">${esc(c.provider)}</span><h2>Private video room</h2><p>${esc(c.note)}</p><p class="small">Both of you get the same room from your Circles page. It is only available while you are connected.</p><div class="chips"><a class="chip primarychip" href="${esc(c.url)}" target="_blank" rel="noopener noreferrer">Join video call ↗</a></div>`); }
    if (d.invite) { await post('community/requests', { user_id: d.invite, message: '' }); toast('Connection request sent.'); return circles.match(); }
    if (d.respond) { await post('community/requests/' + d.respond, { accept: !!d.accept }); return circles.inbox(await api('community/connections')); }
    if (d.block) { if (!confirm('Block this member? You will no longer see each other.')) return; await post('community/block', { user_id: d.block }); toast('Blocked.'); return go('circles', { focus: false }); }
    if (d.unblock) { await post('community/unblock', { user_id: d.unblock }); return go('circles', { focus: false }); }
    if (d.report) { const reason = prompt('What happened? This also blocks the member.'); if (!reason) return; await post('community/report', { user_id: d.report, reason }); toast('Report received and member blocked.'); return go('circles', { focus: false }); }

    // memory & safety
    if (d.forget) { await del('memory/' + d.forget); toast('Deleted.'); return go('memory', { focus: false }); }
    if (d.forgetlayer) { if (!confirm(`Clear the entire ${d.forgetlayer} layer?`)) return; await del('memory?layer=' + d.forgetlayer); toast('Layer cleared.'); await refreshBadges(); return go('memory', { focus: false }); }
    if (el.id === 'deleteaccount') { if (!confirm('Permanently delete your account, memory, plans and history?')) return; await del('me'); state.user = null; return authScreen('register'); }

    // connections
    if (d.connfilter) { connections.setFilter(d.connfilter); return connections.render(connections.cache); }
    if (d.verify) { el.disabled = true; el.textContent = 'Verifying…'; await post(`providers/${d.verify}/verify`); await refreshBadges(); return connections.load(); }
    if (el.id === 'verifyall') { el.disabled = true; el.textContent = 'Verifying live…'; await post('providers/verify-all'); await refreshBadges(); toast('Verification finished.'); return connections.load(); }
    if (d.providerdetail) {
      const p = connections.cache.find(x => x.id === d.providerdetail);
      return openDrawer(`<span class="label">${esc(p.category)} provider</span><h2>${esc(p.name)} ${pill(p.status)}</h2><dl class="meta"><div><dt>Capabilities</dt><dd>${esc(p.capabilities.join(', '))}</dd></div><div><dt>Access</dt><dd>${esc(p.access)}${p.permissions.approval_required ? ' · approval required' : ''}</dd></div>
        <div><dt>Credentials</dt><dd>${p.auth.required.length ? p.auth.required.map(k => `<code>${esc(k)}</code>${p.auth.missing.includes(k) ? ' (missing)' : ' (set)'}`).join('<br>') : 'None required'}</dd></div><div><dt>Scopes</dt><dd>${esc(p.auth.scopes.join(', ') || '—')}</dd></div>
        <div><dt>Rate limit</dt><dd>${p.limits.rate_per_min}/min</dd></div><div><dt>Timeout</dt><dd>${p.limits.timeout_s}s</dd></div><div><dt>Retries</dt><dd>${p.access === 'write' ? 'never (writes)' : p.limits.retries}</dd></div><div><dt>Concurrency</dt><dd>${p.limits.concurrency}</dd></div><div><dt>Cache</dt><dd>${p.limits.cache_ttl_s}s</dd></div>
        <div><dt>Response</dt><dd>${esc(p.response_schema)}</dd></div><div><dt>Calls / errors</dt><dd>${p.usage.calls} / ${p.usage.errors}</dd></div><div><dt>Last check</dt><dd>${p.checked_at ? esc(ago(p.checked_at)) : 'never'}</dd></div></dl>
        ${p.detail ? `<div class="notice">${esc(p.detail)}</div>` : ''}${p.attribution ? `<p class="small provenance">${esc(p.attribution)}</p>` : ''}`);
    }
    if (d.retryDiscover !== undefined) return PAGES[state.page].search();
    if (d.retryTravel !== undefined) return travel.search();
  } catch (err) {
    if (err.status !== 401) toast(err.message, 'bad');
    if (el.disabled) el.disabled = false;
  }
});

boot();
