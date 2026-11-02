"""
Database module for SmartCare AI.
Provides SQLite database initialization, automated schema migrations,
role-based data access (Patients vs Healthcare Providers), medical report tracking,
and secure CRUD operations with parameterized queries.
"""

import sqlite3
import os
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Tuple
import bcrypt

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_PATH = os.path.join(DB_DIR, "smartcare.db")
REPORTS_DIR = os.path.join(DB_DIR, "reports")


def get_connection() -> sqlite3.Connection:
    """Return an active connection to the SQLite database with row factory and foreign keys enabled."""
    os.makedirs(DB_DIR, exist_ok=True)
    os.makedirs(REPORTS_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt with random salt."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Verify a plaintext password against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def init_db():
    """Initialize database tables and run schema migrations if needed."""
    os.makedirs(DB_DIR, exist_ok=True)
    os.makedirs(REPORTS_DIR, exist_ok=True)

    with get_connection() as conn:
        cursor = conn.cursor()

        # 1. System Settings / Metadata (ensures seed runs only once)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS system_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )

        # 2. Users Table (Authentication & RBAC)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('patient', 'provider', 'admin')),
                created_at TEXT NOT NULL
            )
            """
        )

        # 3. Patients Table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS patients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                patient_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                age INTEGER NOT NULL,
                gender TEXT NOT NULL,
                contact TEXT NOT NULL,
                blood_group TEXT DEFAULT 'Unknown',
                registration_date TEXT NOT NULL,
                notes TEXT DEFAULT '',
                is_demo INTEGER DEFAULT 0,
                created_by_provider_id TEXT DEFAULT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
            )
            """
        )

        # Migration check: Ensure user_id, is_demo, created_by_provider_id exist on pre-existing patients table
        cursor.execute("PRAGMA table_info(patients)")
        existing_patient_cols = [c["name"] for c in cursor.fetchall()]
        if "user_id" not in existing_patient_cols:
            cursor.execute("ALTER TABLE patients ADD COLUMN user_id INTEGER DEFAULT NULL")
        if "is_demo" not in existing_patient_cols:
            cursor.execute("ALTER TABLE patients ADD COLUMN is_demo INTEGER DEFAULT 0")
        if "created_by_provider_id" not in existing_patient_cols:
            cursor.execute("ALTER TABLE patients ADD COLUMN created_by_provider_id TEXT DEFAULT NULL")

        # 4. Healthcare Providers Table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS providers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                provider_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                specialty TEXT DEFAULT 'General Medicine',
                contact TEXT NOT NULL,
                license_number TEXT NOT NULL,
                hospital TEXT DEFAULT 'City Medical Center',
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )

        # Migration check: Ensure status and registration_code exist on providers table
        cursor.execute("PRAGMA table_info(providers)")
        existing_provider_cols = [c["name"] for c in cursor.fetchall()]
        if "status" not in existing_provider_cols:
            cursor.execute("ALTER TABLE providers ADD COLUMN status TEXT DEFAULT 'approved'")
        if "registration_code" not in existing_provider_cols:
            cursor.execute("ALTER TABLE providers ADD COLUMN registration_code TEXT DEFAULT ''")

        # 5. Provider-Patient Access Permissions Table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS provider_patient_access (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider_id TEXT NOT NULL,
                patient_id TEXT NOT NULL,
                granted_at TEXT NOT NULL,
                status TEXT DEFAULT 'active' CHECK(status IN ('active', 'revoked')),
                UNIQUE(provider_id, patient_id)
            )
            """
        )

        # 6. Biometric Health Records Table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS health_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT NOT NULL,
                weight_kg REAL NOT NULL,
                height_cm REAL NOT NULL,
                bmi REAL NOT NULL,
                systolic_bp INTEGER NOT NULL,
                diastolic_bp INTEGER NOT NULL,
                blood_glucose REAL NOT NULL,
                glucose_context TEXT NOT NULL DEFAULT 'Random',
                heart_rate INTEGER NOT NULL,
                recording_date TEXT NOT NULL,
                notes TEXT DEFAULT '',
                FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE
            )
            """
        )

        # 7. Uploaded Medical Reports Table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS medical_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT NOT NULL,
                report_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size_kb REAL NOT NULL,
                extracted_text TEXT NOT NULL,
                upload_date TEXT NOT NULL,
                report_type TEXT DEFAULT 'Lab Report',
                summary TEXT DEFAULT '',
                uploaded_by_user_id INTEGER,
                notes TEXT DEFAULT '',
                FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE
            )
            """
        )

        # 8. Anonymized AI Interactions Table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS ai_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                interaction_date TEXT NOT NULL,
                category TEXT NOT NULL
            )
            """
        )

        cursor.execute("PRAGMA table_info(ai_interactions)")
        existing_ai_cols = [c["name"] for c in cursor.fetchall()]
        if "user_id" not in existing_ai_cols:
            cursor.execute("ALTER TABLE ai_interactions ADD COLUMN user_id INTEGER DEFAULT NULL")

        conn.commit()


# ==============================================================================
# AUTHENTICATION & USER MANAGEMENT
# ==============================================================================

def create_user(username: str, email: str, password_plain: str, role: str) -> Optional[int]:
    """Create a new user account with bcrypt password hashing."""
    username = username.strip().lower()
    email = email.strip().lower()
    hashed = hash_password(password_plain)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO users (username, email, password_hash, role, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (username, email, hashed, role, now_str)
            )
            conn.commit()
            return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None  # Username or email already taken


