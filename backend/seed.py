"""Seeds DEMO data (flagged is_demo=True so it can be separated from real data).

Run:  python seed.py            -> adds demo data if missing
      python seed.py --reset    -> removes demo users first
"""
import sys

from sqlalchemy import delete, select

from app.auth.security import hash_password
from app.config import get_settings
from app.database.session import SessionLocal
from app.models import ROLE_ADMIN, ROLE_STUDENT, Admin, Student, Subject, User

DEPT = "Computer Science & Engineering"
SUBJECTS = [
    ("MA201", "Engineering Mathematics", 3, 6),
    ("CS201", "Data Structures", 3, 8),
    ("PH201", "Physics", 3, 5),
    ("CS202", "Object Oriented Programming", 3, 7),
    ("CS203", "Database Management", 3, 6),
]


def main() -> None:
    s = get_settings()
    with SessionLocal() as db:
        if "--reset" in sys.argv:
            db.execute(delete(User).where(User.is_demo.is_(True)))
            db.commit()

        for code, name, sem, units in SUBJECTS:
            if not db.scalar(select(Subject.id).where(Subject.code == code)):
                db.add(Subject(code=code, name=name, department=DEPT, semester=sem, units=units))

        if not db.scalar(select(User.id).where(User.email == "admin.demo@svkmit.ac.in")):
            u = User(email="admin.demo@svkmit.ac.in", password_hash=hash_password(s.seed_admin_password),
                     full_name="Dr. Meera Iyer (demo)", role=ROLE_ADMIN, is_demo=True)
            u.admin = Admin(department=DEPT, designation="Assistant Professor")
            db.add(u)

        if not db.scalar(select(User.id).where(User.email == "aarav.demo@svkmit.ac.in")):
            u = User(email="aarav.demo@svkmit.ac.in", password_hash=hash_password(s.seed_student_password),
                     full_name="Aarav Sharma (demo)", role=ROLE_STUDENT, is_demo=True)
            u.student = Student(department=DEPT, year=2, semester=3)
            db.add(u)

        db.commit()
    print("Seeded demo data.\n  admin:   admin.demo@svkmit.ac.in\n  student: aarav.demo@svkmit.ac.in\n"
          "  (passwords come from SEED_ADMIN_PASSWORD / SEED_STUDENT_PASSWORD in .env)")


if __name__ == "__main__":
    main()
