import csv
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QInputDialog, QFileDialog, QMessageBox
from model import UserModel, ProductModel, TaskModel, NoteModel, ROLES
from view import MainView, AdminWindow


class AuthController:
    def __init__(self, app):
        self.app = app
        self.user_model = UserModel()

    def login(self, login, password):
        try:
            user = self.user_model.authenticate(login, password)
        except PermissionError as e:
            self.app.login_view.show_error(str(e))
            return
        if user:
            self.app.on_login_success(user)
        else:
            self.app.login_view.show_error("Неверный логин или пароль")

    def open_register(self):
        self.app.register_view.clear()
        self.app.register_view.show()
        self.app.register_view.raise_()
        self.app.register_view.activateWindow()

    # Регистрация: Email, ФИО, Login, Телефон + пароль.
    # Аккаунт пустой (role=NULL, is_active=0) — должность выдаёт админ.
    def register(self, login, full_name, email, phone,
                 password, password2):
        if password != password2:
            self.app.register_view.show_error("Пароли не совпадают")
            return
        try:
            self.user_model.register(
                login=login, password=password,
                email=email, phone=phone, full_name=full_name)
        except ValueError as e:
            self.app.register_view.show_error(str(e))
            return
        self.app.register_view.show_info(
            "Регистрация завершена.\n\n"
            "Ваша учётная запись создана и ожидает назначения должности "
            "администратором. Вход станет доступен после активации.")
        self.app.register_view.clear()
        self.app.register_view.close()


class AdminController:
    """Логика отдельного окна администратора (выдача должностей)."""

    def __init__(self, app, admin_user):
        self.app = app
        self.admin_user = admin_user
        self.user_model = UserModel()
        self.view = AdminWindow(admin_user)
        self.view.bind(self)
        self.refresh()

    def refresh(self):
        try:
            self.view.show_pending(self.user_model.list_pending())
            self.view.show_all_users(self.user_model.list_users())
        except Exception as e:
            self.view.show_error("Администрирование", str(e))

    def _find_user_by_login(self, login):
        for u in self.user_model.list_users():
            if u["login"] == login:
                return u
        return None

    def assign_role(self):
        login = self.view.selected_pending_id()
        if not login:
            self.view.show_error("Должность", "Выберите пользователя "
                                              "в верхней таблице")
            return
        u = self._find_user_by_login(login)
        if not u:
            return
        role = self.view.selected_role()
        if login == "admin":
            self.view.show_error("Должность", "Нельзя менять роль "
                                              "главного администратора")
            return
        try:
            self.user_model.assign_role(u["id"], role, is_active=1)
            self.view.show_message(
                "Должность выдана",
                f"Пользователю «{u['full_name'] or login}» назначена "
                f"должность «{role}», аккаунт активирован.")
            self.refresh()
        except Exception as e:
            self.view.show_error("Должность", str(e))

    def reject_user(self):
        login = self.view.selected_pending_id()
        if not login:
            self.view.show_error("Отклонение", "Выберите пользователя "
                                               "в верхней таблице")
            return
        u = self._find_user_by_login(login)
        if not u:
            return
        ans = QMessageBox.question(
            self.view, "Отклонить заявку",
            f"Удалить учётную запись «{login}»?")
        if ans != QMessageBox.StandardButton.Yes:
            return
        try:
            self.user_model.delete(u["id"])
            self.refresh()
        except Exception as e:
            self.view.show_error("Отклонение", str(e))

    def change_role(self):
        login = self.view.selected_all_id()
        if not login:
            self.view.show_error("Должность", "Выберите пользователя "
                                              "в нижней таблице")
            return
        if login == "admin":
            self.view.show_error("Должность", "Нельзя менять роль "
                                              "главного администратора")
            return
        u = self._find_user_by_login(login)
        if not u:
            return
        role, ok = QInputDialog.getItem(
            self.view, "Смена должности",
            f"Новая должность для «{login}»:",
            list(ROLES), 0, False)
        if not ok:
            return
        try:
            self.user_model.assign_role(u["id"], role,
                                        is_active=bool(u["is_active"]))
            self.refresh()
        except Exception as e:
            self.view.show_error("Должность", str(e))

    def toggle_active(self):
        login = self.view.selected_all_id()
        if not login:
            self.view.show_error("Блокировка", "Выберите пользователя "
                                               "в нижней таблице")
            return
        if login == "admin":
            self.view.show_error("Блокировка", "Нельзя блокировать "
                                               "главного администратора")
            return
        u = self._find_user_by_login(login)
        if not u:
            return
        try:
            self.user_model.assign_role(
                u["id"], u["role"] or "Продавец",
                is_active=not bool(u["is_active"]))
            self.refresh()
        except Exception as e:
            self.view.show_error("Блокировка", str(e))

    def delete_user(self):
        login = self.view.selected_all_id()
        if not login:
            self.view.show_error("Удаление", "Выберите пользователя "
                                             "в нижней таблице")
            return
        u = self._find_user_by_login(login)
        if not u:
            return
        ans = QMessageBox.question(
            self.view, "Удаление пользователя",
            f"Удалить пользователя «{login}»?")
        if ans != QMessageBox.StandardButton.Yes:
            return
        try:
            self.user_model.delete(u["id"])
            self.refresh()
        except Exception as e:
            self.view.show_error("Удаление", str(e))


