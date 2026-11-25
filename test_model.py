"""Тесты моделей. БД мокается, чтобы не требовать MySQL."""
import unittest
from unittest.mock import patch, MagicMock

from model import (
    UserModel, ProductModel, TaskModel, NoteModel,
    hash_password, ROLES,
)
from conftest_helpers import make_fake_db, make_user


# ============================================================
#  hash_password
# ============================================================
class TestHashPassword(unittest.TestCase):
    def test_deterministic(self):
        self.assertEqual(hash_password("abc"), hash_password("abc"))

    def test_different_input(self):
        self.assertNotEqual(hash_password("abc"), hash_password("abd"))

    def test_sha256_length(self):
        self.assertEqual(len(hash_password("x")), 64)


# ============================================================
#  UserModel
# ============================================================
class TestUserModel(unittest.TestCase):
    def setUp(self):
        patcher = patch("model.Database")
        self.mock_db_cls = patcher.start()
        self.addCleanup(patcher.stop)
        self.db_instance = make_fake_db()
        self.mock_db_cls.return_value = self.db_instance
        self.model = UserModel()

    # ---- register ----
    def test_register_ok(self):
        self.db_instance.fetch_one.side_effect = [None, None]  # login, email free
        self.db_instance.execute.return_value = 42
        uid = self.model.register(
            login="new", password="1234", email="n@e.com",
            phone="+79991112233", full_name="New User")
        self.assertEqual(uid, 42)
        self.db_instance.execute.assert_called_once()
        sql = self.db_instance.execute.call_args[0][0]
        self.assertIn("INSERT INTO users", sql)

    def test_register_empty_login(self):
        with self.assertRaises(ValueError) as ctx:
            self.model.register("", "1234", "a@b.com", "+79991112233", "F")
        self.assertIn("логин", str(ctx.exception).lower())

    def test_register_empty_full_name(self):
        with self.assertRaises(ValueError):
            self.model.register("l", "1234", "a@b.com", "+79991112233", "")

    def test_register_bad_email(self):
        with self.assertRaises(ValueError):
            self.model.register("l", "1234", "no-at-sign", "+79991112233", "F")

    def test_register_bad_phone(self):
        with self.assertRaises(ValueError):
            self.model.register("l", "1234", "a@b.com", "abc", "F")

    def test_register_short_password(self):
        with self.assertRaises(ValueError):
            self.model.register("l", "1", "a@b.com", "+79991112233", "F")

    def test_register_duplicate_login(self):
        self.db_instance.fetch_one.side_effect = [{"id": 1}, None]
        with self.assertRaises(ValueError) as ctx:
            self.model.register("dup", "1234", "a@b.com",
                                "+79991112233", "F")
        self.assertIn("уже занят", str(ctx.exception))

    def test_register_duplicate_email(self):
        self.db_instance.fetch_one.side_effect = [None, {"id": 1}]
        with self.assertRaises(ValueError) as ctx:
            self.model.register("l", "1234", "a@b.com",
                                "+79991112233", "F")
        self.assertIn("Email", str(ctx.exception))

    # ---- authenticate ----
    def test_auth_ok(self):
        user = make_user()
        user["password_hash"] = hash_password("pass")
        self.db_instance.fetch_one.return_value = user
        result = self.model.authenticate("user", "pass")
        self.assertEqual(result["login"], "user")

    def test_auth_wrong_password(self):
        user = make_user()
        user["password_hash"] = hash_password("pass")
        self.db_instance.fetch_one.return_value = user
        self.assertIsNone(self.model.authenticate("user", "wrong"))

    def test_auth_user_not_found(self):
        self.db_instance.fetch_one.return_value = None
        self.assertIsNone(self.model.authenticate("ghost", "x"))

    def test_auth_inactive_raises(self):
        user = make_user(is_active=0)
        user["password_hash"] = hash_password("pass")
        self.db_instance.fetch_one.return_value = user
        with self.assertRaises(PermissionError):
            self.model.authenticate("user", "pass")

    # ---- assign_role ----
    def test_assign_role_ok(self):
        self.model.assign_role(1, "Администратор", is_active=1)
        self.db_instance.execute.assert_called_once()
        sql = self.db_instance.execute.call_args[0][0]
        self.assertIn("UPDATE users SET role", sql)

    def test_assign_role_invalid(self):
        with self.assertRaises(ValueError):
            self.model.assign_role(1, "Несуществующая роль")

    def test_assign_role_all_roles(self):
        for role in ROLES:
            self.model.assign_role(1, role)
        self.assertEqual(self.db_instance.execute.call_count, len(ROLES))

    # ---- update ----
    def test_update_without_password(self):
        self.model.update(1, "Name", "Продавец", 1)
        sql = self.db_instance.execute.call_args[0][0]
        self.assertNotIn("password_hash", sql)

    def test_update_with_password(self):
        self.model.update(1, "Name", "Продавец", 1, password="new")
        sql = self.db_instance.execute.call_args[0][0]
        self.assertIn("password_hash", sql)

    def test_update_invalid_role(self):
        with self.assertRaises(ValueError):
            self.model.update(1, "Name", "Bad", 1)

    # ---- delete ----
    def test_delete_admin_protected(self):
        self.db_instance.fetch_one.return_value = {"login": "admin",
                                                   "role": "Администратор"}
        with self.assertRaises(ValueError):
            self.model.delete(1)

    def test_delete_ok(self):
        self.db_instance.fetch_one.return_value = {"login": "user",
                                                   "role": "Продавец"}
        self.model.delete(2)
        self.db_instance.execute.assert_called_with(
            "DELETE FROM users WHERE id=%s", (2,))

    def test_delete_not_found(self):
        self.db_instance.fetch_one.return_value = None
        self.model.delete(999)
        self.db_instance.execute.assert_not_called()

    # ---- list ----
    def test_list_pending(self):
        self.model.list_pending()
        sql = self.db_instance.fetch_all.call_args[0][0]
        self.assertIn("role IS NULL OR is_active=0", sql)


