"""
Visualização da aba de Configurações do aplicativo.
"""
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ...core.models import AppConfig


class SettingsView(QWidget):
    settings_saved = pyqtSignal(object)
    test_notification_requested = pyqtSignal()

    def __init__(self, config: AppConfig, parent: QWidget = None):
        super().__init__(parent)
        self.config = config
        self._init_ui()
        self.load_config(config)

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(18)

        # 1. Repositórios Monitorados
        repo_group = QGroupBox("Repositórios do GitHub Monitorados")
        repo_group.setStyleSheet("QGroupBox { font-weight: bold; color: #89b4fa; }")
        repo_layout = QVBoxLayout(repo_group)

        self.repo_list = QListWidget()
        self.repo_list.setStyleSheet(
            "QListWidget { background-color: #181825; border: 1px solid #313244; "
            "border-radius: 6px; padding: 6px; } "
            "QListWidget::item { padding: 6px; border-radius: 4px; } "
            "QListWidget::item:selected { background-color: #3b82f6; color: white; }"
        )
        self.repo_list.setFixedHeight(140)
        repo_layout.addWidget(self.repo_list)

        add_repo_layout = QHBoxLayout()
        self.new_repo_input = QLineEdit()
        self.new_repo_input.setPlaceholderText("Ex: facebook/react ou usuario/meu-repo")
        self.new_repo_input.returnPressed.connect(self._add_repo)
        add_repo_layout.addWidget(self.new_repo_input)

        add_btn = QPushButton("➕ Adicionar")
        add_btn.setProperty("class", "actionButton")
        add_btn.clicked.connect(self._add_repo)
        add_repo_layout.addWidget(add_btn)

        remove_btn = QPushButton("🗑️ Remover Selecionado")
        remove_btn.setProperty("class", "actionButton")
        remove_btn.clicked.connect(self._remove_repo)
        add_repo_layout.addWidget(remove_btn)

        repo_layout.addLayout(add_repo_layout)
        layout.addWidget(repo_group)

        # 2. Token GitHub
        token_group = QGroupBox("Autenticação GitHub (Opcional)")
        token_group.setStyleSheet("QGroupBox { font-weight: bold; color: #89b4fa; }")
        token_layout = QVBoxLayout(token_group)

        token_desc = QLabel(
            "O token de acesso pessoal aumenta o limite de requisições da API de 60 para 5.000 por hora "
            "e permite monitorar repositórios privados."
        )
        token_desc.setWordWrap(True)
        token_desc.setStyleSheet("color: #a6adc8; font-size: 11px;")
        token_layout.addWidget(token_desc)

        token_input_layout = QHBoxLayout()
        self.token_input = QLineEdit()
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_input.setPlaceholderText("ghp_xxxxxxxxxxxxxxxxxxxx")
        token_input_layout.addWidget(self.token_input)

        self.toggle_token_btn = QPushButton("👁️")
        self.toggle_token_btn.setFixedWidth(40)
        self.toggle_token_btn.setProperty("class", "actionButton")
        self.toggle_token_btn.clicked.connect(self._toggle_token_visibility)
        token_input_layout.addWidget(self.toggle_token_btn)

        token_layout.addLayout(token_input_layout)
        layout.addWidget(token_group)

        # 3. Integração com o Jira
        jira_group = QGroupBox("Integração com o Atlassian Jira")
        jira_group.setStyleSheet("QGroupBox { font-weight: bold; color: #89b4fa; }")
        jira_layout = QVBoxLayout(jira_group)
        jira_layout.setSpacing(10)

        self.jira_enabled_check = QCheckBox("Habilitar aba e monitoramento de tarefas do Jira")
        self.jira_enabled_check.setStyleSheet("font-weight: 500;")
        jira_layout.addWidget(self.jira_enabled_check)

        jira_desc = QLabel(
            "Permite acompanhar suas tarefas atribuídas no Jira com notificações ao receber novos itens.\n"
            "Gere seu API Token em: id.atlassian.com/manage-profile/security/api-tokens"
        )
        jira_desc.setWordWrap(True)
        jira_desc.setStyleSheet("color: #a6adc8; font-size: 11px;")
        jira_layout.addWidget(jira_desc)

        jira_form = QGridLayout()
        jira_form.setSpacing(8)

        # URL
        jira_form.addWidget(QLabel("URL do Jira:"), 0, 0)
        self.jira_url_input = QLineEdit()
        self.jira_url_input.setPlaceholderText("https://sua-empresa.atlassian.net")
        jira_form.addWidget(self.jira_url_input, 0, 1, 1, 2)

        # Email
        jira_form.addWidget(QLabel("E-mail Atlassian:"), 1, 0)
        self.jira_email_input = QLineEdit()
        self.jira_email_input.setPlaceholderText("usuario@empresa.com")
        jira_form.addWidget(self.jira_email_input, 1, 1, 1, 2)

        # Token
        jira_form.addWidget(QLabel("API Token:"), 2, 0)
        self.jira_token_input = QLineEdit()
        self.jira_token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.jira_token_input.setPlaceholderText("Cole o API Token do Atlassian aqui...")
        jira_form.addWidget(self.jira_token_input, 2, 1)

        self.toggle_jira_token_btn = QPushButton("👁️")
        self.toggle_jira_token_btn.setFixedWidth(40)
        self.toggle_jira_token_btn.setProperty("class", "actionButton")
        self.toggle_jira_token_btn.clicked.connect(self._toggle_jira_token_visibility)
        jira_form.addWidget(self.toggle_jira_token_btn, 2, 2)

        # JQL
        jira_form.addWidget(QLabel("Filtro JQL:"), 3, 0)
        self.jira_jql_input = QLineEdit()
        self.jira_jql_input.setPlaceholderText("assignee = currentUser() AND resolution = Unresolved ORDER BY updated DESC")
        jira_form.addWidget(self.jira_jql_input, 3, 1, 1, 2)

        jira_layout.addLayout(jira_form)
        layout.addWidget(jira_group)

        # 4. Preferências Gerais
        pref_group = QGroupBox("Preferências do Sistema e Notificações")
        pref_group.setStyleSheet("QGroupBox { font-weight: bold; color: #89b4fa; }")
        pref_layout = QGridLayout(pref_group)
        pref_layout.setSpacing(12)

        # Intervalo de atualização
        pref_layout.addWidget(QLabel("Intervalo de Atualização Automática (minutos):"), 0, 0)
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 120)
        self.interval_spin.setValue(5)
        self.interval_spin.setStyleSheet(
            "background-color: #313244; color: #cdd6f4; border: 1px solid #45475a; "
            "border-radius: 6px; padding: 4px;"
        )
        pref_layout.addWidget(self.interval_spin, 0, 1)

        # Notificações Desktop
        self.notify_check = QCheckBox("Habilitar notificações desktop ao detectar novas PRs")
        self.notify_check.setChecked(True)
        pref_layout.addWidget(self.notify_check, 1, 0, 1, 2)

        # Minimizar para bandeja
        self.tray_check = QCheckBox("Minimizar para a barra/bandeja ao clicar no botão fechar (X)")
        self.tray_check.setChecked(True)
        pref_layout.addWidget(self.tray_check, 2, 0, 1, 2)

        # Botão Testar Notificação
        test_notify_btn = QPushButton("🔔 Testar Notificação do Debian / GNOME")
        test_notify_btn.setProperty("class", "actionButton")
        test_notify_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        test_notify_btn.clicked.connect(self.test_notification_requested.emit)
        pref_layout.addWidget(test_notify_btn, 3, 0, 1, 2)

        layout.addWidget(pref_group)

        # 4. Botão Salvar
        save_layout = QHBoxLayout()
        save_layout.addStretch()

        self.save_btn = QPushButton("💾 Salvar Configurações")
        self.save_btn.setProperty("class", "primaryButton")
        self.save_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.save_btn.clicked.connect(self._save)
        save_layout.addWidget(self.save_btn)

        layout.addLayout(save_layout)
        layout.addStretch()

        scroll.setWidget(content)
        root_layout.addWidget(scroll)

    def load_config(self, config: AppConfig):
        self.config = config
        self.repo_list.clear()
        for repo in config.repositories:
            self.repo_list.addItem(QListWidgetItem(repo))

        self.token_input.setText(config.github_token)
        self.interval_spin.setValue(config.refresh_interval_minutes)
        self.notify_check.setChecked(config.notifications_enabled)
        self.tray_check.setChecked(config.minimize_to_tray_on_close)

        # Jira
        self.jira_enabled_check.setChecked(config.jira_enabled)
        self.jira_url_input.setText(config.jira_url)
        self.jira_email_input.setText(config.jira_email)
        self.jira_token_input.setText(config.jira_api_token)
        self.jira_jql_input.setText(config.jira_jql)

    def _add_repo(self):
        text = self.new_repo_input.text().strip()
        if text and "/" in text:
            # Evita duplicados
            items = [self.repo_list.item(i).text() for i in range(self.repo_list.count())]
            if text not in items:
                self.repo_list.addItem(QListWidgetItem(text))
                self.new_repo_input.clear()

    def _remove_repo(self):
        current_row = self.repo_list.currentRow()
        if current_row >= 0:
            self.repo_list.takeItem(current_row)

    def _toggle_token_visibility(self):
        if self.token_input.echoMode() == QLineEdit.EchoMode.Password:
            self.token_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_token_btn.setText("🔒")
        else:
            self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_token_btn.setText("👁️")

    def _toggle_jira_token_visibility(self):
        if self.jira_token_input.echoMode() == QLineEdit.EchoMode.Password:
            self.jira_token_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_jira_token_btn.setText("🔒")
        else:
            self.jira_token_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_jira_token_btn.setText("👁️")

    def _save(self):
        repos = [self.repo_list.item(i).text() for i in range(self.repo_list.count())]
        new_config = AppConfig(
            github_token=self.token_input.text().strip(),
            repositories=repos,
            refresh_interval_minutes=self.interval_spin.value(),
            sort_order=self.config.sort_order,
            notifications_enabled=self.notify_check.isChecked(),
            minimize_to_tray_on_close=self.tray_check.isChecked(),
            start_minimized=self.config.start_minimized,
            dark_mode=self.config.dark_mode,
            skip_permissions=self.config.skip_permissions,
            jira_enabled=self.jira_enabled_check.isChecked(),
            jira_url=self.jira_url_input.text().strip(),
            jira_email=self.jira_email_input.text().strip(),
            jira_api_token=self.jira_token_input.text().strip(),
            jira_jql=self.jira_jql_input.text().strip() or "assignee = currentUser() AND resolution = Unresolved ORDER BY updated DESC"
        )
        self.config = new_config
        self.settings_saved.emit(new_config)
