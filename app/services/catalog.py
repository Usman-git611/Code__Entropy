"""Subject-aware learning content and a safe beginner coding lesson runner.

The coding runner deliberately does not execute arbitrary student programs on the
server. It recognises the small, editable lesson patterns below and returns the
result immediately. This keeps local and deployed versions safe for students.
"""
from __future__ import annotations

import ast
import re
from datetime import date

SUBJECTS = ['Mathematics', 'Physics', 'Chemistry', 'Programming', 'Biology', 'English']

SUBJECT_PATHS = {
    'Mathematics': 'engineering mathematics foundations',
    'Physics': 'mechanics and electricity foundations',
    'Chemistry': 'moles, equations, and material foundations',
    'Programming': 'programming logic and syntax foundations',
    'Biology': 'cell and systems foundations',
    'English': 'reading and communication foundations',
}

MISSION_TEMPLATES = {
    'Mathematics': [
        ('Engineering algebra sprint', 'Solve six linear-equation questions and show the inverse operation used each time.', 'practice', 70),
        ('Calculus readiness', 'Review functions, powers, and one derivative rule with two worked examples.', 'concept', 65),
        ('Vector mini-lab', 'Find the magnitude of three simple vectors and explain one calculation.', 'practice', 75),
        ('Matrix thinking', 'Practice two 2x2 determinant questions and reflect on the sign pattern.', 'repair', 80),
        ('Formula recall', 'Create a one-page sheet of formulas you used today and test yourself once.', 'reflection', 50),
        ('Problem breakdown', 'Turn one engineering-style word problem into known values, unknowns, and an equation.', 'thinking', 70),
    ],
    'Physics': [
        ('Forces in motion', 'Use F = ma on five short situations and label the units in every answer.', 'practice', 70),
        ('Electricity essentials', 'Practice three V = IR calculations and check whether each answer is realistic.', 'practice', 70),
        ('Free-body diagram', 'Draw one free-body diagram and write what each arrow represents.', 'thinking', 75),
        ('Energy transfer check', 'Explain where energy goes in two everyday systems.', 'concept', 60),
        ('Physics error repair', 'Retry one question you found difficult and write the first step only.', 'repair', 65),
        ('Units detective', 'Check units for speed, force, and energy; correct one deliberately wrong unit.', 'reflection', 50),
    ],
    'Chemistry': [
        ('Mole calculation practice', 'Complete four moles and molarity calculations using units on every line.', 'practice', 70),
        ('Periodic table patterns', 'Compare two groups and explain how one property changes down the group.', 'concept', 60),
        ('Balance the equation', 'Balance three basic chemical equations and count atoms before and after.', 'practice', 70),
        ('Bonding explanation', 'Explain ionic versus covalent bonding in your own words.', 'thinking', 65),
        ('Chemistry error repair', 'Redo one weak topic slowly and highlight the quantity you are solving for.', 'repair', 65),
        ('Lab safety recall', 'Write three lab safety rules and why each one matters.', 'reflection', 45),
    ],
    'Programming': [
        ('Programming fundamentals', 'Run and edit a starter program, then explain every line in one sentence.', 'practice', 75),
        ('Trace the code', 'Trace a small loop by hand and write the value after each iteration.', 'thinking', 70),
        ('Function builder', 'Write one small function with an input, a useful output, and a test case.', 'practice', 80),
        ('SQL query practice', 'Use SELECT, WHERE, and COUNT on the Coding Lab lesson dataset.', 'practice', 70),
        ('Debugging drill', 'Find one syntax or logic issue in a starter snippet and describe the repair.', 'repair', 70),
        ('Code reflection', 'Write one rule you learned about variables, conditions, or loops.', 'reflection', 50),
    ],
    'Biology': [
        ('Cell systems review', 'Label key organelles and connect each organelle to its job.', 'concept', 60),
        ('Living systems quiz', 'Answer five questions about transport, respiration, and cells.', 'practice', 65),
        ('Biology concept map', 'Connect one cell process to an everyday example.', 'thinking', 60),
    ],
    'English': [
        ('Reading clarity practice', 'Read one short paragraph, identify the main claim, and support it with one detail.', 'practice', 55),
        ('Explanation builder', 'Rewrite one technical idea for a younger student in three simple sentences.', 'thinking', 60),
        ('Vocabulary in context', 'Learn five subject words and use each one in a meaningful sentence.', 'practice', 55),
    ],
}

