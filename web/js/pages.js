// Workspace pages. Each page returns markup synchronously and loads live data in `load()`.
import { $, $$, api, post, esc, safeUrl, head, row, tile, skeleton, loading, empty, errorBox, pill, cardsHtml, cardHtml, sectionHtml, handoffsHtml, noticesHtml, state, city, country, ago, clock, STATUS } from './core.js';
import { pipelineHtml, runHtml, approvalHtml } from './runs.js';

export const NAMES = { today: 'Today', assistant: 'AI concierge', events: 'Experiences', dining: 'Food & dining', circles: 'Circles', studio: 'Creator studio', planner: 'My plans', connections: 'App connections', orchestra: 'Orchestrator',
  culture: 'Culture & wellness', travel: 'Travel & escapes', actions: 'Action center', memory: 'Memory & safety', developer: 'Developer view' };
const LABELS = { x: 'X', bluesky: 'Bluesky', linkedin: 'LinkedIn', mastodon: 'Mastodon', facebook: 'Facebook Page', instagram: 'Instagram', wordpress: 'WordPress', telegram: 'Telegram', discord: 'Discord', slack: 'Slack', gmail: 'Gmail',
  google_calendar: 'Google Calendar', google_tasks: 'Google Tasks', google_drive: 'Google Drive', notion: 'Notion', todoist: 'Todoist', ms_graph: 'Microsoft To Do', spotify_playlist: 'Spotify playlist' };
export const label = k => LABELS[k] || k;
const needCity = () => city() ? '' : '<div class="notice">Set your city in the top bar to search nearby.</div>';
const tabs = (items, active) => `<div class="tabs" role="tablist">${items.map(([k, l]) => `<button role="tab" data-tab="${k}" class="${k === active ? 'selected' : ''}">${l}</button>`).join('')}</div>`;

// ------------------------------------------------------------------------------------------------ Today
export const today = {
  html: () => head('A little more life', 'Make life happen.', 'Discover what’s next, make plans with your people, and share the moments that matter.') + `
  <div class="hero"><div><p class="eyebrow">✦ YOUR AI CONCIERGE</p><h2>Good things<br>are just around the corner.</h2><p>From a gig and dinner to a whole weekend — tell us your vibe.</p>
    <form id="heroform" class="heroform"><input name="query" placeholder="Plan a weekend with live music and dinner in my city" required maxlength="1200"><button class="primary">Ask LifeCanvas ↗</button></form>
    <div class="chips"><button class="chip" data-run="Find live music and a good dinner this weekend" data-workflow="weekend">Weekend plans</button><button class="chip" data-go="dining">Food discovery</button><button class="chip" data-go="circles">Meet my people</button><button class="chip" data-go="travel">Plan an escape</button></div></div></div>
  <div id="todaylive">${loading('Loading today’s live picks…')}</div>
  <div class="sectionhead"><h2>What are you in the mood for?</h2><button data-go="events">Explore all experiences ↗</button></div>
  <div class="grid">${tile('music', 'MUSIC & LIVE', 'The sound of the city', 'Find gigs, festivals and your next favourite artist.', 'data-go="events" data-tabgo="music"')}${tile('sports', 'SPORTS', 'Game day energy', 'Upcoming fixtures for your teams and leagues.', 'data-go="events" data-tabgo="sports"')}${tile('food', 'FOOD & DRINK', 'A taste of something new', 'Restaurants, cafes and bars near you.', 'data-go="dining"')}</div>
  <div class="sectionhead"><h2>From idea to experience</h2><button data-go="orchestra">Open the orchestrator ↗</button></div>
  <div class="split"><div class="panel" id="todayruns">${loading('Loading recent activity…')}</div><div class="panel"><h3>How it works</h3>${row('01', 'Discover', 'Specialist agents search live sources in parallel')}${row('02', 'Make a plan', 'Save results and build your itinerary')}${row('03', 'Make it happen', 'Approve every external action yourself')}</div></div>`,
  async load() {
    const d = await api(`today?city=${encodeURIComponent(city())}&country=${encodeURIComponent(country())}`);
    if (state.page !== 'today') return;
    const w = d.weather?.cards || [];
    const now = w.find(c => c.meta.current), days = w.filter(c => !c.meta.current).slice(0, 5);
    const weather = !d.city ? '<div class="panel"><h3>Weather</h3><p class="small">Set your city in the top bar to see the live forecast here.</p></div>'
      : d.weather.ok ? `<div class="panel weatherpanel"><span class="label">${esc(now?.provider || '')} · live</span><h3>${esc(now?.title || d.city)}</h3><p class="small">${esc(now?.summary || '')}</p><div class="forecast">${days.map(c => `<div class="${c.meta.outdoor_ok ? 'fine' : ''}"><strong>${esc(new Date(c.when + 'T12:00').toLocaleDateString([], { weekday: 'short' }))}</strong><span>${esc(c.meta.condition || '')}</span><b>${esc(Math.round(c.meta.t_max))}° / ${esc(Math.round(c.meta.t_min))}°</b><small>${esc(c.meta.rain_probability ?? '–')}% rain</small></div>`).join('')}</div></div>`
      : `<div class="panel"><h3>Weather</h3>${noticesHtml({ errors: [d.weather.error] })}</div>`;
    const approvals = d.pending_approvals.length ? `<div class="notice warn"><strong>${d.pending_approvals.length} action${d.pending_approvals.length === 1 ? '' : 's'} awaiting your approval.</strong> <button class="linkbtn" data-go="actions">Review in the Action Center ↗</button></div>` : '';
    const prefs = Object.entries(d.preferences).flatMap(([k, v]) => v.map(x => `<span class="tag">${esc(k.replace('_', ' '))}: ${esc(x)}</span>`)).join('');
    $('#todaylive').innerHTML = `${approvals}<div class="split spaced">${weather}<div class="panel"><h3>Personalised for you</h3>${prefs ? `<div>${prefs}</div><p class="small">Stated preferences shape ranking across every workspace.</p>` : '<p class="small">Tell the concierge what you love (“I love Thai food”, “I support Arsenal”) and it will remember — with your permission to review or delete anything.</p>'}<button class="linkbtn" data-go="memory">Manage memory ↗</button>
      ${d.plans.length ? `<h3 class="spaced">Saved plans</h3>${d.plans.map((p, i) => `<div class="flowrow"><div class="num">${i + 1}</div><div><strong>${esc(p.title)}</strong><p>${esc(p.data?.provider || p.kind)}${p.starts ? ' · ' + esc(p.starts) : ''}</p></div></div>`).join('')}` : ''}</div></div>
      <div class="sectionhead"><h2>Upcoming fixtures</h2><span class="small">TheSportsDB · live</span></div>${d.fixtures.ok ? (cardsHtml(d.fixtures.cards.slice(0, 4)) || empty('No fixtures returned right now')) : noticesHtml({ errors: [d.fixtures.error] })}
      <div class="sectionhead"><h2>Top movies right now</h2><span class="small">iTunes chart · live</span></div>${d.movies.ok ? (cardsHtml(d.movies.cards.slice(0, 4)) || empty('No chart returned right now')) : noticesHtml({ errors: [d.movies.error] })}`;
    $('#todayruns').innerHTML = `<h3>Recent activity</h3>${d.recent_runs.length ? d.recent_runs.map(r => `<div class="flowrow"><div><strong>${esc(r.goal.slice(0, 70))}</strong><p>${pill(r.status)} ${esc(ago(r.created))}</p></div><button class="secondary" data-openrun="${esc(r.id)}">Open</button></div>`).join('') : '<p class="small">Your runs will appear here. Start with the box above.</p>'}`;
  },
};

