from pathlib import Path
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session
from app.database import Base, engine, get_db
from app.models import CodeChallengeProgress, CommunityPost, LearningDNA, Mission, Notification, QuizAttempt, Reflection, User
from app.security import create_token, current_user, hash_password, require_role, verify_password
from app.services.learning import analyze_answer, dashboard, question_catalog
from app.services.code_execution import coding_dashboard, run_code
from app.services.nova import motivation_and_plan, reply as nova_reply
from app.services.agent_system import build_operating_system

app = FastAPI(title='LearnDNA API', version='1.0.0')
ROOT = Path(__file__).parent
app.mount('/static', StaticFiles(directory=ROOT/'static'), name='static')

@app.middleware('http')
async def prevent_stale_ui_cache(request, call_next):
    response = await call_next(request)
    if request.url.path == '/' or request.url.path.startswith('/static/'):
        response.headers['Cache-Control'] = 'no-store, max-age=0, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
    return response

class Register(BaseModel):
    name: str = Field(min_length=2, max_length=120); email: EmailStr; password: str = Field(min_length=8); role: str = 'student'; goal: str | None = None
class Login(BaseModel): email: EmailStr; password: str
class Answer(BaseModel):
    answer: str = Field(min_length=1,max_length=300)
    reasoning: str = Field(default='',max_length=5000)
    question_id: str | None = Field(default=None, max_length=80)
class CodeRunIn(BaseModel):
    language: str = Field(min_length=1, max_length=30)
    code: str = Field(min_length=1, max_length=6000)
    challenge_id: str | None = Field(default=None, max_length=80)
class ReflectionIn(BaseModel): confused: str; understood: str; difficult: str; confidence: int = Field(ge=1,le=5)
class PostIn(BaseModel): body: str = Field(min_length=2,max_length=1000)
class CoachIn(BaseModel): message: str = Field(min_length=1, max_length=1000)
class NotificationIn(BaseModel):
    recipient_id: str | None = Field(default=None, min_length=1, max_length=36)
    title: str = Field(min_length=2, max_length=120)
    message: str = Field(min_length=2, max_length=600)
class ParentLinkIn(BaseModel): student_id: str = Field(min_length=1, max_length=36)
class ProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    goal: str | None = Field(default=None, max_length=120)
    avatar_url: str | None = Field(default=None, max_length=700000)
    bio: str | None = Field(default=None, max_length=500)
    grade: str | None = Field(default=None, max_length=40)
    study_preference: str | None = Field(default=None, max_length=120)
    subjects: str | None = Field(default=None, max_length=500)
    coding_language: str | None = Field(default=None, max_length=30)

@app.on_event('startup')
def startup():
    Base.metadata.create_all(engine)
    # Lightweight forward-compatible migration for existing local demo databases.
    migrations = {
        'users': {'avatar_url': 'TEXT', 'bio': 'VARCHAR(500)', 'grade': 'VARCHAR(40)', 'study_preference': 'VARCHAR(120)', 'subjects': 'TEXT', 'coding_language': 'VARCHAR(30)', 'linked_student_id': 'VARCHAR(36)'},
        'missions': {'subject': 'VARCHAR(60)', 'day_key': 'VARCHAR(10)'},
        'quiz_attempts': {'question_id': 'VARCHAR(80)', 'subject': 'VARCHAR(60)'},
    }
    with engine.begin() as connection:
        for table_name, additions in migrations.items():
            existing = {column['name'] for column in inspect(engine).get_columns(table_name)}
            for column, kind in additions.items():
                if column not in existing:
                    connection.execute(text(f'ALTER TABLE {table_name} ADD COLUMN {column} {kind}'))
    db = next(get_db())
    try:
        if not db.query(User).filter_by(email='student@learndna.demo').first():
            for name,email,role,goal in [('Alex Student','student@learndna.demo','student','AI Engineer'),('Tara Teacher','teacher@learndna.demo','teacher',None),('Priya Parent','parent@learndna.demo','parent',None),('Admin','admin@learndna.demo','admin',None)]:
                u=User(name=name,email=email,role=role,goal=goal,password_hash=hash_password('LearnDNA123!')); db.add(u); db.flush()
                if role=='student':
                    db.add(LearningDNA(user_id=u.id, xp=820, streak=8)); db.add_all([Mission(user_id=u.id,title='Solve 10 Questions',description='Build algebra fluency.',xp=100),Mission(user_id=u.id,title='Explain one concept',description='Write a short explanation in your own words.',xp=50),Mission(user_id=u.id,title='Replay My Thinking',description='Reflect on a solved question.',xp=75)])
            db.commit()
        demo_student = db.query(User).filter_by(email='student@learndna.demo').first()
        demo_parent = db.query(User).filter_by(email='parent@learndna.demo').first()
        if demo_student and demo_parent and not demo_parent.linked_student_id:
            demo_parent.linked_student_id = demo_student.id
            db.commit()
    finally: db.close()

