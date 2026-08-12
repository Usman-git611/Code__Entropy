from datetime import date
import time

import httpx

from app.settings import settings
from app.services.learning import _stored_iqra_answer, coach_reply


# After a local-model failure, reply with the useful on-device tutor for a
# moment instead of leaving the student waiting behind a second slow request.
_ollama_unavailable_until = 0.0

NOVA_INSTRUCTIONS = """You are Iqra, LearnDNA's warm, expert AI learning companion.
You help students understand school and technical topics. Give accurate, direct answers when
they ask for one, then explain the reasoning in clear numbered steps. For problem-solving,
invite the student to attempt one step, but do not refuse to help or hide the final answer.
Never claim access to a student's hidden thoughts; only discuss reasoning they share. Be
encouraging without overpraising. Do not make medical or psychological diagnoses. Keep your
answer concise, practical, and appropriate for a student. Keep every answer under 180 words,
and simple questions under 100 words. Use simple language unless asked for depth."""


def ollama_chat(payload: dict) -> str:
    """Return a single quick local-model response or let the tutor fallback answer."""
    global _ollama_unavailable_until
    if time.monotonic() < _ollama_unavailable_until:
        raise RuntimeError('Local model is cooling down after a connection failure')
    payload['keep_alive'] = '15m'
    try:
        response = httpx.post(
            f'{settings.ollama_host.rstrip("/")}/api/chat',
            json=payload,
            timeout=httpx.Timeout(connect=2.5, read=26, write=10, pool=2.5),
        )
        response.raise_for_status()
        content = response.json().get('message', {}).get('content', '').strip()
        if content:
            return content
        raise ValueError('Ollama returned no chat content')
    except Exception:
        _ollama_unavailable_until = time.monotonic() + 20
        raise


def reply(db, user, message: str):
    stored = _stored_iqra_answer(db, user, message.lower())
    if stored:
        return {'reply': stored, 'mode': 'Iqra demo answer store', 'handoff': 'Reliable demo response'}
    if settings.ai_provider.lower() == 'openai' and settings.openai_api_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.openai_api_key)
            context = f"Student name: {user.name}. Goal: {user.goal or 'not set'}. Student message: {message}"
            response = client.responses.create(model=settings.ai_model, instructions=NOVA_INSTRUCTIONS, input=context, store=False)
            content = response.output_text.strip()
            if content:
                return {'reply': content, 'mode': f'Real OpenAI model: {settings.ai_model}', 'handoff': 'Direct explanation + guided practice'}
        except Exception:
            pass
        return {'reply': 'Iqra could not reach the AI provider just now. Please try again in a moment.', 'mode': 'Provider connection issue', 'handoff': 'Retry'}
    if settings.ai_provider.lower() == 'ollama':
        try:
            payload = {
                'model': settings.ollama_model,
                'stream': False,
                'messages': [
                    {'role': 'system', 'content': NOVA_INSTRUCTIONS},
                    {'role': 'user', 'content': f'Student name: {user.name}. Goal: {user.goal or "not set"}. Student message: {message}'},
                ],
                'options': {'temperature': 0.4, 'num_predict': 260},
            }
            content = ollama_chat(payload)
            return {'reply': content, 'mode': f'Real local model: {settings.ollama_model}', 'handoff': 'Direct explanation + guided practice'}
        except Exception:
            fallback = coach_reply(db, user, message)
            fallback['mode'] = 'Iqra local guidance (AI model reconnecting)'
            fallback['handoff'] = 'Guided support'
            return fallback
    return coach_reply(db, user, message)