// ------------------------------------------------------------------------------------------------ AI concierge
export const assistant = {
  html: () => head('Conversational intelligence', 'Your AI concierge', 'Ask naturally. Watch the specialists work, inspect the evidence, and approve anything that leaves the app.') + `
  <div class="split"><div class="panel"><div class="sectionhead"><h2>Conversation</h2><div class="formrow tight"><select id="threadpick" aria-label="Conversation"><option value="">New conversation</option></select><button class="secondary" id="newthread">New</button></div></div>
    <div id="chat" aria-live="polite"><div class="bubble">Hi! I can find events, sport, films, music, places to eat, travel ideas, books and art, research a question with citations, or draft something for you to publish. What would you like to do?</div></div>
    <form id="askform" class="formrow"><input id="askq" placeholder="Find jazz this weekend and a vegetarian dinner nearby" required maxlength="1200" autocomplete="off"><button class="primary" id="askbtn">Send ↗</button></form>
    <div class="chips"><button class="chip" data-ask="Find live music and a good dinner this weekend">Music + dinner</button><button class="chip" data-ask="What is the weather and what are the best things to see?">Weather + sights</button><button class="chip" data-ask="Write a LinkedIn post about slow travel and publish it">Draft a post</button><button class="chip" data-ask="Explain the history of jazz with sources">Research with citations</button></div></div>
  <div class="panel"><h3>Agent activity</h3>${pipelineHtml()}<div id="trace" class="steps empty">Specialist routing and tool execution stream here in real time.</div></div></div>
  <div id="answer" class="spaced"></div>`,
  async load() {
    const t = await api('threads');
    const pick = $('#threadpick');
    if (!pick) return;
    pick.innerHTML = '<option value="">New conversation</option>' + t.threads.map(x => `<option value="${esc(x.id)}" ${x.id === state.thread ? 'selected' : ''}>${esc(x.title.slice(0, 48))}</option>`).join('');
    if (state.thread) await assistant.showThread(state.thread);
  },
  async showThread(id) {
    const d = await api('threads/' + id);
    const chat = $('#chat');
    if (!chat) return;
    chat.innerHTML = d.messages.map(m => `<div class="bubble ${m.role === 'user' ? 'user' : ''}">${esc(m.body)}${m.role !== 'user' && m.meta.run_id ? ` <button class="linkbtn" data-openrun="${esc(m.meta.run_id)}">Show results ↗</button>` : ''}</div>`).join('') || '<div class="bubble">This conversation is empty.</div>';
    chat.scrollTop = chat.scrollHeight;
  },
};

// ------------------------------------------------------------------------------------------------ Discovery workspaces
const DISCOVER = {
  events: {
    domain: 'entertainment', head: ['Tickets, culture & play', 'Go somewhere great.', 'Concerts, sport, cinema, shows and music from live sources.'], art: ['music', 'sports', 'film'],
    tabs: [['events', 'Live events'], ['sports', 'Sport'], ['movies', 'Movies'], ['shows', 'TV shows'], ['music', 'Music'], ['artists', 'Artists']],
    form: tab => ({ events: ['Genre, artist or festival', 'jazz'], sports: ['Team (optional)', ''], movies: ['Movie title (leave empty for charts)', ''], shows: ['Show title', 'Sherlock'], music: ['Song, artist or genre', 'indie'], artists: ['Artist name', 'Coldplay'] }[tab]),
    extra: tab => tab === 'sports' ? '<select id="f-sport" aria-label="Sport"><option value="football">Football</option><option value="cricket">Cricket</option><option value="basketball">Basketball</option></select>' : '',
    filters(tab, q) {
      return { events: { wants_events: true, topic: q, genres: q ? [q.toLowerCase()] : [] }, sports: { sport: $('#f-sport')?.value || 'football', team: q }, movies: { wants_movies: true, topic: q }, shows: { wants_shows: true, topic: q },
        music: { wants_music: true, topic: q }, artists: { wants_music: true, topic: q } }[tab];
    },
    keep: tab => ({ events: c => c.kind === 'event', sports: c => ['fixture', 'team'].includes(c.kind), movies: c => c.kind === 'movie', shows: c => c.kind === 'show', music: c => ['track', 'album'].includes(c.kind), artists: c => c.kind === 'artist' }[tab]),
  },
  dining: {
    domain: 'dining', head: ['Taste & discover', 'Find your next favourite bite.', 'Restaurants, cafes and bars near you, with cuisine and dietary filters.'], art: ['food', 'food', 'food'],
    tabs: [['restaurant', 'Restaurants'], ['cafe', 'Cafes'], ['bar', 'Bars'], ['fast_food', 'Quick bites']],
    form: () => ['Cuisine (optional)', ''],
    extra: () => `<select id="f-diet" aria-label="Dietary need"><option value="">Any diet</option><option value="vegetarian">Vegetarian</option><option value="vegan">Vegan</option><option value="halal">Halal</option><option value="gluten-free">Gluten-free</option></select><select id="f-sort" aria-label="Sort"><option value="best">Best match</option><option value="name">Name</option><option value="hours">Has opening hours</option></select>`,
    filters: (tab, q) => ({ amenity: tab, cuisines: q ? [q.toLowerCase()] : [], diets: $('#f-diet').value ? [$('#f-diet').value] : [] }),
    keep: () => c => c.kind === 'place',
  },
  culture: {
    domain: 'culture', head: ['Culture, curiosity & motion', 'Find your next obsession.', 'Books, museum collections and your own activity, from open cultural sources.'], art: ['film', 'music', 'film'],
    tabs: [['books', 'Books'], ['art', 'Art & museums'], ['fitness', 'Movement']],
    form: tab => ({ books: ['Topic, title or author', 'slow travel'], art: ['Artist, movement or subject', 'impressionism'], fitness: ['', ''] }[tab]),
    extra: () => '',
    filters: (tab, q) => ({ books: { wants_books: true, topic: q }, art: { wants_art: true, topic: q }, fitness: { wants_fitness: true } }[tab]),
    keep: tab => ({ books: c => c.kind === 'book', art: c => c.kind === 'artwork', fitness: c => ['activity', 'weather', 'forecast'].includes(c.kind) }[tab]),
  },
};
const tabState = { events: 'events', dining: 'restaurant', culture: 'books' };

function discoveryPage(page) {
  const cfg = DISCOVER[page];
  return {
    html() {
      const tab = tabState[page], [ph, val] = cfg.form(tab);
      return head(...cfg.head) + needCity() + `<div class="panel">${tabs(cfg.tabs, tab)}
        <form id="discoverform" class="formrow filters" data-page="${page}">${ph ? `<input id="discoverq" placeholder="${esc(ph)}" value="${esc(val)}" maxlength="120" aria-label="${esc(ph)}">` : '<span class="small grow">Shows your own recent Strava activities and today’s conditions for getting outside.</span>'}${cfg.extra(tab)}<button class="primary">Discover ↗</button></form>
        <div id="discoverresults">${empty('Search live sources', 'Results show the provider, a source link and when they were retrieved.')}</div></div>`;
    },
    async load() { if (page !== 'dining' || city()) await this.search(); },
    async search() {
      const box = $('#discoverresults'), tab = tabState[page];
      if (!box) return;
      const q = ($('#discoverq')?.value || '').trim();
      box.innerHTML = loading('Asking the specialist to search live providers…') + skeleton(4);
      try {
        const r = await post('discover', { domain: cfg.domain, query: q, city: city(), country: country(), filters: cfg.filters(tab, q) });
        if (state.page !== page || tabState[page] !== tab) return;
        let keep = cfg.keep(tab);
        const sort = $('#f-sort')?.value;
        if (sort === 'name') r.cards.sort((a, b) => a.title.localeCompare(b.title));
        if (sort === 'hours') { const base = keep; keep = c => base(c) && c.meta.opening_hours; }
        box.innerHTML = sectionHtml(r, { filter: keep }) + `<details class="issues"><summary>How this was found (${r.trace.length} steps)</summary><ol class="tracelist">${r.trace.map(t => `<li><strong>${esc(t.node)}</strong> — ${esc(t.summary)}</li>`).join('')}</ol></details>`;
      } catch (e) { box.innerHTML = errorBox(e, 'data-retry-discover'); }
    },
  };
}
export const events = discoveryPage('events');
export const dining = discoveryPage('dining');
export const culture = discoveryPage('culture');
export const setTab = (page, tab) => { tabState[page] = tab; };

