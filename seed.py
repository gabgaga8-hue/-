"""Seed-данные: категории и предустановленный администратор."""
import hashlib
import os


def hash_password(p: str) -> str:
    return hashlib.sha256(p.encode("utf-8")).hexdigest()


DEFAULT_CATEGORIES = [
    ("Посуда и столовые принадлежности", "Кухонные приборы"),
    ("Чистящие и моющие средства", "Моющее"),
    ("Инвентарь для уборки", "Инвентарь"),
    ("Электроника", "Электротовары"),
    ("Хозяйственные мелочи и ремонт", "Для дома и ремонта"),
    ("Уход за домом и текстилем", "Уход за домом"),
    ("Сад и дача", "Сад и дача"),
    ("Уход за обувью и одеждой", "Уход за вещами"),
    ("Прочее", "Прочие товары"),
]

# Пароль админа можно переопределить через переменную окружения ADMIN_PASSWORD
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")


def ensure_seed(cur, conn) -> None:
    """Заполняет категории и создаёт главного администратора, если их нет."""
    cur.execute("SELECT COUNT(*) FROM Product_categories")
    row = cur.fetchone()
    count = row[0] if not isinstance(row, dict) else list(row.values())[0]
    if count == 0:
        cur.executemany(
            "INSERT INTO Product_categories(name, description) VALUES (%s,%s)",
            DEFAULT_CATEGORIES,
        )
        conn.commit()

    cur.execute("SELECT COUNT(*) FROM users")
    row = cur.fetchone()
    count = row[0] if not isinstance(row, dict) else list(row.values())[0]
    if count == 0:
        cur.execute(
            "INSERT INTO users(login, email, phone, full_name, password_hash, "
            "role, is_active) VALUES (%s,%s,%s,%s,%s,%s,1)",
            ("admin", "admin@shop.local", "+70000000000", "Администратор",
             hash_password(ADMIN_PASSWORD), "Администратор"),
        )
        conn.commit()
        print("=" * 60)
        print("Создан главный администратор:")
        print(f"  login: admin / password: {ADMIN_PASSWORD}")
        print("=" * 60)
