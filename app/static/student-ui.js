/* Focused student workspace, deliberately separate from public/auth views. */
const ld = id => document.getElementById(id);
const safe = value => String(value ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
const currentGreeting = () => { const h = new Date().getHours(); return h < 5 ? 'Good night' : h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening'; };
function uiToast(text) { let el = document.querySelector('.v3-toast'); if (!el) { el = document.createElement('div'); el.className = 'v3-toast'; document.body.append(el); } el.textContent = text; el.classList.add('visible'); setTimeout(() => el.classList.remove('visible'), 2600); }
window.v3Notifications = async function v3Notifications() {
  let sheet = ld('studentNotifications'); if (!sheet) { sheet = document.createElement('div'); sheet.id = 'studentNotifications'; sheet.className = 'student-notifications'; document.body.append(sheet); }
  sheet.innerHTML = '<section><button class="student-note-close" onclick="ld(\'studentNotifications\').remove()" aria-label="Close notifications">&times;</button><small>YOUR NOTIFICATIONS</small><h2>Loading your messages…</h2></section>';
  try {
    const data = await api('/api/notifications');
    const items = data.items || [];
    sheet.innerHTML = `<section><button class="student-note-close" onclick="ld('studentNotifications').remove()" aria-label="Close notifications">&times;</button><small>YOUR NOTIFICATIONS</small><h2>${data.unread ? `${data.unread} new message${data.unread === 1 ? '' : 's'}` : 'You’re all caught up.'}</h2><p class="student-note-subtitle">Notes from your teacher or parent appear here.</p><div class="student-note-list">${items.length ? items.map(item => `<article class="${item.read ? '' : 'unread'}"><span>${safe(item.sender_name?.[0] || 'L')}</span><div><small>${safe(item.sender_role || 'LearnDNA')} · ${new Date(item.created_at).toLocaleDateString([], {month:'short', day:'numeric'})}</small><b>${safe(item.title)}</b><p>${safe(item.message)}</p></div></article>`).join('') : '<p class="student-note-empty">No messages yet. Your next update will appear here.</p>'}</div></section>`;
    await Promise.all(items.filter(item => !item.read).map(item => api(`/api/notifications/${item.id}/read`, {method:'POST'})));
  } catch (error) { sheet.innerHTML = `<section><button class="student-note-close" onclick="ld('studentNotifications').remove()" aria-label="Close notifications">&times;</button><small>YOUR NOTIFICATIONS</small><h2>Messages unavailable</h2><p class="student-note-subtitle">${safe(error.message)}</p></section>`; }
};
function iqraDayKey() { const date = new Date(); return `iqra-motivation-v2-${date.getFullYear()}-${date.getMonth() + 1}-${date.getDate()}`; }
function showDailyMotivation(data, firstName) {
  const key = iqraDayKey();
  if (!ld('v3home')) return;
  document.getElementById('iqraMotivationPopup')?.remove();
  const popup = document.createElement('div'); popup.id = 'iqraMotivationPopup'; popup.className = 'iqra-motivation-popup';
  const focus = data.focus || 'your next learning goal';
  popup.innerHTML = `<section role="dialog" aria-modal="true" aria-label="Your daily momentum brief"><button class="motivation-close" onclick="closeMotivationPopup()" aria-label="Close daily brief">&times;</button><header class="momentum-brief-header"><span class="motivation-label">IQRA · DAILY MOMENTUM BRIEF</span><span class="brief-fresh"><i></i> FRESH FOR TODAY</span></header><div class="motivation-layout"><div class="motivation-emblem" aria-hidden="true"><b>IQ</b><i></i><i></i></div><div class="momentum-focus"><small>TODAY'S FOCUS</small><strong>${safe(focus)}</strong><span><i></i><i></i><i></i><i></i><i></i></span></div></div><h2>Make this session count, ${safe(firstName)}.</h2><blockquote><span>YOUR ADAPTIVE CUE</span><p>${safe(data.quote)}</p></blockquote><div class="momentum-note"><b>Why this matters</b><p>Iqra has shaped today’s focus from your progress, active missions, and the skill that needs your attention now.</p></div><div class="motivation-actions"><button onclick="startMotivationPlan()">Open today’s plan <span>&rarr;</span></button><button class="motivation-later" onclick="closeMotivationPopup()">Save this for later</button></div></section>`;
  document.body.append(popup); requestAnimationFrame(() => popup.classList.add('visible'));
}
window.closeMotivationPopup = function closeMotivationPopup() { const popup = document.getElementById('iqraMotivationPopup'); if (!popup) return; popup.classList.remove('visible'); setTimeout(() => popup.remove(), 180); };
window.startMotivationPlan = function startMotivationPlan() { window.closeMotivationPopup(); const button = document.querySelectorAll('.v3-nav button')[4]; v3Tab('v3nova', button); v3Plan(); };
function showDailyMotivation(data, firstName) {
  clearTimeout(window.iqraMotivationDelay);
  window.iqraMotivationDelay = setTimeout(() => {
    if (!ld('v3home')) return;
    document.getElementById('iqraMotivationPopup')?.remove();
    const focus = data.focus || 'your next learning goal';
    const popup = document.createElement('div');
    popup.id = 'iqraMotivationPopup';
    popup.className = 'iqra-motivation-popup';
    popup.innerHTML = `<section role="dialog" aria-modal="true" aria-label="Motivational quote of the day"><button class="motivation-close" onclick="closeMotivationPopup()" aria-label="Close quote">&times;</button><header class="motivation-simple-top"><div><span>QUOTE OF THE DAY</span><small><strong>Made by Iqra AI</strong> for your study mood</small></div><b>AI</b></header><h2>Hi ${safe(firstName)}, here is your study spark.</h2><p class="motivation-made-by"><strong>Iqra AI created this motivation for you.</strong> Read it once, then begin with one small step.</p><blockquote><p><strong>${safe(data.quote)}</strong></p></blockquote><p class="motivation-focus-line">Today’s focus: <b>${safe(focus)}</b></p><div class="motivation-actions"><button onclick="startMotivationPlan()">Start my plan <span>&rarr;</span></button><button class="motivation-later" onclick="closeMotivationPopup()">Not now</button></div></section>`;
    document.body.append(popup);
    requestAnimationFrame(() => popup.classList.add('visible'));
  }, 3000);
}
function v3Tab(id, button) { document.querySelectorAll('.v3-view').forEach(x => x.hidden = true); const target = ld(id); if (target) target.hidden = false; document.querySelectorAll('.v3-nav button').forEach(x => x.classList.remove('selected')); button?.classList.add('selected'); }
function v3Complete(id) { if (typeof window.startMissionSession === 'function') { window.startMissionSession(id); return; } uiToast('Mission sessions are loading. Please refresh once.'); }
async function v3Plan() { const result = ld('v3plan'); result.innerHTML = '<p class="loading">Iqra is designing a plan around your learning pattern...</p>'; try { const d = await api('/api/student/motivation'); result.innerHTML = `<small>${safe(d.mode)}</small><h3>Your best next 30 minutes</h3><p>${safe(d.plan).replaceAll('\n', '<br>')}</p>`; const quote = ld('v3quote'); if (quote) quote.textContent = d.quote; } catch { result.innerHTML = '<h3>Iqra needs a moment</h3><p>Your local study guidance remains available. Please try again shortly.</p>'; } }
async function v3Ask(event) {
  event.preventDefault();
  const form = event.target, input = form.message, text = input.value.trim();
  if (!text) return;
  const log = ld('v3chat');
  log.insertAdjacentHTML('beforeend', `<div class="v3-msg me">${safe(text)}</div><div id="iqra-thinking" class="v3-msg nova iqra-thinking"><span></span><div><b>Iqra is thinking</b><small>Checking your question and learning context…</small></div></div>`);
  input.value = ''; input.disabled = true; form.querySelector('button').disabled = true; log.scrollTop = log.scrollHeight;
  const controller = new AbortController();
  const statusTimer = setTimeout(() => { const thinking = ld('iqra-thinking'); if (thinking) thinking.querySelector('small').textContent = 'Still working — Iqra will return a useful answer shortly.'; }, 3800);
  const deadline = setTimeout(() => controller.abort(), 36000);
  try {
    const d = await api('/api/coach', {method:'POST', body: JSON.stringify({message:text}), signal:controller.signal});
    ld('iqra-thinking')?.remove();
    const response = d.reply || 'Iqra received your question but could not form a reply. Please send it once more.';
    log.insertAdjacentHTML('beforeend', `<div class="v3-msg nova iqra-answer">${safe(response).replaceAll('\n', '<br>')}<small>${safe(d.mode || 'Iqra study guidance')}</small></div>`);
  } catch (error) {
    ld('iqra-thinking')?.remove();
    const timeout = error?.name === 'AbortError';
    log.insertAdjacentHTML('beforeend', `<div class="v3-msg nova iqra-answer"><b>${timeout ? 'Iqra saved your question.' : 'Iqra is briefly offline.'}</b><br>${timeout ? 'The detailed local model took too long to respond. Please try again once; Iqra will use her fast local guidance while the model reconnects.' : 'Please try your question again. The fast local guidance will answer even if Ollama is restarting.'}<small>Connection recovery</small></div>`);
  } finally {
    clearTimeout(statusTimer); clearTimeout(deadline);
    input.disabled = false; form.querySelector('button').disabled = false; input.focus(); log.scrollTop = log.scrollHeight;
  }
}
function v3Settings() { const panel = ld('v3settings'); panel.hidden = !panel.hidden; }
function openAccount(profile) { let drawer = ld('accountDrawer'); if (!drawer) { drawer = document.createElement('div'); drawer.id = 'accountDrawer'; drawer.className = 'account-drawer'; document.body.append(drawer); } drawer.innerHTML = `<div class="account-sheet"><button class="account-close" onclick="ld('accountDrawer').remove()">×</button><div class="account-title"><div id="accountPreview" class="account-photo">${safe(profile.name?.[0] || 'U')}</div><div><small>YOUR ACCOUNT</small><h2>${safe(profile.name)}</h2><p>${safe(profile.email)}</p></div></div><form id="accountForm"><label>Profile picture<input id="avatarFile" type="file" accept="image/*"></label><label>Full name<input name="name" value="${safe(profile.name)}" required></label><label>Dream goal<input name="goal" value="${safe(profile.goal || '')}" placeholder="e.g. AI Engineer"></label><label>Grade / level<input name="grade" value="${safe(profile.grade || '')}" placeholder="e.g. Grade 10"></label><label>Study preference<select name="study_preference"><option value="">Choose one</option>${['Visual learning','Practice questions','Short focused sessions','Deep study sessions'].map(x=>`<option ${profile.study_preference===x?'selected':''}>${x}</option>`).join('')}</select></label><label>About me<textarea name="bio" maxlength="500" placeholder="What are you working towards?">${safe(profile.bio || '')}</textarea></label><button class="account-save">Save profile</button><button type="button" class="account-logout" onclick="logout()">Log out</button></form></div>`; const preview = ld('accountPreview'); if (profile.avatar_url) preview.innerHTML = `<img src="${safe(profile.avatar_url)}" alt="Profile picture">`; ld('avatarFile').onchange = event => { const file = event.target.files[0]; if (!file) return; if (file.size > 500000) return uiToast('Choose an image smaller than 500 KB.'); const reader = new FileReader(); reader.onload = () => { preview.innerHTML = `<img src="${reader.result}" alt="Profile picture">`; preview.dataset.avatar = reader.result; }; reader.readAsDataURL(file); }; ld('accountForm').onsubmit = async event => { event.preventDefault(); const data = Object.fromEntries(new FormData(event.target)); if (preview.dataset.avatar) data.avatar_url = preview.dataset.avatar; try { await api('/api/me',{method:'PATCH',body:JSON.stringify(data)}); uiToast('Your account details are saved.'); drawer.remove(); window.studentView(); } catch (error) { uiToast(error.message); } }; }
function refreshBrandTheme() { const image = document.querySelector('.v3-brand img'); if (image) image.src = document.body.classList.contains('dark') ? '/static/learndna-logo-dark.svg' : '/static/learndna-logo.svg'; }
window.refreshBrandTheme = refreshBrandTheme;
function enhanceBrandAndAccount(profile) { const logo = document.querySelector('.v3-brand'); if (logo) logo.innerHTML = `<img src="${document.body.classList.contains('dark') ? '/static/learndna-logo-dark.svg' : '/static/learndna-logo.svg'}" alt="LearnDNA">`; const avatar = document.querySelector('.v3-avatar'); if (avatar) { if (profile.avatar_url) avatar.innerHTML = `<img src="${safe(profile.avatar_url)}" alt="Your profile">`; else avatar.textContent = profile.name?.[0] || 'U'; avatar.onclick = () => openAccount(profile); avatar.title = 'Open account'; } }
function renderOperatingSystem(data) { const target = ld('osAgentGrid'); if (!target) return; ld('osHeadline').textContent = data.headline; ld('osCount').textContent = `${data.stats.active_agents} agents active`; target.innerHTML = data.agents.map(agent => `<article class="os-agent ${safe(agent.state)}"><div><span>${safe(agent.state)}</span><b>${safe(agent.name)}</b></div><h3>${safe(agent.signal)}</h3><p>${safe(agent.detail)}</p><button onclick="openNeuronAgent('${safe(agent.id)}')">Open tool <span>-></span></button></article>`).join(''); }
function openReflection() { let modal = ld('reflectionModal'); if (!modal) { modal = document.createElement('div'); modal.id = 'reflectionModal'; modal.className = 'reflection-modal'; document.body.append(modal); } modal.innerHTML = `<div class="reflection-sheet"><button class="account-close" onclick="ld('reflectionModal').remove()">&times;</button><small>REFLECTION AI</small><h2>Close the loop on today.</h2><p>Iqra uses only the thoughts you choose to write here to make tomorrow's guidance more useful.</p><form id="reflectionForm"><label>What is still confusing?<textarea name="confused" required placeholder="For example: when to distribute a number into brackets"></textarea></label><label>What did you understand today?<textarea name="understood" required placeholder="For example: I can isolate x using inverse operations"></textarea></label><label>What felt difficult?<textarea name="difficult" required placeholder="For example: keeping track of each step"></textarea></label><label>Confidence right now<select name="confidence"><option value="1">1 - I need a fresh start</option><option value="2">2 - I need more practice</option><option value="3" selected>3 - I am getting there</option><option value="4">4 - I feel confident</option><option value="5">5 - I could explain it</option></select></label><button>Save reflection</button></form><div id="reflectionResult"></div></div>`; ld('reflectionForm').onsubmit = async event => { event.preventDefault(); const button = event.target.querySelector('button'); button.disabled = true; button.textContent = 'Iqra is reflecting...'; try { const result = await api('/api/reflections', {method:'POST', body:JSON.stringify(Object.fromEntries(new FormData(event.target)))}); ld('reflectionResult').innerHTML = `<b>Reflection saved</b><p>${safe(result.summary)}</p>`; event.target.reset(); runOperatingSystem(); } catch (error) { ld('reflectionResult').textContent = error.message; } finally { button.disabled = false; button.textContent = 'Save reflection'; } }; }
function openNeuronAgent(id) { const buttons = document.querySelectorAll('.v3-nav button'); const open = (view, index) => v3Tab(view, buttons[index]); if (id === 'dream') { if (window.neuronProfile) openAccount(window.neuronProfile); return; } if (id === 'reflection') { openReflection(); return; } if (['misconception','replay'].includes(id)) { open('v3replay', 3); uiToast('Use the Thinking Lab to replay your own written steps.'); return; } if (['risk','missions'].includes(id)) { open('v3missions', 1); return; } if (['dna','analytics','game'].includes(id)) { open('v3dna', 2); return; } open('v3nova', 4); if (id === 'motivation') v3Plan(); }
async function runOperatingSystem() { const run = ld('osRun'); if (run) { run.disabled = true; run.textContent = 'Analysing learning signals...'; } try { const data = await api('/api/student/ai-operating-system'); renderOperatingSystem(data); } catch { const headline = ld('osHeadline'); if (headline) headline.textContent = 'The operating system could not refresh right now. Please try again.'; } finally { if (run) { run.disabled = false; run.textContent = 'Refresh AI analysis'; } } }
function enhanceOperatingSystem() { if (ld('v3os')) return; const nav = document.querySelector('.v3-nav'); const novaButton = nav?.querySelectorAll('button')[4]; if (nav && novaButton) { const button = document.createElement('button'); button.innerHTML = '<i>06</i> AI system'; button.onclick = () => { v3Tab('v3os', button); runOperatingSystem(); }; nav.append(button); } const section = document.createElement('section'); section.id = 'v3os'; section.className = 'v3-view os-view'; section.hidden = true; section.innerHTML = `<div class="os-hero"><div><small>NEURONPATH AI OPERATING SYSTEM</small><h2>Your learning data becomes clear next steps.</h2><p id="osHeadline">Building your personalized agent view…</p><button id="osRun" onclick="runOperatingSystem()">Refresh AI analysis</button></div><div class="os-orbit"><b id="osCount">12 agents</b><span>working together</span></div></div><div class="os-path"><span>Authentication</span><i>→</i><span>AI Personal Profile</span><i>→</i><span>Multi-Agent System</span><i>→</i><span>Personalized Dashboard</span></div><div id="osAgentGrid" class="os-agent-grid"><p class="loading">Loading your learning agents…</p></div>`; document.querySelector('.v3-main')?.append(section); }
function osStudentPurpose(id) {
  return {
    misconception: 'Finds the mistakes you repeat',
    risk: 'Shows what may become difficult later',
    handoff: 'Decides hint first or full help',
    motivation: 'Keeps you ready to study',
    dna: 'Explains how you learn best',
    replay: 'Reviews the steps you wrote',
    dream: 'Connects study to your goal',
    avatar: 'Opens Iqra for help',
    reflection: 'Turns reflection into tomorrow\'s plan',
    missions: 'Chooses your next study task',
    game: 'Turns effort into XP and levels',
    analytics: 'Shows progress in simple numbers',
  }[id] || 'Turns your data into a next step';
}
renderOperatingSystem = function renderFriendlyOperatingSystem(data) {
  const target = ld('osAgentGrid');
  if (!target) return;
  ld('osHeadline').textContent = data.headline;
  ld('osCount').textContent = `${data.stats.active_agents} helpers`;
  const summary = ld('osStudentSummary');
  if (summary) summary.innerHTML = `<article><b>${data.stats.risk}%</b><span>topic risk Iqra is watching</span></article><article><b>${data.stats.independence}/100</b><span>independent thinking score</span></article><article><b>${data.stats.accuracy}%</b><span>recent quiz accuracy</span></article>`;
  target.innerHTML = data.agents.map(agent => `<article class="os-agent ${safe(agent.state)}"><div><span>${safe(agent.state)}</span><b>${safe(agent.name)}</b></div><h3>${safe(osStudentPurpose(agent.id))}</h3><p class="os-agent-signal">${safe(agent.signal)}</p><p>${safe(agent.detail)}</p><button onclick="openNeuronAgent('${safe(agent.id)}')">Open related page <span>-></span></button></article>`).join('');
};
enhanceOperatingSystem = function enhanceFriendlyOperatingSystem() {
  if (ld('v3os')) return;
  const nav = document.querySelector('.v3-nav');
  const novaButton = nav?.querySelectorAll('button')[4];
  if (nav && novaButton) {
    const button = document.createElement('button');
    button.innerHTML = '<i>06</i> AI system';
    button.onclick = () => { v3Tab('v3os', button); runOperatingSystem(); };
    nav.append(button);
  }
  const section = document.createElement('section');
  section.id = 'v3os';
  section.className = 'v3-view os-view';
  section.hidden = true;
  section.innerHTML = `<div class="os-hero os-hero-friendly"><div><small>IQRA AI CONTROL ROOM</small><h2>Iqra turns your study activity into your next best step.</h2><p id="osHeadline">Checking your progress, weak topics, missions, and thinking pattern...</p><button id="osRun" onclick="runOperatingSystem()">Refresh my AI guide</button></div><div class="os-orbit"><b id="osCount">helpers</b><span>watching your learning</span></div></div><div id="osStudentSummary" class="os-student-summary"><article><b>--</b><span>topic risk Iqra is watching</span></article><article><b>--</b><span>independent thinking score</span></article><article><b>--</b><span>recent quiz accuracy</span></article></div><div class="os-explain"><b>What is this page for?</b><p>It shows what Iqra AI notices about your learning and which tool can help you next.</p></div><div class="os-path os-path-friendly"><span>Your activity</span><i>-></i><span>Iqra understands it</span><i>-></i><span>Next study step</span><i>-></i><span>Better progress</span></div><div id="osAgentGrid" class="os-agent-grid"><p class="loading">Loading Iqra's learning helpers...</p></div>`;
  document.querySelector('.v3-main')?.append(section);
};
function labelIqra() { const walker = document.createTreeWalker(app, NodeFilter.SHOW_TEXT); const nodes = []; while (walker.nextNode()) nodes.push(walker.currentNode); nodes.forEach(node => node.nodeValue = node.nodeValue.replaceAll('Nova', 'Iqra').replaceAll('NOVA', 'IQRA')); document.querySelectorAll('input[placeholder*="Nova"]').forEach(input => input.placeholder = input.placeholder.replaceAll('Nova', 'Iqra')); }
function enhanceIqraPage(independence) { const page = ld('v3nova'); if (!page || ld('iqra-studio-head')) return; const head = document.createElement('section'); head.id = 'iqra-studio-head'; head.className = 'iqra-studio-head'; head.innerHTML = `<div class="iqra-presence"><div class="iqra-avatar">I<span></span></div><div><small>IQRA AI STUDY STUDIO</small><h2>Your calm space to think, plan, and grow.</h2><p><i></i> Iqra is ready to learn with you</p></div></div><div class="iqra-meter"><small>THINKING INDEPENDENCE</small><strong>${independence}<sup>/100</sup></strong><div><i style="width:${independence}%"></i></div><span>Built through your own explanations.</span></div>`; page.prepend(head); const profile = page.querySelector('.v3-nova-profile'); if (profile) { const avatar = profile.querySelector(':scope > div'); if (avatar) avatar.textContent = 'I'; const quick = document.createElement('div'); quick.className = 'iqra-quick'; quick.innerHTML = '<small>TRY A QUICK START</small><button data-prompt="Explain this topic simply, then give me one practice question.">Explain a topic</button><button data-prompt="Create a focused 20-minute study session for me.">Build a 20-minute plan</button><button data-prompt="Help me start a problem without giving the answer immediately.">Give me a first hint</button>'; profile.append(quick); quick.querySelectorAll('button').forEach(button => button.onclick = () => { const input = document.querySelector('#v3nova input[name="message"]'); if (input) { input.value = button.dataset.prompt; input.focus(); } }); } }
function enhanceOneLookStudentUI(data, first) {
  const home = ld('v3home');
  if (!home || ld('studentOneLook')) return;
  const next = (data.missions || []).find(mission => !mission.completed);
  const heroTitle = home.querySelector('.v3-hero h2');
  const heroText = home.querySelector('.v3-hero p');
  const heroLabel = home.querySelector('.v3-hero small');
  if (heroLabel) heroLabel.textContent = 'TODAY AT A GLANCE';
  if (heroTitle) heroTitle.textContent = `Hi ${first}, start with one clear step.`;
  if (heroText) heroText.textContent = next ? `Your best next action is: ${next.title}. Finish it, then ask Iqra if you get stuck.` : 'You have completed the planned missions. Use Iqra for a review or write a short reflection.';
  const glance = document.createElement('section');
  glance.id = 'studentOneLook';
  glance.className = 'student-one-look';
  glance.innerHTML = `<article><span>1</span><div><b>Start</b><p>${safe(next?.title || 'Review today')}</p></div></article><article><span>2</span><div><b>Ask Iqra</b><p>Get a hint, plan, or simple explanation.</p></div></article><article><span>3</span><div><b>Track progress</b><p>${data.xp} XP · ${data.streak} day streak</p></div></article>`;
  const metrics = home.querySelector('.v3-metrics');
  home.insertBefore(glance, metrics || home.children[1]);
}
window.studentView = async function renderStudentWorkspace() {
  try {
    const d = await api('/api/student/dashboard');
    const first = d.user.name.split(' ')[0];
    const missions = d.missions;
    window.currentMissions = missions;
    const open = missions.filter(x => !x.completed);
    app.innerHTML = `<div class="v3-app">
      <aside class="v3-sidebar"><a class="v3-brand"><b>DNA</b> Learn<span>DNA</span></a><div class="v3-student"><small>STUDENT SPACE</small><strong>${safe(d.user.goal)}</strong><span>Level ${d.level} · ${d.streak} day streak</span></div>
      <nav class="v3-nav"><button class="selected" onclick="v3Tab('v3home',this)"><i>01</i> Overview</button><button onclick="v3Tab('v3missions',this)"><i>02</i> Study plan</button><button onclick="v3Tab('v3dna',this)"><i>03</i> Learning DNA</button><button onclick="v3Tab('v3replay',this)"><i>04</i> Thinking lab</button><button onclick="v3Tab('v3nova',this)"><i>05</i> Nova AI</button></nav>
      <div class="v3-side-card"><small>NOVA AI</small><b>Need a learning nudge?</b><p>Ask Nova for an explanation or plan.</p><button onclick="v3Tab('v3nova',document.querySelectorAll('.v3-nav button')[4])">Open Nova →</button></div><button class="v3-theme" onclick="toggleTheme()">◐ Theme</button></aside>
      <main class="v3-main"><header class="v3-head"><div><p>${new Date().toLocaleDateString('en-US',{weekday:'long',month:'long',day:'numeric'})}</p><h1>${currentGreeting()}, ${safe(first)}.</h1></div><div class="v3-tools"><button onclick="v3Notifications()" aria-label="Notifications" title="Open notifications">♢</button><button onclick="v3Settings()" aria-label="Settings">⚙</button><button class="v3-avatar" onclick="logout()" title="Log out">${safe(first[0])}</button></div></header>
      <section id="v3home" class="v3-view"><div class="v3-hero"><div><small>YOUR FOCUS FOR TODAY</small><h2>One focused session can change your whole week.</h2><p>${open[0]?.description || 'You have completed today’s planned work. Take a moment to reflect.'}</p><button onclick="v3Tab('v3missions',document.querySelectorAll('.v3-nav button')[1])">Begin today’s plan <b>→</b></button></div><div class="v3-hero-orbit"><strong>${d.independent_thinking}</strong><span>independence<br>score</span></div></div>
      <div class="v3-metrics"><article><small>LEVEL</small><b>${d.level}</b><span>${d.xp} XP earned</span></article><article><small>STREAK</small><b>${d.streak} days</b><span>Learning is becoming a habit.</span></article><article><small>FUTURE RISK</small><b>${d.risk.risk}%</b><span>${safe(d.risk.topic)}</span></article><article><small>QUIZ ACCURACY</small><b>${d.quiz_accuracy}%</b><span>Keep practicing with feedback.</span></article></div>
      <div class="v3-grid"><article class="v3-card v3-mission-card"><div class="v3-card-title"><div><small>UP NEXT</small><h2>Your mission queue</h2></div><button onclick="v3Tab('v3missions',document.querySelectorAll('.v3-nav button')[1])">View all</button></div>${missions.slice(0,3).map((m,i)=>`<div class="v3-mission ${m.completed?'complete':''}"><span>${m.completed?'✓':'0'+(i+1)}</span><div><b>${safe(m.title)}</b><p>${safe(m.description)}</p></div><em>+${m.xp} XP</em>${m.completed?'':`<button onclick="v3Complete('${m.id}')">Start</button>`}</div>`).join('')}</article><article class="v3-card v3-dna-card"><small>LEARNING DNA</small><h2>Explorer mindset</h2><p>You’re strongest when connecting ideas and explaining your steps.</p><div class="v3-dna-ring"><b>${Math.round((d.learning_dna.logical+d.learning_dna.creativity+d.learning_dna.attention)/3)}%</b></div><div class="v3-traits">${[['Logic',d.learning_dna.logical],['Focus',d.learning_dna.attention],['Growth',d.learning_dna.problem_solving]].map(x=>`<div><span>${x[0]} <b>${x[1]}%</b></span><i><em style="width:${x[1]}%"></em></i></div>`).join('')}</div></article></div>
      <article class="v3-nova-strip"><div><small>NOVA MOTIVATION ENGINE</small><h2 id="v3quote">A personalized daily encouragement is loading…</h2><p>Nova adapts your study plan from your progress, confidence, risk areas, and current goals.</p></div><button onclick="v3Tab('v3nova',document.querySelectorAll('.v3-nav button')[4]);v3Plan()">Create my plan →</button></article></section>
      <section id="v3missions" class="v3-view" hidden><div class="v3-page-title"><small>PERSONALIZED STUDY PLAN</small><h2>Make progress without overwhelm.</h2><p>Each activity targets what will help you most right now.</p></div><div class="v3-plan-intro"><div><small>PRIORITY REPAIR</small><h2>${safe(d.risk.repair)}</h2><p>${safe(d.risk.reason)} · ${d.risk.minutes} minutes</p></div><button onclick="v3Tab('v3nova',document.querySelectorAll('.v3-nav button')[4]);v3Plan()">Ask Nova to adapt it →</button></div><div class="v3-plan-list">${missions.map((m,i)=>`<article class="${m.completed?'complete':''}"><span>${m.completed?'✓':'0'+(i+1)}</span><div><small>${safe(m.kind).toUpperCase()} ACTIVITY</small><h3>${safe(m.title)}</h3><p>${safe(m.description)}</p></div><b>+${m.xp} XP</b>${m.completed?'<em>Completed</em>':`<button onclick="v3Complete('${m.id}')">Complete →</button>`}</article>`).join('')}</div></section>
      <section id="v3dna" class="v3-view" hidden><div class="v3-page-title"><small>YOUR LEARNING DNA</small><h2>Progress you can understand.</h2><p>Transparent scores change when you learn, reflect, and practice.</p></div><div class="v3-dna-board">${Object.entries(d.learning_dna).map(([key,val])=>`<article><div><b>${safe(key.replaceAll('_',' '))}</b><span>${val}%</span></div><i><em style="width:${val}%"></em></i><small>${val>=75?'A current strength':'Worth a short practice session'}</small></article>`).join('')}</div></section>
      <section id="v3replay" class="v3-view" hidden><div class="v3-lab"><article><small>REPLAY MY THINKING</small><h2>Show your steps. Learn from the exact turn.</h2><p>Solve 2(x + 3) = 10. Nova only reviews reasoning you write.</p><form onsubmit="v3SubmitQuiz(event)"><input name="answer" placeholder="Your answer, e.g. x = 2" required><textarea name="reasoning" placeholder="Step 1: ...&#10;Step 2: ...&#10;Step 3: ..." required></textarea><button>Analyse my thinking →</button></form></article><article id="v3replay-result" class="v3-replay-result"><small>YOUR REPLAY</small><h3>Your feedback will appear here.</h3><p>Use your own written steps to see a better path.</p></article></div></section>
      <section id="v3nova" class="v3-view" hidden><div class="v3-nova-page"><article class="v3-nova-profile"><div>N</div><small>NOVA · YOUR AI STUDY COMPANION</small><h2>Ask questions. Build independence.</h2><p>Nova can explain a concept, check a plan, or help you begin a difficult problem.</p><button onclick="v3Plan()">Generate my study plan →</button></article><article class="v3-chat-card"><div id="v3plan"><p>Choose “Generate my study plan” to turn your current data into a realistic next session.</p></div><div id="v3chat" class="v3-chat"><div class="v3-msg nova">Hi ${safe(first)}. What would you like help understanding today?</div></div><form onsubmit="v3Ask(event)"><input name="message" placeholder="Ask Nova anything about your studies..." required><button>Send</button></form></article></div></section>
      <div id="v3settings" class="v3-settings" hidden><b>Quick settings</b><button onclick="toggleTheme()">Toggle dark mode</button><button onclick="v3Settings()">Close</button></div>
      </main></div>`;
    labelIqra();
    enhanceIqraPage(d.independent_thinking);
    enhanceOneLookStudentUI(d, first);
    enhanceBrandAndAccount(d.user);
    window.neuronProfile = d.user;
    enhanceOperatingSystem();
    if (typeof window.enhanceAdaptiveLearning === 'function') window.enhanceAdaptiveLearning(d);
    runOperatingSystem();
    api('/api/student/motivation').then(d => { const quote = ld('v3quote'); if (quote) quote.textContent = d.quote; showDailyMotivation(d, first); }).catch(() => {});
  } catch (e) { app.innerHTML = `<div class="v3-error"><h2>We couldn’t open your workspace.</h2><p>${safe(e.message)}</p><button onclick="logout()">Sign in again</button></div>`; }
};
async function v3SubmitQuiz(event) {
  event.preventDefault();
  const form = event.target;
  const card = ld('v3replay-result');
  const button = form.querySelector('button');
  const payload = Object.fromEntries(new FormData(form));
  if (button) { button.disabled = true; button.textContent = 'Iqra is checking...'; }
  if (card) {
    card.className = 'v3-replay-result thinking-feedback-card is-loading';
    card.innerHTML = `<div class="thinking-loader"><span></span><div><small>IQRA IS REPLAYING</small><h3>Checking your answer and reasoning...</h3><p>Iqra is saving your learning trail and updating your progress.</p></div></div>`;
  }
  try {
    const d = await api('/api/quiz/submit', {method:'POST', body:JSON.stringify(payload)});
    const steps = Array.isArray(d.replay?.better_path) && d.replay.better_path.length ? d.replay.better_path : ['Read the question carefully.', 'Write the known information.', 'Try one smaller step and check it.'];
    const message = d.replay?.message || (d.correct ? 'Your answer is correct.' : 'This needs one more careful attempt.');
    if (card) {
      card.className = `v3-replay-result thinking-feedback-card ${d.correct ? 'is-correct' : 'needs-repair'}`;
      card.innerHTML = `<div class="thinking-feedback-top"><span>${d.correct ? '✓' : '!'}</span><div><small>${d.correct ? 'GREAT WORK' : 'REPAIR SIGNAL'}</small><h3>${safe(d.correct ? 'Your reasoning is on track.' : 'Iqra found a useful next step.')}</h3></div></div><p class="thinking-feedback-message">${safe(message)}</p><div class="thinking-step-box"><b>Better path</b><ol>${steps.map((x, i) => `<li><span>${i + 1}</span>${safe(x)}</li>`).join('')}</ol></div><div class="thinking-xp-pill">${d.correct ? `+${d.xp_earned} XP added to your profile` : `+${d.xp_earned} XP for an honest attempt`}</div>${d.misconception ? `<p class="thinking-pattern">Pattern detected: <b>${safe(d.misconception.concept)}</b>. Iqra will adapt your next missions.</p>` : ''}<button class="thinking-next-btn" onclick="nextThinkingQuestion()">Try next challenge →</button>`;
    }
    uiToast(d.correct ? `Great work. +${d.xp_earned} XP added.` : `Good attempt. +${d.xp_earned} XP added and Iqra saved the repair signal.`);
    if (typeof window.afterThinkingAnswer === 'function') window.afterThinkingAnswer(d);
  } catch(e) {
    if (card) {
      card.className = 'v3-replay-result thinking-feedback-card needs-repair';
      card.innerHTML = `<small>COULD NOT CHECK</small><h3>Iqra could not save this attempt.</h3><p>${safe(e.message)}</p>`;
    }
  } finally {
    if (button) { button.disabled = false; button.textContent = 'Check my thinking →'; }
  }
}