def _question(question_id, subject, topic, text, answers, steps, hint):
    return {'id': question_id, 'subject': subject, 'topic': topic, 'text': text, 'answers': [str(item) for item in answers], 'steps': steps, 'hint': hint}

def _make_questions():
    bank = []
    equations = [(2, 3, 10), (3, 2, 17), (4, 1, 21), (5, 5, 30), (6, 4, 40), (7, 3, 31), (8, 2, 50), (9, 1, 46), (3, 7, 25), (4, 8, 36), (5, 6, 41), (2, 9, 23)]
    for index, (a, b, c) in enumerate(equations, 1):
        answer = (c - b) / a
        clean = int(answer) if answer.is_integer() else answer
        bank.append(_question(f'math-linear-{index}', 'Mathematics', 'Linear equations', f'Solve {a}x + {b} = {c}. What is x?', [clean], [f'Subtract {b} from both sides.', f'Divide both sides by {a}.', f'x = {clean}.'], f'Undo +{b} before dividing by {a}.'))
    for power in range(2, 10):
        answer = f'{power}x^{power - 1}'
        bank.append(_question(f'math-calculus-{power}', 'Mathematics', 'Differentiation', f'Find the derivative of x^{power}.', [answer, f'{power}x{power - 1}'], [f'Bring down the power {power}.', f'Reduce the exponent by one.', f'The derivative is {answer}.'], 'Use the power rule: d/dx x^n = n x^(n-1).'))
    for index, (mass, acceleration) in enumerate([(2, 4), (3, 5), (4, 6), (5, 3), (6, 7), (7, 2), (8, 4), (9, 3), (10, 2), (12, 5)], 1):
        force = mass * acceleration
        bank.append(_question(f'physics-force-{index}', 'Physics', 'Newton\'s second law', f'A {mass} kg object accelerates at {acceleration} m/s^2. What force acts on it in newtons?', [force, f'{force} n', f'{force}n'], ['Use F = ma.', f'Multiply {mass} by {acceleration}.', f'F = {force} N.'], 'Force equals mass multiplied by acceleration.'))
    for index, (voltage, current) in enumerate([(12, 2), (24, 3), (9, 3), (20, 4), (30, 5), (18, 2), (16, 4), (45, 5), (8, 2), (36, 6)], 1):
        resistance = voltage / current
        bank.append(_question(f'physics-ohm-{index}', 'Physics', 'Ohm\'s law', f'A circuit has {voltage} V and {current} A. What is its resistance in ohms?', [resistance, f'{resistance} ohm', f'{resistance} ohms'], ['Use R = V / I.', f'Divide {voltage} by {current}.', f'R = {resistance} ohms.'], 'Rearrange V = IR to get R = V/I.'))
    molarity_pairs = [(1, 0.5), (2, 1), (3, 1.5), (0.5, 0.25), (4, 2), (1.2, 0.6), (2.5, 0.5), (0.8, 0.4), (1.5, 0.3), (3.6, 1.2)]
    for index, (moles, litres) in enumerate(molarity_pairs, 1):
        molarity = moles / litres
        bank.append(_question(f'chem-molarity-{index}', 'Chemistry', 'Molarity', f'What is the molarity of {moles} mol dissolved in {litres} L of solution?', [molarity, f'{molarity} m', f'{molarity}m'], ['Use M = moles / volume.', f'Divide {moles} by {litres}.', f'Molarity = {molarity} M.'], 'Molarity is moles per litre.'))
    atomic_numbers = [('carbon', 6), ('oxygen', 8), ('sodium', 11), ('magnesium', 12), ('aluminium', 13), ('chlorine', 17), ('calcium', 20), ('iron', 26)]
    for index, (element, number) in enumerate(atomic_numbers, 1):
        bank.append(_question(f'chem-atom-{index}', 'Chemistry', 'Atomic structure', f'What is the atomic number of {element.title()}?', [number], [f'Locate {element.title()} on the periodic table.', 'Its atomic number equals its proton count.', f'The answer is {number}.'], 'The atomic number is the number of protons.'))
    programming = [
        ('python-output', 'Python basics', 'What does print(2 + 3) display?', ['5'], ['Evaluate 2 + 3.', 'print displays the result.', 'The output is 5.'], 'Add the two numbers first.'),
        ('python-variable', 'Python variables', 'If score = 7 and score = score + 4, what is score?', ['11'], ['Start with score = 7.', 'Add 4.', 'score becomes 11.'], 'Read the assignment from right to left.'),
        ('c-output', 'C basics', 'What does printf("Hi"); display?', ['hi'], ['printf writes the text inside quotes.', 'There is no calculation.', 'The output is Hi.'], 'Focus on the text inside double quotes.'),
        ('cpp-output', 'C++ basics', 'What does cout << 4 * 2; display?', ['8'], ['Multiply 4 by 2.', 'cout prints the result.', 'The output is 8.'], 'Multiplication happens before printing.'),
        ('java-variable', 'Java basics', 'If int age = 16; age++; what is age?', ['17'], ['age begins at 16.', '++ adds one.', 'age becomes 17.'], 'The ++ operator increases a value by one.'),
        ('sql-count', 'MySQL basics', 'What does SELECT COUNT(*) FROM students count?', ['rows', 'student rows', 'number of rows'], ['COUNT(*) counts records.', 'The FROM clause chooses students.', 'It returns the number of student rows.'], 'COUNT(*) counts how many rows match.'),
        ('loop-count', 'Loops', 'How many times does for i in range(3) run in Python?', ['3', 'three'], ['range(3) starts at 0.', 'It stops before 3.', 'The values are 0, 1, 2: three runs.'], 'List the values produced by range(3).'),
        ('condition', 'Conditions', 'If x = 4, is x > 2 true or false?', ['true'], ['Compare 4 and 2.', '4 is greater than 2.', 'The condition is true.'], 'Compare the two numbers.'),
        ('function', 'Functions', 'What keyword starts a Python function definition?', ['def'], ['Python uses a keyword before the function name.', 'That keyword is def.', 'The answer is def.'], 'Think of def greet():'),
        ('array-index', 'Arrays', 'In [10, 20, 30], what is the value at index 1?', ['20'], ['Indexes begin at 0.', 'Index 0 is 10.', 'Index 1 is 20.'], 'Count from zero, not one.'),
    ]
    for question_id, topic, text, answers, steps, hint in programming:
        bank.append(_question(f'programming-{question_id}', 'Programming', topic, text, answers, steps, hint))
    bank.extend([
        _question('bio-cell-1', 'Biology', 'Cell biology', 'Which organelle releases energy from food in most cells?', ['mitochondria', 'mitochondrion'], ['Cells need usable energy.', 'Mitochondria release energy from food.', 'The answer is mitochondria.'], 'Think of the cell\'s energy station.'),
        _question('bio-cell-2', 'Biology', 'Cell biology', 'What structure controls what enters and leaves a cell?', ['cell membrane', 'membrane'], ['The boundary regulates movement.', 'It is not the rigid wall in all cells.', 'The answer is the cell membrane.'], 'Think about the thin boundary around every cell.'),
        _question('english-main-1', 'English', 'Reading comprehension', 'What is the name for the central message of a paragraph?', ['main idea', 'main point'], ['A paragraph has one core message.', 'Details support that message.', 'It is the main idea.'], 'It is the big point the details support.'),
        _question('english-main-2', 'English', 'Communication', 'What should a clear explanation include before examples?', ['main idea', 'definition', 'key idea'], ['Start with the key idea.', 'Examples make it clearer afterwards.', 'Begin with the main idea or definition.'], 'Give the reader the key point first.'),
    ])
    return bank