@app.get('/')
def index(): return FileResponse(ROOT/'static'/'index.html')
@app.post('/api/auth/register')
def register(data:Register,db:Session=Depends(get_db)):
    if data.role not in {'student','teacher','parent'}: raise HTTPException(400,'Invalid role.')
    if db.query(User).filter_by(email=data.email.lower()).first(): raise HTTPException(409,'An account with that email already exists.')
    u=User(name=data.name,email=data.email.lower(),password_hash=hash_password(data.password),role=data.role,goal=data.goal);db.add(u);db.flush()
    if u.role=='student': db.add(LearningDNA(user_id=u.id)); db.add(Mission(user_id=u.id,title='First Learning Mission',description='Solve a question and explain your thinking.',xp=75))
    db.commit(); return {'token':create_token(u),'user':{'name':u.name,'role':u.role}}
@app.post('/api/auth/login')
def login(data:Login,db:Session=Depends(get_db)):
    u=db.query(User).filter_by(email=data.email.lower()).first()
    if not u or not verify_password(data.password,u.password_hash): raise HTTPException(401,'Incorrect email or password.')
    return {'token':create_token(u),'user':{'name':u.name,'role':u.role}}
@app.get('/api/me')
def me(user:User=Depends(current_user)): return {'name':user.name,'email':user.email,'role':user.role,'goal':user.goal,'avatar':user.avatar_name,'avatar_url':user.avatar_url,'bio':user.bio,'grade':user.grade,'study_preference':user.study_preference,'subjects':user.subjects,'coding_language':user.coding_language}
@app.patch('/api/me')
def update_me(data: ProfileUpdate, user:User=Depends(current_user), db:Session=Depends(get_db)):
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit(); db.refresh(user)
    return {'name':user.name,'email':user.email,'role':user.role,'goal':user.goal,'avatar':user.avatar_name,'avatar_url':user.avatar_url,'bio':user.bio,'grade':user.grade,'study_preference':user.study_preference,'subjects':user.subjects,'coding_language':user.coding_language}
@app.get('/api/student/dashboard')
def student_dashboard(user:User=Depends(require_role('student')),db:Session=Depends(get_db)): return dashboard(db,user)
@app.get('/api/quiz/questions')
def questions(subject: str | None = None, user:User=Depends(require_role('student'))): return question_catalog(user, subject)
@app.get('/api/code-lab')
def code_lab(user:User=Depends(require_role('student')), db:Session=Depends(get_db)): return coding_dashboard(db, user)
@app.post('/api/code-lab/run')
def code_lab_run(data: CodeRunIn, user:User=Depends(require_role('student')), db:Session=Depends(get_db)): return run_code(db, user, data.language, data.code, data.challenge_id)
@app.post('/api/coach')
def coach(data: CoachIn, user:User=Depends(require_role('student')),db:Session=Depends(get_db)):
    return nova_reply(db, user, data.message)
@app.get('/api/student/motivation')
def motivation(user:User=Depends(require_role('student')),db:Session=Depends(get_db)):
    dna = db.get(LearningDNA, user.id)
    missions = db.query(Mission).filter_by(user_id=user.id, completed=False).all()
    from app.services.learning import risk_for
    return motivation_and_plan(db, user, dna, risk_for(db, user.id), missions)
@app.get('/api/student/ai-operating-system')
def ai_operating_system(user:User=Depends(require_role('student')),db:Session=Depends(get_db)):
    return build_operating_system(db, user)
@app.post('/api/quiz/submit')
def submit(data:Answer,user:User=Depends(require_role('student')),db:Session=Depends(get_db)): return analyze_answer(db,user,data.answer,data.reasoning,data.question_id)
@app.post('/api/missions/{mission_id}/complete')
def complete(mission_id:str,user:User=Depends(require_role('student')),db:Session=Depends(get_db)):
    m=db.get(Mission,mission_id)
    if not m or m.user_id!=user.id: raise HTTPException(404,'Mission not found.')
    if not m.completed: m.completed=True; db.get(LearningDNA,user.id).xp += m.xp; db.commit()
    return {'ok':True}
@app.post('/api/reflections')
def reflection(data:ReflectionIn,user:User=Depends(require_role('student')),db:Session=Depends(get_db)):
    summary=f"You felt most challenged by {data.difficult}. Your confidence is {'growing' if data.confidence>=3 else 'still building'}; revisit {data.confused} in a short session tomorrow."
    db.add(Reflection(user_id=user.id,summary=summary,**data.model_dump()));db.commit();return {'summary':summary,'mode':'Local demo analysis'}
def notification_data(item: Notification, sender: User | None = None):
    return {'id': item.id, 'title': item.title, 'message': item.message, 'read': item.read, 'sender_role': item.sender_role, 'sender_name': sender.name if sender else 'LearnDNA', 'created_at': item.created_at.isoformat()}

