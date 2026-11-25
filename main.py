import sys
from PyQt6.QtWidgets import QApplication

from model import Database
from view import LoginView, RegisterView
from controller import AuthController


class App:
    """Корневой контроллер: переключает окна."""
    def __init__(self):
        self.db = Database()
        self.db.init_db()
        self.db.connect()

        self.login_view = LoginView()
        self.register_view = RegisterView()
        self.auth = AuthController(self)
        self.main = None

        self.login_view.bind(self.auth)
        self.register_view.bind(self.auth)

    def start(self):
        self.login_view.show()

    def on_login_success(self, user):
        self.login_view.clear()
        self.login_view.hide()
        self.main = MainControllerWrapper(self, user)
        self.main.view.show()

    def logout(self):
        self.main = None
        self.login_view.show()
        self.login_view.raise_()
        self.login_view.activateWindow()


class MainControllerWrapper:
    """Обёртка, чтобы не тянуть импорт MainController в шапку main.py."""
    def __init__(self, app, user):
        from controller import MainController
        self._impl = MainController(app, user)
        self.view = self._impl.view


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Инвентаризация магазина")
    root = App()
    root.start()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