// ------------------------------------------------------------------------------------------------ Travel
export const travel = {
  html: () => head('Your next little escape', 'The world is waiting.', 'Live weather, destination guides and sights; flight offers when Amadeus is connected; bookings finish with the provider.') + `
  <div class="grid">${tile('hero', 'ESCAPE', 'Weekend getaway', 'Forecast, guide and sights for a short trip.', 'data-dest="Goa"', 'Try Goa ↗')}${tile('food', 'CITY BREAK', 'Culture and food', 'Landmarks and a guide to the old city.', 'data-dest="Jaipur"', 'Try Jaipur ↗')}${tile('sports', 'OUTDOORS', 'Mountains and air', 'Check conditions before you go.', 'data-dest="Manali"', 'Try Manali ↗')}</div>
  <div class="panel spaced"><h3>Build a trip</h3><form id="travelform" class="formrow filters"><input id="t-origin" placeholder="From (city or IATA)" value="${esc(city())}" aria-label="Origin" maxlength="60"><input id="t-dest" placeholder="To (destination)" required aria-label="Destination" maxlength="60"><input id="t-date" type="date" aria-label="Departure date"><label class="checkline"><input type="checkbox" id="t-flights"> Flights</label><button class="primary">Plan ↗</button></form>
  <div id="travelresults">${empty('Choose a destination', 'You will get the live forecast, a destination guide, nearby landmarks and app handoffs for booking.')}</div></div>`,
  async load() {},
  async search() {
    const box = $('#travelresults'), dest = $('#t-dest').value.trim();
    if (!dest) return;
    box.innerHTML = loading(`Checking weather, guides and sights for ${dest}…`) + skeleton(4);
    try {
      const date = $('#t-date').value;
      const r = await post('discover', { domain: 'travel', query: `trip to ${dest}`, city: dest, country: '', filters: { destination: dest, origin: $('#t-origin').value.trim(), wants_flights: $('#t-flights').checked, when: date ? { label: date, start: date, end: date } : {} } });
      if (state.page !== 'travel') return;
      const by = k => r.cards.filter(c => k.includes(c.kind));
      const wx = by(['weather', 'forecast']);
      const forecast = wx.length ? `<div class="panel weatherpanel inner"><span class="label">${esc(wx[0].provider)} · live</span><h3>${esc(wx[0].title)}</h3><p class="small">${esc(wx[0].summary)}</p><div class="forecast">${wx.filter(c => !c.meta.current).map(c => `<div class="${c.meta.outdoor_ok ? 'fine' : ''}"><strong>${esc(c.when.slice(5, 10))}</strong><span>${esc(c.meta.condition || '')}</span><b>${esc(c.meta.t_max ?? c.meta.temperature_c ?? '')}°</b><small>${c.meta.rain_probability != null ? esc(c.meta.rain_probability) + '% rain' : ''}</small></div>`).join('')}</div></div>` : '';
      const group = (title, cards) => cards.length ? `<div class="sectionhead"><h2>${title}</h2><span class="small">${cards.length}</span></div>${cardsHtml(cards)}` : '';
      box.innerHTML = noticesHtml(r) + forecast + group('Flight offers', by(['flight'])) + group('Destination guide', by(['guide'])) + group('Sights and landmarks', by(['attraction'])) + handoffsHtml(r.handoffs)
        + (!r.cards.length ? empty('Nothing came back for that destination', 'Check the spelling or try a nearby city.') : '');
    } catch (e) { box.innerHTML = errorBox(e, 'data-retry-travel'); }
  },
};