def get_user_by_username_or_email(identifier: str) -> Optional[Dict[str, Any]]:
    """Retrieve user record by username or email."""
    ident = identifier.strip().lower()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE LOWER(username) = ? OR LOWER(email) = ?",
            (ident, ident)
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve user record by user ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (int(user_id),))
        row = cursor.fetchone()
        return dict(row) if row else None


def update_user_password(user_id: int, new_password_plain: str) -> bool:
    """Update user's password with new bcrypt hash."""
    hashed = hash_password(new_password_plain)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hashed, int(user_id)))
        conn.commit()
        return cursor.rowcount > 0


# ==============================================================================
# PATIENT CRUD & ROLE-BASED ACCESS
# ==============================================================================

def generate_patient_id() -> str:
    """Generate next sequential unique patient ID (e.g. SC-1001, SC-1007)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT patient_id FROM patients ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        if row and row["patient_id"]:
            try:
                num = int(row["patient_id"].replace("SC-", ""))
                return f"SC-{num + 1}"
            except ValueError:
                pass
        return "SC-1001"


def add_patient(
    name: str,
    age: int,
    gender: str,
    contact: str,
    blood_group: str = "Unknown",
    registration_date: Optional[str] = None,
    notes: str = "",
    user_id: Optional[int] = None,
    is_demo: int = 0,
    created_by_provider_id: Optional[str] = None
) -> str:
    """Register a new patient and return their unique patient ID with strict input validation."""
    from utils.validators import validate_name, validate_mobile
    
    v_name, err_name, clean_name = validate_name(name, "Patient Name")
    if not v_name:
        raise ValueError(err_name)
    
    v_mob, err_mob, norm_contact = validate_mobile(contact, required=True)
    if not v_mob:
        raise ValueError(err_mob)

    patient_id = generate_patient_id()
    if not registration_date:
        registration_date = date.today().isoformat()

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO patients (
                patient_id, user_id, name, age, gender, contact, blood_group,
                registration_date, notes, is_demo, created_by_provider_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                patient_id, user_id, clean_name, int(age), gender, norm_contact,
                blood_group, registration_date, notes.strip(), is_demo, created_by_provider_id
            )
        )

        # If registered by a provider, grant immediate access to that provider
        if created_by_provider_id:
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                """
                INSERT OR IGNORE INTO provider_patient_access (provider_id, patient_id, granted_at, status)
                VALUES (?, ?, ?, 'active')
                """,
                (created_by_provider_id, patient_id, now_str)
            )

        conn.commit()
    return patient_id


def get_all_patients() -> List[Dict[str, Any]]:
    """Retrieve all registered patients ordered by ID descending."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM patients ORDER BY id DESC")
        return [dict(row) for row in cursor.fetchall()]


def get_patient_by_id(patient_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve patient record by patient ID (case-insensitive)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM patients WHERE LOWER(patient_id) = LOWER(?)", (patient_id.strip(),))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_patient_by_user_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve patient record linked to an authenticated user ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM patients WHERE user_id = ?", (int(user_id),))
        row = cursor.fetchone()
        return dict(row) if row else None


def search_patients(search_term: str, provider_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Search patients by ID, Name, or Contact. If provider_id is specified, filters to authorized patients."""
    term = f"%{search_term.strip()}%"
    with get_connection() as conn:
        cursor = conn.cursor()
        if provider_id:
            cursor.execute(
                """
                SELECT p.* FROM patients p
                INNER JOIN provider_patient_access a ON p.patient_id = a.patient_id
                WHERE a.provider_id = ? AND a.status = 'active'
                AND (p.patient_id LIKE ? OR p.name LIKE ? OR p.contact LIKE ?)
                ORDER BY p.id DESC
                """,
                (provider_id, term, term, term)
            )
        else:
            cursor.execute(
                """
                SELECT * FROM patients 
                WHERE patient_id LIKE ? OR name LIKE ? OR contact LIKE ?
                ORDER BY id DESC
                """,
                (term, term, term)
            )
        return [dict(row) for row in cursor.fetchall()]


def update_patient(
    patient_id: str,
    name: str,
    age: int,
    gender: str,
    contact: str,
    blood_group: str,
    notes: str
) -> bool:
    """Update patient demographic details with strict input validation."""
    from utils.validators import validate_name, validate_mobile
    
    v_name, err_name, clean_name = validate_name(name, "Patient Name")
    if not v_name:
        raise ValueError(err_name)
    
    v_mob, err_mob, norm_contact = validate_mobile(contact, required=True)
    if not v_mob:
        raise ValueError(err_mob)

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE patients
            SET name = ?, age = ?, gender = ?, contact = ?, blood_group = ?, notes = ?
            WHERE LOWER(patient_id) = LOWER(?)
            """,
            (clean_name, int(age), gender, norm_contact, blood_group, notes.strip(), patient_id.strip())
        )
        conn.commit()
        return cursor.rowcount > 0


