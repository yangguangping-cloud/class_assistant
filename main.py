from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from database import engine, get_db, Base, SessionLocal
import models
import schemas
from auth import verify_password, get_password_hash, create_access_token, decode_access_token
import redis
from datetime import datetime, date, timedelta
from typing import List, Optional
import io
import pandas as pd
from dateutil.relativedelta import relativedelta

# Create tables
Base.metadata.create_all(bind=engine)

# Redis connection
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

app = FastAPI(title="班级管理助手 API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()


# Helper functions
def calculate_age(birthday: date) -> int:
    """Calculate age from birthday"""
    today = date.today()
    return relativedelta(today, birthday).years


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    token = credentials.credentials
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication credentials")
    user = db.query(models.User).filter(models.User.id == payload.get("user_id")).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


# Auth routes
@app.post("/api/auth/login")
def login(user_login: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == user_login.username).first()
    if not user or not verify_password(user_login.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    access_token = create_access_token(data={"user_id": user.id, "username": user.username})
    return {"access_token": access_token, "token_type": "bearer", "user": schemas.UserResponse.from_orm(user)}


@app.get("/api/auth/me")
def get_me(current_user: models.User = Depends(get_current_user)):
    return schemas.UserResponse.from_orm(current_user)


# Grade routes
@app.get("/api/grades", response_model=List[schemas.GradeResponse])
def get_grades(db: Session = Depends(get_db)):
    return db.query(models.Grade).all()


@app.post("/api/grades", response_model=schemas.GradeResponse)
def create_grade(grade: schemas.GradeCreate, db: Session = Depends(get_db)):
    db_grade = models.Grade(**grade.dict())
    db.add(db_grade)
    db.commit()
    db.refresh(db_grade)
    return db_grade


@app.put("/api/grades/{grade_id}", response_model=schemas.GradeResponse)
def update_grade(grade_id: int, grade: schemas.GradeUpdate, db: Session = Depends(get_db)):
    db_grade = db.query(models.Grade).filter(models.Grade.id == grade_id).first()
    if not db_grade:
        raise HTTPException(status_code=404, detail="Grade not found")
    for key, value in grade.dict().items():
        setattr(db_grade, key, value)
    db.commit()
    db.refresh(db_grade)
    return db_grade


@app.delete("/api/grades/{grade_id}")
def delete_grade(grade_id: int, db: Session = Depends(get_db)):
    db_grade = db.query(models.Grade).filter(models.Grade.id == grade_id).first()
    if not db_grade:
        raise HTTPException(status_code=404, detail="Grade not found")
    db.delete(db_grade)
    db.commit()
    return {"message": "Grade deleted"}


# Subject routes
@app.get("/api/subjects", response_model=List[schemas.SubjectResponse])
def get_subjects(db: Session = Depends(get_db)):
    return db.query(models.Subject).all()


@app.post("/api/subjects", response_model=schemas.SubjectResponse)
def create_subject(subject: schemas.SubjectCreate, db: Session = Depends(get_db)):
    db_subject = models.Subject(**subject.dict())
    db.add(db_subject)
    db.commit()
    db.refresh(db_subject)
    return db_subject


@app.put("/api/subjects/{subject_id}", response_model=schemas.SubjectResponse)
def update_subject(subject_id: int, subject: schemas.SubjectUpdate, db: Session = Depends(get_db)):
    db_subject = db.query(models.Subject).filter(models.Subject.id == subject_id).first()
    if not db_subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    for key, value in subject.dict().items():
        setattr(db_subject, key, value)
    db.commit()
    db.refresh(db_subject)
    return db_subject


@app.delete("/api/subjects/{subject_id}")
def delete_subject(subject_id: int, db: Session = Depends(get_db)):
    db_subject = db.query(models.Subject).filter(models.Subject.id == subject_id).first()
    if not db_subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    db.delete(db_subject)
    db.commit()
    return {"message": "Subject deleted"}


# Class routes
@app.get("/api/classes")
def get_classes(db: Session = Depends(get_db)):
    classes = db.query(models.Class).all()
    result = []
    for c in classes:
        grade_name = c.grade.name if c.grade else ''
        display_name = c.display_name if c.display_name else f"{grade_name}{c.name}"
        result.append({
            "id": c.id,
            "name": c.name,
            "display_name": display_name,
            "grade_id": c.grade_id,
            "teacher_id": c.teacher_id,
            "created_at": c.created_at
        })
    result.sort(key=lambda x: x["display_name"])
    return result


@app.get("/api/classes/teacher/{teacher_id}")
def get_teacher_classes(teacher_id: int, db: Session = Depends(get_db)):
    """Get classes taught by a specific teacher, grouped by grade"""
    classes = db.query(models.Class).filter(models.Class.teacher_id == teacher_id).all()
    result = []
    for c in classes:
        grade_name = c.grade.name if c.grade else ''
        display_name = c.display_name if c.display_name else f"{grade_name}{c.name}"
        result.append({
            "id": c.id,
            "name": c.name,
            "display_name": display_name,
            "grade_id": c.grade_id,
            "grade_name": grade_name,
            "teacher_id": c.teacher_id,
            "created_at": c.created_at
        })
    result.sort(key=lambda x: x["display_name"])
    return result


@app.post("/api/classes", response_model=schemas.ClassResponse)
def create_class(class_item: schemas.ClassCreate, db: Session = Depends(get_db)):
    grade = db.query(models.Grade).filter(models.Grade.id == class_item.grade_id).first()
    grade_name = grade.name if grade else ''
    del class_item.display_name
    db_class = models.Class(
        **class_item.dict(),
        display_name=f"{grade_name}{class_item.name}"
    )
    db.add(db_class)
    db.commit()
    db.refresh(db_class)
    return db_class


@app.put("/api/classes/{class_id}", response_model=schemas.ClassResponse)
def update_class(class_id: int, class_item: schemas.ClassUpdate, db: Session = Depends(get_db)):
    db_class = db.query(models.Class).filter(models.Class.id == class_id).first()
    if not db_class:
        raise HTTPException(status_code=404, detail="Class not found")
    for key, value in class_item.dict().items():
        setattr(db_class, key, value)
    # Regenerate display_name if name or grade_id changed
    grade = db.query(models.Grade).filter(models.Grade.id == db_class.grade_id).first()
    grade_name = grade.name if grade else ''
    db_class.display_name = f"{grade_name}{db_class.name}"
    db.commit()
    db.refresh(db_class)
    return db_class


@app.delete("/api/classes/{class_id}")
def delete_class(class_id: int, db: Session = Depends(get_db)):
    db_class = db.query(models.Class).filter(models.Class.id == class_id).first()
    if not db_class:
        raise HTTPException(status_code=404, detail="Class not found")
    db.delete(db_class)
    db.commit()
    return {"message": "Class deleted"}


# User routes
@app.get("/api/users", response_model=List[schemas.UserResponse])
def get_users(db: Session = Depends(get_db)):
    return db.query(models.User).all()


@app.post("/api/users", response_model=schemas.UserResponse)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    hashed_password = get_password_hash(user.password)
    db_user = models.User(**user.dict(exclude={"password"}), password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@app.put("/api/users/{user_id}", response_model=schemas.UserResponse)
def update_user(user_id: int, user: schemas.UserUpdate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    for key, value in user.dict(exclude_unset=True).items():
        if key == "password" and value:
            value = get_password_hash(value)
        setattr(db_user, key, value)
    db.commit()
    db.refresh(db_user)
    return db_user


@app.delete("/api/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(db_user)
    db.commit()
    return {"message": "User deleted"}


# Student routes
@app.get("/api/students")
def get_students(active: Optional[bool] = None, db: Session = Depends(get_db)):
    query = db.query(models.Student)
    if active is not None:
        query = query.filter(models.Student.active == active)
    students = query.all()
    result = []
    for s in students:
        tags = db.query(models.Tag).join(models.StudentTag).filter(
            models.StudentTag.student_id == s.id
        ).all()
        result.append({
            "id": s.id,
            "name": s.name,
            "gender": s.gender,
            "birthday": s.birthday,
            "age": s.age,
            "height": s.height,
            "weight": s.weight,
            "hobbies": s.hobbies,
            "friends": s.friends,
            "class_id": s.class_id,
            "active": s.active,
            "created_at": s.created_at,
            "tags": [{"id": t.id, "name": t.name, "created_at": t.created_at} for t in tags]
        })
    return result


@app.get("/api/students/{student_id}")
def get_student(student_id: int, db: Session = Depends(get_db)):
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    tags = db.query(models.Tag).join(models.StudentTag).filter(
        models.StudentTag.student_id == student.id
    ).all()
    
    return {
        "id": student.id,
        "name": student.name,
        "gender": student.gender,
        "birthday": student.birthday,
        "age": student.age,
        "height": student.height,
        "weight": student.weight,
        "hobbies": student.hobbies,
        "friends": student.friends,
        "class_id": student.class_id,
        "active": student.active,
        "created_at": student.created_at,
        "tags": [{"id": t.id, "name": t.name, "created_at": t.created_at} for t in tags]
    }


@app.post("/api/students", response_model=schemas.StudentResponse)
def create_student(student: schemas.StudentCreate, db: Session = Depends(get_db)):
    student_data = student.dict()
    # Calculate age from birthday
    if student_data.get('birthday'):
        student_data['age'] = calculate_age(student_data['birthday'])
    db_student = models.Student(**student_data)
    db.add(db_student)
    db.commit()
    db.refresh(db_student)
    return {
        "id": db_student.id,
        "name": db_student.name,
        "gender": db_student.gender,
        "birthday": db_student.birthday,
        "age": db_student.age,
        "height": db_student.height,
        "weight": db_student.weight,
        "hobbies": db_student.hobbies,
        "friends": db_student.friends,
        "class_id": db_student.class_id,
        "active": db_student.active,
        "created_at": db_student.created_at,
        "tags": []
    }


@app.put("/api/students/{student_id}", response_model=schemas.StudentResponse)
def update_student(student_id: int, student: schemas.StudentUpdate, db: Session = Depends(get_db)):
    db_student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not db_student:
        raise HTTPException(status_code=404, detail="Student not found")
    for key, value in student.dict().items():
        setattr(db_student, key, value)
    # Recalculate age if birthday changed
    if db_student.birthday:
        db_student.age = calculate_age(db_student.birthday)
    db.commit()
    db.refresh(db_student)
    
    tags = db.query(models.Tag).join(models.StudentTag).filter(
        models.StudentTag.student_id == db_student.id
    ).all()
    
    return {
        "id": db_student.id,
        "name": db_student.name,
        "gender": db_student.gender,
        "birthday": db_student.birthday,
        "age": db_student.age,
        "height": db_student.height,
        "weight": db_student.weight,
        "hobbies": db_student.hobbies,
        "friends": db_student.friends,
        "class_id": db_student.class_id,
        "active": db_student.active,
        "created_at": db_student.created_at,
        "tags": [{"id": t.id, "name": t.name, "created_at": t.created_at} for t in tags]
    }


@app.delete("/api/students/{student_id}")
def delete_student(student_id: int, db: Session = Depends(get_db)):
    db_student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not db_student:
        raise HTTPException(status_code=404, detail="Student not found")
    db.delete(db_student)
    db.commit()
    return {"message": "Student deleted"}


@app.post("/api/students/import")
async def import_students(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Import students from Excel file"""
    try:
        content = await file.read()
        df = pd.read_excel(io.BytesIO(content))
        students = []
        for _, row in df.iterrows():
            birthday = row.get('生日')
            age = None
            if pd.notna(birthday):
                if isinstance(birthday, str):
                    birthday = datetime.strptime(birthday, '%Y-%m-%d').date()
                elif hasattr(birthday, 'date'):
                    birthday = birthday.date()
                age = calculate_age(birthday)
            else:
                birthday = None
            class_obj = db.query(models.Class).filter(
                models.Class.display_name == row["班级"]
            ).first()

            student = models.Student(
                name=row['姓名'],
                gender=row['性别'],
                birthday=birthday,
                age=age,
                height=row.get('身高(cm)', 0),
                weight=row.get('体重(kg)', 0),
                hobbies=row.get('爱好', ''),
                friends=row.get('朋友', ''),
                class_id=class_obj.id,
            )
            students.append(student)
        db.bulk_save_objects(students)
        db.commit()
        return {"message": f"Successfully imported {len(students)} students"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/students/promote")
def promote_students(db: Session = Depends(get_db)):
    """Promote all students to next grade (一年级->二年级, 六年级active改为False)"""
    # Get all grades
    grades = db.query(models.Grade).all()
    grade_map = {g.name: g for g in grades}
    
    # Define promotion mapping
    promotion_order = ["一年级", "二年级", "三年级", "四年级", "五年级", "六年级"]
    
    # Get all classes
    classes = db.query(models.Class).all()
    
    # Build target class mapping: old class_id -> new class_id
    target_class_map = {}
    sixth_grade_classes = []  # 六年级班级
    
    for c in classes:
        grade_name = c.grade.name if c.grade else ''
        if grade_name in promotion_order:
            idx = promotion_order.index(grade_name)
            # 六年级单独处理
            if idx == len(promotion_order) - 1:
                sixth_grade_classes.append(c.id)
            else:
                next_grade_name = promotion_order[idx + 1]
                next_grade = grade_map.get(next_grade_name)
                if next_grade:
                    # Find corresponding class in next grade
                    target_class = db.query(models.Class).filter(
                        models.Class.name == c.name,
                        models.Class.grade_id == next_grade.id
                    ).first()
                    if target_class:
                        target_class_map[c.id] = target_class.id
    
    # Update all students' class_id
    updated_count = 0
    deactivated_count = 0
    
    # 升级非六年级学生
    for old_class_id, new_class_id in target_class_map.items():
        students = db.query(models.Student).filter(
            models.Student.class_id == old_class_id
        ).all()
        for student in students:
            student.class_id = new_class_id
            updated_count += 1
    
    # 将六年级学生 active 设为 False
    for class_id in sixth_grade_classes:
        students = db.query(models.Student).filter(
            models.Student.class_id == class_id
        ).all()
        for student in students:
            student.active = False
            deactivated_count += 1
    
    db.commit()
    return {"message": f"Successfully promoted {updated_count} students, deactivated {deactivated_count} sixth-grade students"}


# Score routes
@app.get("/api/scores", response_model=List[schemas.ScoreResponse])
def get_scores(db: Session = Depends(get_db)):
    return db.query(models.Score).all()


@app.get("/api/scores/student/{student_id}", response_model=List[schemas.ScoreResponse])
def get_student_scores(student_id: int, db: Session = Depends(get_db)):
    return db.query(models.Score).filter(models.Score.student_id == student_id).order_by(
        models.Score.exam_date.desc()).all()


@app.get("/api/scores/class/{class_id}/subject/{subject_id}")
def get_class_scores(class_id: int, subject_id: int, db: Session = Depends(get_db)):
    return db.query(models.Score).filter(
        models.Score.class_id == class_id,
        models.Score.subject_id == subject_id
    ).order_by(models.Score.exam_date.desc()).all()


@app.post("/api/scores", response_model=schemas.ScoreResponse)
def create_score(score: schemas.ScoreCreate, db: Session = Depends(get_db)):
    db_score = models.Score(**score.dict())
    db.add(db_score)
    db.commit()
    db.refresh(db_score)
    return db_score


@app.put("/api/scores/{score_id}", response_model=schemas.ScoreResponse)
def update_score(score_id: int, score: schemas.ScoreCreate, db: Session = Depends(get_db)):
    db_score = db.query(models.Score).filter(models.Score.id == score_id).first()
    if not db_score:
        raise HTTPException(status_code=404, detail="Score not found")
    for key, value in score.dict().items():
        setattr(db_score, key, value)
    db.commit()
    db.refresh(db_score)
    return db_score


@app.post("/api/scores/import")
async def import_scores(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        content = await file.read()
        df = pd.read_excel(io.BytesIO(content))
        scores = []
        class_dict = {}

        subject_objs = db.query(models.Subject).all()
        subject_dict = {s.name: s.id for s in subject_objs}

        for _, row in df.iterrows():
            if row["班级"] not in class_dict:
                class_obj = db.query(models.Class).filter(
                    models.Class.display_name == row["班级"]
                ).first()
                class_id = class_obj.id
                class_dict[row["班级"]] = class_id
            else:
                class_id = class_dict[row["班级"]]

            student_obj = db.query(models.Student).filter(
                models.Student.name == row["姓名"],
                models.Student.class_id == class_id
            ).first()

            score = models.Score(
                student_id=student_obj.id,
                class_id=class_id,
                subject_id=subject_dict[row['学科']],
                score_type=row['考试类型'],
                score=row['成绩'],
                exam_date=row['考试日期']
            )
            scores.append(score)
        db.bulk_save_objects(scores)
        db.commit()
        return {"message": f"Successfully imported {len(scores)} scores"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Tag routes
@app.get("/api/tags", response_model=List[schemas.TagResponse])
def get_tags(db: Session = Depends(get_db)):
    return db.query(models.Tag).all()


@app.post("/api/tags", response_model=schemas.TagResponse)
def create_tag(tag: schemas.TagCreate, db: Session = Depends(get_db)):
    db_tag = models.Tag(**tag.dict())
    db.add(db_tag)
    db.commit()
    db.refresh(db_tag)
    return db_tag


@app.put("/api/tags/{tag_id}", response_model=schemas.TagResponse)
def update_tag(tag_id: int, tag: schemas.TagUpdate, db: Session = Depends(get_db)):
    db_tag = db.query(models.Tag).filter(models.Tag.id == tag_id).first()
    if not db_tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    db_tag.name = tag.name
    db.commit()
    db.refresh(db_tag)
    return db_tag


@app.delete("/api/tags/{tag_id}")
def delete_tag(tag_id: int, db: Session = Depends(get_db)):
    db_tag = db.query(models.Tag).filter(models.Tag.id == tag_id).first()
    if not db_tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    db.delete(db_tag)
    db.commit()
    return {"message": "Tag deleted"}


@app.post("/api/students/{student_id}/tags/{tag_id}")
def add_student_tag(student_id: int, tag_id: int, db: Session = Depends(get_db)):
    student_tag = models.StudentTag(student_id=student_id, tag_id=tag_id)
    db.add(student_tag)
    db.commit()
    return {"message": "Tag added"}


@app.delete("/api/students/{student_id}/tags/{tag_id}")
def remove_student_tag(student_id: int, tag_id: int, db: Session = Depends(get_db)):
    db.query(models.StudentTag).filter(
        models.StudentTag.student_id == student_id,
        models.StudentTag.tag_id == tag_id
    ).delete()
    db.commit()
    return {"message": "Tag removed"}


# Schedule routes
@app.get("/api/schedules", response_model=List[schemas.ScheduleResponse])
def get_schedules(db: Session = Depends(get_db)):
    schedules = db.query(models.Schedule).all()
    result = []
    for s in schedules:
        class_display_name = s.class_.display_name if s.class_ and s.class_.display_name else s.class_.name if s.class_ else None
        result.append({
            "id": s.id,
            "class_id": s.class_id,
            "teacher_id": s.teacher_id,
            "subject_id": s.subject_id,
            "day_of_week": s.day_of_week,
            "time_slot": s.time_slot,
            "start_time": s.start_time,
            "end_time": s.end_time,
            "created_at": s.created_at,
            "class_name": class_display_name,
            "teacher_name": s.teacher.name if s.teacher else None,
            "subject_name": s.subject.name if s.subject else None
        })
    return result


@app.get("/api/schedules/teacher/{teacher_id}", response_model=List[schemas.ScheduleResponse])
def get_teacher_schedules(teacher_id: int, db: Session = Depends(get_db)):
    schedules = db.query(models.Schedule).filter(models.Schedule.teacher_id == teacher_id).all()
    result = []
    for s in schedules:
        class_display_name = s.class_.display_name if s.class_ and s.class_.display_name else s.class_.name if s.class_ else None
        result.append({
            "id": s.id,
            "class_id": s.class_id,
            "teacher_id": s.teacher_id,
            "subject_id": s.subject_id,
            "day_of_week": s.day_of_week,
            "time_slot": s.time_slot,
            "start_time": s.start_time,
            "end_time": s.end_time,
            "created_at": s.created_at,
            "class_name": class_display_name,
            "teacher_name": s.teacher.name if s.teacher else None,
            "subject_name": s.subject.name if s.subject else None
        })
    return result


@app.post("/api/schedules", response_model=schemas.ScheduleResponse)
def create_schedule(schedule: schemas.ScheduleCreate, db: Session = Depends(get_db)):
    db_schedule = models.Schedule(**schedule.dict())
    db.add(db_schedule)
    db.commit()
    db.refresh(db_schedule)
    return db_schedule


@app.put("/api/schedules/{schedule_id}", response_model=schemas.ScheduleResponse)
def update_schedule(schedule_id: int, schedule: schemas.ScheduleUpdate, db: Session = Depends(get_db)):
    db_schedule = db.query(models.Schedule).filter(models.Schedule.id == schedule_id).first()
    if not db_schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    for key, value in schedule.dict().items():
        setattr(db_schedule, key, value)
    db.commit()
    db.refresh(db_schedule)
    return db_schedule


@app.delete("/api/schedules/{schedule_id}")
def delete_schedule(schedule_id: int, db: Session = Depends(get_db)):
    db_schedule = db.query(models.Schedule).filter(models.Schedule.id == schedule_id).first()
    if not db_schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    db.delete(db_schedule)
    db.commit()
    return {"message": "Schedule deleted"}


# Dashboard routes
@app.get("/api/dashboard/class/{class_id}")
def get_class_dashboard(class_id: int, subject_id: Optional[int] = None, db: Session = Depends(get_db)):
    import statistics
    
    class_item = db.query(models.Class).filter(models.Class.id == class_id).first()
    if not class_item:
        raise HTTPException(status_code=404, detail="Class not found")

    students = db.query(models.Student).filter(models.Student.class_id == class_id).all()
    male_count = sum(1 for s in students if s.gender == "男")
    female_count = sum(1 for s in students if s.gender == "女")

    # Get latest class average score and statistics
    latest_avg_score = None
    score_query = db.query(
        models.Score.exam_date,
        func.avg(models.Score.score).label('avg_score')
    ).filter(models.Score.class_id == class_id)
    
    if subject_id:
        score_query = score_query.filter(models.Score.subject_id == subject_id)
    
    latest_score_record = score_query.group_by(models.Score.exam_date).order_by(
        models.Score.exam_date.desc()
    ).first()
    
    if latest_score_record:
        # Get all scores for the latest exam to calculate statistics
        latest_date = latest_score_record.exam_date
        scores_query = db.query(models.Score.score).filter(
            models.Score.class_id == class_id,
            models.Score.exam_date == latest_date
        )
        if subject_id:
            scores_query = scores_query.filter(models.Score.subject_id == subject_id)
        
        scores = [s.score for s in scores_query.all()]
        
        if scores:
            max_score = max(scores)
            min_score = min(scores)
            median_score = statistics.median(scores)
            std_dev = statistics.stdev(scores) if len(scores) > 1 else 0
            
            latest_avg_score = {
                "score": float(latest_score_record.avg_score),
                "exam_date": str(latest_score_record.exam_date),
                "max_score": max_score,
                "min_score": min_score,
                "median_score": round(median_score, 2),
                "std_dev": round(std_dev, 2)
            }

    return {
        "class_name": class_item.display_name if class_item.display_name else class_item.name,
        "total_students": len(students),
        "male_count": male_count,
        "female_count": female_count,
        "teacher_name": class_item.teacher.name if class_item.teacher else None,
        "latest_avg_score": latest_avg_score
    }


@app.get("/api/dashboard/class/{class_id}/average-score")
def get_class_average_score(class_id: int, subject_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(
        models.Score.exam_date,
        func.avg(models.Score.score).label('avg_score')
    ).filter(models.Score.class_id == class_id)

    if subject_id:
        query = query.filter(models.Score.subject_id == subject_id)

    scores = query.group_by(models.Score.exam_date).order_by(models.Score.exam_date.desc()).limit(6).all()
    return [{"date": str(s.exam_date), "avg_score": round(float(s.avg_score), 2)} for s in scores]


@app.get("/api/dashboard/student/{student_id}/scores")
def get_student_score_trend(student_id: int, subject_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(models.Score).filter(models.Score.student_id == student_id)

    if subject_id:
        query = query.filter(models.Score.subject_id == subject_id)

    scores = query.order_by(models.Score.exam_date.desc()).limit(6).all()
    return [{
        "date": str(s.exam_date),
        "score": s.score,
        "score_type": s.score_type,
        "subject_name": s.subject.name if s.subject else None
    } for s in scores]


@app.get("/api/dashboard/class/{class_id}/students")
def get_class_students(class_id: int, subject_id: Optional[int] = None, db: Session = Depends(get_db)):
    students = db.query(models.Student).filter(models.Student.class_id == class_id).all()
    result = []
    for s in students:
        tags = db.query(models.Tag).join(models.StudentTag).filter(models.StudentTag.student_id == s.id
        ).all()
        
        # Get latest score for this student
        latest_score = None
        score_query = db.query(models.Score).filter(
            models.Score.student_id == s.id
        )
        if subject_id:
            score_query = score_query.filter(models.Score.subject_id == subject_id)
        latest_score_record = score_query.order_by(models.Score.exam_date.desc()).first()
        if latest_score_record:
            latest_score = {
                "score": latest_score_record.score,
                "exam_date": str(latest_score_record.exam_date),
                "score_type": latest_score_record.score_type
            }
        
        result.append({
            "id": s.id,
            "name": s.name,
            "gender": s.gender,
            "age": s.age,
            "active": s.active,
            "height": s.height,
            "weight": s.weight,
            "hobbies": s.hobbies,
            "friends": s.friends,
            "tags": [{"id": t.id, "name": t.name} for t in tags],
            "latest_score": latest_score
        })
    return result


@app.get("/api/dashboard/current-schedule")
def get_current_schedule(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Return ALL schedules for the teacher, not just today
    schedules = db.query(models.Schedule).filter(
        models.Schedule.teacher_id == current_user.id
    ).all()

    result = []
    for s in schedules:
        class_display_name = s.class_.display_name if s.class_ and s.class_.display_name else s.class_.name if s.class_ else None
        result.append({
            "id": s.id,
            "class_id": s.class_id,
            "teacher_id": s.teacher_id,
            "subject_id": s.subject_id,
            "day_of_week": s.day_of_week,
            "time_slot": s.time_slot,
            "start_time": s.start_time,
            "end_time": s.end_time,
            "created_at": s.created_at,
            "class_name": class_display_name,
            "teacher_name": s.teacher.name if s.teacher else None,
            "subject_name": s.subject.name if s.subject else None
        })

    return result


# Report routes
@app.get("/api/dashboard/class/{class_id}/progress-report")
def get_progress_report(class_id: int, subject_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Get top 10 students with most improved scores"""
    # Find latest exam date for this class and subject
    latest_exam_query = db.query(models.Score.exam_date).filter(
        models.Score.class_id == class_id
    )
    if subject_id:
        latest_exam_query = latest_exam_query.filter(models.Score.subject_id == subject_id)
    
    latest_exam_date = latest_exam_query.order_by(models.Score.exam_date.desc()).first()
    if not latest_exam_date:
        return []
    latest_exam_date = latest_exam_date[0]
    
    # Find previous exam date
    prev_exam_query = db.query(models.Score.exam_date).filter(
        models.Score.class_id == class_id,
        models.Score.exam_date < latest_exam_date
    )
    if subject_id:
        prev_exam_query = prev_exam_query.filter(models.Score.subject_id == subject_id)
        
    prev_exam_date = prev_exam_query.order_by(models.Score.exam_date.desc()).first()
    if not prev_exam_date:
        return []
    prev_exam_date = prev_exam_date[0]
    
    # Get scores for these two dates
    students = db.query(models.Student).filter(models.Student.class_id == class_id).all()
    progress_list = []
    
    for s in students:
        latest_score = db.query(models.Score).filter(
            models.Score.student_id == s.id,
            models.Score.exam_date == latest_exam_date
        ).first()
        
        prev_score = db.query(models.Score).filter(
            models.Score.student_id == s.id,
            models.Score.exam_date == prev_exam_date
        ).first()
        
        if latest_score and prev_score:
            diff = round(latest_score.score - prev_score.score, 2)
            if diff > 0:  # Only include students with positive progress
                progress_list.append({
                    "name": s.name,
                    "gender": s.gender,
                    "latest_score": latest_score.score,
                    "previous_score": prev_score.score,
                    "diff": diff,
                    "latest_date": str(latest_exam_date),
                    "previous_date": str(prev_exam_date)
                })
            
    progress_list.sort(key=lambda x: x["diff"], reverse=True)
    return progress_list[:10]


@app.get("/api/dashboard/class/{class_id}/regression-report")
def get_regression_report(class_id: int, subject_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Get top 10 students with most regressed scores"""
    # Find latest exam date for this class and subject
    latest_exam_query = db.query(models.Score.exam_date).filter(
        models.Score.class_id == class_id
    )
    if subject_id:
        latest_exam_query = latest_exam_query.filter(models.Score.subject_id == subject_id)
    
    latest_exam_date = latest_exam_query.order_by(models.Score.exam_date.desc()).first()
    if not latest_exam_date:
        return []
    latest_exam_date = latest_exam_date[0]
    
    # Find previous exam date
    prev_exam_query = db.query(models.Score.exam_date).filter(
        models.Score.class_id == class_id,
        models.Score.exam_date < latest_exam_date
    )
    if subject_id:
        prev_exam_query = prev_exam_query.filter(models.Score.subject_id == subject_id)
        
    prev_exam_date = prev_exam_query.order_by(models.Score.exam_date.desc()).first()
    if not prev_exam_date:
        return []
    prev_exam_date = prev_exam_date[0]
    
    # Get scores for these two dates
    students = db.query(models.Student).filter(models.Student.class_id == class_id).all()
    regression_list = []
    
    for s in students:
        latest_score = db.query(models.Score).filter(
            models.Score.student_id == s.id,
            models.Score.exam_date == latest_exam_date
        ).first()
        
        prev_score = db.query(models.Score).filter(
            models.Score.student_id == s.id,
            models.Score.exam_date == prev_exam_date
        ).first()
        
        if latest_score and prev_score:
            diff = round(latest_score.score - prev_score.score, 2)
            if diff < 0:  # Only include students with negative regression
                regression_list.append({
                    "name": s.name,
                    "gender": s.gender,
                    "latest_score": latest_score.score,
                    "previous_score": prev_score.score,
                    "diff": diff,
                    "latest_date": str(latest_exam_date),
                    "previous_date": str(prev_exam_date)
                })
            
    regression_list.sort(key=lambda x: x["diff"])
    return regression_list[:10]


@app.get("/api/dashboard/class/{class_id}/score-distribution")
def get_score_distribution(class_id: int, subject_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Get score distribution pie chart data"""
    # Get latest exam date for this class and subject
    score_query = db.query(models.Score).filter(models.Score.class_id == class_id)
    if subject_id:
        score_query = score_query.filter(models.Score.subject_id == subject_id)
    
    latest_exam = score_query.order_by(models.Score.exam_date.desc()).first()
    if not latest_exam:
        return {"distribution": [], "exam_date": None}
    
    latest_date = latest_exam.exam_date
    
    # Get all scores for the latest exam
    scores = db.query(models.Score).filter(
        models.Score.class_id == class_id,
        models.Score.exam_date == latest_date
    )
    if subject_id:
        scores = scores.filter(models.Score.subject_id == subject_id)
    scores = scores.all()
    
    distribution = [
        {"range": "60分以下", "count": 0},
        {"range": "60-70分", "count": 0},
        {"range": "71-80分", "count": 0},
        {"range": "81-90分", "count": 0},
        {"range": "91-100分", "count": 0}
    ]
    
    for sc in scores:
        score = sc.score
        if score < 60:
            distribution[0]["count"] += 1
        elif score <= 70:
            distribution[1]["count"] += 1
        elif score <= 80:
            distribution[2]["count"] += 1
        elif score <= 90:
            distribution[3]["count"] += 1
        else:
            distribution[4]["count"] += 1
    
    return {"distribution": distribution, "exam_date": str(latest_date)}


@app.get("/api/dashboard/class/{class_id}/progress-regression-summary")
def get_progress_regression_summary(class_id: int, subject_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Get summary of progress, regression, and stable students"""
    # Find latest exam date for this class and subject
    latest_exam_query = db.query(models.Score.exam_date).filter(
        models.Score.class_id == class_id
    )
    if subject_id:
        latest_exam_query = latest_exam_query.filter(models.Score.subject_id == subject_id)
    
    latest_exam_date = latest_exam_query.order_by(models.Score.exam_date.desc()).first()
    if not latest_exam_date:
        return {"progress_count": 0, "regression_count": 0, "stable_count": 0, "distribution": []}
    latest_exam_date = latest_exam_date[0]
    
    # Find previous exam date
    prev_exam_query = db.query(models.Score.exam_date).filter(
        models.Score.class_id == class_id,
        models.Score.exam_date < latest_exam_date
    )
    if subject_id:
        prev_exam_query = prev_exam_query.filter(models.Score.subject_id == subject_id)
        
    prev_exam_date = prev_exam_query.order_by(models.Score.exam_date.desc()).first()
    if not prev_exam_date:
        return {"progress_count": 0, "regression_count": 0, "stable_count": 0, "distribution": []}
    prev_exam_date = prev_exam_date[0]
    
    # Get scores for these two dates
    students = db.query(models.Student).filter(models.Student.class_id == class_id).all()
    
    progress_count = 0
    regression_count = 0
    stable_count = 0
    
    distribution = []
    
    for s in students:
        latest_score = db.query(models.Score).filter(
            models.Score.student_id == s.id,
            models.Score.exam_date == latest_exam_date
        ).first()
        
        prev_score = db.query(models.Score).filter(
            models.Score.student_id == s.id,
            models.Score.exam_date == prev_exam_date
        ).first()
        
        if latest_score and prev_score:
            diff = round(latest_score.score - prev_score.score, 2)
            if diff > 0:
                progress_count += 1
                distribution.append({
                    "name": s.name,
                    "gender": s.gender,
                    "latest_score": latest_score.score,
                    "previous_score": prev_score.score,
                    "diff": diff,
                    "category": "进步"
                })
            elif diff < 0:
                regression_count += 1
                distribution.append({
                    "name": s.name,
                    "gender": s.gender,
                    "latest_score": latest_score.score,
                    "previous_score": prev_score.score,
                    "diff": diff,
                    "category": "退步"
                })
            else:
                stable_count += 1
                distribution.append({
                    "name": s.name,
                    "gender": s.gender,
                    "latest_score": latest_score.score,
                    "previous_score": prev_score.score,
                    "diff": 0,
                    "category": "持平"
                })
    
    return {
        "progress_count": progress_count,
        "regression_count": regression_count,
        "stable_count": stable_count,
        "distribution": distribution,
        "latest_date": str(latest_exam_date),
        "previous_date": str(prev_exam_date)
    }


@app.get("/api/dashboard/class/{class_id}/gender-distribution")
def get_gender_distribution(class_id: int, subject_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Get gender distribution by score range bar chart data"""
    score_query = db.query(models.Score).filter(models.Score.class_id == class_id)
    if subject_id:
        score_query = score_query.filter(models.Score.subject_id == subject_id)
    
    latest_exam = score_query.order_by(models.Score.exam_date.desc()).first()
    if not latest_exam:
        return {"distribution": [], "exam_date": None}
    
    latest_date = latest_exam.exam_date
    
    # Get all scores for the latest exam with student info
    scores = db.query(models.Score, models.Student).join(
        models.Student, models.Score.student_id == models.Student.id
    ).filter(
        models.Score.class_id == class_id,
        models.Score.exam_date == latest_date
    )
    if subject_id:
        scores = scores.filter(models.Score.subject_id == subject_id)
    scores = scores.all()
    
    ranges = ["60分以下", "60-70分", "71-80分", "81-90分", "91-100分"]
    distribution = []
    
    for r in ranges:
        distribution.append({
            "range": r,
            "male": 0,
            "female": 0
        })
    
    for sc, student in scores:
        score = sc.score
        gender = student.gender
        if score < 60:
            idx = 0
        elif score <= 70:
            idx = 1
        elif score <= 80:
            idx = 2
        elif score <= 90:
            idx = 3
        else:
            idx = 4
        
        if gender == "男":
            distribution[idx]["male"] += 1
        else:
            distribution[idx]["female"] += 1
    
    return {"distribution": distribution, "exam_date": str(latest_date)}


# Seed data endpoint
@app.post("/api/seed")
def seed_data(db: Session = Depends(get_db)):
    # Create subjects
    subjects = ["语文", "数学", "英语", "物理", "化学", "生物", "历史", "地理", "政治"]
    subject_map = {}
    for subj_name in subjects:
        subj = db.query(models.Subject).filter(models.Subject.name == subj_name).first()
        if not subj:
            subj = models.Subject(name=subj_name)
            db.add(subj)
            db.commit()
            db.refresh(subj)
        subject_map[subj_name] = subj.id

    # Create grades
    grades = ["一年级", "二年级", "三年级"]
    grade_map = {}
    for grade_name in grades:
        grade = db.query(models.Grade).filter(models.Grade.name == grade_name).first()
        if not grade:
            grade = models.Grade(name=grade_name)
            db.add(grade)
            db.commit()
            db.refresh(grade)
        grade_map[grade_name] = grade.id

    # Create users
    if not db.query(models.User).filter(models.User.username == "teacher1").first():
        teacher1 = models.User(
            username="teacher1",
            password=get_password_hash("123456"),
            name="张老师",
            subject_id=subject_map["英语"],
            role="teacher"
        )
        db.add(teacher1)
        db.commit()

    # Create classes
    if not db.query(models.Class).filter(models.Class.name == "一班").first():
        teacher = db.query(models.User).filter(models.User.username == "teacher1").first()
        class1 = models.Class(
            name="一班",
            grade_id=grade_map["一年级"],
            teacher_id=teacher.id
        )
        db.add(class1)
        db.commit()

    return {"message": "Seed data created"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
