import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

def uid(): return str(uuid.uuid4())

class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default='student', index=True)
    goal: Mapped[str | None] = mapped_column(String(120), nullable=True)
    avatar_name: Mapped[str] = mapped_column(String(80), default='Iqra')
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    bio: Mapped[str | None] = mapped_column(String(500), nullable=True)
    grade: Mapped[str | None] = mapped_column(String(40), nullable=True)
    study_preference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    subjects: Mapped[str | None] = mapped_column(Text, nullable=True)
    coding_language: Mapped[str | None] = mapped_column(String(30), nullable=True)
    linked_student_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class LearningDNA(Base):
    __tablename__ = 'learning_dna'
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), primary_key=True)
    logical: Mapped[int] = mapped_column(Integer, default=72); critical: Mapped[int] = mapped_column(Integer, default=68)
    problem_solving: Mapped[int] = mapped_column(Integer, default=70); creativity: Mapped[int] = mapped_column(Integer, default=74)
    memory: Mapped[int] = mapped_column(Integer, default=76); visual: Mapped[int] = mapped_column(Integer, default=71)
    confidence: Mapped[int] = mapped_column(Integer, default=65); attention: Mapped[int] = mapped_column(Integer, default=73)
    communication: Mapped[int] = mapped_column(Integer, default=69); consistency: Mapped[int] = mapped_column(Integer, default=78)
    xp: Mapped[int] = mapped_column(Integer, default=420); streak: Mapped[int] = mapped_column(Integer, default=3)

class Mission(Base):
    __tablename__ = 'missions'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    title: Mapped[str] = mapped_column(String(200)); description: Mapped[str] = mapped_column(String(300), default='')
    xp: Mapped[int] = mapped_column(Integer, default=50); completed: Mapped[bool] = mapped_column(Boolean, default=False)
    kind: Mapped[str] = mapped_column(String(40), default='practice')
    subject: Mapped[str | None] = mapped_column(String(60), nullable=True)
    day_key: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)

class QuizAttempt(Base):
    __tablename__ = 'quiz_attempts'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    question: Mapped[str] = mapped_column(Text); answer: Mapped[str] = mapped_column(String(300)); correct: Mapped[bool] = mapped_column(Boolean)
    reasoning: Mapped[str] = mapped_column(Text, default=''); created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    question_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    subject: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)

class CodeChallengeProgress(Base):
    __tablename__ = 'code_challenge_progress'
    __table_args__ = (UniqueConstraint('user_id', 'challenge_id', name='uq_code_challenge_user'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    challenge_id: Mapped[str] = mapped_column(String(80), index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

class Misconception(Base):
    __tablename__ = 'misconceptions'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    concept: Mapped[str] = mapped_column(String(120)); explanation: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(20)); frequency: Mapped[int] = mapped_column(Integer, default=1)

class Reflection(Base):
    __tablename__ = 'reflection_journals'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    confused: Mapped[str] = mapped_column(Text); understood: Mapped[str] = mapped_column(Text)
    difficult: Mapped[str] = mapped_column(Text); confidence: Mapped[int] = mapped_column(Integer)
    summary: Mapped[str] = mapped_column(Text); created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class CommunityPost(Base):
    __tablename__ = 'community_posts'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    body: Mapped[str] = mapped_column(Text); likes: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Notification(Base):
    __tablename__ = 'notifications'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    recipient_user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    sender_user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    sender_role: Mapped[str] = mapped_column(String(20))
    title: Mapped[str] = mapped_column(String(120))
    message: Mapped[str] = mapped_column(String(600))
    read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