def delete_patient(patient_id: str) -> bool:
    """
    Permanently delete a patient record and all associated records (health vitals,
    uploaded reports, provider access permissions, and linked user account).
    Executed within an explicit committed transaction to ensure complete cleanup.
    """
    pid = patient_id.strip()
    with get_connection() as conn:
        cursor = conn.cursor()

        # Retrieve linked user_id if any before patient row deletion
        cursor.execute("SELECT user_id FROM patients WHERE LOWER(patient_id) = LOWER(?)", (pid,))
        row = cursor.fetchone()
        linked_user_id = row["user_id"] if row and row["user_id"] else None

        # 1. Delete associated health records
        cursor.execute("DELETE FROM health_records WHERE LOWER(patient_id) = LOWER(?)", (pid,))

        # 2. Delete associated medical reports & clean disk files
        cursor.execute("SELECT file_path FROM medical_reports WHERE LOWER(patient_id) = LOWER(?)", (pid,))
        report_files = cursor.fetchall()
        for r_file in report_files:
            try:
                if r_file["file_path"] and os.path.exists(r_file["file_path"]):
                    os.remove(r_file["file_path"])
            except Exception:
                pass
        cursor.execute("DELETE FROM medical_reports WHERE LOWER(patient_id) = LOWER(?)", (pid,))

        # 3. Delete provider access permissions
        cursor.execute("DELETE FROM provider_patient_access WHERE LOWER(patient_id) = LOWER(?)", (pid,))

        # 4. Delete patient row
        cursor.execute("DELETE FROM patients WHERE LOWER(patient_id) = LOWER(?)", (pid,))
        rows_deleted = cursor.rowcount

        # 5. Delete linked user account if exists
        if linked_user_id:
            cursor.execute("DELETE FROM users WHERE id = ? AND role = 'patient'", (linked_user_id,))

        conn.commit()
        return rows_deleted > 0


def delete_patient_account(user_id: int, password_plain: str) -> Tuple[bool, str]:
    """
    Permanently delete a patient user account and all personal health data.
    Requires password re-authentication.
    Safely cleans up:
      - All uploaded digital PDF report files on disk
      - Associated records in medical_reports, health_records, provider_patient_access, ai_interactions
      - Row in patients table
      - Row in users table
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (int(user_id),))
        u = cursor.fetchone()
        if not u:
            return False, "User account not found."
        
        if not verify_password(password_plain, u["password_hash"]):
            return False, "Incorrect password. Re-authentication failed."
        
        # Locate patient profile
        cursor.execute("SELECT * FROM patients WHERE user_id = ?", (int(user_id),))
        pt = cursor.fetchone()
        
        if pt:
            pid = pt["patient_id"]
            # 1. Clean PDF files from disk
            cursor.execute("SELECT file_path FROM medical_reports WHERE LOWER(patient_id) = LOWER(?)", (pid,))
            report_files = cursor.fetchall()
            for r_file in report_files:
                try:
                    if r_file["file_path"] and os.path.exists(r_file["file_path"]):
                        os.remove(r_file["file_path"])
                except Exception:
                    pass
            
            # 2. Delete database rows
            cursor.execute("DELETE FROM medical_reports WHERE LOWER(patient_id) = LOWER(?)", (pid,))
            cursor.execute("DELETE FROM health_records WHERE LOWER(patient_id) = LOWER(?)", (pid,))
            cursor.execute("DELETE FROM provider_patient_access WHERE LOWER(patient_id) = LOWER(?)", (pid,))
            cursor.execute("DELETE FROM ai_interactions WHERE user_id = ?", (int(user_id),))
            cursor.execute("DELETE FROM patients WHERE id = ?", (pt["id"],))
        
        # 3. Delete user row
        cursor.execute("DELETE FROM users WHERE id = ?", (int(user_id),))
        conn.commit()
        return True, "Your patient account and all personal medical data have been permanently deleted."


# ==============================================================================
# PROVIDERS & PERMISSIONS
# ==============================================================================

def generate_provider_id() -> str:
    """Generate sequential unique provider ID (e.g. DOC-101, DOC-102, ...)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT provider_id FROM providers WHERE provider_id LIKE 'DOC-%'")
        existing = [r["provider_id"] for r in cursor.fetchall()]
        max_id = 100
        for pid in existing:
            try:
                num = int(pid.replace("DOC-", ""))
                if num > max_id:
                    max_id = num
            except (ValueError, IndexError):
                continue
        return f"DOC-{max_id + 1}"