DAILY_MOMENTUM_LINES = (
    'Engineers are built one solved problem at a time.',
    'Debug your doubts the same way you debug code: one line, one clue, one fix.',
    'Your future engineering skill is hidden inside today\'s focused practice.',
    'A difficult concept is not a stop sign; it is the next design challenge.',
    'Every formula becomes friendlier after one honest attempt.',
    'Strong students are not always fast; they are willing to return and refine.',
    'One clean solution today can become tomorrow\'s confidence.',
    'The best engineer in you grows when you ask better questions.',
    'Small practice sessions compound like good code reused well.',
    'A mistake is data. Read it, learn from it, and improve the design.',
    'You do not need to master the whole syllabus today; master the next step.',
    'Your attention is your strongest study tool. Protect it for one session.',
    'Every circuit, equation, and program starts with a simple first step.',
    'Progress is built when you stay with the problem a little longer.',
    'Think like an engineer: observe, test, adjust, repeat.',
    'The student who shows up today gives the future engineer a head start.',
    'One focused hour can repair a week of confusion.',
    'Your brain learns patterns by meeting them again with patience.',
    'Do not chase perfect notes; chase clear understanding.',
    'The next problem is practice, not punishment.',
    'Every solved bug teaches you how to think under pressure.',
    'A calm mind can solve what a rushed mind keeps missing.',
    'Your dream career needs today\'s small discipline.',
    'You are not behind; you are building from where you stand.',
    'The strongest foundation is made from repeated basics.',
    'Equations, code, and concepts all reward steady attention.',
    'A clear question is already half of good engineering thinking.',
    'Today, choose depth over distraction.',
    'Learning is not magic; it is repeated contact with the right challenge.',
    'One topic understood deeply is better than five topics skimmed quickly.',
    'The lab starts in your mind before it starts on the screen.',
    'Every line of code you write teaches your logic to be sharper.',
    'You are training your problem-solving muscle today.',
    'A hard question is a workout for your future skill.',
    'Focus on the next ten minutes; momentum will handle the rest.',
    'Engineers do not guess forever; they test and learn.',
    'Your future projects will thank you for today\'s fundamentals.',
    'Slow progress is still progress when it is honest.',
    'A strong concept map beats memorizing without meaning.',
    'If it feels confusing, slow down and find the first clear piece.',
    'The best way to learn code is to write, run, read, and revise.',
    'Every calculation is a chance to build accuracy and patience.',
    'The goal is not to look smart; the goal is to become skilled.',
    'One repaired misconception can unlock an entire chapter.',
    'You are building the mindset that solves real-world problems.',
    'Practice today like someone who trusts their future.',
    'The answer matters, but your method matters more.',
    'A focused student today becomes a reliable engineer tomorrow.',
    'Your consistency is quietly becoming your advantage.',
    'Hard work becomes lighter when you make the task specific.',
    'Start with one example. Understanding often follows examples.',
    'Your notebook is not just paper; it is a record of your thinking.',
    'One clean diagram can turn confusion into a path.',
    'Every engineering dream needs boring basics done well.',
    'Do the small thing fully. That is how big skills are made.',
    'Your questions are signals of growth, not weakness.',
    'The first attempt is allowed to be messy.',
    'Today\'s revision is tomorrow\'s speed.',
    'Be patient with the basics; they carry the advanced topics.',
    'A solved problem is proof that effort can become ability.',
    'The strongest learners know when to pause and reason.',
    'Code improves when you run it; thinking improves when you explain it.',
    'One bug fixed honestly teaches more than copying a perfect answer.',
    'If the chapter feels large, shrink it into one practice question.',
    'Your focus today is an investment in every future interview and exam.',
    'Engineering confidence grows from repeated small wins.',
    'Do not wait for motivation; create it with one completed task.',
    'The concepts you practice today become tools you can use later.',
    'A good study plan starts with one clear target.',
    'You can be tired and still make one meaningful move.',
    'Every expert was once slow at the basics.',
    'Read the error, not your fear.',
    'A formula is easier to remember when you understand why it works.',
    'Build your logic like a bridge: carefully, step by step.',
    'The problem in front of you is training your future self.',
    'Your effort is not wasted when it teaches you what to try next.',
    'A short focused session beats a long distracted one.',
    'Learn the concept, then let practice make it fluent.',
    'Your future depends less on one result and more on repeated effort.',
    'The best students do not avoid hard topics; they break them down.',
    'Today\'s small correction can prevent tomorrow\'s big confusion.',
    'A clear mind starts with a clear next task.',
    'Give yourself one problem worth finishing.',
    'Engineering is applied patience.',
    'The syllabus is big, but your next step is small.',
    'Every solved example gives your brain another pattern to trust.',
    'You are not just studying; you are learning how to think.',
    'A strong foundation makes advanced work feel possible.',
    'The next run, the next calculation, the next explanation: that is progress.',
    'Turn pressure into a plan and the plan into one action.',
    'Your future skill is being assembled quietly today.',
    'One honest explanation in your own words is a real achievement.',
    'If you can explain the step, you are closer than you think.',
    'The engineer inside you grows through practice, not panic.',
    'Do the next problem with care, not hurry.',
    'Learning gets easier when you stop fighting the first draft.',
    'Your consistency today is more powerful than your mood.',
    'Build the basics so well that confidence has somewhere to stand.',
    'The best project you are building right now is yourself.',
    'One focused start can change the tone of the whole day.',
)


def motivation_and_plan(db, user, dna, risk, missions):
    """Return the daily brief instantly, without waiting for a local model."""
    index = date.today().toordinal() % len(DAILY_MOMENTUM_LINES)
    focus = risk['topic'] or 'your next learning goal'
    mission_title = missions[0].title if missions else 'one short practice activity'
    quote = DAILY_MOMENTUM_LINES[index]
    plan = (
        f'1. Spend 10 focused minutes on {focus}.\n'
        f'2. Complete: {mission_title}.\n'
        '3. Finish by writing one sentence about what clicked or needs another try.'
    )
    return {
        'quote': quote,
        'plan': plan,
        'focus': focus,
        'day_key': date.today().isoformat(),
        'mode': 'Instant adaptive momentum brief',
    }