// ------------------------------------------------------------------------------------------------ Circles
export const circles = {
  html: () => head('Meet your kind of people', 'Find your circle.', 'Connect through shared interests at city level. You decide whether you are discoverable; exact location and contact details are never shared.') + `
  <div class="split"><div class="panel"><h3>People who share your interests</h3><div class="field"><label for="interests">Interests (comma separated)</label><input id="interests" placeholder="jazz, running, coffee" maxlength="200"></div>
    <button class="primary" id="matchbtn">Find my people ↗</button><div id="matches" class="results">${empty('Only real, opted-in members appear here', 'There are no sample or fictional profiles.')}</div></div>
  <div class="panel"><h3>Your opt-in profile</h3><div class="field"><label for="pname">Display name</label><input id="pname" maxlength="40"></div><div class="field"><label for="pcity">City</label><input id="pcity" maxlength="60"></div>
    <div class="field"><label for="pinterests">Your interests</label><input id="pinterests" placeholder="jazz, hiking, board games" maxlength="300"></div><div class="field"><label for="pbio">Bio</label><textarea id="pbio" maxlength="280" placeholder="What do you like doing? No contact details."></textarea></div>
    <label class="checkline"><input type="checkbox" id="adult"> I confirm I am 18 or older.</label><label class="checkline"><input type="checkbox" id="optin"> Make my profile discoverable to other members.</label>
    <button id="saveprofile" class="primary spaced">Save profile</button>
    <div class="sectionhead"><h2>Requests & connections</h2><button id="refreshinbox">Refresh</button></div><div id="inbox">${loading('Loading…')}</div></div></div>
  <div class="split spaced"><div class="panel"><h3>Plan together</h3><p class="small">Your agent and your connections' agents agree on an option that fits everyone. Agents share only yes or no per option, never your budget or dates.</p>
    <div class="field"><label for="m-title">What are you planning?</label><input id="m-title" placeholder="Saturday out" maxlength="120"></div>
    <div class="field"><label for="m-options">Options, one per line: title | date (YYYY-MM-DD) | cost per person | tags</label><textarea id="m-options" placeholder="Jazz club | 2026-12-05 | 1800 | jazz, music&#10;Rooftop dinner | 2026-12-06 | 900 | food"></textarea></div>
    <div class="field"><label for="m-invitees">Invite (your connections)</label><select id="m-invitees" multiple size="3"></select></div>
    <h3 class="spaced">Your private limits</h3><div class="formrow filters"><input id="m-budget" type="number" min="0" step="any" placeholder="Max per person" aria-label="Max budget per person"><input id="m-dates" placeholder="Free dates, comma separated" aria-label="Free dates"><input id="m-interests" placeholder="Interests" aria-label="Interests"></div>
    <button class="primary" id="meetupcreate">Ask the agents ↗</button></div>
  <div class="panel"><h3>Meetups</h3><div id="meetups">${loading('Loading meetups…')}</div></div></div>`,
  async load() {
    const [p, c] = await Promise.all([api('community/profile'), api('community/connections')]);
    if (state.page !== 'circles') return;
    const pr = p.profile;
    if (pr) { $('#pname').value = pr.display_name; $('#pcity').value = pr.city; $('#pinterests').value = pr.interests.join(', '); $('#pbio').value = pr.bio; $('#adult').checked = !!pr.adult_confirmed; $('#optin').checked = !!pr.discoverable; $('#interests').value = pr.interests.join(', '); }
    else { $('#pname').value = state.user.name; $('#pcity').value = city(); }
    circles.inbox(c);
    $('#m-invitees').innerHTML = c.connected.map(x => `<option value="${esc(x.user_id)}">${esc(x.display_name)}</option>`).join('') || '<option disabled>No connections yet</option>';
    circles.meetups((await api('meetups')).meetups);
  },
  limits: prefix => { const v = id => ($(id)?.value || '').trim(); const out = {}; if (v(`#${prefix}budget`)) out.max_budget = Number(v(`#${prefix}budget`)); if (v(`#${prefix}dates`)) out.dates = v(`#${prefix}dates`).split(',').map(x => x.trim()).filter(Boolean); if (v(`#${prefix}interests`)) out.interests = v(`#${prefix}interests`).split(',').map(x => x.trim()).filter(Boolean); return out; },
  meetups(list) {
    const box = $('#meetups');
    if (!box) return;
    const label = { collecting: ['Waiting for limits', 'info'], proposed: ['Agents agreed', 'ok'], confirmed: ['Confirmed', 'ok'], no_agreement: ['No option fits everyone', 'warn'] };
    box.innerHTML = list.map(m => { const [text, tone] = label[m.status] || [m.status, 'muted']; const me = m.members.find(x => x.user_id !== undefined && m.my_constraints !== undefined); return `<div class="result" data-meetup="${esc(m.id)}"><div class="sectionhead"><h2>${esc(m.title)}</h2><span class="pill ${tone}">${esc(text)}</span></div>
      <p class="small">${m.members.map(x => `${esc(x.name)}${x.confirmed ? ' ✓' : x.ready ? '' : ' (limits pending)'}`).join(' · ')}</p>
      ${m.chosen ? `<div class="notice ok"><strong>${esc(m.chosen.title)}</strong>${m.chosen.date ? ' · ' + esc(m.chosen.date) : ''}${m.chosen.cost_per_person != null ? ` · ${esc(m.chosen.cost_per_person)} ${esc(m.chosen.currency)} per person` : ''}<br>${esc(m.outcome.explanation || '')}</div>` : m.outcome?.explanation ? `<div class="notice">${esc(m.outcome.explanation)}</div>` : ''}
      ${(m.outcome?.rounds || []).length ? `<div class="trace">${m.outcome.rounds.map(r => { const o = m.options.find(x => x.id === r.option); return `<span class="${r.all_accept ? '' : 'bad'}">${esc(o?.title || r.option)}: ${r.accepted_by}/${r.of} agents accept</span>`; }).join('')}</div>` : ''}
      ${m.my_constraints === null ? `<div class="formrow filters"><input id="j-${esc(m.id)}-budget" type="number" min="0" step="any" placeholder="Max per person"><input id="j-${esc(m.id)}-dates" placeholder="Free dates"><input id="j-${esc(m.id)}-interests" placeholder="Interests"><button class="secondary" data-meetuplimits="${esc(m.id)}">Share with my agent</button></div><p class="small">Your limits stay private. Other members only see whether an option works.</p>` : ''}
      <div class="formrow">${['proposed', 'confirmed'].includes(m.status) && !m.members.every(x => x.confirmed) ? `<button class="primary" data-meetupconfirm="${esc(m.id)}">Confirm for me</button>` : ''}${safeUrl(m.video_call) ? `<a class="chip primarychip" href="${safeUrl(m.video_call)}" target="_blank" rel="noopener noreferrer">Join group video call ↗</a>` : ''}</div></div>`; }).join('')
      || empty('No meetups yet', 'Connect with a member, then add a few options on the left.');
  },
  inbox(c) {
    const item = (x, buttons) => `<div class="flowrow"><div class="avatar">${esc(x.display_name[0] || '?')}</div><div><strong>${esc(x.display_name)}</strong><p>${esc(x.city)} · ${esc(x.interests.slice(0, 4).join(', '))}${x.message ? `<br>“${esc(x.message)}”` : ''}</p></div>${buttons}</div>`;
    const safety = id => `<button class="mini" data-block="${esc(id)}">Block</button><button class="mini" data-report="${esc(id)}">Report</button>`;
    $('#inbox').innerHTML = (c.incoming.map(x => item(x, `<button class="secondary" data-respond="${esc(x.id)}" data-accept="1">Accept</button><button class="mini" data-respond="${esc(x.id)}" data-accept="">Decline</button>${safety(x.user_id)}`)).join('')
      + c.connected.map(x => item(x, `<span class="pill ok">Connected</span><button class="secondary" data-call="${esc(x.user_id)}">Video call</button>${safety(x.user_id)}`)).join('') + c.outgoing.map(x => item(x, '<span class="pill info">Request sent</span>')).join('')
      + (c.blocked.length ? `<p class="small spaced">Blocked: ${c.blocked.map(b => `${esc(b.display_name)} <button class="linkbtn" data-unblock="${esc(b.user_id)}">Unblock</button>`).join(', ')}</p>` : ''))
      || '<p class="small">No requests yet. Requests only reach members who opted in, and either side can block or report at any time.</p>';
  },
  async match() {
    const box = $('#matches');
    box.innerHTML = loading('Matching opted-in members…');
    try {
      const d = await api(`community/matches?interests=${encodeURIComponent($('#interests').value)}&city=${encodeURIComponent(city())}`);
      if (!d.profile?.discoverable) box.insertAdjacentHTML('afterbegin', '');
      box.innerHTML = d.matches.map((m, i) => `<div class="result"><div class="match"><div class="avatar" style="background:${['#ffe58a', '#cfeaff', '#d9f3cf', '#ffd6dc'][i % 4]}">${esc(m.display_name[0])}</div><div><h3>${esc(m.display_name)}</h3><span class="small">${esc(m.city)}${m.same_city ? ' · your city' : ''}</span></div><span class="score">${Math.round(m.score * 100)}% match</span></div>
        <p>${esc(m.bio)}</p><div>${m.shared.map(x => `<span class="tag">${esc(x)}</span>`).join('')}</div>
        <div class="formrow">${m.connection === 'none' ? `<button class="secondary" data-invite="${esc(m.user_id)}">Send connection request</button>` : pill(m.connection === 'accepted' ? 'completed' : 'pending')}<button class="mini" data-block="${esc(m.user_id)}">Block</button><button class="mini" data-report="${esc(m.user_id)}">Report</button></div></div>`).join('')
        || empty(d.profile?.discoverable ? 'No opted-in members share those interests yet' : 'No matches yet', d.profile?.discoverable ? 'Matches appear as more members opt in. Try broader interests.' : 'Save an opt-in profile on the right to send requests. Only real members who chose to be discoverable are shown.');
    } catch (e) { box.innerHTML = errorBox(e); }
  },
};