def create_provider(
    user_id: int,
    provider_id: str,
    name: str,
    email: str,
    specialty: str,
    contact: str,
    license_number: str,
    hospital: str = "City Medical Center",
    status: str = "approved",
    registration_code: str = ""
) -> bool:
    """Register a new healthcare provider with controlled status."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO providers (
                user_id, provider_id, name, email, specialty, contact,
                license_number, hospital, created_at, status, registration_code
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, provider_id, name.strip(), email.strip().lower(), specialty.strip(), contact.strip(), license_number.strip(), hospital.strip(), now_str, status, registration_code)
        )
        conn.commit()
        return True


def deactivate_or_delete_provider_account(user_id: int, password_plain: str) -> Tuple[bool, str]:
    """
    Safely deactivate or delete a healthcare provider account.
    Requires password verification.
    
    Medico-Legal Continuity Rule:
    If this provider has enrolled patients or charted patient vitals, those patient records
    must remain intact for clinical continuity and hospital audit requirements.
    Instead of deleting patient charts, the provider account is permanently deactivated:
      - providers.status = 'deactivated'
      - users.password_hash = 'ACCOUNT_DEACTIVATED'
      - users.role = 'deactivated'
      - provider_patient_access status set to 'revoked'
    If the provider has no associated patient charts or access records, the account is completely purged.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (int(user_id),))
        u = cursor.fetchone()
        if not u:
            return False, "Provider account not found."
        
        if not verify_password(password_plain, u["password_hash"]):
            return False, "Incorrect password. Re-authentication failed."
        
        cursor.execute("SELECT * FROM providers WHERE user_id = ?", (int(user_id),))
        doc = cursor.fetchone()
        if not doc:
            cursor.execute("DELETE FROM users WHERE id = ?", (int(user_id),))
            conn.commit()
            return True, "User account removed."
        
        prov_id = doc["provider_id"]
        
        # Check associated patient records
        cursor.execute("SELECT COUNT(*) as count FROM patients WHERE created_by_provider_id = ?", (prov_id,))
        patient_count = cursor.fetchone()["count"]
        
        cursor.execute("SELECT COUNT(*) as count FROM provider_patient_access WHERE provider_id = ?", (prov_id,))
        access_count = cursor.fetchone()["count"]
        
        if patient_count > 0 or access_count > 0:
            cursor.execute(
                """
                UPDATE providers 
                SET status = 'deactivated', hospital = hospital || ' (Deactivated)'
                WHERE user_id = ?
                """,
                (int(user_id),)
            )
            cursor.execute(
                """
                UPDATE provider_patient_access
                SET status = 'revoked'
                WHERE provider_id = ?
                """,
                (prov_id,)
            )
            cursor.execute(
                """
                UPDATE users
                SET password_hash = 'ACCOUNT_DEACTIVATED'
                WHERE id = ?
                """,
                (int(user_id),)
            )
            conn.commit()
            return True, f"Your provider account has been safely deactivated. Associated hospital patient charts ({patient_count}) have been preserved according to clinical data retention policies, and all active access permissions have been revoked."
        else:
            cursor.execute("DELETE FROM provider_patient_access WHERE provider_id = ?", (prov_id,))
            cursor.execute("DELETE FROM providers WHERE id = ?", (doc["id"],))
            cursor.execute("DELETE FROM users WHERE id = ?", (int(user_id),))
            conn.commit()
            return True, "Your provider account has been completely purged and deleted from the registry."


def get_provider_by_user_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve provider record by user ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM providers WHERE user_id = ?", (int(user_id),))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_provider_by_id(provider_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve provider record by provider ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM providers WHERE provider_id = ?", (provider_id.strip(),))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_patients_for_provider(provider_id: str) -> List[Dict[str, Any]]:
    """Retrieve all patients an authorized healthcare provider has permission to view."""
    with get_connection() as conn:
        cursor = conn.cursor()
        # Verify provider status is approved
        cursor.execute("SELECT status FROM providers WHERE provider_id = ?", (provider_id.strip(),))
        p_row = cursor.fetchone()
        if not p_row or p_row["status"] != "approved":
            return []

        cursor.execute(
            """
            SELECT p.* FROM patients p
            INNER JOIN provider_patient_access a ON p.patient_id = a.patient_id
            WHERE a.provider_id = ? AND a.status = 'active'
            ORDER BY p.id DESC
            """,
            (provider_id.strip(),)
        )
        return [dict(row) for row in cursor.fetchall()]