# ============================================================
#  ProductModel
# ============================================================
class TestProductModel(unittest.TestCase):
    def setUp(self):
        patcher = patch("model.Database")
        self.mock_db_cls = patcher.start()
        self.addCleanup(patcher.stop)
        self.db_instance = make_fake_db()
        self.mock_db_cls.return_value = self.db_instance
        self.model = ProductModel()

    def test_list_products(self):
        self.model.list_products()
        sql = self.db_instance.fetch_all.call_args[0][0]
        self.assertIn("FROM Product", sql)
        self.assertIn("LEFT JOIN Product_categories", sql)

    def test_get_product(self):
        self.model.get_product(5)
        self.db_instance.fetch_one.assert_called_once()
        self.assertEqual(self.db_instance.fetch_one.call_args[0][1], (5,))

    def test_add_product_with_quantity(self):
        self.db_instance.execute.return_value = 7
        new_id = self.model.add_product(
            "SKU", "Name", 1, 100, 5, "A-1", "active", employee_id=2)
        self.assertEqual(new_id, 7)
        # INSERT + INSERT в movements
        self.assertEqual(self.db_instance.execute.call_count, 2)
        self.assertIn("Inventory_movements",
                      self.db_instance.execute.call_args_list[1][0][0])

    def test_add_product_zero_quantity_no_movement(self):
        self.db_instance.execute.return_value = 7
        self.model.add_product("SKU", "Name", 1, 100, 0, "A-1", "active")
        self.assertEqual(self.db_instance.execute.call_count, 1)

    def test_update_product_logs_diff(self):
        self.db_instance.fetch_one.return_value = {
            "quantity": 10, "storage_location": "A-1"}
        self.model.update_product(1, "SKU", "Name", 1, 100, 15, "A-1",
                                  "active", employee_id=2)
        # UPDATE + log adjust (quantity diff)
        self.assertEqual(self.db_instance.execute.call_count, 2)
        log_sql = self.db_instance.execute.call_args_list[1][0][0]
        self.assertIn("Inventory_movements", log_sql)

    def test_update_product_logs_move(self):
        self.db_instance.fetch_one.return_value = {
            "quantity": 10, "storage_location": "A-1"}
        self.model.update_product(1, "SKU", "Name", 1, 100, 10, "B-2",
                                  "active", employee_id=2)
        # UPDATE + log move
        self.assertEqual(self.db_instance.execute.call_count, 2)
        log_sql = self.db_instance.execute.call_args_list[1][0][0]
        self.assertIn("move", log_sql)

    def test_update_product_no_changes(self):
        self.db_instance.fetch_one.return_value = {
            "quantity": 10, "storage_location": "A-1"}
        self.model.update_product(1, "SKU", "Name", 1, 100, 10, "A-1",
                                  "active")
        # только UPDATE
        self.assertEqual(self.db_instance.execute.call_count, 1)

    def test_change_quantity_positive(self):
        self.db_instance.fetch_one.return_value = {"quantity": 5}
        self.model.change_quantity(1, 10, employee_id=2)
        upd = self.db_instance.execute.call_args_list[0]
        self.assertIn("UPDATE Product", upd[0][0])
        self.assertEqual(upd[0][1], (15, 1))

    def test_change_quantity_clamped_at_zero(self):
        self.db_instance.fetch_one.return_value = {"quantity": 3}
        self.model.change_quantity(1, -10)
        upd = self.db_instance.execute.call_args_list[0]
        self.assertEqual(upd[0][1], (0, 1))

    def test_change_quantity_product_missing(self):
        self.db_instance.fetch_one.return_value = None
        self.model.change_quantity(999, 5)
        self.db_instance.execute.assert_not_called()

    def test_delete_product(self):
        self.model.delete_product(3)
        self.db_instance.execute.assert_called_with(
            "DELETE FROM Product WHERE id=%s", (3,))


