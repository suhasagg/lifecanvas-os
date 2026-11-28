// Core utilities: DOM helpers, escaping, API client, formatting. No inline handlers anywhere (strict CSP).
export const $ = (s, root = document) => root.querySelector(s);
export const $$ = (s, root = document) => [...root.querySelectorAll(s)];
export const esc = x => String(x ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
export const safeUrl = x => { try { const u = new URL(x); return u.protocol === 'https:' ? esc(u.href) : ''; } catch { return ''; } };

export const state = { user: null, boot: null, page: 'today', thread: '', lastCards: new Map(), stream: null };

export class ApiError extends Error {
  constructor(status, code, message) { super(message); this.status = status; this.code = code; }
}

export async function api(path, { method = 'GET', body, signal } = {}) {
  const headers = { 'X-Requested-With': 'lifecanvas' };
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  let r;
  try {
    r = await fetch('/api/' + path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body), credentials: 'same-origin', signal });
  } catch (e) {
    if (e.name === 'AbortError') throw e;
    throw new ApiError(0, 'network', 'Cannot reach the LifeCanvasOS server. Check that it is running, then retry.');
  }
  let data = null;
  try { data = await r.json(); } catch { /* non-JSON error body */ }
  if (!r.ok) {
    const message = data?.message || (Array.isArray(data?.detail) ? data.detail.map(d => `${(d.loc || []).slice(-1)[0]}: ${d.msg}`).join('; ') : data?.detail) || `Request failed (${r.status})`;
    if (r.status === 401 && path !== 'auth/login') document.dispatchEvent(new CustomEvent('lc:unauthenticated'));
    throw new ApiError(r.status, data?.error || 'error', message);
  }
  return data;
}
export const post = (path, body = {}) => api(path, { method: 'POST', body });
export const put = (path, body = {}) => api(path, { method: 'PUT', body });
export const del = path => api(path, { method: 'DELETE' });

export function toast(text, kind = '') {
  const n = $('#toast');
  n.textContent = text;
  n.className = kind;
  n.style.display = 'block';
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { n.style.display = 'none'; }, 4600);
}

