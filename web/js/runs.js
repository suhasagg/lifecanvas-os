// Run lifecycle on the client: start, live SSE progress, approval, cancel, resume.
import { $, api, post, esc, pill, sectionHtml, toast, errorBox, loading, clock, state, city, country } from './core.js';

const ICONS = { entertainment: '◉', dining: '✳', culture: '◇', travel: '↗', community: '◎', research: '◈', creative: '✦', action: '▣' };
const PIPELINE = [['recall', 'Recall memory'], ['sentinel', 'Sentinel'], ['planner', 'Planner'], ['specialists', 'Specialists'], ['critic', 'Critic'], ['composer', 'Composer'], ['action', 'Approval'], ['consolidate', 'Memory']];

export function pipelineHtml() {
  return `<div class="pipeline" id="pipeline">${PIPELINE.map(([k, label]) => `<div class="stage" data-stage="${k}"><i></i><span>${label}</span></div>`).join('')}</div>`;
}

function stageOf(node) {
  const head = node.split('.')[0];
  if (['recall', 'sentinel', 'planner', 'critic', 'composer', 'consolidate'].includes(head)) return head;
  if (head === 'action') return 'action';
  if (head === 'refuse') return 'sentinel';
  if (head === 'redispatch') return 'critic';
  return 'specialists';
}

function markStage(root, node, failed = false) {
  const stage = stageOf(node), el = root.querySelector(`[data-stage="${stage}"]`);
  if (!el) return;
  let seen = false;
  root.querySelectorAll('.stage').forEach(s => {
    if (s === el) { seen = true; s.classList.add('active'); s.classList.toggle('bad', failed); }
    else if (!seen) { s.classList.remove('active'); s.classList.add('done'); }
  });
}

export function stepHtml(e) {
  const node = e.node, agent = node.split('.')[0];
  const detail = e.payload.detail || {};
  const bits = [detail.latency_ms != null && `${detail.latency_ms} ms`, detail.provider, detail.mode, detail.tokens && `${detail.tokens} tokens`, detail.cost_usd != null && `$${detail.cost_usd}`].filter(Boolean).join(' · ');
  return `<div class="step ${detail.ok === false ? 'bad' : ''}"><span class="orb">${ICONS[agent] || '✦'}</span><div><strong>${esc(node)}</strong><p>${esc(e.payload.summary)}</p>${bits ? `<small>${esc(bits)}</small>` : ''}</div></div>`;
}

