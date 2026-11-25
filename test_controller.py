"""Тесты контроллеров (AuthController, AdminController, MainController)."""
import unittest
from unittest.mock import MagicMock, patch, PropertyMock

from controller import AuthController, AdminController, MainController
from conftest_helpers import make_user, make_product, make_fake_db


# ============================================================
#  AuthController
# ============================================================
class TestAuthController(unittest.TestCase):
    def setUp(self):
        self.app = MagicMock()
        self.app.login_view = MagicMock()
        self.app.register_view = MagicMock()

    @patch("controller.UserModel")
    def test_login_success(self, mock_um_cls):
        um = mock_um_cls.return_value
        user = make_user()
        um.authenticate.return_value = user
        ctrl = AuthController(self.app)
        ctrl.login("user", "pass")
        self.app.on_login_success.assert_called_once_with(user)

    @patch("controller.UserModel")
    def test_login_wrong_password(self, mock_um_cls):
        um = mock_um_cls.return_value
        um.authenticate.return_value = None
        ctrl = AuthController(self.app)
        ctrl.login("user", "wrong")
        self.app.login_view.show_error.assert_called_once()
        self.app.on_login_success.assert_not_called()

    @patch("controller.UserModel")
    def test_login_inactive(self, mock_um_cls):
        um = mock_um_cls.return_value
        um.authenticate.side_effect = PermissionError("не активирован")
        ctrl = AuthController(self.app)
        ctrl.login("user", "pass")
        self.app.login_view.show_error.assert_called_once()
        self.app.on_login_success.assert_not_called()

    @patch("controller.UserModel")
    def test_register_password_mismatch(self, _):
        ctrl = AuthController(self.app)
        ctrl.register("l", "F", "a@b.com", "+79991112233", "p1", "p2")
        self.app.register_view.show_error.assert_called_once()
        self.app.register_view.show_info.assert_not_called()

    @patch("controller.UserModel")
    def test_register_success(self, mock_um_cls):
        um = mock_um_cls.return_value
        um.register.return_value = 1
        ctrl = AuthController(self.app)
        ctrl.register("l", "F", "a@b.com", "+79991112233", "p", "p")
        um.register.assert_called_once()
        self.app.register_view.show_info.assert_called_once()
        self.app.register_view.close.assert_called_once()

    @patch("controller.UserModel")
    def test_register_value_error(self, mock_um_cls):
        um = mock_um_cls.return_value
        um.register.side_effect = ValueError("bad")
        ctrl = AuthController(self.app)
        ctrl.register("l", "F", "a@b.com", "+79991112233", "p", "p")
        self.app.register_view.show_error.assert_called_once()


