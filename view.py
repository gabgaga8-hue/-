import os
import sys
from datetime import date
from PyQt6 import uic
from PyQt6.QtWidgets import (
    QMainWindow, QMessageBox, QLineEdit, QTableWidgetItem,
    QDialog, QFormLayout, QComboBox, QSpinBox, QDialogButtonBox,
    QListWidgetItem, QHeaderView, QMenu, QSizePolicy,
    QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout,
    QTableWidget, QListWidget, QCheckBox, QDateEdit, QGroupBox,
)
from PyQt6.QtCore import QDate, Qt, QPoint


def resource_path(relative_path):
    """
    Возвращает абсолютный путь к ресурсу.
    Работает и в обычном режиме (рядом со скриптом),
    и внутри EXE, собранного PyInstaller (--onefile).
    """
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller распаковывает данные во временную папку
        return os.path.join(sys._MEIPASS, relative_path)
    # Обычный запуск: путь относительно текущего файла
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, relative_path)


def load_ui(widget, filename):
    """Загружает .ui-файл из папки ui/ (работает и в EXE)."""
    path = resource_path(os.path.join("ui", filename))
    if os.path.exists(path):
        uic.loadUi(path, widget)
        return
    # fallback: файл лежит рядом со скриптом
    fallback = resource_path(filename)
    if os.path.exists(fallback):
        uic.loadUi(fallback, widget)
        return
    raise FileNotFoundError(f"Не найден UI-файл: {filename}")


class LoginView(QMainWindow):
    def __init__(self):
        super().__init__()
        load_ui(self, "Login.ui")
        self.setWindowTitle("Вход в систему")
        self.controller = None

    def bind(self, controller):
        self.controller = controller
        self.btnLogin.clicked.connect(self._on_login)
        self.btnOpenRegister.clicked.connect(self.controller.open_register)
        self.edtPassword.returnPressed.connect(self._on_login)

    def _on_login(self):
        login = self.edtLogin.text().strip()
        password = self.edtPassword.text()
        if not login or not password:
            QMessageBox.warning(self, "Ошибка", "Введите логин и пароль")
            return
        self.controller.login(login, password)

    def show_error(self, msg):
        QMessageBox.critical(self, "Ошибка входа", msg)

    def clear(self):
        self.edtLogin.clear()
        self.edtPassword.clear()


class RegisterView(QMainWindow):
    def __init__(self):
        super().__init__()
        load_ui(self, "Regustrate user.ui")
        self.setWindowTitle("Регистрация")
        self.controller = None

    def bind(self, controller):
        self.controller = controller
        self.btnRegister.clicked.connect(self._on_register)
        self.btnCancelRegister.clicked.connect(self.close)

    def _on_register(self):
        self.controller.register(
            login=self.edtRegLogin.text().strip(),
            full_name=self.edtRegFullName.text().strip(),
            email=self.edtRegEmail.text().strip(),
            phone=self.edtRegPhone.text().strip(),
            password=self.edtRegPassword.text(),
            password2=self.edtRegPassword2.text(),
        )

    def show_info(self, msg):
        QMessageBox.information(self, "Готово", msg)

    def show_error(self, msg):
        QMessageBox.critical(self, "Ошибка", msg)

    def clear(self):
        self.edtRegLogin.clear()
        self.edtRegFullName.clear()
        self.edtRegEmail.clear()
        self.edtRegPhone.clear()
        self.edtRegPassword.clear()
        self.edtRegPassword2.clear()