QUESTION_BANK = _make_questions()

def public_question(item):
    return {key: value for key, value in item.items() if key not in {'answers', 'steps'}}

def subjects_for_user(user) -> list[str]:
    saved = [item.strip() for item in (user.subjects or '').split(',') if item.strip() in SUBJECTS]
    return saved or ['Mathematics', 'Physics', 'Chemistry', 'Programming']

def questions_for_subjects(subjects: list[str], requested: str | None = None):
    chosen = requested if requested in subjects else None
    source = [item for item in QUESTION_BANK if item['subject'] == chosen] if chosen else [item for item in QUESTION_BANK if item['subject'] in subjects]
    return source

def mission_plan_for_day(user, subjects: list[str], performance: dict[str, int | None] | None = None):
    count_per_subject = max(3, (12 + len(subjects) - 1) // len(subjects))
    offset = date.today().toordinal() + sum(ord(char) for char in user.id)
    performance = performance or {}
    items = []
    for subject_index, subject in enumerate(subjects):
        templates = MISSION_TEMPLATES[subject]
        score = performance.get(subject)
        for index in range(count_per_subject):
            title, description, kind, xp = templates[(offset + subject_index * 3 + index) % len(templates)]
            if index == 0 and score is not None and score < 60:
                title = f'AI repair: {subject} foundations'
                description = f'Your recent {subject} accuracy is {score}%. Start with one guided example, then solve two similar questions slowly.'
                kind, xp = 'repair', 85
            elif index == 0 and score is not None and score >= 85:
                title = f'Stretch challenge: {subject}'
                description = f'Your recent {subject} accuracy is {score}%. Try a slightly harder problem and explain why your method works.'
                kind, xp = 'challenge', 90
            items.append({'title': title, 'description': description, 'kind': kind, 'xp': xp, 'subject': subject})
    return items[:max(12, len(subjects) * 3)]

CODE_LABS = {
    'Python': {'title': 'Python: print and variables', 'concept': 'Variables store values; print displays a result.', 'starter': 'name = "Learner"\nprint("Hello, " + name)', 'tip': 'Edit the name or printed message, then run it.'},
    'C': {'title': 'C: first output', 'concept': 'main is the entry point and printf writes text.', 'starter': '#include <stdio.h>\n\nint main() {\n  printf("Hello from C\\n");\n  return 0;\n}', 'tip': 'Change the text inside printf, then run it.'},
    'C++': {'title': 'C++: output with cout', 'concept': 'cout sends values to the console.', 'starter': '#include <iostream>\nusing namespace std;\n\nint main() {\n  cout << "Hello from C++" << endl;\n  return 0;\n}', 'tip': 'Change the text inside quotes, then run it.'},
    'MySQL': {'title': 'MySQL: select a lesson dataset', 'concept': 'SELECT reads data, WHERE filters rows, and COUNT counts them.', 'starter': 'SELECT name, score\nFROM students\nWHERE score >= 80;', 'tip': 'Try SELECT COUNT(*) FROM students; or change the score threshold.'},
    'Java': {'title': 'Java: first output', 'concept': 'System.out.println writes a line to the console.', 'starter': 'public class Main {\n  public static void main(String[] args) {\n    System.out.println("Hello from Java");\n  }\n}', 'tip': 'Change the text inside println, then run it.'},
}

def code_labs(preferred: str | None):
    ordered = [preferred] if preferred in CODE_LABS else []
    ordered.extend(language for language in CODE_LABS if language not in ordered)
    return [{'language': language, **CODE_LABS[language]} for language in ordered]

def _safe_arithmetic(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and abs(node.value) <= 1_000_000:
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        value = _safe_arithmetic(node.operand)
        return -value if isinstance(node.op, ast.USub) else value
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod)):
        left, right = _safe_arithmetic(node.left), _safe_arithmetic(node.right)
        if isinstance(node.op, ast.Add): result = left + right
        elif isinstance(node.op, ast.Sub): result = left - right
        elif isinstance(node.op, ast.Mult): result = left * right
        elif isinstance(node.op, ast.Div): result = left / right
        elif isinstance(node.op, ast.FloorDiv): result = left // right
        else: result = left % right
        if abs(result) <= 1_000_000_000:
            return result
    raise ValueError('Only small basic arithmetic expressions are supported in this lesson.')

