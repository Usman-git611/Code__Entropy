/* Code Quest turns each language lesson into a small, hint-led learning game. */
function codeGameEscape(value) { return String(value ?? '').replace(/[&<>'"]/g, character => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[character])); }

function activeCodeLanguage() { return document.getElementById('codeLanguage')?.value || window.codeGameData?.labs?.[0]?.language || 'Python'; }
function activeQuest() { return window.activeCodeChallenge || null; }

function codeQuestStarter(language) {
  const templates = {
    Python: '# Your quest starts here\n# Write one small step, then run it.\n',
    C: '#include <stdio.h>\n\nint main(void) {\n  // Write one small step.\n  return 0;\n}\n',
    'C++': '#include <iostream>\nusing namespace std;\n\nint main() {\n  // Write one small step.\n  return 0;\n}\n',
    MySQL: '-- Write one query at a time.\nSELECT ',
    Java: 'public class Main {\n  public static void main(String[] args) {\n    // Write one small step.\n  }\n}\n',
  };
  return templates[language] || '// Start your solution here.\n';
}

function currentQuestHint() {
  const quest = activeQuest();
  if (!quest) return '';
  const hints = quest.hints || [];
  return hints[Math.min(window.codeHintLevel || 0, Math.max(0, hints.length - 1))] || 'Break the goal into one small action, then run your draft.';
}

function renderQuestCoach() {
  const quest = activeQuest();
  if (!quest) return `<section class="code-quest-coach code-quest-empty"><div class="quest-orb">?</div><div><small>CHOOSE YOUR NEXT QUEST</small><h4>Pick a level below and write the solution yourself.</h4><p>You receive progressive clues, not a completed answer. Run small attempts, earn XP, and clear the map one challenge at a time.</p></div></section>`;
  const totalHints = (quest.hints || []).length || 3;
  const shown = Math.min((window.codeHintLevel || 0) + 1, totalHints);
  const canReveal = shown < totalHints;
  return `<section class="code-quest-coach"><div class="quest-orb">${quest.completed ? '&#10003;' : quest.level}</div><div class="quest-coach-copy"><small>ACTIVE QUEST · LEVEL ${quest.level}</small><h4>${codeGameEscape(quest.title)}</h4><p>${codeGameEscape(quest.prompt)}</p><div id="codeQuestHint" class="code-quest-hint"><b>CLUE ${shown}/${totalHints}</b><span>${codeGameEscape(currentQuestHint())}</span></div></div><div class="quest-actions"><span>+${quest.xp} XP on clear</span><button ${canReveal ? '' : 'disabled'} onclick="revealCodeHint()">${canReveal ? 'Reveal next clue' : 'All clues shown'}</button></div></section>`;
}

function renderCodingGame() {
  const panel = document.getElementById('codeGamePanel'); const data = window.codeGameData;
  if (!panel || !data) return;
  const language = activeCodeLanguage(); const challenges = data.challenges.filter(challenge => challenge.language === language); const stats = data.stats;
  const percent = Math.round((stats.completed / stats.total) * 100); const active = activeQuest();
  panel.innerHTML = `<div class="code-game-top"><div class="code-quest-title"><small>CODE QUEST · LEARN BY BUILDING</small><h3>${codeGameEscape(language)} adventure map</h3><p>${codeGameEscape(data.engine[language] || 'Learning engine')} Every quest rewards a working idea, not copied code.</p></div><div class="code-game-stats"><div class="code-level-badge"><span>LEVEL</span><b>${stats.level}</b></div><div><b>${stats.completed}<i>/${stats.total}</i></b><span>quests cleared</span></div><div><b>${stats.xp}</b><span>Code XP</span></div></div></div><div class="code-progress-line"><i style="width:${percent}%"></i></div><div class="code-map-meta"><span><b>${percent}%</b> of the full Code Quest map explored</span><span>${active ? `Quest ${active.level} is active` : 'Choose a quest to unlock your next skill'}</span></div>${renderQuestCoach()}<div class="code-challenge-list">${challenges.map(challenge => `<article class="${challenge.completed ? 'cleared' : ''} ${active?.id === challenge.id ? 'active' : ''}"><div class="challenge-number">${challenge.completed ? '&#10003;' : challenge.level}</div><div><small>LEVEL ${challenge.level} · ${codeGameEscape(challenge.concept)}</small><b>${codeGameEscape(challenge.title)}</b><p>${codeGameEscape(challenge.prompt)}</p></div><span>+${challenge.xp} XP</span><button onclick="openCodingChallenge('${challenge.id}')">${challenge.completed ? 'Try again' : 'Play quest'} <i>&rarr;</i></button></article>`).join('')}</div>`;
}

window.refreshCodingGame = renderCodingGame;

window.enhanceCodingGame = function enhanceCodingGame(data) {
  window.codeGameData = data;
  const page = document.getElementById('v3code');
  if (!page) return;
  let panel = document.getElementById('codeGamePanel');
  if (!panel) { panel = document.createElement('section'); panel.id = 'codeGamePanel'; panel.className = 'code-game-panel'; page.querySelector('.coding-grid')?.before(panel); }
  renderCodingGame();
};

window.openCodingChallenge = function openCodingChallenge(id) {
  const challenge = window.codeGameData?.challenges.find(item => item.id === id);
  if (!challenge) return;
  window.activeCodeChallenge = challenge; window.codeHintLevel = 0;
  const language = document.getElementById('codeLanguage'); if (language) language.value = challenge.language;
  const title = document.getElementById('codeLabTitle'); const concept = document.getElementById('codeConcept'); const editor = document.getElementById('codeEditor'); const tip = document.getElementById('codeTip'); const output = document.getElementById('codeOutput');
  if (title) title.textContent = `Quest ${challenge.level}: ${challenge.title}`;
  if (concept) concept.textContent = challenge.prompt;
  // Deliberately use an empty learning scaffold rather than the finished answer.
  if (editor) editor.value = codeQuestStarter(challenge.language);
  if (tip) tip.textContent = `Clue 1: ${currentQuestHint()} Use “Reveal next clue” only when you need it.`;
  if (output) output.textContent = `Quest loaded: ${challenge.title}\n\nGoal: ${challenge.prompt}\n\nWrite your own first attempt. Iqra will reward a working solution.`;
  renderCodingGame();
  document.querySelector('.code-editor')?.scrollIntoView({behavior:'smooth', block:'center'});
};

window.revealCodeHint = function revealCodeHint() {
  const challenge = activeQuest(); if (!challenge) return;
  const max = Math.max(0, (challenge.hints || []).length - 1);
  window.codeHintLevel = Math.min(max, (window.codeHintLevel || 0) + 1);
  const tip = document.getElementById('codeTip'); if (tip) tip.textContent = `Clue ${(window.codeHintLevel || 0) + 1}: ${currentQuestHint()}`;
  renderCodingGame();
};

function codeCelebration(xp) {
  const burst = document.createElement('div'); burst.className = 'code-xp-burst';
  burst.innerHTML = `<span>+${xp} XP</span><i>✦</i><i>✦</i><i>✦</i><i>✦</i>`; document.body.append(burst);
  setTimeout(() => burst.remove(), 1200);
}

window.applyCodingResult = function applyCodingResult(result) {
  const challenge = window.codeGameData?.challenges.find(item => item.id === result.challenge?.id);
  if (!challenge) return;
  challenge.attempts = (challenge.attempts || 0) + 1;
  if (result.challenge.passed) challenge.completed = true;
  if (result.stats) window.codeGameData.stats = result.stats;
  if (!result.challenge.passed) {
    const max = Math.max(0, (challenge.hints || []).length - 1);
    window.codeHintLevel = Math.min(max, (window.codeHintLevel || 0) + 1);
    const tip = document.getElementById('codeTip'); if (tip) tip.textContent = `Try again — Clue ${(window.codeHintLevel || 0) + 1}: ${currentQuestHint()}`;
  }
  renderCodingGame();
  if (result.challenge.newly_completed) { codeCelebration(result.challenge.xp_earned); if (typeof uiToast === 'function') uiToast(`Quest complete! +${result.challenge.xp_earned} Code XP`); }
  else if (!result.challenge.passed && typeof uiToast === 'function') uiToast('Good attempt — Iqra unlocked a new clue.');
};