# ============================================================
#   Отдельное окно администратора: выдача должностей
# ============================================================
class AdminWindow(QMainWindow):
    def __init__(self, current_user):
        super().__init__()
        self.setWindowTitle("Администрирование — выдача должностей")
        self.resize(760, 460)
        self.current_user = current_user
        self.controller = None

        central = QWidget(self)
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.lblPendingInfo = QLabel("Ожидают назначения должности:")
        layout.addWidget(self.lblPendingInfo)

        self.tblPending = QTableWidget(self)
        self.tblPending.setColumnCount(6)
        self.tblPending.setHorizontalHeaderLabels(
            ["Логин", "ФИО", "Email", "Телефон", "Должность", "Статус"])
        self.tblPending.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows)
        self.tblPending.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection)
        self.tblPending.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers)
        self.tblPending.setAlternatingRowColors(True)
        self.tblPending.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.tblPending, 1)

        row = QHBoxLayout()
        row.addWidget(QLabel("Назначить должность:"))
        self.cmbAssignRole = QComboBox()
        self.cmbAssignRole.addItems(
            ["Кладовщик", "Продавец", "Руководитель магазином",
             "Администратор"])
        row.addWidget(self.cmbAssignRole)
        self.btnAssignRole = QPushButton("Выдать и активировать")
        row.addWidget(self.btnAssignRole)
        self.btnReject = QPushButton("Отклонить заявку")
        row.addWidget(self.btnReject)
        row.addStretch(1)
        self.btnRefreshPending = QPushButton("Обновить")
        row.addWidget(self.btnRefreshPending)
        layout.addLayout(row)

        self.lblAllInfo = QLabel("Все пользователи (смена должности / блокировка):")
        layout.addWidget(self.lblAllInfo)

        self.tblAllUsers = QTableWidget(self)
        self.tblAllUsers.setColumnCount(6)
        self.tblAllUsers.setHorizontalHeaderLabels(
            ["Логин", "ФИО", "Email", "Телефон", "Должность", "Статус"])
        self.tblAllUsers.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows)
        self.tblAllUsers.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection)
        self.tblAllUsers.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers)
        self.tblAllUsers.setAlternatingRowColors(True)
        self.tblAllUsers.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.tblAllUsers, 1)

        row2 = QHBoxLayout()
        self.btnChangeRole = QPushButton("Сменить должность выбранному")
        row2.addWidget(self.btnChangeRole)
        self.btnToggleActive = QPushButton("Заблокировать / разблокировать")
        row2.addWidget(self.btnToggleActive)
        self.btnDeleteUser = QPushButton("Удалить пользователя")
        row2.addWidget(self.btnDeleteUser)
        row2.addStretch(1)
        self.btnCloseAdmin = QPushButton("Закрыть")
        row2.addWidget(self.btnCloseAdmin)
        layout.addLayout(row2)

    def bind(self, controller):
        self.controller = controller
        self.btnAssignRole.clicked.connect(self.controller.assign_role)
        self.btnReject.clicked.connect(self.controller.reject_user)
        self.btnRefreshPending.clicked.connect(self.controller.refresh)
        self.btnChangeRole.clicked.connect(self.controller.change_role)
        self.btnToggleActive.clicked.connect(self.controller.toggle_active)
        self.btnDeleteUser.clicked.connect(self.controller.delete_user)
        self.btnCloseAdmin.clicked.connect(self.close)

    # ---------- отрисовка ----------
    def _fill_table(self, table, users):
        table.setRowCount(0)
        table.setRowCount(len(users))
        for r, u in enumerate(users):
            role = u.get("role") or "— не назначена —"
            status = "Активен" if u.get("is_active") else "Ожидает"
            for c, val in enumerate([u["login"], u.get("full_name") or "",
                                     u.get("email") or "",
                                     u.get("phone") or "",
                                     role, status]):
                table.setItem(r, c, QTableWidgetItem(str(val)))

    def show_pending(self, users):
        self._fill_table(self.tblPending, users)
        self.lblPendingInfo.setText(
            f"Ожидают назначения должности: {len(users)}")

    def show_all_users(self, users):
        self._fill_table(self.tblAllUsers, users)
        self.lblAllInfo.setText(f"Все пользователи: {len(users)}")

    def selected_pending_id(self):
        return self._selected_id(self.tblPending)

    def selected_all_id(self):
        return self._selected_id(self.tblAllUsers)

    def _selected_id(self, table):
        row = table.currentRow()
        if row < 0 or row >= table.rowCount():
            return None
        # ID не выводим в таблице — controller восстановит по логину
        item = table.item(row, 0)
        return item.text() if item else None

    def selected_role(self):
        return self.cmbAssignRole.currentText()

    def show_message(self, title, msg):
        QMessageBox.information(self, title, msg)

    def show_error(self, title, msg):
        QMessageBox.critical(self, title, msg)


