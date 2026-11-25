"""Вспомогательные утилиты для тестов."""
from unittest.mock import MagicMock


def make_fake_db(fetch_all=None, fetch_one=None, execute=None):
    """
    Создаёт мок Database с настраиваемыми методами.
    """
    db = MagicMock()
    db.fetch_all = MagicMock(return_value=fetch_all or [])
    db.fetch_one = MagicMock(return_value=fetch_one)
    db.execute = MagicMock(return_value=execute or 1)
    db.connect = MagicMock(return_value=MagicMock())
    return db


def make_user(id=1, login="user", email="u@e.com", phone="+79990000000",
              full_name="User Name", role="Продавец", is_active=1):
    return {
        "id": id, "login": login, "email": email, "phone": phone,
        "full_name": full_name, "role": role, "is_active": is_active,
    }


def make_product(id=1, sku="SKU1", name="Товар", category_id=1,
                 category="Кат", price=100, quantity=10,
                 storage_location="A-1", status="active"):
    return {
        "id": id, "sku": sku, "name": name, "category_id": category_id,
        "category": category, "price": price, "quantity": quantity,
        "storage_location": storage_location, "status": status,
    }