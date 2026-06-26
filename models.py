from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Date, Float
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime


class Grade(Base):
    __tablename__ = "grades"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, unique=True, comment="年级名称")
    created_at = Column(DateTime, default=datetime.now)

    classes = relationship("Class", back_populates="grade")


class Class(Base):
    __tablename__ = "classes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, comment="班级名称（原始）")
    display_name = Column(String(100), nullable=True, comment="显示名称（含年级）")
    grade_id = Column(Integer, ForeignKey("grades.id"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    grade = relationship("Grade", back_populates="classes")
    teacher = relationship("User", back_populates="classes")
    students = relationship("Student", back_populates="class_")
    schedules = relationship("Schedule", back_populates="class_")
    scores = relationship("Score", back_populates="class_")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), nullable=False, unique=True, comment="用户名")
    password = Column(String(255), nullable=False, comment="密码")
    name = Column(String(50), nullable=False, comment="真实姓名")
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True, comment="学科ID")
    role = Column(String(20), nullable=False, default="teacher", comment="角色")
    avatar = Column(String(255), nullable=True, comment="头像URL")
    created_at = Column(DateTime, default=datetime.now)

    subject = relationship("Subject", back_populates="users")
    classes = relationship("Class", back_populates="teacher")


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, unique=True, comment="学科名称")
    created_at = Column(DateTime, default=datetime.now)

    users = relationship("User", back_populates="subject")
    scores = relationship("Score", back_populates="subject")


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, comment="学生姓名")
    gender = Column(String(10), nullable=False, comment="性别")
    birthday = Column(Date, nullable=True, comment="生日")
    age = Column(Integer, nullable=True, comment="年龄（由生日计算）")
    height = Column(Float, nullable=True, comment="身高(cm)")
    weight = Column(Float, nullable=True, comment="体重(kg)")
    hobbies = Column(Text, nullable=True, comment="爱好")
    friends = Column(Text, nullable=True, comment="好友")
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    active = Column(Boolean, default=True, comment="是否有效")
    created_at = Column(DateTime, default=datetime.now)

    class_ = relationship("Class", back_populates="students")
    scores = relationship("Score", back_populates="student")
    tags = relationship("StudentTag", back_populates="student")


class Score(Base):
    __tablename__ = "scores"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    score_type = Column(String(50), nullable=False, comment="考试类型：月考/期中考试/期末考试/随堂测验")
    score = Column(Float, nullable=False, comment="成绩")
    exam_date = Column(Date, nullable=False, comment="考试日期")
    created_at = Column(DateTime, default=datetime.now)

    student = relationship("Student", back_populates="scores")
    class_ = relationship("Class", back_populates="scores")
    subject = relationship("Subject", back_populates="scores")


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, unique=True, comment="标签名称")
    created_at = Column(DateTime, default=datetime.now)

    student_tags = relationship("StudentTag", back_populates="tag")


class StudentTag(Base):
    __tablename__ = "student_tags"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    tag_id = Column(Integer, ForeignKey("tags.id"), nullable=False)

    student = relationship("Student", back_populates="tags")
    tag = relationship("Tag", back_populates="student_tags")


class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    day_of_week = Column(Integer, nullable=False, comment="星期几(0-6)")
    time_slot = Column(String(50), nullable=False, comment="时间段：早自习/上午1/上午2/.../课后服务")
    start_time = Column(String(10), nullable=False, comment="开始时间 HH:MM")
    end_time = Column(String(10), nullable=False, comment="结束时间 HH:MM")
    created_at = Column(DateTime, default=datetime.now)

    class_ = relationship("Class", back_populates="schedules")
    teacher = relationship("User")
    subject = relationship("Subject")
