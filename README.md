# 班级管理助手

一个功能完善的班级管理系统，支持课程表管理、学生管理、成绩管理和我的班級展示。

## 技术栈

### 后端
- FastAPI (Python)
- PostgreSQL
- Redis
- SQLAlchemy
- Pydantic

### 前端
- React 19
- Vite
- Ant Design
- ECharts
- React Router

## 快速开始

### 手动启动

#### 1. 数据库初始化

```bash
# 创建数据库
psql -U postgres -c "CREATE DATABASE class_assistant;"

# 初始化表结构（可选，后端会自动创建）
psql -U postgres -d class_assistant -f backend/init_db.sql
```

#### 2. 启动后端

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
```

## 访问地址

- 前端: http://localhost:5173
- 后端: http://localhost:8000
- API文档: http://localhost:8000/docs

## 默认账号

- 用户名: teacher1
- 密码: 123456

## 功能特性

### 1. 登录页
- 用户名密码登录
- 小学大楼背景图

### 2. 首页 - 课程表
- 显示当前登录老师的课程表
- 即将上课的班级显示黄色背景
- 正在上课的班级显示红色背景
- 1分钟自动刷新
- 支持手动刷新

### 3. 管理页
- 年级管理 (增删改查)
- 班级管理 (增删改查)
- 学生管理 (增删改查 + 导入)
- 用户管理 (增删改查)
- 成绩管理 (增删改查 + 导入)
- 标签管理 (增删改查)

### 4. 我的班級
- 选择班级
- 展示课堂画面（学生卡通形象）
- 根据班级人数自动计算座位布局
- 点击学生查看信息卡片
- 点击成绩查看近6个月成绩变化曲线
- 点击老师查看班级信息
- 点击平均分查看近6个月平均成绩变化曲线

## 数据库表结构

- grades (年级表)
- classes (班级表)
- users (用户表)
- subjects (学科表)
- students (学生表)
- scores (成绩表)
- tags (标签表)
- student_tags (学生标签关联表)
- schedules (课程表)

## 成绩类型

- 月考
- 期中考试
- 期末考试
- 随堂测验
