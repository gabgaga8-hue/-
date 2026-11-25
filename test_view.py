"""Тесты логики представлений без создания реальных Qt-виджетов."""
import unittest
from datetime import date
from unittest.mock import MagicMock, patch

from view import MainView


class _FakeMainView(MainView):
    """Обходим __init__ (который грузит .ui и создаёт виджеты)."""
    def __init__(self):
        # намеренно не вызываем super().__init__
        self.current_user = {"login": "u", "role": "Администратор"}
        self.controller = None


class TestMainViewRoleRestrictions(unittest.TestCase):
    """Проверяем, что _apply_role_restrictions вызывает setVisible правильно."""

    def _make(self, role):
        v = _FakeMainView()
        v.current_user = {"login": "u", "role": role}

        # Создаём фейковые виджеты, которые фиксируют вызовы
        v.tabWidget = MagicMock()
        v.tabUsers = MagicMock()
        v.tabWidget.indexOf.return_value = 3
        for name in ("btnUserAdd", "btnUserDelete", "btnUserSave",
                     "edtUserLogin", "edtUserPassword",
                     "btnAdminPanel", "actionAdminPanel",
                     "btnAddItem", "btnExport",
                     "btnTaskAdd", "btnTaskDelete", "btnTaskSave",
                     "btnNoteNew", "btnNoteDelete", "btnNoteSave",
                     "actionDelete"):
            setattr(v, name, MagicMock())
        return v

    def test_admin_full_access(self):
        v = self._make("Администратор")
        v._apply_role_restrictions()
        v.btnAdminPanel.setVisible.assert_called_with(True)
        v.btnAddItem.setVisible.assert_not_called()

    def test_seller_restrictions(self):
        v = self._make("Продавец")
        v._apply_role_restrictions()
        # вкладка пользователей должна быть скрыта
        v.tabWidget.setTabVisible.assert_called()
        v.btnAddItem.setVisible.assert_called_with(False)
        v.btnExport.setVisible.assert_called_with(False)
        v.btnTaskAdd.setVisible.assert_called_with(False)

    def test_storekeeper_restrictions(self):
        v = self._make("Кладовщик")
        v._apply_role_restrictions()
        v.btnExport.setVisible.assert_called_with(False)

    def test_manager_restrictions(self):
        v = self._make("Руководитель магазином")
        v._apply_role_restrictions()
        v.actionDelete.setVisible.assert_called_with(False)
        # вкладка пользователей доступна, но кнопки скрыты
        v.btnUserAdd.setVisible.assert_called_with(False)

    def test_admin_panel_only_admin(self):
        for role in ("Продавец", "Кладовщик", "Руководитель магазином"):
            v = self._make(role)
            v._apply_role_restrictions()
            v.btnAdminPanel.setVisible.assert_called_with(False)


class TestMainViewTaskForm(unittest.TestCase):
    """Проверяем fill_task_form при разных типах due."""

    def _make_view(self):
        v = _FakeMainView()
        v.edtTaskName = MagicMock()
        v.cmbTaskPriority = MagicMock()
        v.cmbTaskPriority.findText.return_value = 1
        v.dtTaskDue = MagicMock()
        v.chkTaskDone = MagicMock()
        v.txtTaskDesc = MagicMock()
        return v

    def test_fill_task_with_date(self):
        v = self._make_view()
        t = {"name": "T", "priority": "Средний", "due": date(2025, 3, 15),
             "done": False, "description": "desc"}
        v.fill_task_form(t)
        v.edtTaskName.setText.assert_called_with("T")
        # QDate(2025, 3, 15)
        from PyQt6.QtCore import QDate
        v.dtTaskDue.setDate.assert_called_with(QDate(2025, 3, 15))

    def test_fill_task_with_string_date(self):
        v = self._make_view()
        t = {"name": "T", "priority": "Средний", "due": "2024-12-01",
             "done": True, "description": ""}
        v.fill_task_form(t)
        from PyQt6.QtCore import QDate
        v.dtTaskDue.setDate.assert_called_with(QDate(2024, 12, 1))

    def test_fill_task_with_invalid_string(self):
        v = self._make_view()
        t = {"name": "T", "priority": "Средний", "due": "not-a-date",
             "done": False, "description": ""}
        v.fill_task_form(t)  # не должно падать
        v.dtTaskDue.setDate.assert_called()

    def test_fill_task_with_none(self):
        v = self._make_view()
        t = {"name": "T", "priority": "Средний", "due": None,
             "done": False, "description": ""}
        v.fill_task_form(t)
        v.dtTaskDue.setDate.assert_called()

    def test_clear_task_form(self):
        v = self._make_view()
        v.clear_task_form()
        v.edtTaskName.clear.assert_called()
        v.txtTaskDesc.clear.assert_called()
        v.cmbTaskPriority.setCurrentIndex.assert_called_with(1)