export const city = () => $('#city').value.trim();
export const country = () => $('#country').value;
export const ago = t => { const s = Math.max(0, Date.now() / 1000 - t); return s < 60 ? 'just now' : s < 3600 ? `${Math.floor(s / 60)} min ago` : s < 86400 ? `${Math.floor(s / 3600)} h ago` : `${Math.floor(s / 86400)} d ago`; };
export const clock = iso => { try { return new Date(iso).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' }); } catch { return iso; } };
export const money = (price, currency) => { if (price == null) return ''; try { return new Intl.NumberFormat([], { style: 'currency', currency: currency || 'USD', maximumFractionDigits: 2 }).format(price); } catch { return `${price} ${currency || ''}`.trim(); } };

export const head = (label, title, desc, extra = '') => `<div class="pagehead"><div><p class="eyebrow">${label}</p><h1>${title}</h1><p>${desc}</p></div>${extra}</div>`;
export const row = (n, t, d) => `<div class="flowrow"><div class="num">${n}</div><div><strong>${t}</strong><p>${d}</p></div><span class="arrow">›</span></div>`;
export const tile = (art, tag, title, desc, action, label = 'Explore ↗') => `<div class="tile"><div class="art" style="background-image:url('/static/assets/${art}.svg')"><span>${tag}</span></div><div class="body"><h3>${title}</h3><p>${desc}</p><div class="bottom"><span>Live sources</span><button ${action}>${label}</button></div></div></div>`;
export const skeleton = (n = 4) => `<div class="results">${'<div class="result skeleton"><div class="sk img"></div><div class="sk line"></div><div class="sk line short"></div></div>'.repeat(n)}</div>`;
export const loading = text => `<div class="loadingline"><span class="pulse">✦</span> ${esc(text)}</div>`;
export const empty = (title, hint = '') => `<div class="emptystate"><strong>${esc(title)}</strong>${hint ? `<p>${hint}</p>` : ''}</div>`;
export const errorBox = (e, retry = '') => `<div class="errorbox" role="alert"><strong>${esc(e.code === 'network' ? 'Connection problem' : e.status === 429 ? 'Slow down a moment' : 'That did not work')}</strong><p>${esc(e.message)}</p>${retry ? `<button class="secondary" ${retry}>Try again</button>` : ''}</div>`;

export const STATUS = {
  connected_verified: ['Connected', 'ok'], configured_unverified: ['Ready · not yet verified', 'info'], configuration_required: ['Configuration required', 'warn'], authentication_expired: ['Authentication expired', 'bad'],
  temporarily_unavailable: ['Temporarily unavailable', 'bad'], rate_limited: ['Rate limited', 'warn'], external_handoff: ['External handoff', 'muted'],
  ok: ['Results', 'ok'], no_results: ['No matches', 'muted'], needs_configuration: ['Needs a connection', 'warn'], failed: ['Provider failed', 'bad'], needs_review: ['Needs review', 'warn'],
  running: ['Running', 'info'], completed: ['Completed', 'ok'], awaiting_approval: ['Awaiting approval', 'warn'], cancelled: ['Cancelled', 'muted'], interrupted: ['Interrupted · resumable', 'warn'], blocked: ['Blocked by sentinel', 'bad'],
  pending: ['Pending approval', 'warn'], approved: ['Approved · held', 'info'], executing: ['Sending', 'info'], executed: ['Sent', 'ok'], rejected: ['Rejected', 'muted'], expired: ['Expired', 'muted'], unknown: ['Outcome unknown', 'bad'],
};
export const pill = s => { const [label, tone] = STATUS[s] || [s, 'muted']; return `<span class="pill ${tone}">${esc(label)}</span>`; };

// ---- result cards -------------------------------------------------------------------------------------------
const KIND_ICON = { event: '◉', fixture: '◉', team: '✦', movie: '▶', show: '▣', track: '♪', album: '♪', artist: '✦', video: '▶', place: '✳', weather: '✺', forecast: '✺', flight: '↗', guide: '◈', attraction: '◈', book: '▤', artwork: '◩', activity: '↗', source: '◇', image: '▣', member: '◎', handoff: '↗' };
let cardSeq = 0;

export function cardHtml(c, { save = true } = {}) {
  const id = 'c' + (++cardSeq);
  state.lastCards.set(id, c);
  const img = safeUrl(c.image);
  const facts = [c.when && `<span class="fwhen">${esc(c.when)}</span>`, c.where && `<span class="fwhere">${esc(c.where)}</span>`, c.price != null && `<span class="price">${esc(money(c.price, c.currency))}</span>`, c.rating != null && `<span>★ ${esc(c.rating)}</span>`,
    c.availability && `<span class="avail">${esc(c.availability)}</span>`].filter(Boolean).join('');
  return `<article class="result card" data-card="${id}" tabindex="0">
    ${img ? `<div class="cardimg"><img src="${img}" alt="" loading="lazy" referrerpolicy="no-referrer"></div>` : `<div class="cardimg noimg"><span>${KIND_ICON[c.kind] || '✦'}</span></div>`}
    <div class="cardbody"><span class="label">${esc(c.provider)} · ${esc(c.kind)}</span><h4>${esc(c.title)}</h4>
    ${facts ? `<div class="facts">${facts}</div>` : ''}${c.summary ? `<p class="clamp">${esc(c.summary)}</p>` : ''}
    ${(c.why || []).length ? `<p class="why">✦ ${esc(c.why[0])}</p>` : ''}
    <div class="cardfoot">${(c.tags || []).slice(0, 3).map(t => `<span class="tag">${esc(t)}</span>`).join('')}<span class="grow"></span>
    ${save && c.kind !== 'member' ? `<button class="mini" data-save="${id}" title="Save to My plans">+ Save</button>` : ''}<button class="mini" data-detail="${id}">Details</button></div></div></article>`;
}

export function cardsHtml(cards, opts) {
  return cards.length ? `<div class="results cards">${cards.map(c => cardHtml(c, opts)).join('')}</div>` : '';
}

export function noticesHtml(r) {
  const notices = (r.notices || []).map(n => `<div class="notice config"><strong>${esc(n.provider)}</strong> — configuration required. ${esc(n.message)} <button class="linkbtn" data-go="connections">Open App Connections ↗</button></div>`);
  const errors = (r.errors || []).map(e => `<div class="notice error"><strong>${esc(e.provider)}</strong> — ${esc({ timeout: 'timed out', deadline: 'took too long', unavailable: 'is temporarily unavailable', rate_limit: 'rate limit reached', auth: 'rejected the credentials', circuit_open: 'is paused after repeated failures', bad_response: 'returned an unusable response', bad_request: 'needs more detail' }[e.error_class] || e.error_class)}. ${esc(e.message)}</div>`);
  return notices.concat(errors).join('');
}

export function handoffsHtml(list) {
  if (!list?.length) return '';
  return `<div class="handoffs"><p class="small"><strong>Continue in an app.</strong> These open the provider with your search. Availability, price and booking are confirmed there, not by LifeCanvasOS.</p><div class="chips">${list.map(h => `<a class="chip handoff" href="${safeUrl(h.url)}" target="_blank" rel="noopener noreferrer">${esc(h.provider)} ↗</a>`).join('')}</div></div>`;
}

export function sectionHtml(r, { filter = null } = {}) {
  const cards = filter ? r.cards.filter(filter) : r.cards;
  const tools = (r.tools || []).map(t => `<span class="${t.ok ? '' : 'bad'}" title="${esc(t.latency_ms)} ms">${esc(t.tool)} · ${t.ok ? t.items : 'failed'}</span>`).join('');
  let body = noticesHtml(r);
  if (r.brief) body += briefHtml(r);
  body += cards.length ? cardsHtml(cards) : (!r.brief && !r.creative ? empty(r.status === 'needs_configuration' ? 'No connected provider could answer this' : 'No live results matched', r.status === 'needs_configuration' ? 'Connect one of the providers above to enable this search.' : 'Try a broader search, another city, or fewer filters.') : '');
  body += handoffsHtml(r.handoffs);
  return `<div class="sectionblock"><div class="sectionhead"><h2>${esc(r.specialist ? r.specialist[0].toUpperCase() + r.specialist.slice(1) : 'Results')} ${pill(r.status)}</h2><span class="small">${cards.length} result${cards.length === 1 ? '' : 's'}${r.place ? ` · ${esc(r.place.name)}` : ''}</span></div>${tools ? `<div class="trace">${tools}</div>` : ''}${body}</div>`;
}

export function briefHtml(r) {
  const b = r.brief, v = b.verification || {};
  if (!b.claims?.length) return '';
  return `<div class="brief"><div class="kpis mini"><div><strong>${v.claims_verified ?? 0}</strong><span>Claims traced to source</span></div><div><strong>${v.sources ?? 0}</strong><span>Sources</span></div><div><strong>${v.independent_providers ?? 0}</strong><span>Independent providers</span></div><div><strong>${v.claims_dropped ?? 0}</strong><span>Dropped as unverifiable</span></div></div>
  ${b.synthesis ? `<div class="bubble">${esc(b.synthesis)}</div>` : '<p class="small">No language model is connected, so this brief shows verbatim extracts from each source rather than a written synthesis.</p>'}
  <ol class="claims">${b.claims.map(c => `<li>${esc(c.text)} <sup>[${c.source}]</sup></li>`).join('')}</ol></div>`;
}

export function openDrawer(html) {
  const d = $('#drawer');
  d.innerHTML = `<div class="drawerback" data-close></div><div class="drawerpanel"><button class="round drawerclose" data-close aria-label="Close">×</button>${html}</div>`;
  d.classList.remove('hidden');
  $('.drawerclose', d).focus();
}
export const closeDrawer = () => $('#drawer').classList.add('hidden');

export function cardDetail(c) {
  const img = safeUrl(c.image), link = safeUrl(c.url);
  const meta = Object.entries(c.meta || {}).filter(([k, v]) => !['lat', 'lon', 'user_id'].includes(k) && typeof v !== 'object').map(([k, v]) => `<div><dt>${esc(k.replace(/_/g, ' '))}</dt><dd>${esc(v === true ? 'yes' : v === false ? 'no' : v)}</dd></div>`).join('');
  const lists = Object.entries(c.meta || {}).filter(([, v]) => Array.isArray(v) && v.length).map(([k, v]) => `<div><dt>${esc(k.replace(/_/g, ' '))}</dt><dd>${v.map(esc).join(', ')}</dd></div>`).join('');
  const map = c.meta?.lat != null ? `<a class="chip" target="_blank" rel="noopener noreferrer" href="https://www.openstreetmap.org/?mlat=${encodeURIComponent(c.meta.lat)}&mlon=${encodeURIComponent(c.meta.lon)}#map=16/${encodeURIComponent(c.meta.lat)}/${encodeURIComponent(c.meta.lon)}">Open map ↗</a>` : '';
  const audio = safeUrl(c.meta?.preview_url) ? `<audio controls preload="none" src="${safeUrl(c.meta.preview_url)}"></audio>` : '';
  return `${img ? `<img class="drawerimg" src="${img}" alt="" referrerpolicy="no-referrer">` : ''}<span class="label">${esc(c.provider)} · ${esc(c.kind)}</span><h2>${esc(c.title)}</h2>
  <div class="facts big">${[c.when && `<span class="fwhen">${esc(c.when)}</span>`, c.where && `<span class="fwhere">${esc(c.where)}</span>`, c.price != null && `<span class="price">${esc(money(c.price, c.currency))}</span>`, c.rating != null && `<span>★ ${esc(c.rating)}</span>`, c.availability && `<span class="avail">${esc(c.availability)}</span>`].filter(Boolean).join('')}</div>
  ${c.summary ? `<p>${esc(c.summary)}</p>` : ''}${(c.why || []).map(w => `<p class="why">✦ ${esc(w)}</p>`).join('')}${audio}
  ${c.meta?.diet_note ? `<div class="notice">${esc(c.meta.diet_note)}</div>` : ''}
  <dl class="meta">${meta}${lists}</dl>
  <div class="chips">${link ? `<a class="chip primarychip" href="${link}" target="_blank" rel="noopener noreferrer">Open source ↗</a>` : ''}${map}</div>
  <p class="small provenance">Source: ${esc(c.provider)}${c.attribution ? ` — ${esc(c.attribution)}` : ''}<br>Retrieved ${esc(clock(c.retrieved_at))}${c.price == null && ['event', 'place', 'flight', 'movie'].includes(c.kind) ? '<br>Price not supplied by this source.' : ''}</p>`;
}
