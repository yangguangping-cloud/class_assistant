-- Database initialization script for class_assistant

-- Drop tables if they exist
-- DROP TABLE IF EXISTS student_tags CASCADE;
-- DROP TABLE IF EXISTS schedules CASCADE;
-- DROP TABLE IF EXISTS scores CASCADE;
-- DROP TABLE IF EXISTS students CASCADE;
-- DROP TABLE IF EXISTS tags CASCADE;
-- DROP TABLE IF EXISTS classes CASCADE;
-- DROP TABLE IF EXISTS users CASCADE;
-- DROP TABLE IF EXISTS subjects CASCADE;
-- DROP TABLE IF EXISTS grades CASCADE;

-- Create tables
CREATE TABLE IF NOT EXISTS grades (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS subjects (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    name VARCHAR(50) NOT NULL,
    subject_id INTEGER REFERENCES subjects(id),
    role VARCHAR(20) NOT NULL DEFAULT 'teacher',
    avatar VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS classes (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    display_name VARCHAR(100),
    grade_id INTEGER NOT NULL REFERENCES grades(id),
    teacher_id INTEGER NOT NULL REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS students (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    gender VARCHAR(10) NOT NULL,
    birthday DATE NOT NULL,
    age INTEGER,
    height FLOAT,
    weight FLOAT,
    hobbies TEXT,
    friends TEXT,
    class_id INTEGER NOT NULL REFERENCES classes(id),
    created_at TIMESTAMP DEFAULT NOW(),
    active BOOLEAN NOT NULL DEFAULT true
);

CREATE TABLE IF NOT EXISTS tags (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS student_tags (
    id SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES students(id),
    tag_id INTEGER NOT NULL REFERENCES tags(id)
);

CREATE TABLE IF NOT EXISTS scores (
    id SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES students(id),
    class_id INTEGER NOT NULL REFERENCES classes(id),
    subject_id INTEGER NOT NULL REFERENCES subjects(id),
    score_type VARCHAR(50) NOT NULL,
    score FLOAT NOT NULL,
    exam_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS schedules (
    id SERIAL PRIMARY KEY,
    class_id INTEGER NOT NULL REFERENCES classes(id),
    teacher_id INTEGER NOT NULL REFERENCES users(id),
    subject_id INTEGER NOT NULL REFERENCES subjects(id),
    day_of_week INTEGER NOT NULL,
    time_slot VARCHAR(50) NOT NULL,
    start_time VARCHAR(10) NOT NULL,
    end_time VARCHAR(10) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Insert seed data
-- Subjects
INSERT INTO subjects (name) VALUES
('语文'), ('数学'), ('英语'), ('物理'), ('化学'),
('生物'), ('历史'), ('地理'), ('政治')
ON CONFLICT (name) DO NOTHING;

-- Grades
INSERT INTO grades (name) VALUES
('一年级'), ('二年级'), ('三年级'), ('四年级'), ('五年级'), ('六年级')
ON CONFLICT (name) DO NOTHING;

-- Create a default teacher (password: 123456, hashed with bcrypt)
-- Hash generated using: from passlib.context import CryptContext; CryptContext(schemes=['bcrypt']).hash('123456')
INSERT INTO users (username, password, name, subject_id, role)
SELECT 'teacher1', 'e10adc3949ba59abbe56e057f20f883e', '张老师',
       (SELECT id FROM subjects WHERE name = '英语'), 'teacher'
WHERE NOT EXISTS (SELECT 1 FROM users WHERE username = 'teacher1');

-- Create classes
INSERT INTO classes (name, grade_id, teacher_id)
SELECT '一班', (SELECT id FROM grades WHERE name = '一年级'), (SELECT id FROM users WHERE username = 'teacher1')
WHERE NOT EXISTS (SELECT 1 FROM classes WHERE name = '一班');

-- Create some sample students
INSERT INTO students (name, gender, birthday, age, height, weight, hobbies, friends, class_id)
SELECT name, gender, birthday, age, height, weight, hobbies, friends, (SELECT id FROM classes WHERE name = '一班')
FROM (VALUES
  ('小明', '男', DATE '2016-01-01', 10, 140.5, 35.2, '篮球,游泳', '小红,小刚', 1),
  ('小红', '女', DATE '2016-01-01', 10, 138.2, 32.5, '绘画,音乐', '小明,小丽', 1),
  ('小刚', '男', DATE '2016-01-01', 11, 142.8, 38.0, '足球,跑步', '小明,小强', 1),
  ('小丽', '女', DATE '2016-01-01', 10, 136.5, 30.8, '舞蹈,阅读', '小红,小美', 1),
  ('小强', '男', DATE '2016-01-01', 11, 145.0, 40.5, '篮球,游戏', '小刚,小伟', 1),
  ('小美', '女', DATE '2016-01-01', 10, 137.8, 31.2, '唱歌,绘画', '小丽,小红', 1),
  ('小伟', '男', DATE '2016-01-01', 11, 143.5, 39.0, '跑步,游泳', '小强,小明', 1),
  ('小芳', '女', DATE '2016-01-01', 10, 139.0, 33.5, '阅读,写作', '小红,小丽', 1)
) AS t(name, gender, birthday, age, height, weight, hobbies, friends, class_id)
WHERE NOT EXISTS (SELECT 1 FROM students LIMIT 1);

-- Create tags
INSERT INTO tags (name) VALUES
('优秀学生'), ('进步之星'), ('体育健将'), ('文艺标兵'), ('学习委员')
ON CONFLICT (name) DO NOTHING;

-- Create sample schedule
INSERT INTO schedules (class_id, teacher_id, subject_id, day_of_week, time_slot, start_time, end_time)
SELECT
    (SELECT id FROM classes WHERE name = '一班'),
    (SELECT id FROM users WHERE username = 'teacher1'),
    (SELECT id FROM subjects WHERE name = '英语'),
    0, -- Monday
    '上午1',
    '08:00',
    '08:45'
WHERE NOT EXISTS (SELECT 1 FROM schedules LIMIT 1);