def _literal_output(code: str, language: str):
    if language == 'Python':
        concat = re.search(r'print\s*\(\s*([\'\"])(.*?)\1\s*\+\s*([A-Za-z_]\w*)\s*\)', code, flags=re.S)
        if concat:
            variable = re.search(rf'{re.escape(concat.group(3))}\s*=\s*([\'\"])(.*?)\1', code, flags=re.S)
            if variable:
                return bytes(concat.group(2) + variable.group(2), 'utf-8').decode('unicode_escape')
        match = re.search(r'print\s*\(\s*([\'\"])(.*?)\1\s*\)', code, flags=re.S)
        if match:
            return bytes(match.group(2), 'utf-8').decode('unicode_escape')
        numeric = re.search(r'print\s*\(\s*([0-9+*/ ().-]+)\s*\)', code)
        if numeric:
            try:
                return str(_safe_arithmetic(ast.parse(numeric.group(1), mode='eval').body))
            except (SyntaxError, ValueError, ZeroDivisionError):
                return None
    if language == 'C':
        match = re.search(r'printf\s*\(\s*"(.*?)"', code, flags=re.S)
        if match:
            return bytes(match.group(1), 'utf-8').decode('unicode_escape')
    if language == 'C++':
        match = re.search(r'cout\s*<<\s*"(.*?)"', code, flags=re.S)
        if match:
            return bytes(match.group(1), 'utf-8').decode('unicode_escape')
    if language == 'Java':
        match = re.search(r'System\.out\.println\s*\(\s*"(.*?)"', code, flags=re.S)
        if match:
            return bytes(match.group(1), 'utf-8').decode('unicode_escape')
    return None