// ------------------------------------------------------------------------------------------------ Creator studio
const studioState = { platforms: new Set(['linkedin']), result: null };
export const studio = {
  state: studioState,
  html: () => head('From inspiration to expression', 'Creator studio.', 'Research, draft, adapt for each platform, then approve exactly what gets published.') + `
  <div class="split"><div class="panel"><h3>Create a campaign</h3><div class="platforms" id="platformpick">${['x', 'linkedin', 'bluesky', 'mastodon', 'facebook', 'instagram', 'wordpress', 'telegram', 'discord', 'slack', 'gmail'].map(t => `<button data-target="${t}" class="${studioState.platforms.has(t) ? 'selected' : ''}">${label(t)}</button>`).join('')}</div>
    <div class="field"><label for="topic">Topic</label><input id="topic" placeholder="Slow travel in Hampi" maxlength="200"></div><div class="field"><label for="notes">Your notes (optional — your own words are used first)</label><textarea id="notes" maxlength="2000" placeholder="What do you want to say?"></textarea></div>
    <div class="formrow filters"><select id="tone" aria-label="Tone"><option value="warm">Warm</option><option value="professional">Professional</option><option value="playful">Playful</option><option value="bold">Bold</option></select><label class="checkline"><input type="checkbox" id="skipresearch"> Skip research</label></div>
    <div id="studioextra"></div><button class="primary" id="draftbtn">✦ Research & draft</button>
    <div class="sectionhead"><h2>Workflow</h2></div>${row('01', 'Research', 'Read-only sources with verified citations')}${row('02', 'Draft & adapt', 'One draft, fitted to each platform’s limits')}${row('03', 'Critique', 'Citations, length, safety checks')}${row('04', 'Approve', 'Nothing is published without you')}</div>
  <div class="panel"><h3>Drafts & review</h3><div id="studioout">${studioState.result ? studio.render(studioState.result) : empty('No draft yet', 'A draft never posts by itself. You review and edit every variant first.')}</div></div></div>`,
  async load() { studio.extra(); },
  extra() {
    const p = studioState.platforms, box = $('#studioextra');
    if (!box) return;
    box.innerHTML = (p.has('gmail') ? '<div class="field"><label for="s-to">Recipient email</label><input id="s-to" type="email" maxlength="254"></div>' : '') + (p.has('slack') ? '<div class="field"><label for="s-channel">Slack channel ID</label><input id="s-channel" placeholder="C0123456789" maxlength="40"></div>' : '')
      + (p.has('instagram') ? '<div class="field"><label for="s-image">Public HTTPS image URL (Instagram requires an image)</label><input id="s-image" placeholder="https://…" maxlength="800"></div>' : '');
  },
  render(r) {
    const c = r.creative;
    return `<p class="small">${c.mode === 'model' ? `Written by ${esc(c.draft.model || 'a language model')}.` : 'No language model is connected: this draft is assembled from your topic, your notes and cited source extracts. Edit freely.'} ${pill(r.status)}</p>
    ${noticesHtml(r)}${c.critique.issues.length ? `<div class="notice error">Review found: ${c.critique.issues.map(esc).join('; ')}</div>` : ''}
    ${c.variants.map((v, i) => `<div class="result variant" data-variant="${i}"><div class="sectionhead"><h2>${esc(label(v.platform))}</h2><span class="small"><span data-count>${v.chars}</span> / ${v.limit}</span></div>
      ${v.payload.title != null ? `<div class="field"><label>Title</label><input data-field="title" value="${esc(v.payload.title)}" maxlength="200"></div>` : ''}${v.payload.subject != null ? `<div class="field"><label>Subject</label><input data-field="subject" value="${esc(v.payload.subject)}" maxlength="200"></div>` : ''}
      <div class="field"><label>Exact content</label><textarea data-field="text" maxlength="${v.limit}">${esc(v.payload.text)}</textarea></div>${v.needs ? `<div class="notice">Add a ${esc(v.needs)} on the left and draft again to propose this one.</div>` : ''}
      <label class="checkline"><input type="checkbox" data-include ${v.needs ? 'disabled' : 'checked'}> Include in approval request</label></div>`).join('')}
    <button class="primary" id="sendapproval">Send to approval ↗</button>
    <h3 class="spaced">Research evidence</h3>${cardsHtml(r.cards.slice(0, 4), { save: false }) || '<p class="small">No sources were used.</p>'}
    <details class="issues"><summary>Angles, outline and trace</summary><p class="small"><strong>Angles</strong></p><ul>${c.angles.map(a => `<li>${esc(a)}</li>`).join('')}</ul><p class="small"><strong>Outline</strong></p><ol>${c.outline.map(a => `<li>${esc(a)}</li>`).join('')}</ol><ol class="tracelist">${r.trace.map(t => `<li><strong>${esc(t.node)}</strong> — ${esc(t.summary)}</li>`).join('')}</ol></details>`;
  },
};

// ------------------------------------------------------------------------------------------------ My plans
export function budgetHtml(b) {
  const line = x => `<div class="flowrow"><div><strong>${esc(x.title)}</strong><p>${esc(x.category || x.kind)} · ${esc(x.provider || '')}</p></div><span class="price">${esc(x.price)} ${esc(x.currency)}</span>${safeUrl(x.url) ? `<a class="mini" href="${safeUrl(x.url)}" target="_blank" rel="noopener noreferrer">${x.booking === 'approval' ? 'View offer ↗' : 'Provider checkout ↗'}</a>` : ''}</div>`;
  return `<div class="kpis"><div><strong>${esc(b.total)} ${esc(b.currency)}</strong><span>Plan total</span></div><div><strong>${esc(b.remaining)} ${esc(b.currency)}</strong><span>Left of ${esc(b.budget)}</span></div><div><strong>${b.selected.length}</strong><span>Items chosen</span></div><div><strong>${b.price_to_confirm.length}</strong><span>Price to confirm</span></div></div>
  ${b.selected.length ? b.selected.map(line).join('') : empty('Nothing with a known price fits this budget', 'Raise the budget or save more priced results.')}
  ${b.price_to_confirm.length ? `<h3 class="spaced">Price to confirm with the provider</h3>${b.price_to_confirm.map(x => `<div class="flowrow"><div><strong>${esc(x.title)}</strong><p>${esc(x.kind)} · ${esc(x.provider)} · no price supplied</p></div>${safeUrl(x.url) ? `<a class="mini" href="${safeUrl(x.url)}" target="_blank" rel="noopener noreferrer">Check price ↗</a>` : ''}</div>`).join('')}` : ''}
  ${b.other_currency.length ? `<p class="small">Not counted (different currency, no conversion assumed): ${b.other_currency.map(x => `${esc(x.title)} (${esc(x.price)} ${esc(x.currency)})`).join(', ')}</p>` : ''}<p class="small">${esc(b.note)}</p>`;
}

export const planner = {
  html: () => head('Make time for what matters', 'My plans.', 'Collect what you find, then turn confirmed details into calendar entries, tasks or a playlist — each with your approval.') + `
  <div class="split"><div class="panel"><h3>Saved ideas</h3><div id="saved">${loading('Loading your plans…')}</div><form id="planform" class="formrow"><input id="planname" placeholder="Add a personal idea" required maxlength="160"><input id="plandate" type="date" aria-label="Date"><button class="primary">Add</button></form></div>
  <div class="panel"><h3>Calendar event</h3><div class="field"><label for="caltitle">Event title</label><input id="caltitle" placeholder="Concert and dinner" maxlength="200"></div><div class="formrow"><div class="field grow"><label for="calstart">Start</label><input id="calstart" type="datetime-local"></div><div class="field grow"><label for="calend">End</label><input id="calend" type="datetime-local"></div></div>
    <div class="field"><label for="calloc">Location (optional)</label><input id="calloc" maxlength="300"></div><button class="primary" id="calendarbtn">Review calendar event ↗</button>
    <h3 class="spaced">Task</h3><div class="formrow"><input id="tasktitle" placeholder="Book tickets for Saturday" maxlength="200"><select id="taskapp" aria-label="Task app"><option value="google_tasks">Google Tasks</option><option value="todoist">Todoist</option><option value="ms_graph">Microsoft To Do</option></select><button class="secondary" id="taskbtn">Review task</button></div>
    <p class="small">These create approval requests in the Action Center. They never reserve a ticket or a table.</p><div id="planapproval"></div></div></div>
  <div class="panel spaced"><h3>Budget planner</h3><p class="small">Pick the best combination of your saved ideas that fits a budget. Only prices supplied by the provider are counted.</p>
    <form id="budgetform" class="formrow filters"><input id="budgetamount" type="number" min="1" step="any" placeholder="Budget, e.g. 5000" required aria-label="Budget"><input id="budgetcurrency" placeholder="Currency, e.g. INR" maxlength="3" required aria-label="Currency"><select id="budgetper" aria-label="Choices per category"><option value="1">One per category</option><option value="2">Up to two per category</option><option value="3">Up to three per category</option></select><button class="primary">Plan within budget ↗</button></form>
    <div id="budgetout">${empty('No budget plan yet', 'Save results that carry a price (movies, tracks, flights, ticketed events), then set a budget.')}</div></div>`,
  async load() {
    const d = await api('plans');
    const box = $('#saved');
    if (!box) return;
    box.innerHTML = d.plans.length ? d.plans.map((x, i) => `<div class="flowrow"><div class="num">${i + 1}</div><div><strong>${esc(x.title)}</strong><p>${esc(x.data?.provider || 'Personal idea')}${x.starts ? ' · ' + esc(x.starts) : ''}${x.data?.where ? ' · ' + esc(x.data.where) : ''}</p>${safeUrl(x.data?.url) ? `<a href="${safeUrl(x.data.url)}" target="_blank" rel="noopener noreferrer">Open source ↗</a>` : ''}</div>
      ${x.starts ? `<button class="mini" data-plancal="${esc(x.id)}" data-title="${esc(x.title)}" data-starts="${esc(x.starts)}" data-where="${esc(x.data?.where || '')}">→ Calendar</button>` : ''}<button class="secondary" data-removeplan="${esc(x.id)}">Remove</button></div>`).join('') : empty('Nothing saved yet', 'Use “+ Save” on any result to build your itinerary here.');
  },
};

