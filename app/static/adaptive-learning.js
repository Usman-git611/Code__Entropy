/* Subject selection, large thinking-question bank, adaptive missions, and Coding Lab. */
const ADAPTIVE_SUBJECTS = ['Mathematics', 'Physics', 'Chemistry', 'Programming', 'Biology', 'English'];
const ADAPTIVE_LANGUAGES = ['Python', 'C', 'C++', 'MySQL', 'Java'];
const html = value => String(value ?? '').replace(/[&<>'"]/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));

function selectedSubjects(value) { return String(value || '').split(',').map(item => item.trim()).filter(item => ADAPTIVE_SUBJECTS.includes(item)); }

window.openSubjectSetup = function openSubjectSetup(allowClose = true) {
  const current = window.adaptiveCurrent || {user:{}};
  const selected = selectedSubjects(current.user.subjects);
  let modal = document.getElementById('subjectSetup');
  if (!modal) { modal = document.createElement('div'); modal.id = 'subjectSetup'; modal.className = 'adaptive-modal'; document.body.append(modal); }
  modal.innerHTML = `<section class="subject-sheet">${allowClose ? '<button class="account-close" onclick="document.getElementById(\'subjectSetup\').remove()">&times;</button>' : ''}<small>PERSONALIZED LEARNING SETUP</small><h2>What do you want to study?</h2><p>Choose the subjects that matter to you. Iqra will use them to create your questions, daily missions, risk signals, and Coding Lab.</p><form id="subjectForm"><div class="subject-options">${ADAPTIVE_SUBJECTS.map(subject => `<label><input type="checkbox" name="subject" value="${subject}" ${selected.includes(subject) || (!selected.length && ['Mathematics','Physics','Chemistry','Programming'].includes(subject)) ? 'checked' : ''}><span>${subject}</span></label>`).join('')}</div><label class="language-choice">Main programming language<select name="coding_language">${ADAPTIVE_LANGUAGES.map(language => `<option ${current.user.coding_language === language ? 'selected' : ''}>${language}</option>`).join('')}</select></label><p id="subjectError" class="adaptive-error"></p><button>Build my adaptive learning plan</button></form></section>`;
  document.getElementById('subjectForm').onsubmit = async event => {
    event.preventDefault();
    const subjects = [...event.target.querySelectorAll('input[name="subject"]:checked')].map(input => input.value);
    if (!subjects.length) { document.getElementById('subjectError').textContent = 'Choose at least one subject.'; return; }
    const button = event.target.querySelector('button'); button.disabled = true; button.textContent = 'Creating your plan...';
    try {
      await api('/api/me', {method:'PATCH', body:JSON.stringify({subjects:subjects.join(', '), coding_language:event.target.coding_language.value})});
      modal.remove(); uiToast('Your subjects are saved. Today\'s missions are now personalized.'); window.studentView();
    } catch (error) { document.getElementById('subjectError').textContent = error.message; button.disabled = false; button.textContent = 'Build my adaptive learning plan'; }
  };
};

async function loadThinkingQuestions(subject) {
  const select = document.getElementById('thinkingSubject');
  const requested = subject || select?.value || '';
  try {
    const result = await api('/api/quiz/questions' + (requested ? '?subject=' + encodeURIComponent(requested) : ''));
    window.thinkingQuestions = result.questions;
    window.thinkingIndex = 0;
    if (select) {
      select.innerHTML = '<option value="">All my subjects</option>' + result.subjects.map(item => `<option value="${html(item)}">${html(item)}</option>`).join('');
      select.value = requested;
    }
    const count = document.getElementById('thinkingCount'); if (count) count.textContent = `${result.total} questions ready`;
    renderThinkingQuestion();
  } catch (error) { const count = document.getElementById('thinkingCount'); if (count) count.textContent = error.message; }
}

function renderThinkingQuestion() {
  const question = window.thinkingQuestions?.[window.thinkingIndex || 0];
  const problem = document.querySelector('#v3replay .v3-lab > article');
  if (!question || !problem) return;
  const position = (window.thinkingIndex || 0) + 1;
  problem.classList.add('thinking-problem');
  problem.innerHTML = `<div class="thinking-question-head"><div><small>IQRA'S ADAPTIVE CHALLENGE</small><span>${html(question.subject)} · ${html(question.topic)}</span></div><b>${String(position).padStart(2, '0')}<i>/${String(window.thinkingQuestions.length).padStart(2, '0')}</i></b></div><div class="thinking-prompt"><span>?</span><div><p>YOUR QUESTION</p><h2>${html(question.text)}</h2></div></div><p class="adaptive-hint"><b>Iqra hint</b>${html(question.hint)}</p><form onsubmit="v3SubmitQuiz(event)"><input type="hidden" name="question_id" value="${html(question.id)}"><label>Your answer<input name="answer" placeholder="Type your answer here" autocomplete="off" required></label><label>Show your reasoning<textarea name="reasoning" placeholder="Explain your first step in your own words. Iqra will give feedback on what you write." required></textarea></label><button>Check my thinking <span>-></span></button></form>`;
  const result = document.getElementById('v3replay-result');
  if (result) result.innerHTML = '<small>YOUR REPLAY</small><h3>Ready when you are.</h3><p>Answer the challenge and show one honest step. Iqra will explain the better path after your attempt.</p>';
}

window.nextThinkingQuestion = function nextThinkingQuestion() {
  if (!window.thinkingQuestions?.length) return;
  window.thinkingIndex = ((window.thinkingIndex || 0) + 1) % window.thinkingQuestions.length;
  renderThinkingQuestion();
};

window.afterThinkingAnswer = function afterThinkingAnswer() {
  if (typeof runOperatingSystem === 'function') runOperatingSystem();
};

async function loadCodingLab(preferred) {
  const select = document.getElementById('codeLanguage');
  try {
    const result = await api('/api/code-lab');
    window.codeLabs = result.labs;
    if (!select) return;
    select.innerHTML = result.labs.map(lab => `<option value="${html(lab.language)}">${html(lab.language)}</option>`).join('');
    select.value = preferred || result.labs[0].language;
    chooseCodeLab(select.value);
    if (typeof window.enhanceCodingGame === 'function') window.enhanceCodingGame(result);
  } catch (error) { const output = document.getElementById('codeOutput'); if (output) output.textContent = error.message; }
}

window.chooseCodeLab = function chooseCodeLab(language) {
  const lab = window.codeLabs?.find(item => item.language === language);
  if (!lab) return;
  const title = document.getElementById('codeLabTitle'); const concept = document.getElementById('codeConcept'); const editor = document.getElementById('codeEditor'); const tip = document.getElementById('codeTip'); const output = document.getElementById('codeOutput');
  if (title) title.textContent = lab.title;
  if (concept) concept.textContent = lab.concept;
  if (editor) editor.value = lab.starter;
  if (tip) tip.textContent = lab.tip;
  if (output) output.textContent = 'Ready. Edit the starter code, then press Run code.';
  window.activeCodeChallenge = null;
  if (typeof window.refreshCodingGame === 'function') window.refreshCodingGame();
};

window.runCodeLab = async function runCodeLab() {
  const language = document.getElementById('codeLanguage')?.value; const code = document.getElementById('codeEditor')?.value || ''; const output = document.getElementById('codeOutput'); const button = document.getElementById('runCode');
  if (!language || !output) return;
  button.disabled = true; button.textContent = 'Running...'; output.textContent = 'Checking your lesson code safely...';
  try { const result = await api('/api/code-lab/run', {method:'POST', body:JSON.stringify({language, code, challenge_id:window.activeCodeChallenge?.id || null})}); output.textContent = `[${result.runner}]\n\n${result.output}${result.challenge ? `\n\n${result.challenge.message}${result.challenge.xp_earned ? ` +${result.challenge.xp_earned} XP` : ''}` : ''}`; output.classList.toggle('error', !result.ok); if (result.challenge && typeof window.applyCodingResult === 'function') window.applyCodingResult(result); }
  catch (error) { output.textContent = error.message; output.classList.add('error'); }
  finally { button.disabled = false; button.textContent = 'Run code'; }
};

function tagAdaptiveMissions(missions) {
  const cards = document.querySelectorAll('.v3-plan-list article');
  cards.forEach((card, index) => { const subject = missions[index]?.subject; if (subject && !card.querySelector('.adaptive-subject-badge')) { const tag = document.createElement('span'); tag.className = 'adaptive-subject-badge'; tag.textContent = subject; card.querySelector('div')?.append(tag); } });
}

function installAdaptiveViews(data) {
  const nav = document.querySelector('.v3-nav');
  if (!document.getElementById('adaptiveCodeNav') && nav) {
    const button = document.createElement('button'); button.id = 'adaptiveCodeNav'; button.innerHTML = '<i>07</i> Code lab'; button.onclick = () => { v3Tab('v3code', button); loadCodingLab(data.user.coding_language); }; nav.append(button);
  }
  if (!document.getElementById('adaptiveThinkingControls')) {
    const page = document.getElementById('v3replay');
    if (page) { const controls = document.createElement('section'); controls.id = 'adaptiveThinkingControls'; controls.className = 'adaptive-thinking-controls'; controls.innerHTML = `<div class="thinking-library-copy"><small>ADAPTIVE QUESTION LIBRARY</small><b id="thinkingCount">Loading questions...</b><span>Questions adjust to the subjects you selected.</span></div><div class="thinking-library-actions"><label>Choose subject<select id="thinkingSubject" onchange="loadThinkingQuestions(this.value)"></select></label><button onclick="nextThinkingQuestion()">Next challenge <span>-></span></button></div>`; page.prepend(controls); loadThinkingQuestions(); }
  }
  if (!document.getElementById('v3code')) {
    const section = document.createElement('section'); section.id = 'v3code'; section.className = 'v3-view coding-view'; section.hidden = true; section.innerHTML = `<div class="coding-hero"><div><small>PROGRAMMING LAB</small><h2>Write, edit, and learn the basics.</h2><p>Choose Python, C, C++, MySQL, or Java. The lesson runner checks beginner code patterns locally without running unsafe server code.</p></div><label>Language<select id="codeLanguage" onchange="chooseCodeLab(this.value)"></select></label></div><div class="coding-grid"><article class="code-lesson"><small>LESSON</small><h3 id="codeLabTitle">Loading a lesson...</h3><p id="codeConcept"></p><small id="codeTip"></small></article><article class="code-editor"><div><b>Editor</b><button id="runCode" onclick="runCodeLab()">Run code</button></div><textarea id="codeEditor" spellcheck="false" aria-label="Code editor"></textarea></article><article class="code-console"><div><b>Output</b><span>safe local lesson runner</span></div><pre id="codeOutput">Choose a language to begin.</pre></article></div>`; document.querySelector('.v3-main')?.append(section); }
  const settings = document.getElementById('v3settings');
  if (settings && !document.getElementById('editSubjects')) { const button = document.createElement('button'); button.id = 'editSubjects'; button.textContent = 'Edit subjects'; button.onclick = () => openSubjectSetup(true); settings.prepend(button); }
  tagAdaptiveMissions(data.missions);
}

window.enhanceAdaptiveLearning = function enhanceAdaptiveLearning(data) {
  window.adaptiveCurrent = data;
  installAdaptiveViews(data);
  if (!data.user.subjects) setTimeout(() => openSubjectSetup(false), 250);
};