# ============================================================
#  AdminController
# ============================================================
class TestAdminController(unittest.TestCase):
    def setUp(self):
        self.app = MagicMock()
        self.admin_user = make_user(login="admin", role="Администратор")

    @patch("controller.AdminWindow")
    @patch("controller.UserModel")
    def test_init_calls_refresh(self, mock_um_cls, mock_view_cls):
        um = mock_um_cls.return_value
        um.list_pending.return_value = []
        um.list_users.return_value = []
        view = mock_view_cls.return_value
        ctrl = AdminController(self.app, self.admin_user)
        view.bind.assert_called_once_with(ctrl)
        view.show_pending.assert_called_once()
        view.show_all_users.assert_called_once()

    @patch("controller.AdminWindow")
    @patch("controller.UserModel")
    def test_assign_role_no_selection(self, mock_um_cls, mock_view_cls):
        view = mock_view_cls.return_value
        view.selected_pending_id.return_value = None
        ctrl = AdminController(self.app, self.admin_user)
        view.show_error.reset_mock()
        ctrl.assign_role()
        view.show_error.assert_called_once()

    @patch("controller.AdminWindow")
    @patch("controller.UserModel")
    def test_assign_role_admin_protected(self, mock_um_cls, mock_view_cls):
        um = mock_um_cls.return_value
        um.list_users.return_value = [
            make_user(id=1, login="admin", role="Администратор")]
        view = mock_view_cls.return_value
        view.selected_pending_id.return_value = "admin"
        ctrl = AdminController(self.app, self.admin_user)
        view.show_error.reset_mock()
        ctrl.assign_role()
        view.show_error.assert_called_once()
        um.assign_role.assert_not_called()

    @patch("controller.AdminWindow")
    @patch("controller.UserModel")
    def test_assign_role_ok(self, mock_um_cls, mock_view_cls):
        um = mock_um_cls.return_value
        um.list_users.return_value = [make_user(id=2, login="u1")]
        view = mock_view_cls.return_value
        view.selected_pending_id.return_value = "u1"
        view.selected_role.return_value = "Продавец"
        ctrl = AdminController(self.app, self.admin_user)
        view.show_message.reset_mock()
        ctrl.assign_role()
        um.assign_role.assert_called_once_with(2, "Продавец", is_active=1)
        view.show_message.assert_called_once()

    @patch("controller.AdminWindow")
    @patch("controller.UserModel")
    def test_change_role_admin_protected(self, mock_um_cls, mock_view_cls):
        um = mock_um_cls.return_value
        um.list_users.return_value = [make_user(login="admin")]
        view = mock_view_cls.return_value
        view.selected_all_id.return_value = "admin"
        ctrl = AdminController(self.app, self.admin_user)
        view.show_error.reset_mock()
        ctrl.change_role()
        view.show_error.assert_called_once()

    @patch("controller.AdminWindow")
    @patch("controller.UserModel")
    def test_toggle_active(self, mock_um_cls, mock_view_cls):
        um = mock_um_cls.return_value
        um.list_users.return_value = [make_user(id=5, login="u",
                                                role="Продавец",
                                                is_active=1)]
        view = mock_view_cls.return_value
        view.selected_all_id.return_value = "u"
        ctrl = AdminController(self.app, self.admin_user)
        ctrl.toggle_active()
        um.assign_role.assert_called_once_with(5, "Продавец",
                                                is_active=False)


