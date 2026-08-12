/* Guided Study Plan sessions: answer a question, see XP feedback, then finish the mission. */
const missionEscape = value => String(value ?? '').replace(/[&<>'"]/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));

function missionGuidance(mission) {
  const subject = mission.subject || 'your selected subject';
  if (mission.kind === 'reflection') return `Pause after the question and write one specific idea you want to remember from ${subject}.`;
  if (mission.kind === 'challenge') return 'This is a stretch task. Aim for clear reasoning, not speed.';
  if (mission.kind === 'repair') return 'This mission repairs a weak area. Use the hint, take one step at a time, and do not rush.';
  if (mission.kind === 'thinking') return 'Break the task into known information, unknown information, and your first action.';
  return 'Work actively: attempt the question, then write the small idea that helped you move forward.';
}

function missionClock(totalSeconds) {
  const minutes = Math.floor(totalSeconds / 60).toString().padStart(2, '0');
  const seconds = (totalSeconds % 60).toString().padStart(2, '0');
  return `${minutes}:${seconds}`;
}

function setMissionProgress() {
  const session = window.activeMissionSession;
  if (!session) return;
  const read = Boolean(document.getElementById('missionRead')?.checked);
  const questionDone = Boolean(session.questionAttempted || session.questionCorrect);
  const takeaway = (document.getElementById('missionTakeaway')?.value || '').trim().length >= 15;
  const complete = read && questionDone && takeaway;
  const count = [read, questionDone, takeaway].filter(Boolean).length;
  const completeButton = document.getElementById('finishMission');
  if (completeButton) {
    completeButton.disabled = !complete;
    completeButton.textContent = complete ? `Finish mission +${session.mission.xp} XP` : `Complete ${count}/3 steps to finish`;
  }
  document.querySelectorAll('[data-mission-step]').forEach((element, index) => {
    element.classList.toggle('done', [read, questionDone, takeaway][index]);
  });
}

async function loadMissionQuestion() {
  const session = window.activeMissionSession;
  const target = document.getElementById('missionQuestion');
  if (!session || !target) return;
  target.innerHTML = '<p class="loading">Iqra is selecting a practice question...</p>';
  try {
    const subject = session.mission.subject ? '?subject=' + encodeURIComponent(session.mission.subject) : '';
    const result = await api('/api/quiz/questions' + subject);
    if (!result.questions?.length) {
      target.innerHTML = '<p class="mission-error">No practice question is available for this subject yet. Try another mission or edit your subjects.</p>';
      return;
    }
    const index = [...session.mission.id].reduce((sum, char) => sum + char.charCodeAt(0), 0) % result.questions.length;
    const question = result.questions[index];
    session.question = question;
    target.innerHTML = `<div class="mission-question-head"><div><small>${missionEscape(question.subject)} · ${missionEscape(question.topic)}</small><h3>${missionEscape(question.text)}</h3></div><span id="missionQuestionState">Practice</span></div><p class="mission-hint"><b>Hint</b> ${missionEscape(question.hint)}</p><form id="missionQuestionForm"><input name="answer" placeholder="Your answer" required><textarea name="reasoning" placeholder="Show the first step you used" required></textarea><button>Check my attempt</button></form><div id="missionAnswerFeedback"></div>`;
    document.getElementById('missionQuestionForm').onsubmit = submitMissionQuestion;
  } catch (error) {
    target.innerHTML = `<p class="mission-error">${missionEscape(error.message)}</p>`;
  }
}

async function submitMissionQuestion(event) {
  event.preventDefault();
  const session = window.activeMissionSession;
  if (!session?.question) return;
  const form = event.target;
  const button = form.querySelector('button');
  const feedback = document.getElementById('missionAnswerFeedback');
  if (button) { button.disabled = true; button.textContent = 'Iqra is checking...'; }
  if (feedback) {
    feedback.className = 'mission-feedback loading';
    feedback.innerHTML = '<strong>Iqra is checking your answer...</strong><p>XP will appear here as soon as the attempt is saved.</p>';
  }
  try {
    const payload = Object.fromEntries(new FormData(form));
    payload.question_id = session.question.id;
    const result = await api('/api/quiz/submit', {method:'POST', body:JSON.stringify(payload)});
    session.questionAttempted = true;
    session.questionCorrect = Boolean(result.correct);
    const steps = Array.isArray(result.replay?.better_path) && result.replay.better_path.length ? result.replay.better_path : ['Read the question carefully.', 'Write the known information.', 'Try one smaller step and check it.'];
    const state = document.getElementById('missionQuestionState');
    if (state) {
      state.className = result.correct ? 'mission-state-correct' : 'mission-state-repair';
      state.textContent = result.correct ? `Cleared +${result.xp_earned} XP` : `Saved +${result.xp_earned} XP`;
    }
    if (feedback) {
      feedback.className = result.correct ? 'mission-feedback correct' : 'mission-feedback repair';
      feedback.innerHTML = `<div><strong>${result.correct ? 'Correct — quiz XP added now.' : 'Attempt saved — XP added for trying.'}</strong><span>+${result.xp_earned} XP</span></div><p>${missionEscape(result.replay?.message || 'Your attempt was saved.')}</p><ol>${steps.map(step => `<li>${missionEscape(step)}</li>`).join('')}</ol><p class="mission-next-note">${result.correct ? 'Now write your takeaway below to unlock the mission completion XP.' : 'Review the better path, write your takeaway, then finish the mission when ready.'}</p>`;
    }
    form.querySelectorAll('input,textarea,button').forEach(item => item.disabled = true);
    if (button) button.textContent = result.correct ? 'Question cleared' : 'Attempt saved';
    uiToast(result.correct ? `Correct. +${result.xp_earned} XP added.` : `Attempt saved. +${result.xp_earned} XP added.`);
    setMissionProgress();
    if (typeof runOperatingSystem === 'function') runOperatingSystem();
  } catch (error) {
    if (feedback) {
      feedback.className = 'mission-feedback repair';
      feedback.innerHTML = `<strong>Could not check this attempt.</strong><p>${missionEscape(error.message)}</p>`;
    }
    if (button) { button.disabled = false; button.textContent = 'Check my attempt'; }
  }
}

function closeMissionSession() {
  if (window.activeMissionTimer) clearInterval(window.activeMissionTimer);
  window.activeMissionTimer = null;
  window.activeMissionSession = null;
  document.getElementById('missionSession')?.remove();
}

async function finishMissionSession() {
  const session = window.activeMissionSession;
  if (!session) return;
  const button = document.getElementById('finishMission');
  if (button) { button.disabled = true; button.textContent = 'Saving your progress...'; }
  try {
    await api(`/api/missions/${session.mission.id}/complete`, {method:'POST'});
    closeMissionSession();
    uiToast(`Mission completed. +${session.mission.xp} XP added to your profile.`);
    window.studentView();
  } catch (error) {
    if (button) { button.disabled = false; button.textContent = 'Try finishing again'; }
    const errorBox = document.getElementById('missionError');
    if (errorBox) errorBox.textContent = error.message;
  }
}

window.startMissionSession = function startMissionSession(id) {
  const mission = window.currentMissions?.find(item => item.id === id);
  if (!mission) { uiToast('This mission could not be loaded. Refresh the dashboard and try again.'); return; }
  closeMissionSession();
  window.activeMissionSession = {mission, questionAttempted:false, questionCorrect:false, remaining:20 * 60};
  const modal = document.createElement('div');
  modal.id = 'missionSession';
  modal.className = 'mission-session';
  const codingAction = mission.subject === 'Programming' ? '<button type="button" class="mission-code-link" onclick="openMissionCodeLab()">Open Code Lab for this mission</button>' : '';
  modal.innerHTML = `<section class="mission-sheet mission-sheet-friendly"><button class="mission-close" onclick="closeMissionSession()" aria-label="Close mission">&times;</button><header><div><small>${missionEscape(mission.subject || 'PERSONALIZED')} MISSION</small><h2>${missionEscape(mission.title)}</h2><p>${missionEscape(mission.description)}</p></div><div class="mission-timer"><span>FOCUS TIMER</span><b id="missionTimer">20:00</b><small>pause anytime</small></div></header><p class="mission-guidance">${missionEscape(missionGuidance(mission))}</p>${codingAction}<ol class="mission-steps mission-steps-friendly"><li data-mission-step><label><input id="missionRead" type="checkbox" onchange="setMissionProgress()"><span><b>1. Set your intention</b> Read the goal and decide what one small result you want.</span></label></li><li data-mission-step><span><b>2. Clear one focused question</b> Answer the question below. Quiz XP is added immediately after Iqra checks it.</span></li><li data-mission-step><label><span><b>3. Capture your takeaway</b> Write at least one sentence about what clicked or what to revisit.</span><textarea id="missionTakeaway" oninput="setMissionProgress()" placeholder="Today I noticed that..."></textarea></label></li></ol><section id="missionQuestion" class="mission-question mission-question-friendly"></section><p id="missionError" class="mission-error"></p><footer><span>Quiz XP appears after checking. Mission XP appears after finishing all 3 steps.</span><button id="finishMission" disabled onclick="finishMissionSession()">Complete 0/3 steps to finish</button></footer></section>`;
  document.body.append(modal);
  loadMissionQuestion();
  window.activeMissionTimer = setInterval(() => {
    const session = window.activeMissionSession;
    const timer = document.getElementById('missionTimer');
    if (!session || !timer) return;
    session.remaining = Math.max(0, session.remaining - 1);
    timer.textContent = missionClock(session.remaining);
  }, 1000);
};

window.openMissionCodeLab = function openMissionCodeLab() {
  closeMissionSession();
  const button = document.getElementById('adaptiveCodeNav');
  if (button) { v3Tab('v3code', button); loadCodingLab(window.adaptiveCurrent?.user?.coding_language); }
};