def check_provider_has_patient_access(provider_id: str, patient_id: str) -> bool:
    """Check if an approved provider is authorized to access a given patient's records."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM providers WHERE provider_id = ?", (provider_id.strip(),))
        p_row = cursor.fetchone()
        if not p_row or p_row["status"] != "approved":
            return False

        cursor.execute(
            """
            SELECT id FROM provider_patient_access 
            WHERE provider_id = ? AND LOWER(patient_id) = LOWER(?) AND status = 'active'
            """,
            (provider_id.strip(), patient_id.strip())
        )
        return cursor.fetchone() is not None


has_provider_access = check_provider_has_patient_access


def grant_provider_access(provider_id: str, patient_id: str) -> bool:
    """Grant an authorized healthcare provider access to a patient record."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO provider_patient_access (provider_id, patient_id, granted_at, status)
            VALUES (?, ?, ?, 'active')
            """,
            (provider_id.strip(), patient_id.strip(), now_str)
        )
        conn.commit()
        return True


# ==============================================================================
# BIOMETRIC HEALTH RECORDS CRUD
# ==============================================================================

def calculate_bmi(weight_kg: float, height_cm: float) -> float:
    """Calculate Body Mass Index (BMI)."""
    if height_cm <= 0:
        return 0.0
    height_m = height_cm / 100.0
    return round(weight_kg / (height_m * height_m), 1)


def add_health_record(
    patient_id: str,
    weight_kg: float,
    height_cm: float,
    systolic_bp: int,
    diastolic_bp: int,
    blood_glucose: float,
    glucose_context: str,
    heart_rate: int,
    recording_date: Optional[str] = None,
    notes: str = ""
) -> int:
    """Insert a new biometric measurement record with strict physiological validation."""
    from utils.validators import validate_vitals_input
    
    rec_d = date.fromisoformat(recording_date) if recording_date else date.today()
    v_vitals, err_vitals = validate_vitals_input(
        float(weight_kg), float(height_cm), int(systolic_bp), int(diastolic_bp),
        float(blood_glucose), int(heart_rate), rec_d
    )
    if not v_vitals:
        raise ValueError(err_vitals)

    if not recording_date:
        recording_date = date.today().isoformat()

    bmi = calculate_bmi(weight_kg, height_cm)

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO health_records (
                patient_id, weight_kg, height_cm, bmi, systolic_bp, diastolic_bp,
                blood_glucose, glucose_context, heart_rate, recording_date, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                patient_id.strip(),
                float(weight_kg),
                float(height_cm),
                float(bmi),
                int(systolic_bp),
                int(diastolic_bp),
                float(blood_glucose),
                glucose_context.strip(),
                int(heart_rate),
                recording_date,
                notes.strip()
            )
        )
        conn.commit()
        return cursor.lastrowid


def get_health_records(
    patient_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    provider_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Retrieve health records with optional patient ID, provider authorization, and date filtering."""
    if provider_id:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM providers WHERE provider_id = ?", (provider_id.strip(),))
            p_status = cursor.fetchone()
            if not p_status or p_status["status"] != "approved":
                return []

    params = []
    
    if provider_id and not patient_id:
        query = """
            SELECT r.*, p.name as patient_name, p.gender, p.age
            FROM health_records r
            INNER JOIN provider_patient_access a ON r.patient_id = a.patient_id
            LEFT JOIN patients p ON r.patient_id = p.patient_id
            WHERE a.provider_id = ? AND a.status = 'active'
        """
        params.append(provider_id.strip())
    else:
        query = """
            SELECT r.*, p.name as patient_name, p.gender, p.age
            FROM health_records r
            LEFT JOIN patients p ON r.patient_id = p.patient_id
            WHERE 1=1
        """

    if patient_id:
        query += " AND LOWER(r.patient_id) = LOWER(?)"
        params.append(patient_id.strip())

    if start_date:
        query += " AND r.recording_date >= ?"
        params.append(start_date)

    if end_date:
        query += " AND r.recording_date <= ?"
        params.append(end_date)

    query += " ORDER BY r.recording_date DESC, r.id DESC"

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, tuple(params))
        return [dict(row) for row in cursor.fetchall()]


def delete_health_record(record_id: int, patient_id: Optional[str] = None) -> bool:
    """Delete an individual health record by primary key, optionally scoped to patient_id."""
    with get_connection() as conn:
        cursor = conn.cursor()
        if patient_id:
            cursor.execute(
                "DELETE FROM health_records WHERE id = ? AND LOWER(patient_id) = LOWER(?)",
                (int(record_id), patient_id.strip())
            )
        else:
            cursor.execute("DELETE FROM health_records WHERE id = ?", (int(record_id),))
        conn.commit()
        return cursor.rowcount > 0


# ==============================================================================
# MEDICAL REPORTS MANAGEMENT (PDF STORAGE & EXTRACTION METADATA)
# ==============================================================================

def add_medical_report(
    patient_id: str,
    report_name: str,
    file_path: str,
    file_size_kb: float,
    extracted_text: str,
    report_type: str = "Lab Report",
    uploaded_by_user_id: Optional[int] = None,
    notes: str = ""
) -> int:
    """Save an uploaded medical report metadata record."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO medical_reports (
                patient_id, report_name, file_path, file_size_kb, extracted_text,
                upload_date, report_type, uploaded_by_user_id, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                patient_id.strip(),
                report_name.strip(),
                file_path,
                float(file_size_kb),
                extracted_text,
                now_str,
                report_type,
                uploaded_by_user_id,
                notes.strip()
            )
        )
        conn.commit()
        return cursor.lastrowid


def get_medical_reports(
    patient_id: Optional[str] = None,
    provider_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Retrieve medical reports for a patient or all authorized reports for a provider."""
    if provider_id:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM providers WHERE provider_id = ?", (provider_id.strip(),))
            p_status = cursor.fetchone()
            if not p_status or p_status["status"] != "approved":
                return []

    with get_connection() as conn:
        cursor = conn.cursor()
        if patient_id and provider_id:
            cursor.execute(
                """
                SELECT r.*, p.name as patient_name
                FROM medical_reports r
                INNER JOIN provider_patient_access a ON r.patient_id = a.patient_id
                LEFT JOIN patients p ON r.patient_id = p.patient_id
                WHERE a.provider_id = ? AND a.status = 'active' AND LOWER(r.patient_id) = LOWER(?)
                ORDER BY r.id DESC
                """,
                (provider_id.strip(), patient_id.strip())
            )
        elif patient_id:
            cursor.execute(
                """
                SELECT r.*, p.name as patient_name
                FROM medical_reports r
                LEFT JOIN patients p ON r.patient_id = p.patient_id
                WHERE LOWER(r.patient_id) = LOWER(?)
                ORDER BY r.id DESC
                """,
                (patient_id.strip(),)
            )
        elif provider_id:
            cursor.execute(
                """
                SELECT r.*, p.name as patient_name
                FROM medical_reports r
                INNER JOIN provider_patient_access a ON r.patient_id = a.patient_id
                LEFT JOIN patients p ON r.patient_id = p.patient_id
                WHERE a.provider_id = ? AND a.status = 'active'
                ORDER BY r.id DESC
                """,
                (provider_id.strip(),)
            )
        else:
            cursor.execute(
                """
                SELECT r.*, p.name as patient_name
                FROM medical_reports r
                LEFT JOIN patients p ON r.patient_id = p.patient_id
                ORDER BY r.id DESC
                """
            )
        return [dict(row) for row in cursor.fetchall()]


