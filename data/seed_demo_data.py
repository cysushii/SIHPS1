"""
Synthetic seed data generator for SIH26263 platform testing & demo.
Generates:
- 5 AICTE Approved Institutions with configured program capacities
- 60 Synthetic Student records with realistic APAAR IDs
- Specific edge cases for demo:
  1. Capacity overflow in one program (to trigger trust score capacity mismatch signal)
  2. Cross-Institute Duplicate APAAR ID (exact match dedup demo)
  3. Fuzzy duplicate name with same DOB but different APAAR ID (suspected duplicate dedup demo)
  4. Sybil cluster: 3 distinct students sharing identical address at the same institute (graph fraud demo)
"""

import random
from models.database import SessionLocal, Base, engine
from models.models import Institute, InstituteProgram, Student, Batch, StudentBatch, VerificationToken
from security.hash_chain import log_event
from engines.dedup import run_deduplication
from engines.graph_fraud import analyze_graph_fraud
import secrets
import datetime

def generate_seed_data():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    print("Seeding institutes and programs...")
    # 1. Clean existing records for fresh demo run
    db.query(VerificationToken).delete()
    db.query(StudentBatch).delete()
    db.query(Batch).delete()
    db.query(Student).delete()
    db.query(InstituteProgram).delete()
    db.query(Institute).delete()
    db.commit()

    inst_data = [
        {"code": "1-1001", "name": "Indian Institute of Technology Bombay", "state": "Maharashtra", "district": "Mumbai Suburban", "type": "Central"},
        {"code": "1-1005", "name": "Vellore Institute of Technology", "state": "Tamil Nadu", "district": "Vellore", "type": "Private"},
        {"code": "1-1006", "name": "SRM Institute of Science and Technology", "state": "Tamil Nadu", "district": "Chengalpattu", "type": "Deemed"},
        {"code": "1-1008", "name": "College of Engineering Pune", "state": "Maharashtra", "district": "Pune", "type": "State"},
        {"code": "1-1009", "name": "Delhi Technological University", "state": "Delhi", "district": "North West Delhi", "type": "State"},
    ]

    institutes = []
    for item in inst_data:
        inst = Institute(
            aicte_code=item["code"],
            name=item["name"],
            state=item["state"],
            district=item["district"],
            type=item["type"],
            approval_status="Approved"
        )
        db.add(inst)
        db.flush()
        institutes.append(inst)

        # Add programs
        prog_cs = InstituteProgram(institute_id=inst.id, program="B.Tech Computer Science", approved_intake=10)
        prog_mech = InstituteProgram(institute_id=inst.id, program="B.Tech Mechanical", approved_intake=30)
        prog_mba = InstituteProgram(institute_id=inst.id, program="MBA", approved_intake=20)
        db.add_all([prog_cs, prog_mech, prog_mba])
        log_event(db, "Institute", inst.id, "CREATE", "system_seed")

    db.commit()

    print("Seeding students...")
    first_names = ["Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Ayaan", "Krishna", "Ishaan",
                   "Diya", "Saanvi", "Ananya", "Aadhya", "Pari", "Chiara", "Myra", "Riya", "Avni", "Prisha"]
    last_names = ["Sharma", "Verma", "Patel", "Reddy", "Nair", "Iyer", "Gupta", "Kumar", "Singh", "Das",
                  "Joshi", "Bose", "Mehta", "Bhat", "Choudhury", "Rao", "Pillai", "Mukherjee", "Banerjee", "Kulkarni"]

    apaar_counter = 1000000000

    # Populate 45 regular students distributed across institutes
    for i in range(45):
        inst = random.choice(institutes)
        fname = random.choice(first_names)
        lname = random.choice(last_names)
        # APAAR format: registration year 24 + 10 digits
        apaar = f"24{apaar_counter + i:010d}"
        prog = "B.Tech Mechanical" if i % 2 == 0 else "MBA"
        dob = f"2002-{random.randint(1,12):02d}-{random.randint(1,28):02d}"
        addr = f"{random.randint(10, 999)}, Sector {random.randint(1, 25)}, {inst.district}"

        student = Student(
            apaar_id=apaar,
            name=f"{fname} {lname}",
            institute_id=inst.id,
            program=prog,
            enrollment_year=2024,
            status="Active",
            dob=dob,
            address=addr
        )
        db.add(student)
        db.flush()
        log_event(db, "Student", student.id, "CREATE", "system_seed")

    # DEMO CASE 1: Capacity Overflow at Institute 1 (IIT Bombay B.Tech Computer Science approved intake is 10)
    # Adding 14 students to B.Tech Computer Science
    print("Injecting Demo Case 1: Capacity Overflow (14 submitted vs 10 approved intake)...")
    for j in range(14):
        apaar = f"23{apaar_counter + 100 + j:010d}"
        s = Student(
            apaar_id=apaar,
            name=f"{random.choice(first_names)} {random.choice(last_names)}",
            institute_id=institutes[0].id,
            program="B.Tech Computer Science",
            enrollment_year=2023,
            status="Active",
            dob="2003-05-15",
            address=f"{j+1} Powai Road, Mumbai"
        )
        db.add(s)
        db.flush()
        log_event(db, "Student", s.id, "CREATE", "system_seed")

    # DEMO CASE 2: Exact Cross-Institute Duplicate APAAR ID
    # Same APAAR ID enrolled at IIT Bombay (Institute 1) AND VIT (Institute 2)
    print("Injecting Demo Case 2: Cross-Institute Duplicate APAAR ID...")
    dup_apaar = "225500112233"
    s_dup1 = Student(
        apaar_id=dup_apaar,
        name="Rohan Suresh Verma",
        institute_id=institutes[0].id,
        program="B.Tech Computer Science",
        enrollment_year=2022,
        status="Active",
        dob="2002-08-20",
        address="102 Marine Drive, Mumbai"
    )
    s_dup2 = Student(
        apaar_id=dup_apaar,
        name="Rohan S. Verma",
        institute_id=institutes[1].id,
        program="B.Tech Computer Science",
        enrollment_year=2022,
        status="Active",
        dob="2002-08-20",
        address="102 Marine Drive, Mumbai"
    )
    db.add_all([s_dup1, s_dup2])
    db.flush()
    log_event(db, "Student", s_dup1.id, "CREATE", "system_seed")
    log_event(db, "Student", s_dup2.id, "CREATE", "system_seed")

    # DEMO CASE 3: Suspected Duplicate (Fuzzy name > 90% + same DOB, but different APAAR ID)
    print("Injecting Demo Case 3: Fuzzy Identity Match with Distinct APAAR IDs...")
    s_fuzzy1 = Student(
        apaar_id="248811223344",
        name="Vikramaditya Narayan Singh",
        institute_id=institutes[2].id,
        program="MBA",
        enrollment_year=2024,
        status="Active",
        dob="2001-11-12",
        address="Flat 4B, Green Glen, Bangalore"
    )
    s_fuzzy2 = Student(
        apaar_id="248899776655",
        name="Vikramaditya N. Singh",
        institute_id=institutes[3].id,
        program="MBA",
        enrollment_year=2024,
        status="Active",
        dob="2001-11-12",
        address="Plot 5, Kalyani Nagar, Pune"
    )
    db.add_all([s_fuzzy1, s_fuzzy2])
    db.flush()
    log_event(db, "Student", s_fuzzy1.id, "CREATE", "system_seed")
    log_event(db, "Student", s_fuzzy2.id, "CREATE", "system_seed")

    # DEMO CASE 4: Sybil Fraud Cluster (3+ different APAAR IDs sharing same address at same institute)
    print("Injecting Demo Case 4: Sybil Fraud Cluster (3 students sharing same address at Delhi Tech)...")
    shared_address = "Flat 304, Shanti Niwas, Sector 14, Rohini, Delhi"
    sybil1 = Student(
        apaar_id="247700010001",
        name="Amitabh Saxena",
        institute_id=institutes[4].id,
        program="MBA",
        enrollment_year=2024,
        status="Active",
        dob="2000-01-10",
        address=shared_address
    )
    sybil2 = Student(
        apaar_id="247700020002",
        name="Deepak Trivedi",
        institute_id=institutes[4].id,
        program="MBA",
        enrollment_year=2024,
        status="Active",
        dob="2001-04-12",
        address=shared_address
    )
    sybil3 = Student(
        apaar_id="247700030003",
        name="Sunil Bhardwaj",
        institute_id=institutes[4].id,
        program="MBA",
        enrollment_year=2024,
        status="Active",
        dob="2000-09-25",
        address=shared_address
    )
    db.add_all([sybil1, sybil2, sybil3])
    db.flush()
    log_event(db, "Student", sybil1.id, "CREATE", "system_seed")
    log_event(db, "Student", sybil2.id, "CREATE", "system_seed")
    log_event(db, "Student", sybil3.id, "CREATE", "system_seed")

    db.commit()

    print("Running initial deduplication & graph fraud scanners...")
    dedup_results = run_deduplication(db)
    graph_results = analyze_graph_fraud(db)

    print("Seeding batches and verification tokens for hackathon workflow demo...")
    # Create Batch 1: Draft with student self-verification links
    inst1 = institutes[0]
    inst1_students = db.query(Student).filter(Student.institute_id == inst1.id).all()
    b1 = Batch(
        institute_id=inst1.id,
        name="2024-25 Fall Undergraduate Cohort",
        status="draft",
    )
    db.add(b1)
    db.flush()

    for idx, s in enumerate(inst1_students[:12]):
        sb = StudentBatch(batch_id=b1.id, student_id=s.id)
        db.add(sb)
        vt = VerificationToken(
            token=f"demo_token_{idx}_{secrets.token_hex(8)}",
            student_id=s.id,
            batch_id=b1.id,
            status="verified" if idx % 3 == 0 else "pending",
            expires_at=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=3),
        )
        db.add(vt)

    # Create Batch 2: Pushed to AICTE for review
    b2 = Batch(
        institute_id=inst1.id,
        name="2024-25 Post-Graduate MCA & MBA Batch",
        status="pushed",
        pushed_at=datetime.datetime.now(datetime.timezone.utc),
    )
    db.add(b2)
    db.flush()
    for s in inst1_students[12:20]:
        db.add(StudentBatch(batch_id=b2.id, student_id=s.id))
        db.add(VerificationToken(
            token=f"demo_pushed_{s.id}_{secrets.token_hex(8)}",
            student_id=s.id,
            batch_id=b2.id,
            status="verified",
            expires_at=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=3),
        ))

    db.commit()

    print(f"Seed complete! Generated {db.query(Student).count()} students across {len(institutes)} institutes.")
    print(f"Batches initialized: {db.query(Batch).count()}")
    print(f"Deduplication flags raised: {len(dedup_results)}")
    print(f"Graph fraud clusters flagged: {len(graph_results)}")

    db.close()

if __name__ == "__main__":
    generate_seed_data()

