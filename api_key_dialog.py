"""
API Key Dialog for FS25 Language Translator
Secure dialog for entering and managing API keys
"""

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *


class ApiKeyDialog(QDialog):
    """Dialog for entering and managing API keys"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("API Key Configuration")
        self.setModal(True)
        self.setFixedWidth(500)
        
        # Main layout
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = QLabel("🔐 Secure API Key Storage")
        header.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #4CAF50;
                padding: 10px;
                background: rgba(76, 175, 80, 0.1);
                border-radius: 8px;
            }
        """)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # Information text
        info_text = (
            "Your API key will be securely stored in your system's credential manager:\n"
            "• Windows: Windows Credential Manager\n"
            "• macOS: Keychain\n"
            "• Linux: Secret Service\n\n"
            "The key is encrypted and protected by your system."
        )
        
        info_label = QLabel(info_text)
        info_label.setWordWrap(True)
        info_label.setStyleSheet("""
            QLabel {
                color: #cccccc;
                padding: 10px;
                background: #2a2a2a;
                border-radius: 8px;
                font-size: 12px;
            }
        """)
        layout.addWidget(info_label)
        
        # API Key input group
        key_group = QGroupBox("DeepL API Key")
        key_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #4CAF50;
                border-radius: 8px;
                margin-top: 20px;
                padding-top: 25px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 20px;
                padding: 5px 10px;
                color: white;
                background: #4CAF50;
                border-radius: 4px;
            }
        """)
        
        key_layout = QVBoxLayout()
        
        # Input field
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("Paste your DeepL API key here...")
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_input.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                font-size: 14px;
                border: 1px solid #3a3a3a;
                border-radius: 6px;
                background: #1e1e1e;
                color: white;
            }
            QLineEdit:focus {
                border: 1px solid #4CAF50;
            }
        """)
        key_layout.addWidget(self.key_input)
        
        # Show/Hide checkbox
        self.show_key_cb = QCheckBox("Show API key")
        self.show_key_cb.setStyleSheet("""
            QCheckBox {
                color: #cccccc;
                padding: 5px;
            }
        """)
        self.show_key_cb.toggled.connect(self.toggle_key_visibility)
        key_layout.addWidget(self.show_key_cb)
        
        # Link to DeepL
        deepl_link = QLabel('<a href="https://www.deepl.com/your-account/keys" style="color: #4CAF50;">Get your DeepL API key here</a>')
        deepl_link.setOpenExternalLinks(True)
        deepl_link.setStyleSheet("padding: 5px;")
        key_layout.addWidget(deepl_link)
        
        key_group.setLayout(key_layout)
        layout.addWidget(key_group)
        
        # Skip button (use Google only)
        skip_btn = QPushButton("Skip (Use Google Translate only)")
        skip_btn.setStyleSheet("""
            QPushButton {
                padding: 8px;
                background: #666666;
                border: none;
                border-radius: 6px;
                color: white;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #777777;
            }
        """)
        skip_btn.clicked.connect(self.reject)
        layout.addWidget(skip_btn)
        
        # Button box
        buttons = QDialogButtonBox()
        
        save_btn = buttons.addButton("Save Key", QDialogButtonBox.ButtonRole.AcceptRole)
        save_btn.setStyleSheet("""
            QPushButton {
                padding: 10px 20px;
                background: #4CAF50;
                border: none;
                border-radius: 6px;
                color: white;
                font-weight: bold;
                font-size: 14px;
                min-width: 100px;
            }
            QPushButton:hover {
                background: #5cbf60;
            }
        """)
        
        cancel_btn = buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        cancel_btn.setStyleSheet("""
            QPushButton {
                padding: 10px 20px;
                background: #666666;
                border: none;
                border-radius: 6px;
                color: white;
                font-weight: bold;
                font-size: 14px;
                min-width: 100px;
            }
            QPushButton:hover {
                background: #777777;
            }
        """)
        
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        
        layout.addWidget(buttons)
        
        self.setLayout(layout)
        
        # Set dark theme for dialog
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
            }
        """)
    
    def toggle_key_visibility(self, checked):
        """Toggle visibility of the API key input"""
        if checked:
            self.key_input.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
    
    def validate_and_accept(self):
        """Validate the API key before accepting"""
        api_key = self.key_input.text().strip()
        
        if not api_key:
            QMessageBox.warning(self, "Invalid Key", "Please enter an API key.")
            return
        
        # Basic validation
        if len(api_key) < 20:
            reply = QMessageBox.question(
                self,
                "Short API Key",
                "This API key seems unusually short. Continue anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
        
        self.accept()
    
    def get_api_key(self) -> str:
        """Get the entered API key"""
        return self.key_input.text().strip()