def student_snapshot(db: Session, student: User):
    dna = db.get(LearningDNA, student.id)
    recent = db.query(QuizAttempt).filter_by(user_id=student.id).order_by(QuizAttempt.created_at.desc()).limit(10).all()
    missions = db.query(Mission).filter_by(user_id=student.id).all()
    accuracy = round(sum(item.correct for item in recent) * 100 / len(recent)) if recent else 0
    completed = sum(item.completed for item in missions)
    from app.services.learning import risk_for
    risk = risk_for(db, student.id)
    return {
        'id': student.id, 'name': student.name, 'goal': student.goal or 'Learning goal not set', 'grade': student.grade or 'Student',
        'xp': dna.xp if dna else 0, 'streak': dna.streak if dna else 0, 'consistency': dna.consistency if dna else 0,
        'accuracy': accuracy, 'missions_completed': completed, 'missions_total': len(missions), 'risk': risk,
        'subjects': student.subjects or 'Subjects not selected',
    }

@app.get('/api/notifications')
def notifications(user: User = Depends(current_user), db: Session = Depends(get_db)):
    entries = db.query(Notification).filter_by(recipient_user_id=user.id).order_by(Notification.created_at.desc()).limit(30).all()
    senders = {entry.sender_user_id: db.get(User, entry.sender_user_id) for entry in entries}
    return {'items': [notification_data(entry, senders.get(entry.sender_user_id)) for entry in entries], 'unread': sum(not entry.read for entry in entries)}

@app.post('/api/notifications')
def send_notification(data: NotificationIn, user: User = Depends(require_role('teacher', 'parent', 'admin')), db: Session = Depends(get_db)):
    recipient_id = data.recipient_id
    if user.role == 'parent':
        recipient_id = user.linked_student_id
        if not recipient_id:
            raise HTTPException(400, 'Choose your child in the Parent workspace before sending a note.')
    if not recipient_id:
        raise HTTPException(400, 'Choose a student to receive this note.')
    recipient = db.get(User, recipient_id)
    if not recipient or recipient.role != 'student':
        raise HTTPException(404, 'Student not found.')
    entry = Notification(recipient_user_id=recipient.id, sender_user_id=user.id, sender_role=user.role, title=data.title.strip(), message=data.message.strip())
    db.add(entry); db.commit(); db.refresh(entry)
    return {'ok': True, 'notification': notification_data(entry, user)}

@app.post('/api/notifications/{notification_id}/read')
def read_notification(notification_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    entry = db.get(Notification, notification_id)
    if not entry or entry.recipient_user_id != user.id:
        raise HTTPException(404, 'Notification not found.')
    entry.read = True; db.commit()
    return {'ok': True}

@app.post('/api/parent/link-child')
def link_child(data: ParentLinkIn, user: User = Depends(require_role('parent', 'admin')), db: Session = Depends(get_db)):
    student = db.get(User, data.student_id)
    if not student or student.role != 'student':
        raise HTTPException(404, 'Student account not found.')
    user.linked_student_id = student.id; db.commit()
    return {'ok': True, 'child': {'id': student.id, 'name': student.name}}

@app.get('/api/teacher/dashboard')
def teacher(user:User=Depends(require_role('teacher','admin')),db:Session=Depends(get_db)):
    students = db.query(User).filter_by(role='student').order_by(User.name).all()
    snapshots = [student_snapshot(db, student) for student in students]
    average_accuracy = round(sum(item['accuracy'] for item in snapshots) / len(snapshots)) if snapshots else 0
    heatmap = [{'topic':'Algebra', 'value':82}, {'topic':'Functions', 'value':64}, {'topic':'Programming logic', 'value':47}]
    recent_notes = db.query(Notification).filter_by(sender_user_id=user.id).order_by(Notification.created_at.desc()).limit(6).all()
    return {'teacher': {'name': user.name}, 'students': len(students), 'student_list': snapshots, 'average_accuracy': average_accuracy, 'heatmap': heatmap, 'recommendation':'Use a short worked-example lesson, then ask students to explain the first algebra step in their own words.', 'recent_notes': [notification_data(note) for note in recent_notes]}

@app.get('/api/parent/dashboard')
def parent(user:User=Depends(require_role('parent','admin')),db:Session=Depends(get_db)):
    children = db.query(User).filter_by(role='student').order_by(User.name).all()
    selected = db.get(User, user.linked_student_id) if user.linked_student_id else (children[0] if children else None)
    snapshot = student_snapshot(db, selected) if selected else None
    recent_notes = db.query(Notification).filter_by(sender_user_id=user.id).order_by(Notification.created_at.desc()).limit(6).all()
    return {'parent': {'name': user.name}, 'child': snapshot, 'available_children': [{'id': child.id, 'name': child.name, 'goal': child.goal or 'Student'} for child in children], 'recent_notes': [notification_data(note) for note in recent_notes], 'support': f'Build confidence with a short {snapshot["risk"]["topic"]} practice session.' if snapshot else 'Link a child account to see supportive next steps.'}
@app.get('/api/community')
def community(db:Session=Depends(get_db)):
    posts=db.query(CommunityPost).order_by(CommunityPost.created_at.desc()).limit(20).all(); return [{'id':p.id,'body':p.body,'likes':p.likes} for p in posts]
@app.post('/api/community')
def post(data:PostIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    p=CommunityPost(user_id=user.id,body=data.body);db.add(p);db.commit();return {'id':p.id,'body':p.body,'likes':0}