// ------------------------------------------------------------------------------------------------ Orchestrator
export const orchestra = {
  html: () => head('The intelligence layer', 'One request. Many possibilities.', 'A supervisor plans the work, specialist agents run in parallel, an independent critic checks the evidence, and you approve anything external.') + `
  <div class="hero studiohero"><div><p class="eyebrow">✧ SUPERVISOR ONLINE</p><h2>Make the perfect<br>day happen.</h2><p>Pick a workflow or describe your goal. Every step streams live.</p>
    <div class="chips">${state.boot.workflows.filter(w => w.id !== 'auto').map(w => `<button class="chip" data-workflowpick="${esc(w.id)}" title="${esc(w.about)}">${esc(w.label)}</button>`).join('')}</div></div></div>
  <div class="split spaced"><div class="panel"><h3>Describe your goal</h3><div class="field"><label for="runq">Request</label><textarea id="runq" maxlength="1200" placeholder="Find live music, a vegetarian dinner and check the weather for Saturday"></textarea></div>
    <div class="formrow filters"><select id="workflow" aria-label="Workflow">${state.boot.workflows.map(w => `<option value="${esc(w.id)}">${esc(w.label)}</option>`).join('')}</select><select id="strategy" aria-label="Model routing"><option value="balanced">Balanced routing</option><option value="quality">Quality first</option><option value="cost">Lowest cost</option><option value="latency">Lowest latency</option></select><button class="primary" id="runbtn">✦ Run</button></div>
    <p class="small" id="modelnote"></p></div>
  <div class="panel"><h3>Live pipeline</h3>${pipelineHtml()}<div id="trace" class="steps empty">Steps stream here as the graph executes.</div></div></div>
  <div id="orchestraout" class="spaced"></div><div class="panel spaced"><h3>Run history</h3><div id="runhistory">${loading('Loading runs…')}</div></div>`,
  async load() {
    const m = state.boot.models;
    $('#modelnote').textContent = m.configured.length ? `Model providers connected: ${m.configured.join(', ')}.` : 'No language model is connected: planning, critique and composition use transparent rules, and results still come from live providers.';
    await orchestra.history();
  },
  async history() {
    const d = await api('runs');
    const box = $('#runhistory');
    if (!box) return;
    box.innerHTML = d.runs.length ? d.runs.map(r => `<div class="flowrow"><div><strong>${esc(r.goal.slice(0, 90))}</strong><p>${pill(r.status)} ${esc(r.workflow)} · ${esc(ago(r.created))}</p></div>${['interrupted', 'failed', 'cancelled'].includes(r.status) ? `<button class="mini" data-resume="${esc(r.id)}">Resume</button>` : ''}<button class="secondary" data-openrun="${esc(r.id)}">Open</button></div>`).join('') : empty('No runs yet');
  },
};

// ------------------------------------------------------------------------------------------------ Action center
const TEMPLATES = {
  x: { text: '' }, linkedin: { text: '' }, bluesky: { text: '' }, mastodon: { text: '' }, facebook: { text: '' }, telegram: { text: '' }, discord: { text: '' }, instagram: { text: '', image_url: '' }, slack: { channel: '', text: '' },
  wordpress: { title: '', text: '', status: 'draft' }, gmail: { to: '', subject: '', text: '' }, google_calendar: { title: '', start: '', end: '', location: '' }, google_tasks: { title: '', notes: '' }, todoist: { title: '', notes: '' }, ms_graph: { title: '', notes: '' },
  google_drive: { title: '', text: '' }, notion: { page_id: '', text: '' }, spotify_playlist: { name: '', description: '', tracks: '' },
};
const HINTS = { start: 'ISO date-time with offset, e.g. 2026-12-05T18:00:00+05:30', end: 'ISO date-time with offset', channel: 'Channel ID, e.g. C0123456789', page_id: '32-character Notion page ID', image_url: 'Public HTTPS image URL', tracks: 'One track per line', to: 'One recipient email' };
export const actionDraft = [];
export const actions = {
  html: () => head('Human approval · multi-app actions', 'Action center.', 'Every post, email, calendar entry and task waits here. Inspect the exact content and destination, then approve only what you want.') + `
  <div id="pendingbox">${loading('Loading approvals…')}</div>
  <div class="split spaced"><div class="panel"><h3>Build an action batch</h3><div class="field"><label for="batchtarget">Destination</label><select id="batchtarget">${Object.keys(TEMPLATES).map(t => `<option value="${t}">${label(t)}</option>`).join('')}</select></div><div id="batchfields"></div>
    <button id="batchadd" class="secondary">+ Add to batch</button><div id="batchdraft" class="spaced"></div><button id="batchreview" class="primary spaced">Request approval ↗</button></div>
  <div class="panel"><h3>History & receipts</h3><div id="actionhistory">${loading('Loading history…')}</div></div></div>`,
  fields() {
    const t = $('#batchtarget').value;
    $('#batchfields').innerHTML = Object.entries(TEMPLATES[t]).map(([k]) => `<div class="field"><label for="bf-${k}">${esc(k.replace('_', ' '))}${HINTS[k] ? ` <small>— ${esc(HINTS[k])}</small>` : ''}</label>${['text', 'notes', 'tracks'].includes(k) ? `<textarea id="bf-${k}" data-bf="${k}"></textarea>` : k === 'status' ? '<select id="bf-status" data-bf="status"><option value="draft">Create draft</option><option value="publish">Publish</option></select>' : `<input id="bf-${k}" data-bf="${k}">`}</div>`).join('');
  },
  draft() {
    $('#batchdraft').innerHTML = actionDraft.map((x, i) => `<div class="flowrow"><div class="num">${i + 1}</div><div><strong>${esc(label(x.kind))}</strong><p>${esc(JSON.stringify(x.payload).slice(0, 110))}</p></div><button class="secondary" data-dropbatch="${i}" aria-label="Remove">×</button></div>`).join('') || '<p class="small">No actions in the batch yet.</p>';
  },
  async load() {
    actions.fields();
    actions.draft();
    const d = await api('actions');
    if (state.page !== 'actions') return;
    const pending = d.actions.filter(a => a.status === 'pending'), held = d.actions.filter(a => a.status === 'approved');
    const batches = [...new Set(pending.map(a => a.batch_id))];
    $('#pendingbox').innerHTML = (batches.map(b => `<div class="panel spaced">${approvalHtml(d.actions.filter(a => a.batch_id === b), { title: 'Approval required' })}</div>`).join('') || `<div class="panel">${empty('Nothing is waiting for approval', 'Proposals from the concierge, Creator studio and My plans appear here.')}</div>`)
      + (held.length ? `<div class="panel spaced">${approvalHtml(held, { title: 'Approved and held' })}</div>` : '');
    const done = d.actions.filter(a => !['pending', 'approved'].includes(a.status));
    $('#actionhistory').innerHTML = done.length ? done.slice(0, 30).map(a => `<div class="flowrow"><div><strong>${esc(a.platform)}</strong> ${pill(a.status)}<p>${esc(a.summary || JSON.stringify(a.payload).slice(0, 80))} · ${esc(ago(a.created))}${a.result?.receipt ? ` · receipt ${esc(String(a.result.receipt).slice(0, 18))}` : ''}</p></div><button class="mini" data-ledger="${esc(a.id)}">Ledger</button></div>`).join('') : '<p class="small">Decided actions and their receipts are kept here. Uncertain outcomes are marked “Outcome unknown” and are never retried automatically.</p>';
  },
};