class MainController:
    def __init__(self, app, user):
        self.app = app
        self.user = user
        self.product_model = ProductModel()
        self.user_model = UserModel()
        self.task_model = TaskModel()
        self.note_model = NoteModel()
        self.view = MainView(user)
        self.view.bind(self)
        self.admin_window = None
        self.selected_user_id = None
        self.selected_task_id = None
        self.selected_note_id = None
        self._nav_history = []
        self._nav_index = -1
        self._nav_guard = False

        self.TAB_KEYS = {}
        if hasattr(self.view, 'tabWidget'):
            for attr, key in (("tabMain", "main"), ("tabTasks", "tasks"),
                              ("tabNotes", "notes"), ("tabUsers", "users")):
                w = getattr(self.view, attr, None)
                if w:
                    self.TAB_KEYS[w] = key
            self._push_nav("main")

        try:
            self.refresh_products()
            self.view.show_categories(self.product_model.list_categories())
            self.refresh_tasks()
            self.refresh_notes()
            if user.get("role") in ("Администратор", "Руководитель магазином"):
                self.refresh_users()
        except Exception as e:
            print(f"[INIT LOAD ERROR] {e}")
            self.view.show_error("Инициализация",
                                 f"Ошибка загрузки данных: {e}")

    # ---------- навигация ----------
    def _push_nav(self, key):
        if self._nav_index + 1 < len(self._nav_history):
            self._nav_history = self._nav_history[: self._nav_index + 1]
        if not self._nav_history or self._nav_history[-1] != key:
            self._nav_history.append(key)
            self._nav_index += 1
        self._update_nav_buttons()

    def _update_nav_buttons(self):
        if hasattr(self.view, 'btnBack'):
            self.view.btnBack.setEnabled(self._nav_index > 0)
        if hasattr(self.view, 'btnForward'):
            self.view.btnForward.setEnabled(
                self._nav_index + 1 < len(self._nav_history))

    def on_tab_changed(self, index):
        if self._nav_guard or not hasattr(self.view, 'tabWidget'):
            return
        if index < 0:
            return
        w = self.view.tabWidget.widget(index)
        key = self.TAB_KEYS.get(w)
        if key:
            self._push_nav(key)

    def go_home(self):
        if hasattr(self.view, 'tabMain'):
            self._nav_guard = True
            self.view.tabWidget.setCurrentWidget(self.view.tabMain)
            self._nav_guard = False
            self._push_nav("main")

    def go_back(self):
        if self._nav_index > 0:
            self._nav_index -= 1
            self._apply_nav(self._nav_history[self._nav_index])
        self._update_nav_buttons()

    def go_forward(self):
        if self._nav_index + 1 < len(self._nav_history):
            self._nav_index += 1
            self._apply_nav(self._nav_history[self._nav_index])
        self._update_nav_buttons()

    def _apply_nav(self, key):
        mapping = {
            "main": getattr(self.view, "tabMain", None),
            "tasks": getattr(self.view, "tabTasks", None),
            "notes": getattr(self.view, "tabNotes", None),
            "users": getattr(self.view, "tabUsers", None),
        }
        w = mapping.get(key)
        if w and hasattr(self.view, 'tabWidget'):
            self._nav_guard = True
            self.view.tabWidget.setCurrentWidget(w)
            self._nav_guard = False

    def show_account_menu(self):
        role = self.user.get('role') or "— не назначена —"
        self.view.show_message(
            "Учётная запись",
            f"Логин: {self.user['login']}\n"
            f"ФИО: {self.user.get('full_name') or '—'}\n"
            f"Email: {self.user.get('email') or '—'}\n"
            f"Телефон: {self.user.get('phone') or '—'}\n"
            f"Должность: {role}"
        )

    def show_about(self):
        self.view.show_message(
            "О программе",
            "Инвентаризация магазина v2.0\nPyQt6 + MySQL")

    # ---------- товары ----------
    def model_categories(self):
        return self.product_model.list_categories()

    def _get_product(self, pid):
        return self.product_model.get_product(pid)

    def refresh_products(self):
        try:
            rows = self.product_model.list_products()
            print(f"[refresh_products] rows={len(rows)}")
            self.view.show_products(rows)
        except Exception as e:
            print(f"[refresh_products ERROR] {e}")
            self.view.show_error("Товары", f"Ошибка чтения: {e}")

    def apply_filter(self, *_):
        cat_id = self.view.cmbFilter.currentData()
        only_dev = self.view.chkOnlyDeviations.isChecked()
        rows = self.product_model.list_products()
        if cat_id is not None:
            rows = [r for r in rows if r.get("category_id") == cat_id]
        if only_dev:
            rows = [r for r in rows if (r["quantity"] or 0) < 20]
        self.view.show_products(rows)

    def add_product(self):
        data = self.view.ask_product_data("Новый товар")
        if not data:
            return
        try:
            new_id = self.product_model.add_product(
                **data, employee_id=self.user["id"])
            print(f"[add_product] inserted id={new_id}")
            self.refresh_products()
        except Exception as e:
            print(f"[add_product ERROR] {e}")
            self.view.show_error("Товары", str(e))

    def edit_product(self, index):
        row = index.row()
        item = self.view.tblProducts.item(row, 0)
        if not item:
            return
        try:
            pid = int(item.text())
        except (TypeError, ValueError):
            return
        self._edit_product_by_id(pid)

    def _edit_product_by_id(self, pid):
        product = self._get_product(pid)
        if not product:
            return
        data = self.view.ask_product_data("Изменить товар", product)
        if not data:
            return
        try:
            self.product_model.update_product(
                pid, **data, employee_id=self.user["id"])
            self.refresh_products()
        except Exception as e:
            self.view.show_error("Товары", str(e))

    def delete_product_action(self):
        if hasattr(self.view, 'tabWidget'):
            cur = self.view.tabWidget.currentWidget()
            if cur is not getattr(self.view, 'tabMain', None):
                return
        pid = self.view.get_selected_product_id()
        if pid is None:
            self.view.show_error("Удаление", "Выберите товар в таблице")
            return
        self._delete_product_by_id(pid)

    def _delete_product_by_id(self, pid):
        product = self._get_product(pid)
        if not product:
            return
        try:
            self.product_model.delete_product(pid)
            self.refresh_products()
            self.view.show_message(
                "Удаление", f"Товар «{product['name']}» удалён")
        except Exception as e:
            self.view.show_error("Удаление", str(e))

    def export_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self.view, "Экспорт в CSV", "products_export.csv",
            "CSV files (*.csv)")
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow(["ID", "SKU", "Наименование", "Категория",
                            "Цена", "Количество", "Ячейка", "Статус"])
                for r in self.product_model.list_products():
                    w.writerow([r["id"], r["sku"], r["name"], r["category"],
                                r["price"], r["quantity"],
                                r["storage_location"], r["status"]])
            self.view.show_message("Экспорт", f"{path} сохранён")
        except Exception as e:
            self.view.show_error("Экспорт", str(e))

    # ---------- контекстное меню товара ----------
    def product_context_menu(self, pos):
        pid = self.view.select_product_at(pos)
        if pid is None:
            return
        product = self._get_product(pid)
        if not product:
            return
        action = self.view.show_product_context_menu(
            self.view.tblProducts.viewport().mapToGlobal(pos), product)
        if action == "details":
            self._show_product_details(product)
        elif action == "edit":
            self._edit_product_by_id(pid)
        elif action == "in":
            self._change_quantity_dialog(product, sign=+1)
        elif action == "out":
            self._change_quantity_dialog(product, sign=-1)
        elif action == "move":
            self._move_product_dialog(product)
        elif action == "delete":
            self._delete_product_by_id(pid)

    def _show_product_details(self, product):
        self.view.show_message(
            "Сведения о товаре",
            f"ID: {product['id']}\n"
            f"SKU: {product['sku'] or '—'}\n"
            f"Наименование: {product['name']}\n"
            f"Категория: {product['category'] or '—'}\n"
            f"Цена: {product['price']}\n"
            f"Количество: {product['quantity']}\n"
            f"Ячейка: {product['storage_location'] or '—'}\n"
            f"Статус: {product['status'] or '—'}"
        )

    def _change_quantity_dialog(self, product, sign):
        title = "Пополнить количество" if sign > 0 else "Списать (убрать)"
        max_val = 1_000_000 if sign > 0 else int(product["quantity"] or 0)
        if sign < 0 and max_val == 0:
            self.view.show_error(title, "На складе нет этого товара")
            return
        qty, ok = QInputDialog.getInt(
            self.view, title,
            f"«{product['name']}» — количество:",
            value=1, min=1, max=max_val, step=1)
        if not ok:
            return
        delta = qty * sign
        try:
            self.product_model.change_quantity(
                product["id"], delta,
                employee_id=self.user["id"],
                op="in" if sign > 0 else "out",
                notes="Пополнение" if sign > 0 else "Списание")
            self.refresh_products()
            self.view.show_message(
                title,
                f"«{product['name']}»: {delta:+d} шт.")
        except Exception as e:
            self.view.show_error(title, str(e))

    def _move_product_dialog(self, product):
        new_loc, ok = QInputDialog.getText(
            self.view, "Переместить товар",
            f"«{product['name']}» — новая ячейка хранения:",
            text=product["storage_location"] or "")
        new_loc = new_loc.strip()
        if not ok or not new_loc:
            return
        try:
            self.product_model.update_product(
                product["id"], product["sku"] or "", product["name"],
                product.get("category_id"),
                product["price"] or 0, product["quantity"] or 0,
                new_loc, product["status"] or "active",
                employee_id=self.user["id"])
            self.refresh_products()
            self.view.show_message(
                "Перемещение",
                f"«{product['name']}» перемещён в ячейку {new_loc}")
        except Exception as e:
            self.view.show_error("Перемещение", str(e))

    # ---------- пользователи (вкладка) ----------
    def refresh_users(self):
        try:
            self.view.show_users(self.user_model.list_users())
        except Exception as e:
            self.view.show_error("Пользователи", str(e))

    def select_user(self, row, col):
        # FIXED: пользователь определяется по логину строки, а не по индексу
        item = self.view.tblUsers.item(row, 0)
        if not item:
            return
        login = item.text()
        for u in self.user_model.list_users():
            if u["login"] == login:
                self.selected_user_id = u["id"]
                self.view.fill_user_form(u)
                return

    def add_user(self):
        self.view.clear_user_form()
        self.selected_user_id = None

    def save_user(self):
        d = self.view.get_user_form_data()
        if not d["login"]:
            self.view.show_error("Пользователи", "Введите логин")
            return
        try:
            if self.selected_user_id is None:
                pwd = d["password"]
                if not pwd:
                    self.view.show_error(
                        "Пользователи",
                        "Введите пароль для нового пользователя")
                    return
                self.user_model.register(
                    d["login"], pwd,
                    email=d.get("email") or f"{d['login']}@local",
                    phone=d.get("phone") or "+70000000000",
                    full_name=d["full_name"] or d["login"])
                self.user_model.assign_role(
                    self._last_user_id(d["login"]),
                    d["role"], is_active=d["is_active"])
            else:
                self.user_model.update(
                    self.selected_user_id, d["full_name"], d["role"],
                    d["is_active"], password=d["password"] or None)
            self.refresh_users()
            self.view.show_message("Пользователи", "Сохранено")
        except Exception as e:
            self.view.show_error("Пользователи", str(e))

    def _last_user_id(self, login):
        for u in self.user_model.list_users():
            if u["login"] == login:
                return u["id"]
        return None

    def delete_user(self):
        if self.selected_user_id is None:
            return
        try:
            self.user_model.delete(self.selected_user_id)
            self.selected_user_id = None
            self.view.clear_user_form()
            self.refresh_users()
        except Exception as e:
            self.view.show_error("Пользователи", str(e))

    # ---------- админ-панель (отдельное окно) ----------
    def open_admin_panel(self):
        if self.user.get("role") != "Администратор":
            self.view.show_error("Доступ запрещён",
                                 "Только для администратора")
            return
        if self.admin_window is None:
            self.admin_window = AdminController(self.app, self.user)
            self.admin_window.view.destroyed.connect(
                lambda *_: setattr(self, "admin_window", None))
        self.admin_window.view.show()
        self.admin_window.view.raise_()
        self.admin_window.view.activateWindow()
        self.admin_window.refresh()

    # ---------- задачи ----------
    def refresh_tasks(self):
        try:
            self.view.show_tasks(self.task_model.list_tasks())
        except Exception as e:
            self.view.show_error("Задачи", str(e))

    def filter_tasks(self, text):
        text = (text or "").lower()
        tasks = self.task_model.list_tasks()
        if text:
            tasks = [t for t in tasks
                     if text in (t.get("name") or "").lower()]
        self.view.show_tasks(tasks)

    def select_task(self, row):
        if row < 0:
            self.selected_task_id = None
            self.view.clear_task_form()
            return
        item = self.view.lstTasks.item(row)
        if not item:
            return
        tid = item.data(Qt.ItemDataRole.UserRole)
        self.selected_task_id = tid
        for t in self.task_model.list_tasks():
            if t["id"] == tid:
                self.view.fill_task_form(t)
                break

    def add_task(self):
        self.selected_task_id = None
        self.view.clear_task_form()
        self.view.lstTasks.clearSelection()
        self.view.lstTasks.setCurrentRow(-1)

    def save_task(self):
        d = self.view.get_task_form_data()
        if not d["name"]:
            self.view.show_error("Задачи", "Введите название задачи")
            return
        try:
            if self.selected_task_id is None:
                self.selected_task_id = self.task_model.add_task(**d)
            else:
                self.task_model.update_task(self.selected_task_id, **d)
            self.refresh_tasks()
            self._highlight_task(self.selected_task_id)
            self.view.show_message("Задачи", "Сохранено")
        except Exception as e:
            self.view.show_error("Задачи", str(e))

    def _highlight_task(self, tid):
        for i in range(self.view.lstTasks.count()):
            it = self.view.lstTasks.item(i)
            if it.data(Qt.ItemDataRole.UserRole) == tid:
                self.view.lstTasks.setCurrentRow(i)
                return

    def delete_task(self):
        if self.selected_task_id is None:
            return
        try:
            self.task_model.delete_task(self.selected_task_id)
            self.selected_task_id = None
            self.view.clear_task_form()
            self.refresh_tasks()
        except Exception as e:
            self.view.show_error("Задачи", str(e))

    # ---------- заметки ----------
    def refresh_notes(self):
        try:
            self.view.show_notes(self.note_model.list_notes())
        except Exception as e:
            self.view.show_error("Заметки", str(e))

    def filter_notes(self, text):
        text = (text or "").lower()
        notes = self.note_model.list_notes()
        if text:
            notes = [n for n in notes
                     if text in (n.get("title") or "").lower()
                     or text in (n.get("content") or "").lower()]
        self.view.show_notes(notes)

    def select_note(self, row):
        if row < 0:
            self.selected_note_id = None
            self.view.clear_note_content()
            return
        item = self.view.lstNotes.item(row)
        if not item:
            return
        nid = item.data(Qt.ItemDataRole.UserRole)
        self.selected_note_id = nid
        for n in self.note_model.list_notes():
            if n["id"] == nid:
                self.view.fill_note_content(n)
                break

    def new_note(self):
        self.selected_note_id = None
        self.view.clear_note_content()
        self.view.lstNotes.clearSelection()
        self.view.lstNotes.setCurrentRow(-1)

    def save_note(self):
        content = self.view.txtNoteContent.toPlainText()
        title = self.view.get_note_title() or "Новая заметка"
        try:
            if self.selected_note_id is None:
                self.selected_note_id = self.note_model.add_note(
                    title, content)
            else:
                self.note_model.update_note(
                    self.selected_note_id, title=title, content=content)
            self.refresh_notes()
            self._highlight_note(self.selected_note_id)
            self.view.show_message("Заметки", "Сохранено")
        except Exception as e:
            self.view.show_error("Заметки", str(e))

    def _highlight_note(self, nid):
        for i in range(self.view.lstNotes.count()):
            it = self.view.lstNotes.item(i)
            if it.data(Qt.ItemDataRole.UserRole) == nid:
                self.view.lstNotes.setCurrentRow(i)
                return

    def delete_note(self):
        if self.selected_note_id is None:
            return
        try:
            self.note_model.delete_note(self.selected_note_id)
            self.selected_note_id = None
            self.view.clear_note_content()
            self.refresh_notes()
        except Exception as e:
            self.view.show_error("Заметки", str(e))

    def logout(self):
        if self.admin_window is not None:
            try:
                self.admin_window.view.close()
            except Exception:
                pass
            self.admin_window = None
        self.view.close()
        self.app.logout()
