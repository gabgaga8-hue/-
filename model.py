import hashlib
import os
import re
import mysql.connector
from mysql.connector import Error
from pathlib import Path

from seed import ensure_seed

# Пароль к MySQL берём из переменной окружения MYSQL_PASSWORD,
# fallback — значение по умолчанию (НЕ храните реальный пароль в коде!)
DB_CONFIG = {
    "host": os.environ.get("MYSQL_HOST", "localhost"),
    "user": os.environ.get("MYSQL_USER", "root"),
    "password": os.environ.get("MYSQL_PASSWORD", "1322568790eewqqA"),
    "database": "MDB",
    "charset": "utf8mb4",
    "autocommit": True,
}

ROLES = ("Администратор", "Кладовщик", "Продавец", "Руководитель магазином")


def hash_password(p: str) -> str:
    return hashlib.sha256(p.encode("utf-8")).hexdigest()


class Database:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._conn = None
        return cls._instance

    def connect(self):
        if self._conn is None or not self._conn.is_connected():
            try:
                self._conn = mysql.connector.connect(**DB_CONFIG)
            except Error as e:
                raise RuntimeError(f"MySQL: {e}")
        return self._conn

    def fetch_all(self, sql, params=()):
        cur = self.connect().cursor(dictionary=True)
        cur.execute(sql, params)
        rows = cur.fetchall()
        cur.close()
        return rows

    def fetch_one(self, sql, params=()):
        cur = self.connect().cursor(dictionary=True)
        cur.execute(sql, params)
        row = cur.fetchone()
        cur.close()
        return row

    def execute(self, sql, params=()):
        conn = self.connect()
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
        last_id = cur.lastrowid
        cur.close()
        return last_id

    def init_db(self):
        # 1. создать БД, если нет
        root = mysql.connector.connect(
            host=DB_CONFIG["host"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            charset="utf8mb4",
        )
        rc = root.cursor()
        rc.execute(
            f"CREATE DATABASE IF NOT EXISTS `{DB_CONFIG['database']}` "
            f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        root.commit()
        rc.close()
        root.close()

        # 2. создать таблицы из schema.sql
        conn = self.connect()
        cur = conn.cursor()
        schema_path = Path(__file__).with_name("schema.sql")
        for stmt in schema_path.read_text(encoding="utf-8").split(";"):
            stmt = stmt.strip()
            if not stmt:
                continue
            if re.match(r"(?i)^CREATE\s+(DATABASE|SCHEMA)\b", stmt):
                print(f"[schema] пропущено: {stmt}")
                continue
            print(f"[schema] выполняю: {stmt[:70]}")
            cur.execute(stmt)
        conn.commit()
        cur.close()

        # 3. seed: категории + первый админ
        cur = conn.cursor()
        ensure_seed(cur, conn)
        cur.close()


# ---------- Модели-домены ----------
class UserModel:
    EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    PHONE_RE = re.compile(r"^[+\d][\d\s\-()]{6,18}$")

    def __init__(self):
        self.db = Database()

    # Регистрация: Email, ФИО, Login, Телефон + пароль.
    # Аккаунт создаётся "пустым": role=NULL, is_active=0.
    def register(self, login, password, email, phone, full_name):
        login = (login or "").strip()
        email = (email or "").strip()
        phone = (phone or "").strip()
        full_name = (full_name or "").strip()

        if not login:
            raise ValueError("Введите логин")
        if not full_name:
            raise ValueError("Введите ФИО")
        if not self.EMAIL_RE.match(email):
            raise ValueError("Некорректный Email")
        if not self.PHONE_RE.match(phone):
            raise ValueError("Некорректный телефон")
        if len(password or "") < 4:
            raise ValueError("Пароль слишком короткий (мин. 4 символа)")
        if self.db.fetch_one("SELECT id FROM users WHERE login=%s", (login,)):
            raise ValueError(f"Логин '{login}' уже занят")
        if self.db.fetch_one("SELECT id FROM users WHERE email=%s", (email,)):
            raise ValueError(f"Email '{email}' уже занят")

        return self.db.execute(
            "INSERT INTO users(login, email, phone, full_name, password_hash, "
            "role, is_active) VALUES (%s,%s,%s,%s,%s,NULL,0)",
            (login, email, phone, full_name, hash_password(password)),
        )

    # Вход: логин ИЛИ email + пароль. Неактивный аккаунт не пускает.
    def authenticate(self, login_or_email, password):
        u = self.db.fetch_one(
            "SELECT * FROM users WHERE (login=%s OR email=%s)",
            (login_or_email, login_or_email),
        )
        if not u or u["password_hash"] != hash_password(password):
            return None
        if not u["is_active"]:
            raise PermissionError(
                "Аккаунт ожидает активации. Должность выдаёт администратор.")
        return u

    def list_users(self):
        return self.db.fetch_all(
            "SELECT id, login, email, phone, full_name, role, is_active, "
            "created_at FROM users ORDER BY id"
        )

    # Пользователи без должности или неактивные — для окна администратора
    def list_pending(self):
        return self.db.fetch_all(
            "SELECT id, login, email, phone, full_name, role, is_active, "
            "created_at FROM users WHERE role IS NULL OR is_active=0 "
            "ORDER BY created_at"
        )

    # Выдача/смена должности + активация аккаунта
    def assign_role(self, uid, role, is_active=1):
        if role not in ROLES:
            raise ValueError("Неизвестная должность")
        self.db.execute(
            "UPDATE users SET role=%s, is_active=%s WHERE id=%s",
            (role, 1 if is_active else 0, uid),
        )

    def update(self, uid, full_name, role, is_active, password=None):
        if role not in ROLES:
            raise ValueError("Неизвестная должность")
        if password:
            self.db.execute(
                "UPDATE users SET full_name=%s, role=%s, is_active=%s, "
                "password_hash=%s WHERE id=%s",
                (full_name, role, is_active, hash_password(password), uid),
            )
        else:
            self.db.execute(
                "UPDATE users SET full_name=%s, role=%s, is_active=%s "
                "WHERE id=%s",
                (full_name, role, is_active, uid),
            )

    def delete(self, uid):
        u = self.db.fetch_one(
            "SELECT login, role FROM users WHERE id=%s", (uid,)
        )
        if not u:
            return
        if u["login"] == "admin":
            raise ValueError("Нельзя удалить главного администратора")
        self.db.execute("DELETE FROM users WHERE id=%s", (uid,))


class ProductModel:
    def __init__(self):
        self.db = Database()

    def list_products(self):
        return self.db.fetch_all("""
            SELECT p.id, p.sku, p.name, p.category_id,
                   c.name AS category, p.price,
                   p.quantity, p.storage_location, p.status
            FROM Product p
            LEFT JOIN Product_categories c ON c.id = p.category_id
            ORDER BY p.id
        """)

    def get_product(self, pid):
        return self.db.fetch_one("""
            SELECT p.id, p.sku, p.name, p.category_id,
                   c.name AS category, p.price,
                   p.quantity, p.storage_location, p.status
            FROM Product p
            LEFT JOIN Product_categories c ON c.id = p.category_id
            WHERE p.id=%s
        """, (pid,))

    def list_categories(self):
        return self.db.fetch_all(
            "SELECT id, name FROM Product_categories ORDER BY name"
        )

    def _log_movement(self, pid, op, qty, employee_id=None, notes=""):
        self.db.execute(
            "INSERT INTO Inventory_movements(product_id, operation_type, "
            "quantity, employee_id, notes) VALUES (%s,%s,%s,%s,%s)",
            (pid, op, qty, employee_id, notes),
        )

    def add_product(self, sku, name, category_id, price, quantity,
                    storage_location, status="active", employee_id=None):
        new_id = self.db.execute(
            "INSERT INTO Product(sku, name, category_id, price, quantity, "
            "storage_location, status) VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (sku, name, category_id, price, quantity, storage_location, status),
        )
        if quantity:
            self._log_movement(new_id, "in", quantity, employee_id,
                               "Создание товара")
        return new_id

    def update_product(self, pid, sku, name, category_id, price, quantity,
                       storage_location, status, employee_id=None):
        old = self.db.fetch_one(
            "SELECT quantity, storage_location FROM Product WHERE id=%s",
            (pid,),
        )
        self.db.execute("""
            UPDATE Product SET sku=%s, name=%s, category_id=%s, price=%s,
                   quantity=%s, storage_location=%s, status=%s
            WHERE id=%s
        """, (sku, name, category_id, price, quantity,
              storage_location, status, pid))
        if old:
            diff = (quantity or 0) - (old["quantity"] or 0)
            if diff:
                self._log_movement(pid, "adjust", diff, employee_id,
                                   "Корректировка при редактировании")
            if (storage_location or "") != (old["storage_location"] or ""):
                self._log_movement(
                    pid, "move", 0, employee_id,
                    f"Ячейка: {old['storage_location'] or '—'} → "
                    f"{storage_location or '—'}",
                )

    def delete_product(self, pid):
        self.db.execute("DELETE FROM Product WHERE id=%s", (pid,))

    def change_quantity(self, pid, delta, employee_id=None,
                        op="adjust", notes=""):
        row = self.db.fetch_one(
            "SELECT quantity FROM Product WHERE id=%s", (pid,)
        )
        if not row:
            return
        new_qty = max(0, row["quantity"] + delta)
        self.db.execute(
            "UPDATE Product SET quantity=%s WHERE id=%s", (new_qty, pid)
        )
        self.db.execute(
            "INSERT INTO Inventory_movements(product_id, operation_type, "
            "quantity, employee_id, notes) VALUES (%s,%s,%s,%s,%s)",
            (pid, op, delta, employee_id, notes),
        )

    def add_category(self, name, description=""):
        return self.db.execute(
            "INSERT INTO Product_categories(name, description) VALUES (%s,%s)",
            (name, description),
        )


class TaskModel:
    def __init__(self):
        self.db = Database()

    def list_tasks(self):
        return self.db.fetch_all(
            "SELECT id, name, priority, due, description, done "
            "FROM tasks ORDER BY id"
        )

    def add_task(self, name, priority="Средний", due=None,
                 description="", done=False):
        return self.db.execute(
            "INSERT INTO tasks(name, priority, due, description, done) "
            "VALUES (%s,%s,%s,%s,%s)",
            (name, priority, due, description, 1 if done else 0),
        )

    def update_task(self, tid, **kwargs):
        if not kwargs:
            return
        allowed = {"name", "priority", "due", "description", "done"}
        fields, values = [], []
        for k, v in kwargs.items():
            if k not in allowed:
                continue
            if k == "done":
                v = 1 if v else 0
            fields.append(f"{k}=%s")
            values.append(v)
        if not fields:
            return
        values.append(tid)
        self.db.execute(
            f"UPDATE tasks SET {', '.join(fields)} WHERE id=%s", tuple(values)
        )

    def delete_task(self, tid):
        self.db.execute("DELETE FROM tasks WHERE id=%s", (tid,))


class NoteModel:
    def __init__(self):
        self.db = Database()

    def list_notes(self):
        return self.db.fetch_all(
            "SELECT id, title, content, modified FROM notes ORDER BY id"
        )

    def add_note(self, title="Новая заметка", content=""):
        return self.db.execute(
            "INSERT INTO notes(title, content) VALUES (%s,%s)",
            (title, content),
        )

    def update_note(self, nid, title=None, content=None):
        fields, values = [], []
        if title is not None:
            fields.append("title=%s"); values.append(title)
        if content is not None:
            fields.append("content=%s"); values.append(content)
        if not fields:
            return
        values.append(nid)
        self.db.execute(
            f"UPDATE notes SET {', '.join(fields)} WHERE id=%s", tuple(values)
        )

    def delete_note(self, nid):
        self.db.execute("DELETE FROM notes WHERE id=%s", (nid,))