// ------------------------------------------------------------------------------------------------ Memory & safety
const LAYER_INFO = { working: 'Scratchpad for the current conversation', conversation: 'Your threads and turns', episodic: 'What happened in past runs', semantic: 'Verified facts with their sources', procedural: 'Workflows that worked for you', preferences: 'What you told us you like' };
export const memory = {
  html: () => head('Trust, transparency & context', 'Memory & safety.', 'See everything the assistant retains across six layers, delete any of it, and inspect the security controls and audit chain.') + `
  <div class="panel"><div class="sectionhead"><h2>Teach a preference</h2></div><form id="prefform" class="formrow filters"><select id="prefkind" aria-label="Kind"><option value="cuisine">Cuisine</option><option value="diet">Diet</option><option value="artist">Artist</option><option value="team">Team</option><option value="travel_style">Travel style</option><option value="home_city">Home city</option><option value="interest">Interest</option></select><input id="prefvalue" placeholder="e.g. Thai" required maxlength="80"><button class="primary">Remember</button></form>
    <form id="recallform" class="formrow"><input id="recallq" placeholder="Test recall: what would be remembered for “dinner in Delhi”?" maxlength="200"><button class="secondary">Test semantic recall</button></form><div id="recallout"></div></div>
  <div id="memoryout" class="spaced">${loading('Loading memory layers…')}</div><div id="securityout" class="spaced">${loading('Loading security status…')}</div>`,
  async load() {
    const [m, s] = await Promise.all([api('memory'), api('security')]);
    if (state.page !== 'memory') return;
    $('#memoryout').innerHTML = `<div class="grid">${Object.entries(m.layers).map(([k, v]) => `<div class="panel layer"><div class="sectionhead"><h2>${esc(k[0].toUpperCase() + k.slice(1))}</h2><span class="pill muted">${v.length}</span></div><p class="small">${LAYER_INFO[k]}</p>
      ${v.slice(0, 6).map(x => `<div class="memitem"><div><strong>${esc(x.key)}</strong><p>${esc(x.content)}</p>${x.meta?.source ? `<small>${esc(x.meta.source)}</small>` : ''}</div><button class="mini" data-forget="${esc(x.id)}" aria-label="Delete memory">Delete</button></div>`).join('') || '<p class="small">Empty.</p>'}
      ${v.length > 6 ? `<p class="small">+ ${v.length - 6} more</p>` : ''}${v.length ? `<button class="linkbtn" data-forgetlayer="${esc(k)}">Clear this layer</button>` : ''}</div>`).join('')}</div>`;
    $('#securityout').innerHTML = `<div class="split"><div class="panel"><div class="sectionhead"><h2>Security controls</h2>${s.chain.verified ? '<span class="pill ok">Audit chain verified</span>' : '<span class="pill bad">Audit chain broken</span>'}</div>${s.controls.map((c, i) => `<div class="flowrow"><div class="num">${i + 1}</div><div><strong>${esc(c.name)}</strong><p>${esc(c.detail)}</p></div></div>`).join('')}
      <h3 class="spaced">Try the sentinel</h3><form id="screenform" class="formrow"><input id="screenq" placeholder="Paste any text to screen and redact" maxlength="2000"><button class="secondary">Screen</button></form><div id="screenout"></div></div>
      <div class="panel"><h3>Security events</h3>${s.events.map(e => `<div class="flowrow"><div><strong>${esc(e.kind.replace(/_/g, ' '))}</strong><p>${esc((e.detail.rules || []).join(', '))} · ${esc(ago(e.created))}</p></div></div>`).join('') || '<p class="small">No security events for your account.</p>'}
      <h3 class="spaced">Audit log <span class="small">(${s.chain.count} entries, hash-chained)</span></h3><div class="auditlist">${s.audit.slice(0, 14).map(a => `<div class="flowrow"><div><strong>${esc(a.kind)}</strong><p><code>${esc(a.hash.slice(0, 16))}…</code> · ${esc(ago(a.created))}</p></div></div>`).join('') || '<p class="small">No entries yet.</p>'}</div>
      <h3 class="spaced">Your data</h3><p class="small">Delete individual memories above, or erase your account and every record tied to it.</p><button class="secondary danger" id="deleteaccount">Delete my account and data</button></div></div>`;
  },
};