export function approvalHtml(actions, { title = 'Approval required' } = {}) {
  if (!actions.length) return '';
  const pending = actions.filter(a => a.status === 'pending');
  return `<div class="approval" data-batch="${esc(actions[0].batch_id)}"><div class="sectionhead"><h2>${esc(title)}</h2><span class="small">${pending.length} pending</span></div>
  ${pending.length ? '<p class="small">Review the exact content and destination. Nothing is sent until you approve, and each approval works once for exactly this content.</p>' : ''}
  ${actions.map(a => `<div class="result actioncard ${a.status}"><label class="checkline"><input type="checkbox" data-actionid="${esc(a.id)}" data-digest="${esc(a.digest)}" ${a.status === 'pending' ? 'checked' : 'disabled'}> <strong>${esc(a.platform)}</strong> ${pill(a.status)} <span class="pill risk-${esc(a.risk)}">${esc(a.risk)} risk</span></label>
    <p class="small">${esc(a.summary)}</p>
    <dl class="meta compact"><div><dt>Destination</dt><dd>${esc(a.destination)}</dd></div><div><dt>Visibility</dt><dd>${esc(a.visibility)}</dd></div><div><dt>When</dt><dd>${esc(a.when)}</dd></div><div><dt>Cost</dt><dd>${esc(a.cost)}</dd></div>
    <div><dt>Depends on</dt><dd>${a.depends_on.length ? a.depends_on.map(d => esc(d.slice(0, 8))).join(', ') : 'Nothing'}</dd></div><div><dt>Expires</dt><dd>${esc(clock(a.expires * 1000))}</dd></div>
    <div><dt>Payload digest</dt><dd><code>${esc(a.digest.slice(0, 20))}…</code></dd></div><div><dt>Connection</dt><dd>${a.connected ? 'Connected' : `Not connected (${esc(a.missing.join(', '))})`}</dd></div></dl>
    <pre class="preview">${esc(Object.entries(a.payload).map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join('\n  ') : v}`).join('\n'))}</pre>
    ${!a.connected && a.status === 'pending' ? `<div class="notice config">${esc(a.platform)} is not connected. You can still approve; the action is then held and nothing is sent until the connection is configured.</div>` : ''}
    ${a.result?.receipt ? `<p class="receipt">Receipt ${esc(a.result.receipt)} ${a.result.url ? `· <a href="${esc(a.result.url)}" target="_blank" rel="noopener noreferrer">Open ↗</a>` : ''}</p>` : ''}
    ${a.result?.note ? `<div class="notice ${a.status === 'unknown' ? 'error' : ''}">${esc(a.result.note)}</div>` : ''}
    ${a.status === 'approved' ? `<div class="formrow"><button class="secondary" data-execute="${esc(a.id)}" ${a.connected ? '' : 'disabled'}>${a.connected ? 'Send now' : 'Waiting for connection'}</button><button class="linkbtn" data-ledger="${esc(a.id)}">View ledger</button></div>` : `<button class="linkbtn" data-ledger="${esc(a.id)}">View ledger</button>`}
  </div>`).join('')}
  ${pending.length ? '<div class="formrow"><button class="primary" data-approve>Approve selected</button><button class="secondary" data-rejectall>Reject all</button></div>' : ''}</div>`;
}

export function runHtml(run, actions = []) {
  const a = run.result || {};
  const sections = a.sections || [];
  const crit = a.critique || {};
  const kpis = `<div class="kpis"><div><strong>${sections.length}</strong><span>Specialists</span></div><div><strong>${a.total_cards ?? 0}</strong><span>Grounded results</span></div><div><strong>${(a.providers || []).length}</strong><span>Live providers</span></div><div><strong>${crit.score != null ? Math.round(crit.score * 100) + '%' : '—'}</strong><span>Critic coverage</span></div></div>`;
  const modes = `<p class="small">Planner: ${a.planner_mode === 'model' ? 'language model' : 'rules (no language model connected)'} · Composer: ${a.mode === 'model' ? esc(a.model || 'language model') : 'template (no language model connected)'}${crit.mode ? ` · Critic: ${esc(crit.mode)}` : ''}</p>`;
  const issues = (crit.issues || []).length ? `<details class="issues"><summary>${crit.issues.length} critic note${crit.issues.length === 1 ? '' : 's'}</summary><ul>${crit.issues.map(i => `<li>${esc(i)}</li>`).join('')}</ul></details>` : '';
  const learned = (a.learned || []).length ? `<div class="notice ok">Remembered: ${a.learned.map(l => `${esc(l.kind)} — ${esc(l.content)}`).join(', ')}. <button class="linkbtn" data-go="memory">Review memory ↗</button></div>` : '';
  const creative = sections.filter(s => s.creative).map(s => `<div class="sectionblock"><div class="sectionhead"><h2>Draft ${pill(s.status)}</h2><span class="small">${s.creative.mode === 'model' ? 'Written by a language model' : 'Assembled from your topic and cited sources'}</span></div><div class="preview"><strong>${esc(s.creative.draft.title)}</strong>\n\n${esc(s.creative.draft.body)}</div></div>`).join('');
  return `<div class="panel runpanel" data-run="${esc(run.id)}"><div class="sectionhead"><h2>Run ${esc(run.id.slice(0, 8))} ${pill(run.status)}</h2><div class="formrow tight">${run.status === 'running' ? `<button class="secondary" data-cancel="${esc(run.id)}">Cancel</button>` : ''}${['interrupted', 'failed', 'cancelled'].includes(run.status) ? `<button class="secondary" data-resume="${esc(run.id)}">Resume from checkpoint</button>` : ''}<button class="linkbtn" data-checkpoints="${esc(run.id)}">Checkpoints</button></div></div>
  ${a.blocked ? '' : kpis}<div class="bubble">${esc(a.summary || (run.status === 'running' ? 'Working…' : 'No answer was produced.'))}</div>${a.blocked ? '' : modes}${learned}${issues}
  ${approvalHtml(actions)}${creative}${sections.map(s => sectionHtml(s)).join('')}</div>`;
}

export async function loadRun(runId) {
  const run = await api('runs/' + runId);
  let actions = [];
  if (run.result?.batch_id) actions = (await api('actions')).actions.filter(a => a.batch_id === run.result.batch_id);
  return { run, actions };
}

/** Start a run and stream its progress into `traceEl`; resolves with the finished run. */
export async function startRun(goal, { workflow = 'auto', strategy = '', traceEl, pipelineEl, onFinish } = {}) {
  const started = await post('runs', { goal, city: city(), country: country(), workflow, strategy, thread_id: state.thread });
  state.thread = started.thread_id;
  return followRun(started.run_id, { traceEl, pipelineEl, onFinish });
}

export function followRun(runId, { traceEl, pipelineEl, onFinish, after = 0 } = {}) {
  if (traceEl && !after) traceEl.innerHTML = '';
  if (traceEl) traceEl.classList.remove('empty');
  state.stream?.close();
  return new Promise(resolve => {
    const es = new EventSource(`/api/runs/${runId}/stream?after=${after}`);
    state.stream = es;
    const finish = async () => {
      es.close();
      if (state.stream === es) state.stream = null;
      try {
        const out = await loadRun(runId);
        pipelineEl?.querySelectorAll('.stage').forEach(s => { if (out.run.status === 'completed') { s.classList.add('done'); s.classList.remove('active'); } });
        document.dispatchEvent(new CustomEvent('lc:refresh-badges'));
        onFinish?.(out);
        resolve(out);
      } catch (e) { toast(e.message, 'bad'); resolve(null); }
    };
    es.addEventListener('step', ev => {
      const e = JSON.parse(ev.data);
      if (traceEl && document.contains(traceEl)) { traceEl.insertAdjacentHTML('beforeend', stepHtml(e)); traceEl.scrollTop = traceEl.scrollHeight; }
      if (pipelineEl) markStage(pipelineEl, e.node, e.payload.detail?.ok === false && false);
    });
    es.addEventListener('interrupt', () => { if (pipelineEl) markStage(pipelineEl, 'action'); });
    es.addEventListener('status', ev => {
      const e = JSON.parse(ev.data);
      if (e.payload.note && traceEl && document.contains(traceEl)) traceEl.insertAdjacentHTML('beforeend', `<div class="step note"><span class="orb">i</span><div><p>${esc(e.payload.note)}</p></div></div>`);
    });
    es.addEventListener('end', finish);
    es.addEventListener('final', () => {});
    es.onerror = () => { if (es.readyState === EventSource.CLOSED) finish(); };
  });
}

export async function decide(root, approveAll) {
  const box = root.closest('.approval');
  const batch = box.dataset.batch;
  const checks = [...box.querySelectorAll('[data-actionid]:not(:disabled)')];
  const approve = approveAll ? checks.filter(c => c.checked).map(c => ({ id: c.dataset.actionid, digest: c.dataset.digest })) : [];
  const reject = approveAll ? [] : checks.map(c => c.dataset.actionid);
  if (approveAll && !approve.length) { toast('Select at least one action to approve, or reject all.'); return null; }
  box.querySelectorAll('button').forEach(b => { b.disabled = true; });
  box.insertAdjacentHTML('beforeend', loading(approveAll ? 'Recording approval and running the action executor…' : 'Recording your decision…'));
  try {
    const out = await post('actions/decide', { batch_id: batch, approve, reject });
    document.dispatchEvent(new CustomEvent('lc:refresh-badges'));
    return out;
  } catch (e) {
    box.insertAdjacentHTML('beforeend', errorBox(e));
    box.querySelectorAll('button').forEach(b => { b.disabled = false; });
    return null;
  }
}