def get_report_by_id(report_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve an individual medical report by primary key."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM medical_reports WHERE id = ?", (int(report_id),))
        row = cursor.fetchone()
        return dict(row) if row else None


def update_report_summary(report_id: int, summary_text: str) -> bool:
    """Save an AI-generated summary to a medical report record."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE medical_reports SET summary = ? WHERE id = ?",
            (summary_text.strip(), int(report_id))
        )
        conn.commit()
        return cursor.rowcount > 0


def delete_medical_report(report_id: int, patient_id: Optional[str] = None) -> bool:
    """Delete a medical report record and its file on disk, optionally verifying patient ownership."""
    with get_connection() as conn:
        cursor = conn.cursor()
        if patient_id:
            cursor.execute(
                "SELECT file_path FROM medical_reports WHERE id = ? AND LOWER(patient_id) = LOWER(?)",
                (int(report_id), patient_id.strip())
            )
        else:
            cursor.execute("SELECT file_path FROM medical_reports WHERE id = ?", (int(report_id),))
        
        row = cursor.fetchone()
        if not row:
            return False  # Record not found or does not belong to specified patient

        if row["file_path"] and os.path.exists(row["file_path"]):
            try:
                os.remove(row["file_path"])
            except Exception:
                pass

        if patient_id:
            cursor.execute(
                "DELETE FROM medical_reports WHERE id = ? AND LOWER(patient_id) = LOWER(?)",
                (int(report_id), patient_id.strip())
            )
        else:
            cursor.execute("DELETE FROM medical_reports WHERE id = ?", (int(report_id),))
        
        conn.commit()
        return cursor.rowcount > 0


# ==============================================================================
# AI INTERACTIONS & DASHBOARDS METRICS
# ==============================================================================

def log_ai_interaction(category: str = "General Health", user_id: Optional[int] = None):
    """Log an interaction timestamp and broad topic without recording sensitive personal queries."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO ai_interactions (user_id, interaction_date, category) VALUES (?, ?, ?)",
            (user_id, now_str, category)
        )
        conn.commit()