// ------------------------------------------------------------------------------------------------ Developer view
export const developer = {
  html: () => head('Under the hood', 'Developer view.', 'The compiled LangGraph topology, tool allowlists, model routing and telemetry measured on this installation.') + `<div id="devout">${loading('Reading the compiled graph…')}</div>`,
  async load() {
    const [g, t, m, r] = await Promise.all([api('dev/graph'), api('dev/tools'), api('dev/telemetry'), api('runs')]);
    if (state.page !== 'developer') return;
    const flow = (name, nodes) => `<div class="graphline"><strong>${esc(name)}</strong><div class="trace">${nodes.map(n => `<span>${esc(n)}</span>`).join('<i>→</i>')}</div></div>`;
    const ORDER = { action: ['prepare', 'gate', 'decide', 'execute', 'verify'], research: ['plan_queries', 'search', 'extract', 'aggregate', 'synthesise', 'verify', 'revise', 'report'], creative: ['research', 'ideate', 'outline', 'draft', 'adapt', 'critique', 'revise', 'propose'] };
    const disc = ['resolve', 'select', 'act', 'observe', 'rank', 'report'];
    const table = (cols, rows) => rows.length ? `<div class="tablewrap"><table><thead><tr>${cols.map(c => `<th>${esc(c[1])}</th>`).join('')}</tr></thead><tbody>${rows.map(x => `<tr>${cols.map(c => `<td>${esc(x[c[0]] ?? '—')}</td>`).join('')}</tr>`).join('')}</tbody></table></div>` : '<p class="small">No calls recorded yet.</p>';
    $('#devout').innerHTML = `<div class="kpis"><div><strong>${g.nodes.length}</strong><span>Graph nodes (expanded)</span></div><div><strong>${g.edges}</strong><span>Edges</span></div><div><strong>${g.subgraphs.length}</strong><span>Compiled subgraphs</span></div><div><strong>${t.tools.length}</strong><span>Registered tools</span></div></div>
    <div class="panel spaced"><h3>Supervisor graph</h3>${flow('supervisor', ['recall', 'sentinel', 'planner', 'Send → specialists (parallel)', 'critic', 'composer', 'action (interrupt)', 'consolidate'])}<p class="small">Conditional edges: sentinel → refuse when blocked; critic → redispatch for bounded revisions; composer → action only when proposals exist.</p>
      <h3 class="spaced">Specialist subgraphs</h3>${Object.entries(g.specialist_nodes).map(([n, nodes]) => flow(n, (ORDER[n] || disc).filter(x => nodes.includes(x)))).join('')}
      <details class="issues"><summary>Mermaid source of the compiled graph</summary><pre class="preview code">${esc(g.mermaid)}</pre></details></div>
    <div class="split spaced"><div class="panel"><h3>Least-privilege tool allowlists</h3>${Object.entries(t.allowlists).map(([a, list]) => `<div class="graphline"><strong>${esc(a)}</strong><div class="trace">${list.map(x => `<span>${esc(x)}</span>`).join('')}</div></div>`).join('')}
      <div class="graphline"><strong>action <span class="pill warn">write · approval only</span></strong><div class="trace">${t.write_tools.map(x => `<span class="bad">${esc(x)}</span>`).join('')}</div></div></div>
    <div class="panel"><h3>Model routing</h3><p class="small">${state.boot.models.configured.length ? 'Connected: ' + esc(state.boot.models.configured.join(', ')) : 'No model provider is connected. Routes below activate when a key is added; until then agents use rules.'}</p>
      ${table([['provider', 'Provider'], ['name', 'Model'], ['tier', 'Tier'], ['usd_in', '$/M in'], ['usd_out', '$/M out'], ['configured', 'Connected']], state.boot.models.catalog.map(x => ({ ...x, configured: x.configured ? 'yes' : 'no' })))}
      <h3 class="spaced">Runs</h3>${table([['status', 'Status'], ['n', 'Runs'], ['avg_seconds', 'Avg seconds']], m.runs)}</div></div>
    <div class="panel spaced"><h3>Tool telemetry <span class="small">(measured)</span></h3>${table([['agent', 'Agent'], ['tool', 'Tool'], ['provider', 'Provider'], ['calls', 'Calls'], ['ok', 'OK'], ['items', 'Items'], ['avg_latency_ms', 'Avg ms'], ['max_latency_ms', 'Max ms']], m.tools)}</div>
    <div class="split spaced"><div class="panel"><h3>Provider calls <span class="small">(measured)</span></h3>${table([['provider', 'Provider'], ['calls', 'Calls'], ['ok', 'OK'], ['cached', 'Cached'], ['retries', 'Retries'], ['avg_latency_ms', 'Avg ms']], m.providers)}</div>
    <div class="panel"><h3>Model usage <span class="small">(measured)</span></h3>${table([['provider', 'Provider'], ['model', 'Model'], ['agent', 'Agent'], ['calls', 'Calls'], ['prompt_tokens', 'In tokens'], ['completion_tokens', 'Out tokens'], ['cost_usd', 'Cost $']], m.llm)}<p class="small">${esc(m.note)}</p>
      <h3 class="spaced">Checkpoints</h3>${r.runs.slice(0, 5).map(x => `<div class="flowrow"><div><strong>${esc(x.goal.slice(0, 60))}</strong><p>${pill(x.status)}</p></div><button class="mini" data-checkpoints="${esc(x.id)}">Inspect</button></div>`).join('') || '<p class="small">Run something to see its checkpoints.</p>'}</div></div>`;
  },
};

// ------------------------------------------------------------------------------------------------ App connections
let connFilter = 'all';
export const connections = {
  html: () => head('Your ecosystem', 'Connected world.', 'Every provider with its real status. A provider counts as connected only after a live verification call succeeds.') + `<div id="connout">${loading('Reading provider registry…')}</div>`,
  setFilter(f) { connFilter = f; },
  async load() {
    const d = await api('providers');
    if (state.page !== 'connections') return;
    connections.render(d.providers);
  },
  render(list) {
    const counts = {};
    list.forEach(p => { counts[p.status] = (counts[p.status] || 0) + 1; });
    const cats = ['all', ...new Set(list.map(p => p.category))];
    const shown = list.filter(p => connFilter === 'all' || p.category === connFilter || p.status === connFilter);
    $('#connout').innerHTML = `<div class="kpis"><div><strong>${counts.connected_verified || 0}</strong><span>Connected & verified</span></div><div><strong>${counts.configured_unverified || 0}</strong><span>Ready, not yet verified</span></div><div><strong>${counts.configuration_required || 0}</strong><span>Configuration required</span></div><div><strong>${counts.external_handoff || 0}</strong><span>External handoffs</span></div></div>
    <div class="panel spaced"><div class="sectionhead"><h2>Provider registry</h2><button class="secondary" id="verifyall">Verify all configured</button></div>
      <div class="tabs">${cats.map(c => `<button data-connfilter="${esc(c)}" class="${c === connFilter ? 'selected' : ''}">${esc(c)}</button>`).join('')}<button data-connfilter="configuration_required" class="${connFilter === 'configuration_required' ? 'selected' : ''}">needs setup</button></div>
      <div class="providers">${shown.map(p => `<div class="result provider" data-provider="${esc(p.id)}"><div class="sectionhead"><h2>${esc(p.name)}</h2>${pill(p.status)}</div>
        <p class="small">${esc(p.category)} · ${esc(p.access === 'write' ? 'write (approval required)' : p.access === 'llm' ? 'language model' : p.access === 'handoff' ? 'opens the app' : 'read-only')} · ${esc(p.capabilities.join(', '))}</p>
        ${p.auth.missing.length ? `<p class="small"><strong>Add to .env:</strong> ${p.auth.missing.map(k => `<code>${esc(k)}</code>`).join(' ')}</p>` : ''}${p.auth.scopes.length ? `<p class="small">Scopes: ${esc(p.auth.scopes.join(', '))}</p>` : ''}
        ${p.detail && p.status !== 'connected_verified' ? `<p class="small">${esc(p.detail)}</p>` : ''}${p.checked_at ? `<p class="small">Verified ${esc(ago(p.checked_at))}${p.probe_latency_ms ? ` · ${esc(p.probe_latency_ms)} ms` : ''}</p>` : ''}
        ${p.usage.calls ? `<p class="small">${p.usage.calls} calls · ${p.usage.errors} errors · ${p.usage.cached} cached${p.usage.avg_latency_ms ? ` · ${esc(p.usage.avg_latency_ms)} ms avg` : ''}</p>` : ''}
        <div class="cardfoot">${p.access === 'handoff' ? `<a class="mini" href="${safeUrl(p.homepage)}" target="_blank" rel="noopener noreferrer">Open app ↗</a>` : `<button class="mini" data-verify="${esc(p.id)}" ${p.auth.missing.length ? 'disabled' : ''}>Verify now</button>`}${safeUrl(p.docs) ? `<a class="mini" href="${safeUrl(p.docs)}" target="_blank" rel="noopener noreferrer">API docs ↗</a>` : ''}<button class="mini" data-providerdetail="${esc(p.id)}">Details</button></div></div>`).join('')}</div></div>
    <p class="small">Credentials are read from server-side environment variables and never shown here. External handoffs open the provider’s own site or app; LifeCanvasOS does not book, pay or confirm availability on your behalf.</p>`;
    connections.cache = list;
  },
};

export const PAGES = { today, assistant, events, dining, circles, studio, planner, orchestra, culture, travel, actions, memory, developer, connections };
export { runHtml, STATUS, cardHtml };