class TestMainViewNoteForm(unittest.TestCase):
    def _make_view(self):
        v = _FakeMainView()
        v.txtNoteContent = MagicMock()
        v.edtNoteTitle = MagicMock()
        v.lblNoteModified = MagicMock()
        return v

    def test_fill_note_with_datetime(self):
        from datetime import datetime
        v = self._make_view()
        n = {"title": "T", "content": "C",
             "modified": datetime(2025, 1, 2, 10, 30)}
        v.fill_note_content(n)
        v.txtNoteContent.setPlainText.assert_called_with("C")
        v.edtNoteTitle.setText.assert_called_with("T")
        text = v.lblNoteModified.setText.call_args[0][0]
        self.assertIn("02.01.2025", text)

    def test_fill_note_without_modified(self):
        v = self._make_view()
        n = {"title": "T", "content": "", "modified": None}
        v.fill_note_content(n)
        v.lblNoteModified.setText.assert_called_with("Изменено: —")

    def test_clear_note_content(self):
        v = self._make_view()
        v.clear_note_content()
        v.txtNoteContent.clear.assert_called()
        v.edtNoteTitle.clear.assert_called()

    def test_get_note_title(self):
        v = self._make_view()
        v.edtNoteTitle.text.return_value = "  Title  "
        self.assertEqual(v.get_note_title(), "Title")


class TestMainViewProductContextMenu(unittest.TestCase):
    def _make_view(self, role):
        v = _FakeMainView()
        v.current_user = {"login": "u", "role": role}
        return v

    def test_menu_has_all_actions_for_admin(self):
        v = self._make_view("Администратор")
        with patch("view.QMenu") as mock_menu_cls:
            menu = MagicMock()
            mock_menu_cls.return_value = menu
            act_details = MagicMock()
            act_edit = MagicMock()
            act_in = MagicMock()
            act_out = MagicMock()
            act_move = MagicMock()
            act_del = MagicMock()
            # каждый addAction возвращает свой мок по порядку
            menu.addAction.side_effect = [
                act_details, act_edit, act_in, act_out, act_move, act_del,
            ]
            menu.exec.return_value = act_in
            result = v.show_product_context_menu((0, 0), {})
            self.assertEqual(result, "in")

    def test_menu_seller_has_no_in_out(self):
        v = self._make_view("Продавец")
        with patch("view.QMenu") as mock_menu_cls:
            menu = MagicMock()
            mock_menu_cls.return_value = menu
            act_details = MagicMock()
            act_edit = MagicMock()
            menu.addAction.side_effect = [act_details, act_edit]
            menu.exec.return_value = act_edit
            result = v.show_product_context_menu((0, 0), {})
            self.assertEqual(result, "edit")
            # addAction вызван ровно 2 раза (без separator-логики — она через addSeparator)
            self.assertEqual(menu.addAction.call_count, 2)

    def test_menu_returns_none_when_closed(self):
        v = self._make_view("Администратор")
        with patch("view.QMenu") as mock_menu_cls:
            menu = MagicMock()
            mock_menu_cls.return_value = menu
            menu.addAction.return_value = MagicMock()
            menu.exec.return_value = None
            result = v.show_product_context_menu((0, 0), {})
            self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()