def get_dashboard_metrics(provider_id: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve aggregate metrics for executive and provider dashboards."""
    with get_connection() as conn:
        cursor = conn.cursor()

        if provider_id:
            cursor.execute("SELECT status FROM providers WHERE provider_id = ?", (provider_id.strip(),))
            p_status = cursor.fetchone()
            if not p_status or p_status["status"] != "approved":
                return {
                    "total_patients": 0,
                    "total_records": 0,
                    "total_reports": 0,
                    "total_ai_consultations": 0,
                    "recent_patients": [],
                    "recent_records": [],
                    "recent_interactions": []
                }

            cursor.execute(
                """
                SELECT COUNT(DISTINCT p.id) as count FROM patients p
                INNER JOIN provider_patient_access a ON p.patient_id = a.patient_id
                WHERE a.provider_id = ? AND a.status = 'active'
                """,
                (provider_id,)
            )
            total_patients = cursor.fetchone()["count"]

            cursor.execute(
                """
                SELECT COUNT(*) as count FROM health_records r
                INNER JOIN provider_patient_access a ON r.patient_id = a.patient_id
                WHERE a.provider_id = ? AND a.status = 'active'
                """,
                (provider_id,)
            )
            total_records = cursor.fetchone()["count"]

            cursor.execute(
                """
                SELECT COUNT(*) as count FROM medical_reports r
                INNER JOIN provider_patient_access a ON r.patient_id = a.patient_id
                WHERE a.provider_id = ? AND a.status = 'active'
                """,
                (provider_id,)
            )
            total_reports = cursor.fetchone()["count"]

            cursor.execute(
                """
                SELECT p.* FROM patients p
                INNER JOIN provider_patient_access a ON p.patient_id = a.patient_id
                WHERE a.provider_id = ? AND a.status = 'active'
                ORDER BY p.id DESC LIMIT 5
                """,
                (provider_id,)
            )
            recent_patients = [dict(row) for row in cursor.fetchall()]

            cursor.execute(
                """
                SELECT r.*, p.name as patient_name FROM health_records r
                INNER JOIN provider_patient_access a ON r.patient_id = a.patient_id
                LEFT JOIN patients p ON r.patient_id = p.patient_id
                WHERE a.provider_id = ? AND a.status = 'active'
                ORDER BY r.recording_date DESC, r.id DESC LIMIT 5
                """,
                (provider_id,)
            )
            recent_records = [dict(row) for row in cursor.fetchall()]
        else:
            cursor.execute("SELECT COUNT(*) as count FROM patients")
            total_patients = cursor.fetchone()["count"]

            cursor.execute("SELECT COUNT(*) as count FROM health_records")
            total_records = cursor.fetchone()["count"]

            cursor.execute("SELECT COUNT(*) as count FROM medical_reports")
            total_reports = cursor.fetchone()["count"]

            cursor.execute("SELECT * FROM patients ORDER BY id DESC LIMIT 5")
            recent_patients = [dict(row) for row in cursor.fetchall()]

            cursor.execute(
                """
                SELECT r.*, p.name as patient_name FROM health_records r
                LEFT JOIN patients p ON r.patient_id = p.patient_id
                ORDER BY r.recording_date DESC, r.id DESC LIMIT 5
                """
            )
            recent_records = [dict(row) for row in cursor.fetchall()]

        cursor.execute("SELECT COUNT(*) as count FROM ai_interactions")
        total_ai_consultations = cursor.fetchone()["count"]

        cursor.execute("SELECT * FROM ai_interactions ORDER BY id DESC LIMIT 5")
        recent_interactions = [dict(row) for row in cursor.fetchall()]

    return {
        "total_patients": total_patients,
        "total_records": total_records,
        "total_reports": total_reports,
        "total_ai_consultations": total_ai_consultations,
        "recent_patients": recent_patients,
        "recent_records": recent_records,
        "recent_interactions": recent_interactions,
    }


def get_patient_dashboard_metrics(patient_id: str) -> Dict[str, Any]:
    """Retrieve personalized metrics for a single patient's dashboard."""
    pid = patient_id.strip()
    with get_connection() as conn:
        cursor = conn.cursor()

        # Latest vitals
        cursor.execute(
            """
            SELECT * FROM health_records 
            WHERE LOWER(patient_id) = LOWER(?)
            ORDER BY recording_date DESC, id DESC LIMIT 1
            """,
            (pid,)
        )
        latest_vital_row = cursor.fetchone()
        latest_vital = dict(latest_vital_row) if latest_vital_row else None

        # Total vitals count
        cursor.execute("SELECT COUNT(*) as count FROM health_records WHERE LOWER(patient_id) = LOWER(?)", (pid,))
        total_vitals = cursor.fetchone()["count"]

        # Total reports count & recent reports
        cursor.execute("SELECT COUNT(*) as count FROM medical_reports WHERE LOWER(patient_id) = LOWER(?)", (pid,))
        total_reports = cursor.fetchone()["count"]

        cursor.execute(
            """
            SELECT * FROM medical_reports 
            WHERE LOWER(patient_id) = LOWER(?)
            ORDER BY id DESC LIMIT 4
            """,
            (pid,)
        )
        recent_reports = [dict(row) for row in cursor.fetchall()]

        # All records for charting
        cursor.execute(
            """
            SELECT * FROM health_records 
            WHERE LOWER(patient_id) = LOWER(?)
            ORDER BY recording_date ASC, id ASC
            """,
            (pid,)
        )
        all_vitals = [dict(row) for row in cursor.fetchall()]

    return {
        "latest_vital": latest_vital,
        "total_vitals": total_vitals,
        "total_reports": total_reports,
        "recent_reports": recent_reports,
        "all_vitals": all_vitals
    }


# ==============================================================================
# SEED INITIAL DEMO DATA (RUNS ONLY ONCE EVER)
# ==============================================================================

def seed_sample_data():
    """
    Populate database with initial demo accounts and fictional patient records ONCE.
    Uses system_settings to record that seeding has occurred, so deleted patients
    are NEVER resurrected on application restarts.
    """
    init_db()

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM system_settings WHERE key = 'seed_data_initialized'")
        row = cursor.fetchone()
        if row and row["value"] == "1":
            return  # Seeding has already been completed; never re-insert deleted records!

    # 1. Create Demo Provider Account
    # Username: dr.sharma | Email: dr.sharma@smartcare.ai | Password: Provider@123
    provider_user_id = create_user(
        username="dr.sharma",
        email="dr.sharma@smartcare.ai",
        password_plain="Provider@123",
        role="provider"
    )
    if not provider_user_id:
        existing_doc = get_user_by_username_or_email("dr.sharma")
        if existing_doc:
            provider_user_id = existing_doc["id"]

    if provider_user_id:
        if not get_provider_by_id("DOC-101"):
            create_provider(
                user_id=provider_user_id,
                provider_id="DOC-101",
                name="Dr. Ramesh Sharma, MD",
                email="dr.sharma@smartcare.ai",
                specialty="Internal Medicine & Preventive Cardiology",
                contact="+91 98111 22233",
                license_number="MCI-REG-2024-9081",
                hospital="SmartCare Apex Healthcare Center"
            )

    # 2. Create Demo Patient Account
    # Username: aarav | Email: aarav.sharma@example.com | Password: Patient@123
    patient_user_id = create_user(
        username="aarav",
        email="aarav.sharma@example.com",
        password_plain="Patient@123",
        role="patient"
    )
    if not patient_user_id:
        existing_aarav = get_user_by_username_or_email("aarav")
        if existing_aarav:
            patient_user_id = existing_aarav["id"]

    # Check existing patients
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM patients")
        existing_patients_count = cursor.fetchone()["count"]

    if existing_patients_count == 0:
        # Insert initial fictional patients marked as is_demo=1
        p1 = add_patient("Aarav Sharma", 32, "Male", "+91 98765 43210", "B+", "2026-10-15", "Routine wellness monitoring", user_id=patient_user_id, is_demo=1, created_by_provider_id="DOC-101")
        p2 = add_patient("Priya Patel", 28, "Female", "+91 98123 45678", "O+", "2026-10-18", "Pre-marathon fitness monitoring", is_demo=1, created_by_provider_id="DOC-101")
        p3 = add_patient("Rajesh Kumar", 54, "Male", "+91 97654 32109", "A+", "2026-10-20", "Monitoring blood pressure trends", is_demo=1, created_by_provider_id="DOC-101")
        p4 = add_patient("Ananya Sen", 41, "Female", "+91 96543 21098", "AB+", "2026-10-25", "Post-dietary lifestyle tracking", is_demo=1, created_by_provider_id="DOC-101")

        # Initial vitals records
        add_health_record(p1, 74.5, 175.0, 118, 78, 92.0, "Fasting", 72, "2026-10-15", "Normal baseline readings")
        add_health_record(p1, 74.0, 175.0, 120, 80, 95.0, "Fasting", 70, "2026-10-22", "Follow-up checkup")
        add_health_record(p1, 73.5, 175.0, 116, 76, 90.0, "Fasting", 68, "2026-10-29", "Improved vitals after hydration plan")

        add_health_record(p2, 58.0, 162.0, 112, 74, 88.0, "Fasting", 64, "2026-10-18", "Athletic training vitals")
        add_health_record(p2, 57.5, 162.0, 110, 72, 94.0, "Post-Prandial", 65, "2026-10-26", "Post-workout meal check")

        add_health_record(p3, 85.0, 170.0, 138, 88, 115.0, "Fasting", 82, "2026-10-20", "Mild elevation observed")
        add_health_record(p3, 84.2, 170.0, 132, 85, 108.0, "Fasting", 78, "2026-10-27", "Vitals after reducing sodium intake")

        add_health_record(p4, 66.0, 165.0, 122, 80, 102.0, "Random", 75, "2026-10-25", "Standard afternoon vitals")
    else:
        # Existing patients found in database (preserve user-created SC-1005, SC-1006, etc.)
        # Link aarav user to SC-1001 if SC-1001 exists and has no user_id
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE patients SET user_id = ? WHERE patient_id = 'SC-1001' AND (user_id IS NULL OR user_id = 0)", (patient_user_id,))
            cursor.execute("SELECT patient_id FROM patients")
            all_pids = [r["patient_id"] for r in cursor.fetchall()]
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for pid in all_pids:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO provider_patient_access (provider_id, patient_id, granted_at, status)
                    VALUES (?, ?, ?, 'active')
                    """,
                    ("DOC-101", pid, now_str)
                )
            conn.commit()

    # Create a sample demo medical report for patient SC-1001
    sample_report_text = (
        "SmartCare Apex Diagnostics • Comprehensive Metabolic & Lipid Profile\n"
        "Patient ID: SC-1001 | Patient Name: Aarav Sharma | Age: 32 | Gender: Male\n"
        "Sample Date: 2026-10-22 | Reporting Date: 2026-10-23\n\n"
        "TEST INVESTIGATION                   RESULT     UNIT       REFERENCE RANGE\n"
        "---------------------------------------------------------------------------\n"
        "Fasting Plasma Glucose (FBS)        95.0       mg/dL      70.0 - 99.0      (NORMAL)\n"
        "Glycated Hemoglobin (HbA1c)         5.4        %          4.0 - 5.6        (NORMAL)\n"
        "Total Serum Cholesterol             185.0      mg/dL      < 200.0          (DESIRABLE)\n"
        "HDL Cholesterol (Good)              52.0       mg/dL      > 40.0           (NORMAL)\n"
        "LDL Cholesterol (Calculated)        112.0      mg/dL      < 100.0          (BORDERLINE HIGH)\n"
        "Serum Triglycerides                 110.0      mg/dL      < 150.0          (NORMAL)\n"
        "Serum Creatinine                    0.9        mg/dL      0.7 - 1.2        (NORMAL)\n"
        "Estimated GFR                       > 90       mL/min     > 90             (NORMAL)\n"
        "Blood Urea Nitrogen (BUN)           14.0       mg/dL      7.0 - 20.0       (NORMAL)\n"
        "Serum Bilirubin (Total)             0.8        mg/dL      0.2 - 1.2        (NORMAL)\n\n"
        "CLINICAL INTERPRETATION NOTE:\n"
        "Metabolic parameters within healthy baseline ranges. Borderline LDL noted; dietary fiber\n"
        "enhancement and regular cardiovascular aerobic exercise recommended for routine follow-up."
    )
    demo_pdf_path = os.path.join(REPORTS_DIR, "SC-1001_Comprehensive_Metabolic_Report.txt")
    with open(demo_pdf_path, "w", encoding="utf-8") as f:
        f.write(sample_report_text)

    add_medical_report(
        patient_id="SC-1001",
        report_name="Comprehensive Metabolic & Lipid Panel.pdf",
        file_path=demo_pdf_path,
        file_size_kb=4.2,
        extracted_text=sample_report_text,
        report_type="Biochemical Lab Panel",
        uploaded_by_user_id=patient_user_id,
        notes="Annual wellness executive screening panel"
    )

    # Initial AI interactions log
    log_ai_interaction("Understanding Blood Pressure Ranges")
    log_ai_interaction("Healthy Hydration & Sleep Habits")
    log_ai_interaction("General Guidance on Dietary Fiber")
    log_ai_interaction("Questions to Ask Your Doctor About Cholesterol")
    log_ai_interaction("Interpreting Complete Blood Count Reference Ranges")

    # Mark seed data as completed in system_settings
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO system_settings (key, value) VALUES ('seed_data_initialized', '1')"
        )
        conn.commit()