# ============================================================
#  TaskModel
# ============================================================
class TestTaskModel(unittest.TestCase):
    def setUp(self):
        patcher = patch("model.Database")
        self.mock_db_cls = patcher.start()
        self.addCleanup(patcher.stop)
        self.db_instance = make_fake_db()
        self.mock_db_cls.return_value = self.db_instance
        self.model = TaskModel()

    def test_add_task(self):
        self.db_instance.execute.return_value = 11
        tid = self.model.add_task("Задача", "Высокий",
                                  "2025-01-01", "Desc", False)
        self.assertEqual(tid, 11)
        sql = self.db_instance.execute.call_args[0][0]
        self.assertIn("INSERT INTO tasks", sql)

    def test_update_task(self):
        self.model.update_task(1, name="New", done=True)
        sql = self.db_instance.execute.call_args[0][0]
        self.assertIn("UPDATE tasks SET", sql)
        self.assertIn("done=%s", sql)

    def test_update_task_empty(self):
        self.model.update_task(1)
        self.db_instance.execute.assert_not_called()

    def test_update_task_ignores_unknown(self):
        self.model.update_task(1, unknown_field="x")
        self.db_instance.execute.assert_not_called()

    def test_delete_task(self):
        self.model.delete_task(4)
        self.db_instance.execute.assert_called_with(
            "DELETE FROM tasks WHERE id=%s", (4,))


# ============================================================
#  NoteModel
# ============================================================
class TestNoteModel(unittest.TestCase):
    def setUp(self):
        patcher = patch("model.Database")
        self.mock_db_cls = patcher.start()
        self.addCleanup(patcher.stop)
        self.db_instance = make_fake_db()
        self.mock_db_cls.return_value = self.db_instance
        self.model = NoteModel()

    def test_add_note(self):
        self.db_instance.execute.return_value = 3
        nid = self.model.add_note("Title", "Content")
        self.assertEqual(nid, 3)

    def test_update_note_title_only(self):
        self.model.update_note(1, title="New")
        sql = self.db_instance.execute.call_args[0][0]
        self.assertIn("title=%s", sql)
        self.assertNotIn("content=%s", sql)

    def test_update_note_both(self):
        self.model.update_note(1, title="T", content="C")
        sql = self.db_instance.execute.call_args[0][0]
        self.assertIn("title=%s", sql)
        self.assertIn("content=%s", sql)

    def test_update_note_nothing(self):
        self.model.update_note(1)
        self.db_instance.execute.assert_not_called()

    def test_delete_note(self):
        self.model.delete_note(2)
        self.db_instance.execute.assert_called_with(
            "DELETE FROM notes WHERE id=%s", (2,))


if __name__ == "__main__":
    unittest.main()