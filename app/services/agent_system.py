"""Transparent, independently testable learning-agent summaries for the MVP."""
from sqlalchemy.orm import Session
from app.models import LearningDNA, Misconception, Mission, QuizAttempt, Reflection, User
from app.services.learning import risk_for

def build_operating_system(db: Session, user: User) -> dict:
    dna = db.get(LearningDNA, user.id)
    missions = db.query(Mission).filter_by(user_id=user.id).all()
    attempts = db.query(QuizAttempt).filter_by(user_id=user.id).order_by(QuizAttempt.created_at.desc()).limit(10).all()
    misconceptions = db.query(Misconception).filter_by(user_id=user.id).all()
    reflections = db.query(Reflection).filter_by(user_id=user.id).order_by(Reflection.created_at.desc()).limit(1).all()
    risk = risk_for(db, user.id)
    accuracy = round(sum(item.correct for item in attempts) * 100 / len(attempts)) if attempts else 0
    independence = max(35, min(95, 100 - len(attempts) * 3 + dna.confidence // 4))
    open_missions = [mission for mission in missions if not mission.completed]
    top_misconception = max(misconceptions, key=lambda item: item.frequency, default=None)
    agents = [
        {'id':'misconception', 'name':'Misconception DNA Agent', 'state':'active', 'signal': top_misconception.concept if top_misconception else 'No recurring misconception yet', 'detail': f'{top_misconception.frequency} pattern(s) recorded' if top_misconception else 'Continue collecting explicit reasoning.'},
        {'id':'risk', 'name':'Future Risk Predictor', 'state':'active', 'signal': f"{risk['topic']} · {risk['risk']}% risk", 'detail': risk['reason']},
        {'id':'handoff', 'name':'Cognitive Handoff', 'state':'active', 'signal': f'{independence}/100 independent thinking', 'detail': 'Iqra will guide first steps before giving a full solution.'},
        {'id':'motivation', 'name':'Motivation Engine', 'state':'active', 'signal': f'{dna.streak}-day learning rhythm', 'detail': 'Missions stay short and encouraging when confidence dips.'},
        {'id':'dna', 'name':'Learning DNA Engine', 'state':'active', 'signal': f'Logic {dna.logical}% · Memory {dna.memory}%', 'detail': 'Scores update from practice, explanations, and reflection.'},
        {'id':'replay', 'name':'Replay Thinking Agent', 'state':'ready', 'signal': f'{len(attempts)} recent thinking trail(s)', 'detail': 'Reviews only written reasoning, never hidden thoughts.'},
        {'id':'dream', 'name':'Dream Builder', 'state':'active', 'signal': user.goal or 'Set a future goal', 'detail': 'Connects today’s skills with a possible future pathway.'},
        {'id':'avatar', 'name':'Iqra AI Avatar', 'state':'online', 'signal':'Ready to coach', 'detail':'Supports questions, plans, explanations, and encouragement.'},
        {'id':'reflection', 'name':'Reflection AI', 'state':'ready', 'signal':'Reflection saved' if reflections else 'Reflection needed', 'detail': reflections[0].summary if reflections else 'A short reflection helps tomorrow’s plan adapt.'},
        {'id':'missions', 'name':'Daily Mission Generator', 'state':'active', 'signal': f'{len(open_missions)} mission(s) ready', 'detail':'Prioritizes weak prerequisites, goal relevance, and momentum.'},
        {'id':'game', 'name':'Gamification Engine', 'state':'active', 'signal': f'{dna.xp} XP · Level {max(1, dna.xp // 500 + 1)}', 'detail':'Rewards effort, completion, and independent explanation.'},
        {'id':'analytics', 'name':'Learning Analytics', 'state':'active', 'signal': f'{accuracy}% recent accuracy', 'detail':'Shows trends without reducing the student to marks.'},
    ]
    return {
        'profile': {'role':user.role, 'goal':user.goal or 'Not set', 'grade':user.grade or 'Not set', 'preference':user.study_preference or 'Not set'},
        'headline': f"Today, repair {risk['topic']} while protecting your {dna.streak}-day learning rhythm.",
        'agents': agents,
        'stats': {'accuracy':accuracy, 'independence':independence, 'risk':risk['risk'], 'active_agents':sum(agent['state'] in {'active','online'} for agent in agents)},
    }