class MainView(QMainWindow):
    def __init__(self, current_user):
        super().__init__()
        load_ui(self, "mainwindow.ui")

        self.current_user = current_user
        self.setWindowTitle(f"Инвентаризация — {current_user['login']}")

        if hasattr(self, 'lblDate'):
            self.lblDate.setText(
                f"Дата: {QDate.currentDate().toString('dd.MM.yyyy')}")
        if hasattr(self, 'btnAccount'):
            name = current_user.get('full_name') or current_user['login']
            self.btnAccount.setText(f"👤 {name}")

        self.controller = None

        self._make_responsive()

        if hasattr(self, 'dtTaskDue'):
            self.dtTaskDue.setDate(QDate.currentDate().addDays(7))

        self._ensure_note_title_field()
        self._apply_role_restrictions()

    def _apply_role_restrictions(self):
        role = self.current_user.get('role')  # None = пустой аккаунт

        # Вкладка "Пользователи" — только полноценные роли выше продавца
        if hasattr(self, 'tabWidget') and hasattr(self, 'tabUsers'):
            idx = self.tabWidget.indexOf(self.tabUsers)
            if idx >= 0:
                if role == "Администратор":
                    pass  # полный доступ
                elif role == "Руководитель магазином":
                    self.tabWidget.setTabEnabled(idx, True)
                    for w in ('btnUserAdd', 'btnUserDelete', 'btnUserSave'):
                        if hasattr(self, w):
                            getattr(self, w).setVisible(False)
                    if hasattr(self, 'edtUserLogin'):
                        self.edtUserLogin.setEnabled(False)
                    if hasattr(self, 'edtUserPassword'):
                        self.edtUserPassword.setEnabled(False)
                else:
                    self.tabWidget.setTabEnabled(idx, False)
                    self.tabWidget.setTabVisible(idx, False)

        # Кнопка админ-панели (выдача должностей) — только администратор
        if hasattr(self, 'btnAdminPanel'):
            self.btnAdminPanel.setVisible(role == "Администратор")
        if hasattr(self, 'actionAdminPanel'):
            self.actionAdminPanel.setVisible(role == "Администратор")

        if role in ("Продавец", None):
            if hasattr(self, 'btnAddItem'):
                self.btnAddItem.setVisible(False)
            if hasattr(self, 'btnExport'):
                self.btnExport.setVisible(False)
            for w in ('btnTaskAdd', 'btnTaskDelete', 'btnTaskSave',
                      'btnNoteNew', 'btnNoteDelete', 'btnNoteSave'):
                if hasattr(self, w):
                    getattr(self, w).setVisible(False)

        if role == "Кладовщик":
            if hasattr(self, 'btnExport'):
                self.btnExport.setVisible(False)
        elif role == "Руководитель магазином":
            if hasattr(self, 'actionDelete'):
                self.actionDelete.setVisible(False)

    def _ensure_note_title_field(self):
        if hasattr(self, 'edtNoteTitle'):
            return
        if not hasattr(self, 'txtNoteContent'):
            return

        parent = self.txtNoteContent.parentWidget()
        if parent is None:
            return
        old_layout = parent.layout()
        if old_layout is None:
            return

        idx_in_parent_layout = old_layout.indexOf(self.txtNoteContent)
        old_layout.removeWidget(self.txtNoteContent)

        container = QWidget(parent)
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(4)

        lbl_title = QLabel("Название:", container)
        self.edtNoteTitle = QLineEdit(container)
        self.edtNoteTitle.setObjectName("edtNoteTitle")
        self.edtNoteTitle.setPlaceholderText("Введите название заметки")

        vbox.addWidget(lbl_title)
        vbox.addWidget(self.edtNoteTitle)
        vbox.addWidget(self.txtNoteContent, 1)

        if idx_in_parent_layout >= 0:
            old_layout.insertWidget(idx_in_parent_layout, container, 1)
        else:
            old_layout.addWidget(container, 1)

    def _make_responsive(self):
        for name in ('tblProducts', 'tblUsers'):
            if not hasattr(self, name):
                continue
            t = getattr(self, name)
            t.setSizePolicy(QSizePolicy.Policy.Expanding,
                            QSizePolicy.Policy.Expanding)
            t.horizontalHeader().setSectionResizeMode(
                QHeaderView.ResizeMode.Stretch)

        if hasattr(self, 'tabWidget'):
            self.tabWidget.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        if hasattr(self, 'tblProducts'):
            self.tblProducts.setContextMenuPolicy(
                Qt.ContextMenuPolicy.CustomContextMenu)

    def bind(self, controller):
        self.controller = controller

        # Товары
        if hasattr(self, 'btnRefresh'):
            self.btnRefresh.clicked.connect(self.controller.refresh_products)
        if hasattr(self, 'cmbFilter'):
            self.cmbFilter.currentIndexChanged.connect(
                self.controller.apply_filter)
        if hasattr(self, 'chkOnlyDeviations'):
            self.chkOnlyDeviations.toggled.connect(self.controller.apply_filter)
        if hasattr(self, 'btnAddItem'):
            self.btnAddItem.clicked.connect(self.controller.add_product)
        if hasattr(self, 'btnExport'):
            self.btnExport.clicked.connect(self.controller.export_csv)
        if hasattr(self, 'tblProducts'):
            self.tblProducts.doubleClicked.connect(self.controller.edit_product)
            self.tblProducts.customContextMenuRequested.connect(
                self.controller.product_context_menu)

        # Навигация по вкладкам
        if hasattr(self, 'tabWidget'):
            self.tabWidget.currentChanged.connect(self.controller.on_tab_changed)

        # Пользователи
        if hasattr(self, 'btnUserAdd'):
            self.btnUserAdd.clicked.connect(self.controller.add_user)
        if hasattr(self, 'btnUserDelete'):
            self.btnUserDelete.clicked.connect(self.controller.delete_user)
        if hasattr(self, 'btnUserRefresh'):
            self.btnUserRefresh.clicked.connect(self.controller.refresh_users)
        if hasattr(self, 'btnUserSave'):
            self.btnUserSave.clicked.connect(self.controller.save_user)
        if hasattr(self, 'tblUsers'):
            self.tblUsers.cellClicked.connect(self.controller.select_user)

        # Задачи
        if hasattr(self, 'btnTaskAdd'):
            self.btnTaskAdd.clicked.connect(self.controller.add_task)
        if hasattr(self, 'btnTaskDelete'):
            self.btnTaskDelete.clicked.connect(self.controller.delete_task)
        if hasattr(self, 'btnTaskSave'):
            self.btnTaskSave.clicked.connect(self.controller.save_task)
        if hasattr(self, 'lstTasks'):
            self.lstTasks.currentRowChanged.connect(self.controller.select_task)
        if hasattr(self, 'edtTaskSearch'):
            self.edtTaskSearch.textChanged.connect(self.controller.filter_tasks)

        # Заметки
        if hasattr(self, 'btnNoteNew'):
            self.btnNoteNew.clicked.connect(self.controller.new_note)
        if hasattr(self, 'btnNoteDelete'):
            self.btnNoteDelete.clicked.connect(self.controller.delete_note)
        if hasattr(self, 'btnNoteSave'):
            self.btnNoteSave.clicked.connect(self.controller.save_note)
        if hasattr(self, 'lstNotes'):
            self.lstNotes.currentRowChanged.connect(self.controller.select_note)
        if hasattr(self, 'edtNoteSearch'):
            self.edtNoteSearch.textChanged.connect(self.controller.filter_notes)

        # Верхняя панель
        if hasattr(self, 'btnHome'):
            self.btnHome.clicked.connect(self.controller.go_home)
        if hasattr(self, 'btnBack'):
            self.btnBack.clicked.connect(self.controller.go_back)
        if hasattr(self, 'btnForward'):
            self.btnForward.clicked.connect(self.controller.go_forward)
        if hasattr(self, 'btnAccount'):
            self.btnAccount.clicked.connect(self.controller.show_account_menu)
        if hasattr(self, 'btnAdminPanel'):
            self.btnAdminPanel.clicked.connect(self.controller.open_admin_panel)

        # Меню
        if hasattr(self, 'actionExit'):
            self.actionExit.triggered.connect(self.controller.logout)
        if hasattr(self, 'actionRefresh'):
            self.actionRefresh.triggered.connect(self.controller.refresh_products)
        if hasattr(self, 'actionExport'):
            self.actionExport.triggered.connect(self.controller.export_csv)
        if hasattr(self, 'actionAdd'):
            self.actionAdd.triggered.connect(self.controller.add_product)
        if hasattr(self, 'actionDelete'):
            self.actionDelete.triggered.connect(
                self.controller.delete_product_action)
        if hasattr(self, 'actionAbout'):
            self.actionAbout.triggered.connect(self.controller.show_about)
        if hasattr(self, 'actionAdminPanel'):
            self.actionAdminPanel.triggered.connect(
                self.controller.open_admin_panel)

    # ---------- ТОВАРЫ ----------
    def show_products(self, rows):
        self.tblProducts.setSortingEnabled(False)
        self.tblProducts.setRowCount(0)
        self.tblProducts.setColumnCount(8)
        self.tblProducts.setHorizontalHeaderLabels(
            ["ID", "SKU", "Наименование", "Категория", "Цена",
             "Кол-во", "Ячейка", "Статус"]
        )
        self.tblProducts.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, key in enumerate(["id", "sku", "name", "category",
                                     "price", "quantity",
                                     "storage_location", "status"]):
                val = row.get(key)
                self.tblProducts.setItem(
                    r, c, QTableWidgetItem("" if val is None else str(val))
                )
        self.tblProducts.setSortingEnabled(True)
        self.tblProducts.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)

        if hasattr(self, 'lblRowsCount'):
            self.lblRowsCount.setText(f"Строк: {len(rows)}")
        if hasattr(self, 'lblDeviationsSum'):
            dev_count = sum(1 for r in rows if (r.get("quantity") or 0) < 20)
            deficit = sum(max(0, 20 - (r.get("quantity") or 0)) for r in rows)
            self.lblDeviationsSum.setText(
                f"Отклонений: {dev_count} (дефицит {deficit} шт.)")

    def show_categories(self, cats):
        if not hasattr(self, 'cmbFilter'):
            return
        self.cmbFilter.blockSignals(True)
        self.cmbFilter.clear()
        self.cmbFilter.addItem("Все категории", None)
        for c in cats:
            self.cmbFilter.addItem(c["name"], c["id"])
        self.cmbFilter.blockSignals(False)

    def ask_product_data(self, title="Добавить товар", defaults=None):
        dlg = QDialog(self)
        dlg.setWindowTitle(title)
        form = QFormLayout(dlg)
        ed_sku = QLineEdit()
        ed_name = QLineEdit()
        cmb_cat = QComboBox()
        for c in self.controller.model_categories():
            cmb_cat.addItem(c["name"], c["id"])
        sp_price = QSpinBox(); sp_price.setMaximum(10_000_000)
        sp_qty = QSpinBox(); sp_qty.setMaximum(10_000_000)
        ed_loc = QLineEdit()
        ed_status = QLineEdit("active")

        if defaults:
            ed_sku.setText(defaults.get("sku") or "")
            ed_name.setText(defaults.get("name") or "")
            if defaults.get("category_id") is not None:
                i = cmb_cat.findData(defaults["category_id"])
                if i >= 0:
                    cmb_cat.setCurrentIndex(i)
            sp_price.setValue(int(defaults.get("price") or 0))
            sp_qty.setValue(int(defaults.get("quantity") or 0))
            ed_loc.setText(defaults.get("storage_location") or "")
            ed_status.setText(defaults.get("status") or "active")

        form.addRow("SKU:", ed_sku)
        form.addRow("Наименование:", ed_name)
        form.addRow("Категория:", cmb_cat)
        form.addRow("Цена:", sp_price)
        form.addRow("Количество:", sp_qty)
        form.addRow("Ячейка:", ed_loc)
        form.addRow("Статус:", ed_status)
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        form.addRow(btns)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return None
        if not ed_name.text().strip():
            QMessageBox.warning(self, title, "Введите наименование товара")
            return None
        if cmb_cat.currentData() is None:
            QMessageBox.warning(self, title, "Выберите категорию")
            return None
        return {
            "sku": ed_sku.text().strip(),
            "name": ed_name.text().strip(),
            "category_id": cmb_cat.currentData(),
            "price": sp_price.value(),
            "quantity": sp_qty.value(),
            "storage_location": ed_loc.text().strip(),
            "status": ed_status.text().strip() or "active",
        }

    def get_selected_product_id(self):
        row = self.tblProducts.currentRow()
        if row < 0:
            return None
        item = self.tblProducts.item(row, 0)
        if not item:
            return None
        try:
            return int(item.text())
        except (TypeError, ValueError):
            return None

    def select_product_at(self, pos: QPoint):
        item = self.tblProducts.itemAt(pos)
        if item:
            self.tblProducts.selectRow(item.row())
            self.tblProducts.setCurrentItem(item)
        return self.get_selected_product_id()

    def show_product_context_menu(self, global_pos: QPoint, product):
        """FIXED: menu.exec() теперь вызывается ВСЕГДА, независимо от роли."""
        menu = QMenu(self)
        role = self.current_user.get('role')

        act_details = menu.addAction("🔍 Сведения о товаре")
        act_edit = menu.addAction("✏️ Изменить…")
        act_in = act_out = act_move = act_del = None
        if role in ("Администратор", "Кладовщик", "Руководитель магазином"):
            menu.addSeparator()
            act_in = menu.addAction("📥 Пополнить количество…")
            act_out = menu.addAction("📤 Списать (убрать)…")
            act_move = menu.addAction("📦 Переместить в другую ячейку…")
        if role == "Администратор":
            menu.addSeparator()
            act_del = menu.addAction("🗑 Удалить товар")

        chosen = menu.exec(global_pos)   # <-- единственный вызов exec

        if chosen == act_details:
            return "details"
        if chosen == act_edit:
            return "edit"
        if act_in and chosen == act_in:
            return "in"
        if act_out and chosen == act_out:
            return "out"
        if act_move and chosen == act_move:
            return "move"
        if act_del and chosen == act_del:
            return "delete"
        return None

    def show_message(self, title, msg):
        QMessageBox.information(self, title, msg)

    def show_error(self, title, msg):
        QMessageBox.critical(self, title, msg)

    # ---------- ПОЛЬЗОВАТЕЛИ ----------
    def show_users(self, rows):
        self.tblUsers.setRowCount(0)
        self.tblUsers.setColumnCount(6)
        self.tblUsers.setHorizontalHeaderLabels(
            ["Логин", "ФИО", "Email", "Телефон", "Роль", "Статус"])
        self.tblUsers.setRowCount(len(rows))
        for r, u in enumerate(rows):
            status = "Активен" if u["is_active"] else "Ожидает"
            role = u["role"] or "— не назначена —"
            for c, val in enumerate(
                    [u["login"], u["full_name"] or "", u["email"] or "",
                     u["phone"] or "", role, status]):
                self.tblUsers.setItem(r, c, QTableWidgetItem(str(val)))
        self.tblUsers.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)

    def get_user_form_data(self):
        return {
            "login": self.edtUserLogin.text().strip(),
            "full_name": self.edtUserName.text().strip(),
            "password": self.edtUserPassword.text(),
            "role": self.cmbUserRole.currentText(),
            "is_active": 1 if self.chkUserActive.isChecked() else 0,
        }

    def fill_user_form(self, u):
        self.edtUserLogin.setText(u["login"])
        self.edtUserLogin.setEnabled(False)
        self.edtUserName.setText(u["full_name"] or "")
        self.edtUserPassword.clear()
        if hasattr(self, 'edtUserEmail'):
            self.edtUserEmail.setText(u.get("email") or "")
            self.edtUserEmail.setEnabled(False)
        if hasattr(self, 'edtUserPhone'):
            self.edtUserPhone.setText(u.get("phone") or "")
        i = self.cmbUserRole.findText(u["role"] or "")
        if i >= 0:
            self.cmbUserRole.setCurrentIndex(i)
        self.chkUserActive.setChecked(bool(u["is_active"]))

    def clear_user_form(self):
        self.edtUserLogin.clear()
        self.edtUserLogin.setEnabled(True)
        self.edtUserName.clear()
        self.edtUserPassword.clear()
        if hasattr(self, 'edtUserEmail'):
            self.edtUserEmail.clear()
            self.edtUserEmail.setEnabled(True)
        if hasattr(self, 'edtUserPhone'):
            self.edtUserPhone.clear()
        self.chkUserActive.setChecked(True)

    # ---------- ЗАДАЧИ ----------
    def show_tasks(self, tasks):
        self.lstTasks.blockSignals(True)
        self.lstTasks.clear()
        for t in tasks:
            mark = "✓ " if t.get("done") else "• "
            item = QListWidgetItem(
                f"{mark}{t['name']} [{t.get('priority', '—')}]")
            item.setData(Qt.ItemDataRole.UserRole, t["id"])
            self.lstTasks.addItem(item)
        self.lstTasks.blockSignals(False)

    def fill_task_form(self, t):
        self.edtTaskName.setText(t.get("name") or "")
        i = self.cmbTaskPriority.findText(t.get("priority") or "Средний")
        if i >= 0:
            self.cmbTaskPriority.setCurrentIndex(i)
        due = t.get("due")
        # FIXED: due может быть date, datetime или строкой из MySQL
        if isinstance(due, date):
            self.dtTaskDue.setDate(
                QDate(due.year, due.month, due.day))
        elif isinstance(due, str) and len(due) >= 10:
            try:
                y, m, d = int(due[0:4]), int(due[5:7]), int(due[8:10])
                self.dtTaskDue.setDate(QDate(y, m, d))
            except ValueError:
                self.dtTaskDue.setDate(QDate.currentDate().addDays(7))
        else:
            self.dtTaskDue.setDate(QDate.currentDate().addDays(7))
        self.chkTaskDone.setChecked(bool(t.get("done")))
        self.txtTaskDesc.setPlainText(t.get("description") or "")

    def clear_task_form(self):
        self.edtTaskName.clear()
        self.cmbTaskPriority.setCurrentIndex(1)
        self.dtTaskDue.setDate(QDate.currentDate().addDays(7))
        self.chkTaskDone.setChecked(False)
        self.txtTaskDesc.clear()

    def get_task_form_data(self):
        return {
            "name": self.edtTaskName.text().strip(),
            "priority": self.cmbTaskPriority.currentText(),
            "due": self.dtTaskDue.date().toPyDate(),
            "description": self.txtTaskDesc.toPlainText().strip(),
            "done": self.chkTaskDone.isChecked(),
        }

    # ---------- ЗАМЕТКИ ----------
    def show_notes(self, notes):
        self.lstNotes.blockSignals(True)
        self.lstNotes.clear()
        for n in notes:
            item = QListWidgetItem(n.get("title") or f"Заметка #{n['id']}")
            item.setData(Qt.ItemDataRole.UserRole, n["id"])
            self.lstNotes.addItem(item)
        self.lstNotes.blockSignals(False)

    def fill_note_content(self, n):
        self.txtNoteContent.setPlainText(n.get("content") or "")
        if hasattr(self, 'edtNoteTitle'):
            self.edtNoteTitle.setText(n.get("title") or "")
        if hasattr(self, 'lblNoteModified'):
            m = n.get("modified")
            if m and hasattr(m, "strftime"):
                self.lblNoteModified.setText(
                    f"Изменено: {m.strftime('%d.%m.%Y %H:%M')}")
            elif m:
                self.lblNoteModified.setText(f"Изменено: {m}")
            else:
                self.lblNoteModified.setText("Изменено: —")

    def clear_note_content(self):
        self.txtNoteContent.clear()
        if hasattr(self, 'edtNoteTitle'):
            self.edtNoteTitle.clear()
        if hasattr(self, 'lblNoteModified'):
            self.lblNoteModified.setText("Изменено: —")

    def get_note_title(self):
        if hasattr(self, 'edtNoteTitle'):
            return self.edtNoteTitle.text().strip()
        return ""