# ============================================================
#  MainController
# ============================================================
class TestMainController(unittest.TestCase):
    def setUp(self):
        self.app = MagicMock()
        self.user = make_user()
        self.view_patcher = patch("controller.MainView")
        self.mock_view_cls = self.view_patcher.start()
        self.addCleanup(self.view_patcher.stop)
        self.view = MagicMock()
        self.mock_view_cls.return_value = self.view

        # Заглушки моделей
        self.pm_patcher = patch("controller.ProductModel")
        self.um_patcher = patch("controller.UserModel")
        self.tm_patcher = patch("controller.TaskModel")
        self.nm_patcher = patch("controller.NoteModel")
        self.pm = self.pm_patcher.start().return_value
        self.um = self.um_patcher.start().return_value
        self.tm = self.tm_patcher.start().return_value
        self.nm = self.nm_patcher.start().return_value
        for p in (self.pm_patcher, self.um_patcher,
                  self.tm_patcher, self.nm_patcher):
            self.addCleanup(p.stop)

        self.pm.list_products.return_value = [make_product()]
        self.pm.list_categories.return_value = [{"id": 1, "name": "Кат"}]
        self.pm.get_product.side_effect = lambda pid: make_product(id=pid)
        self.um.list_users.return_value = [self.user]
        self.tm.list_tasks.return_value = []
        self.nm.list_notes.return_value = []

        # tabWidget нужен для навигации
        self.view.tabWidget = MagicMock()
        self.view.tabWidget.currentWidget.return_value = self.view.tabMain

    def _make(self):
        return MainController(self.app, self.user)

    # ---- товары ----
    def test_refresh_products(self):
        ctrl = self._make()
        self.pm.list_products.return_value = [make_product()]
        ctrl.refresh_products()
        self.view.show_products.assert_called()

    def test_apply_filter_by_category(self):
        ctrl = self._make()
        self.view.cmbFilter.currentData.return_value = 1
        self.view.chkOnlyDeviations.isChecked.return_value = False
        self.pm.list_products.return_value = [
            make_product(id=1, category_id=1),
            make_product(id=2, category_id=2),
        ]
        ctrl.apply_filter()
        called_rows = self.view.show_products.call_args[0][0]
        self.assertEqual(len(called_rows), 1)
        self.assertEqual(called_rows[0]["category_id"], 1)

    def test_apply_filter_only_deviations(self):
        ctrl = self._make()
        self.view.cmbFilter.currentData.return_value = None
        self.view.chkOnlyDeviations.isChecked.return_value = True
        self.pm.list_products.return_value = [
            make_product(id=1, quantity=30),
            make_product(id=2, quantity=5),
        ]
        ctrl.apply_filter()
        rows = self.view.show_products.call_args[0][0]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], 2)

    def test_add_product_ok(self):
        ctrl = self._make()
        self.view.ask_product_data.return_value = {
            "sku": "S", "name": "N", "category_id": 1, "price": 10,
            "quantity": 5, "storage_location": "A", "status": "active"}
        self.pm.add_product.return_value = 99
        ctrl.add_product()
        self.pm.add_product.assert_called_once()
        self.view.show_error.assert_not_called()

    def test_add_product_cancelled(self):
        ctrl = self._make()
        self.view.ask_product_data.return_value = None
        ctrl.add_product()
        self.pm.add_product.assert_not_called()

    def test_delete_product_no_selection(self):
        ctrl = self._make()
        self.view.get_selected_product_id.return_value = None
        self.view.tabWidget.currentWidget.return_value = self.view.tabMain
        ctrl.delete_product_action()
        self.view.show_error.assert_called()
        self.pm.delete_product.assert_not_called()

    def test_delete_product_ok(self):
        ctrl = self._make()
        self.view.get_selected_product_id.return_value = 1
        self.view.tabWidget.currentWidget.return_value = self.view.tabMain
        ctrl.delete_product_action()
        self.pm.delete_product.assert_called_once_with(1)
        self.view.show_message.assert_called()

    # ---- контекстное меню ----
    def test_context_menu_details(self):
        ctrl = self._make()
        self.view.select_product_at.return_value = 1
        self.view.show_product_context_menu.return_value = "details"
        ctrl.product_context_menu((0, 0))
        self.view.show_message.assert_called()

    def test_context_menu_cancelled(self):
        ctrl = self._make()
        self.view.select_product_at.return_value = 1
        self.view.show_product_context_menu.return_value = None
        ctrl.product_context_menu((0, 0))
        # никаких действий не требуется

    def test_change_quantity_dialog_positive(self):
        ctrl = self._make()
        product = make_product(quantity=5)
        with patch("controller.QInputDialog.getInt",
                   return_value=(3, True)):
            ctrl._change_quantity_dialog(product, sign=+1)
        self.pm.change_quantity.assert_called_once()
        args = self.pm.change_quantity.call_args
        self.assertEqual(args[0][1], 3)

    def test_change_quantity_dialog_negative(self):
        ctrl = self._make()
        product = make_product(quantity=5)
        with patch("controller.QInputDialog.getInt",
                   return_value=(2, True)):
            ctrl._change_quantity_dialog(product, sign=-1)
        args = self.pm.change_quantity.call_args
        self.assertEqual(args[0][1], -2)

    def test_change_quantity_zero_stock(self):
        ctrl = self._make()
        product = make_product(quantity=0)
        ctrl._change_quantity_dialog(product, sign=-1)
        self.view.show_error.assert_called()
        self.pm.change_quantity.assert_not_called()

    # ---- пользователи ----
    def test_select_user(self):
        ctrl = self._make()
        self.view.tblUsers = MagicMock()
        item = MagicMock()
        item.text.return_value = "user"
        self.view.tblUsers.item.return_value = item
        ctrl.select_user(0, 0)
        self.assertEqual(ctrl.selected_user_id, self.user["id"])
        self.view.fill_user_form.assert_called_with(self.user)

    def test_add_user_clears_form(self):
        ctrl = self._make()
        ctrl.add_user()
        self.view.clear_user_form.assert_called()
        self.assertIsNone(ctrl.selected_user_id)

    def test_save_user_new_without_password(self):
        ctrl = self._make()
        ctrl.selected_user_id = None
        self.view.get_user_form_data.return_value = {
            "login": "new", "full_name": "F", "password": "",
            "role": "Продавец", "is_active": 1}
        ctrl.save_user()
        self.view.show_error.assert_called()

    def test_save_user_update(self):
        ctrl = self._make()
        ctrl.selected_user_id = 3
        self.view.get_user_form_data.return_value = {
            "login": "u", "full_name": "F", "password": "",
            "role": "Продавец", "is_active": 1}
        ctrl.save_user()
        self.um.update.assert_called_once()
        self.view.show_message.assert_called()

    # ---- задачи ----
    def test_select_task(self):
        ctrl = self._make()
        item = MagicMock()
        item.data.return_value = 7
        self.view.lstTasks.item.return_value = item
        self.tm.list_tasks.return_value = [
            {"id": 7, "name": "T", "priority": "Средний",
             "due": None, "description": "", "done": False}]
        ctrl.select_task(0)
        self.assertEqual(ctrl.selected_task_id, 7)
        self.view.fill_task_form.assert_called()

    def test_select_task_invalid_row(self):
        ctrl = self._make()
        ctrl.selected_task_id = 5
        ctrl.select_task(-1)
        self.assertIsNone(ctrl.selected_task_id)
        self.view.clear_task_form.assert_called()

    def test_save_task_no_name(self):
        ctrl = self._make()
        self.view.get_task_form_data.return_value = {"name": ""}
        ctrl.save_task()
        self.view.show_error.assert_called()

    def test_save_task_new(self):
        ctrl = self._make()
        ctrl.selected_task_id = None
        self.view.get_task_form_data.return_value = {
            "name": "T", "priority": "Средний", "due": None,
            "description": "", "done": False}
        self.tm.add_task.return_value = 12
        ctrl.save_task()
        self.assertEqual(ctrl.selected_task_id, 12)
        self.view.show_message.assert_called()

    def test_delete_task_no_selection(self):
        ctrl = self._make()
        ctrl.selected_task_id = None
        ctrl.delete_task()
        self.tm.delete_task.assert_not_called()

    def test_delete_task_ok(self):
        ctrl = self._make()
        ctrl.selected_task_id = 5
        ctrl.delete_task()
        self.tm.delete_task.assert_called_with(5)
        self.assertIsNone(ctrl.selected_task_id)

    # ---- заметки ----
    def test_save_note_new(self):
        ctrl = self._make()
        ctrl.selected_note_id = None
        self.view.txtNoteContent.toPlainText.return_value = "text"
        self.view.get_note_title.return_value = "Title"
        self.nm.add_note.return_value = 8
        ctrl.save_note()
        self.nm.add_note.assert_called_with("Title", "text")
        self.assertEqual(ctrl.selected_note_id, 8)

    def test_save_note_default_title(self):
        ctrl = self._make()
        self.view.txtNoteContent.toPlainText.return_value = ""
        self.view.get_note_title.return_value = ""
        self.nm.add_note.return_value = 1
        ctrl.save_note()
        self.nm.add_note.assert_called_with("Новая заметка", "")

    def test_delete_note_ok(self):
        ctrl = self._make()
        ctrl.selected_note_id = 3
        ctrl.delete_note()
        self.nm.delete_note.assert_called_with(3)

    # ---- админ-панель ----
    def test_open_admin_panel_forbidden(self):
        ctrl = self._make()
        ctrl.user["role"] = "Продавец"
        ctrl.open_admin_panel()
        self.view.show_error.assert_called()

    @patch("controller.AdminController")
    def test_open_admin_panel_ok(self, mock_admin_cls):
        admin_view = MagicMock()
        admin_view.destroyed = MagicMock()
        mock_admin_cls.return_value.view = admin_view
        ctrl = self._make()
        ctrl.user["role"] = "Администратор"
        ctrl.open_admin_panel()
        mock_admin_cls.assert_called_once()
        admin_view.show.assert_called()

    # ---- навигация ----
    def test_push_nav(self):
        ctrl = self._make()
        ctrl._nav_history = []
        ctrl._nav_index = -1
        ctrl._push_nav("main")
        ctrl._push_nav("tasks")
        self.assertEqual(ctrl._nav_history, ["main", "tasks"])
        self.assertEqual(ctrl._nav_index, 1)

    def test_go_back_and_forward(self):
        ctrl = self._make()
        ctrl._nav_history = ["main", "tasks"]
        ctrl._nav_index = 1
        with patch.object(ctrl, "_apply_nav") as mock_apply:
            ctrl.go_back()
            mock_apply.assert_called_with("main")
            ctrl.go_forward()
            mock_apply.assert_called_with("tasks")

    # ---- logout ----
    def test_logout(self):
        ctrl = self._make()
        ctrl.logout()
        self.view.close.assert_called()
        self.app.logout.assert_called()


if __name__ == "__main__":
    unittest.main()