def run_lesson_code(language: str, code: str):
    if language not in CODE_LABS:
        return {'ok': False, 'output': 'Choose C, C++, Python, MySQL, or Java.', 'runner': 'Safe learning runner'}
    if language == 'MySQL':
        query = ' '.join(code.lower().split())
        if not query.startswith('select'):
            return {'ok': False, 'output': 'This beginner lab accepts read-only SELECT queries only.', 'runner': 'Safe lesson dataset'}
        if 'count(*)' in query:
            return {'ok': True, 'output': 'count\n3', 'runner': 'Safe lesson dataset'}
        threshold = re.search(r'score\s*>=\s*(\d+)', query)
        rows = [('Aanya', 92), ('Ravi', 84), ('Mina', 73)]
        if threshold:
            rows = [row for row in rows if row[1] >= int(threshold.group(1))]
        return {'ok': True, 'output': 'name | score\n' + '\n'.join(f'{name} | {score}' for name, score in rows), 'runner': 'Safe lesson dataset'}
    output = _literal_output(code, language)
    if output is None:
        return {'ok': False, 'output': 'Try editing the text in the starter print statement. This safe lesson runner supports beginner output exercises.', 'runner': 'Safe learning runner'}
    return {'ok': True, 'output': output, 'runner': 'Safe learning runner'}
