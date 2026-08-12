from datetime import date
import re

from sqlalchemy.orm import Session

from app.models import LearningDNA, Misconception, Mission, QuizAttempt, User
from app.services.catalog import QUESTION_BANK, SUBJECT_PATHS, public_question, questions_for_subjects, mission_plan_for_day, subjects_for_user


def _normalise_answer(value: str) -> str:
    return re.sub(r'\s+', '', value.casefold().replace('x=', '').replace('ohms', 'ohm'))


def _find_question(question_id: str | None, user: User) -> dict:
    available = questions_for_subjects(subjects_for_user(user))
    if question_id:
        found = next((item for item in available if item['id'] == question_id), None)
        if found:
            return found
    return available[0]


def _subject_accuracy(db: Session, user_id: str, subject: str) -> int | None:
    attempts = db.query(QuizAttempt).filter_by(user_id=user_id, subject=subject).order_by(QuizAttempt.created_at.desc()).limit(12).all()
    return round(100 * sum(item.correct for item in attempts) / len(attempts)) if attempts else None


def risk_for(db: Session, user_id: str):
    user = db.get(User, user_id)
    dna = db.get(LearningDNA, user_id)
    subjects = subjects_for_user(user)
    scores = {subject: _subject_accuracy(db, user_id, subject) for subject in subjects}
    attempts = db.query(QuizAttempt).filter_by(user_id=user_id).order_by(QuizAttempt.created_at.desc()).limit(20).all()
    known_scores = {subject: score for subject, score in scores.items() if score is not None}
    if known_scores:
        target = min(known_scores, key=known_scores.get)
        accuracy = known_scores[target]
    else:
        target = subjects[0]
        accuracy = 50
    mistakes = db.query(Misconception).filter_by(user_id=user_id).all()
    relevant_mistakes = [item for item in mistakes if item.concept.casefold() in target.casefold() or target.casefold() in item.concept.casefold()]
    frequency = sum(item.frequency for item in relevant_mistakes) or sum(item.frequency for item in mistakes)
    risk = min(92, max(18, 76 - accuracy + frequency * 7 + max(0, 70 - dna.confidence) // 3))
    reason = f'{accuracy}% recent accuracy in {target}' if known_scores else f'No answered {target} questions yet'
    if frequency:
        reason += '; repeated repair signals were detected'
    return {
        'topic': SUBJECT_PATHS[target], 'subject': target, 'risk': risk, 'reason': reason,
        'repair': f'Complete a focused {target} repair mission', 'minutes': 20,
        'performance': scores, 'attempts': len(attempts),
    }


def ensure_daily_missions(db: Session, user: User):
    today = date.today().isoformat()
    subjects = subjects_for_user(user)
    current = db.query(Mission).filter_by(user_id=user.id, day_key=today).all()
    current_subjects = {item.subject for item in current if item.subject}
    if current and current_subjects == set(subjects):
        return current
    # Subject choices are explicit user input. Keep completed work, replace only uncompleted
    # generated missions if the student changes their selected subjects mid-day.
    for mission in current:
        if not mission.completed:
            db.delete(mission)
    db.flush()
    performance = {subject: _subject_accuracy(db, user.id, subject) for subject in subjects}
    generated = []
    for item in mission_plan_for_day(user, subjects, performance):
        mission = Mission(user_id=user.id, day_key=today, **item)
        db.add(mission)
        generated.append(mission)
    db.commit()
    return db.query(Mission).filter_by(user_id=user.id, day_key=today).all()


def question_catalog(user: User, subject: str | None = None):
    subjects = subjects_for_user(user)
    questions = questions_for_subjects(subjects, subject)
    selected_subject = subject if subject in subjects else 'All selected subjects'
    return {
        'subjects': subjects,
        'selected_subject': selected_subject,
        'total': len(questions),
        'questions': [public_question(item) for item in questions],
    }


def analyze_answer(db: Session, user: User, answer: str, reasoning: str, question_id: str | None = None):
    question = _find_question(question_id, user)
    correct = _normalise_answer(answer) in {_normalise_answer(item) for item in question['answers']}
    dna = db.get(LearningDNA, user.id)
    attempt = QuizAttempt(user_id=user.id, question=question['text'], answer=answer, correct=correct, reasoning=reasoning, question_id=question['id'], subject=question['subject'])
    db.add(attempt)
    xp = 75 if correct else 25
    misconception = None
    if correct:
        dna.logical = min(100, dna.logical + 2)
        dna.problem_solving = min(100, dna.problem_solving + 2)
        dna.confidence = min(100, dna.confidence + 2)
        dna.consistency = min(100, dna.consistency + 1)
        replay = {'status': 'correct', 'message': 'Your answer is correct. Your written reasoning has been saved so you can reflect on the strategy that worked.', 'better_path': question['steps']}
    else:
        concept = f"{question['subject']}: {question['topic']}"
        existing = db.query(Misconception).filter_by(user_id=user.id, concept=concept).first()
        if existing:
            existing.frequency += 1
            misconception = existing
        else:
            misconception = Misconception(user_id=user.id, concept=concept, explanation=question['hint'], severity='medium')
            db.add(misconception)
        dna.confidence = max(20, dna.confidence - 2)
        replay = {'status': 'needs-repair', 'message': f"The answer needs another pass. Start with this hint: {question['hint']}", 'better_path': question['steps']}
    dna.xp += xp
    if not correct:
        existing_repair = db.query(Mission).filter_by(user_id=user.id, title=f"Repair {question['topic']}", day_key=date.today().isoformat()).first()
        if not existing_repair:
            db.add(Mission(user_id=user.id, title=f"Repair {question['topic']}", description=f"Practice {question['topic']} with guided feedback and explain one step.", xp=60, kind='repair', subject=question['subject'], day_key=date.today().isoformat()))
    db.commit()
    return {
        'correct': correct, 'xp_earned': xp, 'question': public_question(question),
        'misconception': None if correct else {'concept': misconception.concept, 'severity': misconception.severity, 'frequency': misconception.frequency, 'confidence': dna.confidence},
        'replay': replay, 'future_risk': risk_for(db, user.id),
    }


def dashboard(db: Session, user: User):
    dna = db.get(LearningDNA, user.id)
    missions = ensure_daily_missions(db, user)
    missions.sort(key=lambda item: (item.completed, item.subject or '', item.title))
    recent = db.query(QuizAttempt).filter_by(user_id=user.id).order_by(QuizAttempt.created_at.desc()).limit(12).all()
    accuracy = round(100 * sum(item.correct for item in recent) / len(recent)) if recent else 0
    subjects = subjects_for_user(user)
    return {
        'user': {'name': user.name, 'role': user.role, 'goal': user.goal or 'Your future', 'avatar': user.avatar_name, 'avatar_url': user.avatar_url, 'bio': user.bio, 'grade': user.grade, 'study_preference': user.study_preference, 'subjects': user.subjects, 'coding_language': user.coding_language},
        'subjects': subjects, 'subject_performance': {subject: _subject_accuracy(db, user.id, subject) for subject in subjects},
        'level': max(1, dna.xp // 500 + 1), 'xp': dna.xp, 'next_level_xp': (dna.xp // 500 + 1) * 500, 'streak': dna.streak,
        'learning_dna': {key: getattr(dna, key) for key in ['logical', 'critical', 'problem_solving', 'creativity', 'memory', 'visual', 'confidence', 'attention', 'communication', 'consistency']},
        'missions': [{'id': item.id, 'title': item.title, 'description': item.description, 'xp': item.xp, 'completed': item.completed, 'kind': item.kind, 'subject': item.subject} for item in missions],
        'risk': risk_for(db, user.id), 'quiz_accuracy': accuracy,
        'independent_thinking': max(35, min(95, 100 - (len(recent) * 3) + dna.confidence // 4)),
        'ai_mode': 'Local adaptive analysis',
    }


def coach_reply(db: Session, user: User, message: str):
    """A useful, transparent fallback when the optional local model is unavailable."""
    dna = db.get(LearningDNA, user.id)
    independent = max(35, min(95, 100 - dna.confidence // 5))
    msg = message.lower()
    stored = _stored_iqra_answer(db, user, msg)
    if stored:
        return {'reply': stored, 'mode': 'Iqra demo answer store', 'independent_thinking': independent, 'handoff': 'Reliable demo response'}
    # These focused paths make the local tutor genuinely useful when Ollama is
    # restarting.  They deliberately match the student's *task*, rather than
    # returning one generic Python paragraph for every programming question.
    if ('python' in msg or 'program' in msg or 'code' in msg) and ('print' in msg or 'output' in msg or 'display' in msg):
        reply = ('To print text in Python, use print() with quotation marks:\n\n'
                 'print("Hello, Learner!")\n\n'
                 'Run it once, then change the words inside the quotes to make it your own.\n'
                 'Tip: text needs quotes; a number such as print(7) does not.')
    elif 'python' in msg and ('variable' in msg or 'store' in msg):
        reply = ('A variable gives a value a useful name. In Python, use = to store it:\n\n'
                 'score = 12\nprint(score)\n\n'
                 'The first line stores 12. The second line shows the value. Try changing score to a number you choose.')
    elif 'python' in msg and ('loop' in msg or 'range' in msg or 'repeat' in msg):
        reply = ('A for loop repeats an action. This prints the numbers 1 to 5:\n\n'
                 'for number in range(1, 6):\n    print(number)\n\n'
                 'range stops before its last number, so 6 is used to include 5. Try changing the end number.')
    elif 'python' in msg and ('if' in msg or 'condition' in msg):
        reply = ('An if statement runs code only when a condition is true:\n\n'
                 'score = 72\nif score >= 50:\n    print("Passed")\n\n'
                 'Keep the indented print line underneath the if line. What should happen if score is 40?')
    elif 'python' in msg and ('function' in msg or 'def ' in msg):
        reply = ('A function groups a reusable action. Here is a small example:\n\n'
                 'def greet(name):\n    return "Hello, " + name\n\nprint(greet("Iqra"))\n\n'
                 'Try calling greet with your own name and notice which value is returned.')
    elif 'python' in msg and ('list' in msg or 'array' in msg):
        reply = ('A Python list keeps several values together:\n\n'
                 'subjects = ["Maths", "Physics", "Python"]\nprint(subjects[0])\n\n'
                 'List positions start at 0, so subjects[0] shows Maths. Try accessing a different position.')
    elif 'python' in msg:
        reply = ('Python is a readable programming language used for automation, websites, data, and AI.\n\n'
                 'A good first step is to combine a variable with print():\n\n'
                 'name = "Learner"\nprint("Hello, " + name)\n\n'
                 'Tell me whether you want to learn variables, loops, conditions, functions, or lists next.')
    elif ('c++' in msg or 'cpp' in msg) and ('print' in msg or 'output' in msg):
        reply = ('In C++, cout sends text to the screen:\n\n'
                 '#include <iostream>\nusing namespace std;\n\nint main() {\n  cout << "Hello, Learner!" << endl;\n  return 0;\n}\n\n'
                 'Use << to send text to cout. Try changing the message.')
    elif ('c language' in msg or msg.startswith('c ') or ' c code' in msg) and ('print' in msg or 'output' in msg):
        reply = ('In C, printf() displays text:\n\n'
                 '#include <stdio.h>\n\nint main(void) {\n  printf("Hello, Learner!\\n");\n  return 0;\n}\n\n'
                 'The \\n moves the cursor to the next line after printing.')
    elif 'java' in msg and ('print' in msg or 'output' in msg):
        reply = ('In Java, System.out.println() prints a line:\n\n'
                 'public class Main {\n  public static void main(String[] args) {\n    System.out.println("Hello, Learner!");\n  }\n}\n\n'
                 'Try editing the message first, then run it in Code Quest.')
    elif 'derivative' in msg or 'differentiat' in msg:
        reply = ('For a power such as x^n, use the power rule: bring n to the front, then reduce the exponent by 1.\n\n'
                 'Example: d/dx x^9 = 9x^8.\n\n'
                 'Now try the same two moves on x^5. What coefficient and exponent do you get?')
    elif 'sql' in msg or 'mysql' in msg:
        reply = ('SQL asks questions of a database. A basic query starts with SELECT, chooses columns, and names a table with FROM.\n\n'
                 'Example pattern: SELECT name FROM students;\n\n'
                 'Try changing name to another column you want to see. What information would you request?')
    elif 'algebra' in msg or 'equation' in msg:
        reply = ('For an equation, keep both sides balanced and undo operations in reverse order.\n\n'
                 'In 2(x + 3) = 10, first divide both sides by 2. Then remove 3 from both sides.\n\n'
                 'Try writing the result after the division step.')
    elif 'answer' in msg or 'solve' in msg or 'help' in msg:
        reply = ('Let\'s make the first move small and clear.\n\n'
                 '1. Write what the question gives you.\n2. Mark what you need to find.\n3. Choose one rule or operation that connects them.\n\n'
                 'Send the question or your first step and Iqra will check it with you.')
    elif 'stuck' in msg or 'confused' in msg:
        reply = ('Being stuck is useful information: it tells us where to make the task smaller.\n\n'
                 'Write one fact, formula, or keyword you recognise in the question. Then tell me the exact line where it stopped making sense.\n\n'
                 'Iqra will help you build the next step from there.')
    else:
        reply = ('I can help with that. Tell me the subject and paste the exact question or topic.\n\n'
                 'I will explain the key idea, show one worked step, and give you a short practice prompt so you can check your understanding.')
    return {'reply': reply, 'mode': 'Iqra local guidance while the AI model reconnects', 'independent_thinking': independent, 'handoff': 'Guided explanation'}


def _has_any(message: str, *words: str) -> bool:
    return any(word in message for word in words)


def _has_all(message: str, *words: str) -> bool:
    return all(word in message for word in words)


def _stored_iqra_answer(db: Session, user: User, msg: str) -> str | None:
    """Deterministic answers for demo videos, judging, and offline deployment.

    Ollama is still supported, but these answers make the hackathon demo reliable
    even when the judge's machine has no local model running.
    """
    if _has_any(msg, '20-minute', '20 minute', 'study session', 'study plan', 'focused session', 'make my plan', 'build a plan'):
        risk = risk_for(db, user.id)
        mission = db.query(Mission).filter_by(user_id=user.id, completed=False).order_by(Mission.day_key.desc(), Mission.title.asc()).first()
        mission_text = mission.title if mission else 'one short practice question'
        return (
            f"Here is a focused 20-minute plan for {user.name.split()[0]}:\n\n"
            f"1. 3 minutes: Open your notebook and write today's target: {risk['topic']}.\n"
            f"2. 7 minutes: Review one example or rule connected to {risk['subject']}.\n"
            f"3. 7 minutes: Complete this mission: {mission_text}.\n"
            "4. 3 minutes: Write one sentence: what became clearer, and what still needs practice?\n\n"
            "Iqra tip: keep the session short. The goal is to restart momentum, not finish the whole subject."
        )
    if _has_all(msg, 'explain', 'topic'):
        return (
            "Sure. Pick one topic and Iqra will explain it simply.\n\n"
            "For a demo, try one of these:\n"
            "1. What is Python?\n"
            "2. Explain MySQL.\n"
            "3. What is OOP?\n"
            "4. Explain derivatives.\n\n"
            "Once you send the topic, Iqra will give a short explanation, one example, and one practice question."
        )
    if _has_any(msg, 'first hint', 'give me a hint', 'without giving the answer', 'start a problem'):
        return (
            "Here is a first-hint method:\n\n"
            "1. Underline what the question is asking.\n"
            "2. Circle the numbers, formula, or keyword given.\n"
            "3. Write only the first operation you think applies.\n\n"
            "Do not solve the full question yet. Send me your first step and Iqra will check it."
        )

    demo_answers = [
        (('what is python', 'python meaning', 'explain python'), (
            "Python is a beginner-friendly programming language used for AI, websites, automation, data science, and scripting.\n\n"
            "Simple example:\n"
            "name = \"Learner\"\nprint(\"Hello, \" + name)\n\n"
            "The variable stores a value, and print() displays it. For engineering students, Python is useful because it lets you build ideas quickly."
        )),
        (('python variable', 'variables in python'), (
            "A Python variable is a name that stores a value.\n\n"
            "Example:\n"
            "marks = 85\nprint(marks)\n\n"
            "Here, marks stores 85. Variables help you remember and reuse information in a program."
        )),
        (('python loop', 'for loop in python', 'range in python'), (
            "A Python for loop repeats code.\n\n"
            "Example:\n"
            "for number in range(1, 6):\n    print(number)\n\n"
            "This prints 1 to 5. range(1, 6) stops before 6, so 5 is the last value."
        )),
        (('python function', 'function in python'), (
            "A function is a reusable block of code.\n\n"
            "Example:\n"
            "def square(n):\n    return n * n\n\nprint(square(6))\n\n"
            "This prints 36. Functions help you organize logic and avoid repeating code."
        )),
        (('what is c language', 'explain c language', 'c programming'), (
            "C is a powerful programming language used to understand memory, operating systems, embedded systems, and core programming logic.\n\n"
            "Basic example:\n"
            "#include <stdio.h>\nint main(void) {\n  printf(\"Hello C\");\n  return 0;\n}\n\n"
            "For engineering students, C builds strong foundations for how computers actually work."
        )),
        (('what is c++', 'explain c++', 'cpp'), (
            "C++ is an extension of C that supports object-oriented programming. It is used in games, competitive programming, system software, and high-performance apps.\n\n"
            "Example output line:\n"
            "cout << \"Hello C++\" << endl;\n\n"
            "C++ is excellent for building logic, data structures, and problem-solving speed."
        )),
        (('what is java', 'explain java', 'java programming'), (
            "Java is an object-oriented programming language used for Android apps, backend systems, enterprise software, and large applications.\n\n"
            "Basic output:\n"
            "System.out.println(\"Hello Java\");\n\n"
            "Java is useful because code can run on many platforms through the JVM."
        )),
        (('what is mysql', 'explain mysql', 'mysql database'), (
            "MySQL is a database system used to store and manage data in tables.\n\n"
            "Example query:\n"
            "SELECT name, score FROM students;\n\n"
            "In a real website, MySQL stores users, progress, missions, quiz attempts, and dashboard data."
        )),
        (('what is sql', 'sql query', 'explain sql'), (
            "SQL is the language used to ask questions from a database.\n\n"
            "Example:\n"
            "SELECT name FROM students WHERE score >= 80;\n\n"
            "SELECT chooses columns, FROM chooses the table, and WHERE filters rows."
        )),
        (('what is oop', 'explain oop', 'object oriented', 'oops'), (
            "OOP means Object-Oriented Programming. It organizes code using classes and objects.\n\n"
            "Main ideas:\n"
            "1. Class: blueprint\n2. Object: real item made from the blueprint\n3. Encapsulation: keep data and methods together\n4. Inheritance: reuse features\n5. Polymorphism: same action, different behavior"
        )),
        (('what is dsa', 'data structure', 'algorithm'), (
            "DSA means Data Structures and Algorithms. It teaches how to store data and solve problems efficiently.\n\n"
            "Examples:\n"
            "Array: stores values in order\nStack: last in, first out\nQueue: first in, first out\nAlgorithm: step-by-step method to solve a problem\n\n"
            "DSA is important for engineering exams, coding interviews, and strong logic."
        )),
        (('what is ai', 'explain ai', 'artificial intelligence'), (
            "AI, or Artificial Intelligence, means making computers perform tasks that usually need human intelligence.\n\n"
            "Examples include chatbots, recommendation systems, face recognition, and learning apps like Iqra.\n\n"
            "In LearnDNA, AI is used to suggest missions, explain topics, detect weak areas, and create study plans."
        )),
        (('machine learning', 'what is ml', 'explain ml'), (
            "Machine Learning is a part of AI where computers learn patterns from data instead of being manually programmed for every rule.\n\n"
            "Example: if a system sees many quiz attempts, it can predict which topic a student may struggle with next.\n\n"
            "Simple idea: data goes in, pattern is learned, prediction comes out."
        )),
        (('explain learndna', 'what is learndna', 'about this website'), (
            "LearnDNA is an AI learning operating system for students.\n\n"
            "It gives login, dashboard, progress tracking, Iqra AI coaching, thinking lab, study missions, code lab, parent/teacher support, notifications, and motivation.\n\n"
            "The main idea is simple: understand how a student learns, then give the best next study step."
        )),
        (('iqra ai', 'what is iqra', 'who is iqra'), (
            "Iqra AI is the study companion inside LearnDNA.\n\n"
            "Iqra can explain topics, create 20-minute study plans, give hints, motivate students, and guide them to the right page.\n\n"
            "For demo and judging, Iqra also has a reliable answer store, so it can answer common questions even without an online API key."
        )),
        (('hackathon', 'judge', 'demo video'), (
            "For the hackathon demo, show these flows:\n\n"
            "1. Login as a student.\n2. Show the motivation popup made by Iqra AI.\n3. Open the dashboard and progress cards.\n4. Ask Iqra for a 20-minute plan.\n5. Open Thinking Lab and Code Lab.\n6. Show AI System explaining weak areas and next steps.\n7. Show parent/teacher notifications.\n\n"
            "This proves the website is functional, personalized, and demo-ready."
        )),
        (('how to improve', 'how can i improve', 'study better'), (
            "Use this simple improvement loop:\n\n"
            "1. Pick one weak topic.\n2. Study one short example.\n3. Solve one question without looking at the answer.\n4. Write your reasoning.\n5. Ask Iqra to check the next step.\n\n"
            "Repeat this daily. Small focused repair is stronger than random long study."
        )),
        (('exam', 'prepare for exam', 'exam preparation'), (
            "For exam preparation, use a 3-block method:\n\n"
            "1. Concept block: revise formulas and definitions.\n2. Practice block: solve 5-10 questions.\n3. Reflection block: write what went wrong and what to revise tomorrow.\n\n"
            "Iqra tip: do not only read. Exams improve through active solving."
        )),
        (('derivative', 'differentiate', 'calculus'), (
            "For derivatives, start with the power rule:\n\n"
            "d/dx x^n = n*x^(n-1)\n\n"
            "Example:\n"
            "d/dx x^9 = 9x^8\n\n"
            "Bring the power down, then reduce the power by 1."
        )),
        (('matrix', 'matrices', 'determinant'), (
            "A matrix is a rectangular arrangement of numbers. For a 2x2 matrix:\n\n"
            "|a b|\n|c d|\n\n"
            "determinant = ad - bc\n\n"
            "Example: if a=2, b=3, c=1, d=4, determinant = 2*4 - 3*1 = 5."
        )),
        (('newton', 'force', 'physics'), (
            "Newton's second law says:\n\n"
            "Force = mass x acceleration\nF = m*a\n\n"
            "If mass is 5 kg and acceleration is 2 m/s^2, force = 10 N.\n\n"
            "This helps engineers connect motion with cause."
        )),
        (('ohm', 'resistance', 'current', 'voltage'), (
            "Ohm's law connects voltage, current, and resistance:\n\n"
            "V = I * R\n\n"
            "If current is 2 A and resistance is 5 ohms, voltage = 10 V.\n\n"
            "Use the triangle idea: cover the value you need and calculate from the other two."
        )),
        (('dbms', 'normalization', 'database design'), (
            "DBMS means Database Management System. It stores, organizes, and retrieves data.\n\n"
            "Normalization means arranging data to reduce duplication and avoid update problems.\n\n"
            "For example, student details and course details should be stored in separate related tables."
        )),
    ]
    for keywords, answer in demo_answers:
        if any(keyword in msg for keyword in keywords):
            return answer
    return None
