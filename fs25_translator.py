#!/usr/bin/env python3
"""
FS25 Language Translator
A tool for translating Farming Simulator 25 language files to multiple languages.
"""

import sys
import certifi
import ssl
import base64
import os
import json
import time
import re
import copy
import keyring
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import traceback
from datetime import datetime
from html import escape

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

import deepl
from googletrans import Translator as GoogleTranslator
from api_key_dialog import ApiKeyDialog

if sys.version_info < (3, 9):
    try:
        from ctypes import windll
        windll.user32.MessageBoxW(None, "Python 3.9+ required (uses ET.indent).", "FS25 Translator", 0x10)
    except Exception:
        print("Python 3.9+ required (uses ET.indent).")
    raise SystemExit(1)

def resource_path(rel: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / rel

# Language mapping configuration
LANGUAGE_MAP = {
    'l10n_br': {'deepl': 'PT-BR', 'google': 'pt', 'name': 'Portuguese (Brazil)'},
    'l10n_cs': {'deepl': 'CS', 'google': 'cs', 'name': 'Czech'},
    'l10n_ct': {'deepl': None, 'google': 'ca', 'name': 'Catalan'},
    'l10n_da': {'deepl': 'DA', 'google': 'da', 'name': 'Danish'},
    'l10n_de': {'deepl': 'DE', 'google': 'de', 'name': 'German'},
    'l10n_ea': {'deepl': 'ES', 'google': 'es', 'name': 'Spanish (Latin America)'},
    'l10n_en': {'deepl': 'EN-US', 'google': 'en', 'name': 'English'},
    'l10n_es': {'deepl': 'ES', 'google': 'es', 'name': 'Spanish (Spain)'},
    'l10n_fc': {'deepl': 'FR', 'google': 'fr', 'name': 'French (Canada)'},
    'l10n_fi': {'deepl': 'FI', 'google': 'fi', 'name': 'Finnish'},
    'l10n_fr': {'deepl': 'FR', 'google': 'fr', 'name': 'French (France)'},
    'l10n_hu': {'deepl': 'HU', 'google': 'hu', 'name': 'Hungarian'},
    'l10n_id': {'deepl': 'ID', 'google': 'id', 'name': 'Indonesian'},
    'l10n_it': {'deepl': 'IT', 'google': 'it', 'name': 'Italian'},
    'l10n_jp': {'deepl': 'JA', 'google': 'ja', 'name': 'Japanese'},
    'l10n_kr': {'deepl': 'KO', 'google': 'ko', 'name': 'Korean'},
    'l10n_nl': {'deepl': 'NL', 'google': 'nl', 'name': 'Dutch'},
    'l10n_no': {'deepl': 'NB', 'google': 'no', 'name': 'Norwegian'},
    'l10n_pl': {'deepl': 'PL', 'google': 'pl', 'name': 'Polish'},
    'l10n_pt': {'deepl': 'PT-PT', 'google': 'pt', 'name': 'Portuguese (Portugal)'},
    'l10n_ro': {'deepl': 'RO', 'google': 'ro', 'name': 'Romanian'},
    'l10n_ru': {'deepl': 'RU', 'google': 'ru', 'name': 'Russian'},
    'l10n_sv': {'deepl': 'SV', 'google': 'sv', 'name': 'Swedish'},
    'l10n_tr': {'deepl': 'TR', 'google': 'tr', 'name': 'Turkish'},
    'l10n_uk': {'deepl': 'UK', 'google': 'uk', 'name': 'Ukrainian'},
    'l10n_vi': {'deepl': None, 'google': 'vi', 'name': 'Vietnamese'},
}

FLAG_BY_L10N = {
    "l10n_br": "br",   # Portuguese (Brazil)
    "l10n_cs": "cz",
    "l10n_ct": "ad",   # Catalan -> Andorra
    "l10n_da": "dk",
    "l10n_de": "de",
    "l10n_ea": "mx",   # Spanish (Latin America) -> Mexico as proxy
    "l10n_en": "us",
    "l10n_es": "es",
    "l10n_fc": "ca",   # French (Canada)
    "l10n_fi": "fi",
    "l10n_fr": "fr",
    "l10n_hu": "hu",
    "l10n_id": "id",
    "l10n_it": "it",
    "l10n_jp": "jp",
    "l10n_kr": "kr",
    "l10n_nl": "nl",
    "l10n_no": "no",
    "l10n_pl": "pl",
    "l10n_pt": "pt",
    "l10n_ro": "ro",
    "l10n_ru": "ru",
    "l10n_sv": "se",
    "l10n_tr": "tr",
    "l10n_uk": "ua",   # Ukrainian -> UA (important: not UK)
    "l10n_vi": "vn",
}

class TranslationWorker(QThread):
    """Worker thread for handling translations"""

    PLACEHOLDER_RE = re.compile(r'(%\d*\$?[sd]|%\w|{\w+}|\{\d+\})')
    
    progress_update = pyqtSignal(int, int)  # current, total
    status_update = pyqtSignal(str)
    log_message = pyqtSignal(str, str)  # message, level (info/warning/error/success)
    language_completed = pyqtSignal(str, bool, str)  # language, success, service_used
    finished_all = pyqtSignal()
    
    def __init__(self, xml_file_path: str, output_dir: str, api_keys: dict, selected_languages: list):
        super().__init__()
        self.xml_file_path = xml_file_path
        self.output_dir = output_dir
        self.api_keys = api_keys
        self.selected_languages = selected_languages
        self.deepl_translator = None
        self.google_translator = None
        self._is_running = True
        self.source_google = "auto"  # Google: 'auto' => autodetect
        self.source_deepl  = None    # DeepL: None  => autodetect (ingen source_lang skickas)
    
    def stop(self):
        """Stop the translation process"""
        self._is_running = False
        
    def init_translators(self) -> None:
        """Initialize translation services"""
        try:
            if self.api_keys.get('deepl_api_key') and self.api_keys['deepl_api_key'] != "YOUR_DEEPL_API_KEY_HERE":
                self.deepl_translator = deepl.Translator(self.api_keys['deepl_api_key'])
                self.log_message.emit("DeepL API initialized successfully", "success")
            else:
                self.log_message.emit("DeepL API key not found, using Google Translate as primary", "warning")
        except deepl.AuthenticationException as e:
            self.log_message.emit(f"DeepL API key invalid: {str(e)}", "error")
        except deepl.QuotaExceededException as e:
            self.log_message.emit(f"DeepL quota exceeded: {str(e)}", "error")
        except Exception as e:
            self.log_message.emit(f"Unexpected DeepL error: {str(e)}", "error")
            
        try:
            self.google_translator = GoogleTranslator()
            self.log_message.emit("Google Translate initialized successfully", "success")
        except Exception as e:
            self.log_message.emit(f"Failed to initialize Google Translate: {str(e)}", "error")
    
    def safe_google_translate(self, text: str, src: str, dest: str, retries: int = 2, delay: float = 0.4):
        """Robust wrapper around googletrans.translate: tolerates None/broken responses, retries and reinitializes on error."""
        if not self.google_translator:
            return None
        last_exc = None
        for attempt in range(retries + 1):
            try:
                r = self.google_translator.translate(text, src=src, dest=dest)
                if r and getattr(r, "text", None):
                    return r.text
            except Exception as e:
                last_exc = e
                # restart and try again
                try:
                    self.google_translator = GoogleTranslator()
                except Exception:
                    pass
            if delay and attempt < retries:
                time.sleep(delay)
        # Log why it went wrong (in general)
        if last_exc:
            self.log_message.emit(
                f"Google Translate error ({dest}) for '{escape(text)}': {escape(str(last_exc))}", "warning"
            )
        return None
    
    @staticmethod
    def _same(a: str, b: str) -> bool:
        return a.strip().casefold() == b.strip().casefold()

    def freeze_placeholders(self, s: str):
        tokens, out, idx = [], [], 0
        for m in self.PLACEHOLDER_RE.finditer(s):
            out.append(s[idx:m.start()])
            tokens.append(m.group(0))
            out.append(f'__PH_{len(tokens)-1}__')
            idx = m.end()
        out.append(s[idx:])
        return ''.join(out), tokens

    def restore_placeholders(self, s: str, tokens):
        for i, tok in enumerate(tokens):
            s = s.replace(f'__PH_{i}__', tok)
        return s

    def translate_text(
        self, 
        text: str, 
        target_lang_code: str, 
        lang_info: Dict[str, Optional[str]]
    ) -> Tuple[Optional[str], str]:
        """
            Translate text using available translation services.
    
            Args:
                text: Source text to translate
                target_lang_code: Target language code (e.g., 'l10n_sv')
                lang_info: Dictionary with language service mappings
        
            Returns:
                Tuple of (translated_text, service_used)
                Returns (None, "failed") if translation fails
        
            Raises:        
                None - all exceptions are handled internally
        """
        if not text or not text.strip():
            return text, "none"

        original_text = text.strip()

        # --- Freeze placeholders first ---
        frozen, ph_tokens = self.freeze_placeholders(original_text)

        # DeepL first (use explicit source if provided; otherwise let DeepL auto-detect by omitting source_lang)
        if self.deepl_translator and lang_info.get('deepl'):
            try:
                if getattr(self, "source_deepl", None):
                    result = self.deepl_translator.translate_text(
                        frozen, target_lang=lang_info['deepl'], source_lang=self.source_deepl
                    )
                else:
                    result = self.deepl_translator.translate_text(
                        frozen, target_lang=lang_info['deepl']
                    )
                translated = self.restore_placeholders(result.text, ph_tokens) if result and getattr(result, "text", None) else None
                if translated and translated.strip():
                    return translated, "DeepL"
            except Exception as e:
                self.log_message.emit(
                    f"DeepL translation failed for {lang_info['name']}: {str(e)}. Falling back to Google Translate",
                    "warning"
                )

        # Google fallback - always translate `frozen` with selected/auto source
        if self.google_translator and lang_info.get('google'):
            src_code = getattr(self, "source_google", "auto") or "auto"

            translated_text = self.safe_google_translate(frozen, src=src_code, dest=lang_info['google'])

            if not translated_text:
                t1 = self.safe_google_translate(f"Please translate: {frozen}", src=src_code, dest=lang_info['google'])
                if t1:
                    translated_text = t1.split(":", 1)[-1].strip()

            if not translated_text or self._same(translated_text, frozen):
                t2 = self.safe_google_translate(f"({frozen})", src=src_code, dest=lang_info['google'])
                if t2:
                    translated_text = t2.strip("()").strip()

            if not translated_text or self._same(translated_text, frozen):
                t3 = self.safe_google_translate(f'Say "{frozen}" in {lang_info["name"]}', src=src_code, dest=lang_info['google'])
                if t3:
                    quotes = re.findall(r'"([^"]*)"', t3)
                    translated_text = quotes[0] if quotes else t3.replace('"', '').strip()

            if not translated_text or self._same(translated_text, frozen):
                t4 = self.safe_google_translate(f"The word is: {frozen}.", src=src_code, dest=lang_info['google'])
                if t4:
                    translated_text = t4.split(":", 1)[-1].strip().rstrip(".")

            if not translated_text or self._same(translated_text, frozen):
                return None, "failed"

            # restore before returning
            translated_text = self.restore_placeholders(translated_text, ph_tokens)
            return translated_text, "Google"

        return None, "failed"
    
    def translate_xml_element(self, element: ET.Element, target_lang_code: str, lang_info: dict, service_used_set: set):
        """Recursively translate XML element text and attributes - DRY + escaped logs"""

        # Resolve and escape the key once for this element
        key_name = element.attrib.get('name', element.attrib.get('k', '?'))
        key_name_esc = escape(key_name)

        # Small helper for safe, short previews in HTML log
        def esc_preview(s: str, limit: int = 120) -> str:
            if not s:
                return ""
            s = s if len(s) <= limit else s[:limit] + "..."
            return escape(s)

        # 1) FS l10n: translate 'v' attribute
        if 'v' in element.attrib:
            text_to_translate = element.attrib['v']
            if text_to_translate and text_to_translate.strip():
                translated, service = self.translate_text(text_to_translate, target_lang_code, lang_info)
                if translated is None:
                    self.log_message.emit(
                        f"Translation FAILED for {lang_info['name']} - key='{key_name_esc}', value='{esc_preview(text_to_translate)}'. Keeping original.",
                        "warning"
                    )
                else:
                    element.set('v', translated)
                    service_used_set.add(service)

        # 2) Element text (rare in your files, but supported)
        if element.text and element.text.strip():
            translated, service = self.translate_text(element.text, target_lang_code, lang_info)
            if translated is None:
                self.log_message.emit(
                    f"Translation FAILED for {lang_info['name']} - key='{key_name_esc}', element.text='{esc_preview(element.text)}'. Keeping original.",
                    "warning"
                )
            else:
                element.text = translated
                service_used_set.add(service)
        else:
            # Keep as None to preserve self-closing form when applicable
            element.text = None

        # 3) Other text-like attributes
        text_attributes = ['text', 'value', 'description', 'tooltip', 'title', 'label', 'caption']
        for attr_name in text_attributes:
            if attr_name in element.attrib and attr_name != 'v':
                attr_value = element.attrib[attr_name]
                if attr_value and attr_value.strip():
                    translated, service = self.translate_text(attr_value, target_lang_code, lang_info)
                    if translated is None:
                        self.log_message.emit(
                            f"Translation FAILED for {lang_info['name']} - key='{key_name_esc}', attr='{attr_name}', value='{esc_preview(attr_value)}'. Keeping original.",
                            "warning"
                        )
                    else:
                        element.set(attr_name, translated)
                        service_used_set.add(service)

        # 4) Recurse into children
        for child in element:
            if not self._is_running:
                break
            self.translate_xml_element(child, target_lang_code, lang_info, service_used_set)
    
    def run(self):
        """Main translation process"""
        try:
            self.log_message.emit("Starting translation process...", "info")
            self.init_translators()

            if not self.deepl_translator and not self.google_translator:
                self.log_message.emit("No translation services available!", "error")
                return

            # Log selected source-language behavior (auto or explicit)
            src_desc = f"Google src={self.source_google or 'auto'}, DeepL src={self.source_deepl or 'auto'}"
            self.log_message.emit(f"Using source language settings: {src_desc}", "info")

            # Ensure output_dir is set (fallback if not already set by UI)
            try:
                from pathlib import Path
                if not getattr(self, "output_dir", None):
                    src_dir = Path(self.xml_file_path).resolve().parent
                    out = src_dir if src_dir.name.lower() == "l10n" else (src_dir / "l10n")
                    out.mkdir(parents=True, exist_ok=True)
                    self.output_dir = str(out)
            except Exception as e:
                self.log_message.emit(f"Failed to prepare output folder: {str(e)}", "error")
                return

            # Parse the source XML
            self.status_update.emit("Parsing source XML file...")
            tree = ET.parse(self.xml_file_path)
            root = tree.getroot()

            total_languages = len(self.selected_languages)

            for idx, lang_code in enumerate(self.selected_languages):
                if not self._is_running:
                    self.log_message.emit("Translation process stopped by user", "warning")
                    break

                lang_info = LANGUAGE_MAP[lang_code]
                self.status_update.emit(f"Translating to {lang_info['name']}...")
                self.log_message.emit(f"Starting translation for {lang_info['name']}", "info")

                try:
                    import copy
                    lang_root = copy.deepcopy(root)

                    # Track which service(s) were used for this language
                    service_used_set = set()

                    # Translate the XML content (attributes/text); this populates service_used_set
                    self.translate_xml_element(lang_root, lang_code, lang_info, service_used_set)

                    if not self._is_running:
                        break

                    # -------------------------
                    # Save translated XML file
                    # -------------------------
                    output_path = Path(self.output_dir) / f"{lang_code}.xml"

                    # 1) Write a first pass (pretty-printed, with xml declaration)
                    lang_tree = ET.ElementTree(lang_root)
                    ET.indent(lang_tree, space="    ")
                    with open(output_path, 'wb') as f:
                        lang_tree.write(f, encoding='utf-8', xml_declaration=True)

                    # 2) Read original + just-written file
                    with open(self.xml_file_path, 'r', encoding='utf-8') as f:
                        original_content = f.read()
                    with open(output_path, 'r', encoding='utf-8') as f:
                        translated_content = f.read()

                    # 3) Post-process: tidy self-closing tags and preserve original XML declaration
                    translated_content = re.sub(r'(<[^>]+?)\s*/>', r'\1/>', translated_content)

                    original_decl_match   = re.match(r'^\ufeff?\s*<\?xml[^>]*\?>', original_content)
                    translated_decl_match = re.match(r'^\ufeff?\s*<\?xml[^>]*\?>', translated_content)
                    if original_decl_match and translated_decl_match:
                        translated_content = translated_content.replace(
                            translated_decl_match.group(0),
                            original_decl_match.group(0)
                        )

                    # 4) Write back the cleaned content and log absolute path
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(translated_content)
                    self.log_message.emit(f"Saved: {output_path}", "success")

                    # Determine primary service used
                    if "DeepL" in service_used_set:
                        service_used = "DeepL"
                    elif "Google" in service_used_set:
                        service_used = "Google Translate"
                    else:
                        service_used = "None"

                    self.log_message.emit(
                        f"Successfully translated {lang_info['name']} using {service_used}",
                        "success"
                    )
                    self.language_completed.emit(lang_code, True, service_used)

                except Exception as e:
                    self.log_message.emit(
                        f"Failed to translate {lang_info['name']}: {str(e)}",
                        "error"
                    )
                    self.language_completed.emit(lang_code, False, "Failed")

                # Per-language progress
                self.progress_update.emit(idx + 1, total_languages)

            if self._is_running:
                self.status_update.emit("Translation completed!")
                self.log_message.emit("All translations completed successfully!", "success")
            else:
                self.status_update.emit("Translation stopped")

        except Exception as e:
            self.log_message.emit(f"Critical error: {str(e)}\n{traceback.format_exc()}", "error")
            self.status_update.emit("Translation failed!")
        finally:
            self.finished_all.emit()

class MainWindow(QMainWindow):
    """Main application window"""

    SERVICE_NAME = "FS25_Translator"  # Service identifier for keyring
    
    def __init__(self):
        super().__init__()
        self.worker = None
        self.api_keys = {}
        self.source_file = None
        self.ultrawide_positioning = False  # Flag for ultrawide positioning
        self.target_x = None  # Store target position
        self.target_y = None
        self.init_ui()
        self.load_api_keys()
    
    def load_api_keys(self):
        """Load API keys from system keyring with fallback"""
        try:
            import keyring
            deepl_key = keyring.get_password(self.SERVICE_NAME, "deepl_api_key")
            if deepl_key:
                self.api_keys = {"deepl_api_key": deepl_key}
                self.add_log("API keys loaded from secure storage", "success")
                self.update_api_status(True)
            else:
                self.add_log("No API keys found in secure storage", "info")
                self.update_api_status(False)
                QTimer.singleShot(500, self.prompt_for_api_key)
        except ImportError:
            # Keyring not available in EXE
            self.add_log("Keyring service not available, using alternative storage", "warning")
            self.load_from_config_file()
        except Exception as e:
            self.add_log(f"Keyring error: {str(e)}, using alternative storage", "warning")
            self.load_from_config_file()

    def load_from_config_file(self):
        """Fallback method using local encrypted config"""
        config_path = Path.home() / ".fs25_translator" / "config.dat"
        if config_path.exists():
            try:
                # Simple obfuscation (you should use proper encryption)
                with open(config_path, 'rb') as f:
                    encoded = f.read()
                    decoded = base64.b64decode(encoded).decode('utf-8')
                    self.api_keys = {"deepl_api_key": decoded}
                    self.update_api_status(True)
            except Exception:
                self.update_api_status(False)
        else:
            self.update_api_status(False)
            QTimer.singleShot(500, self.prompt_for_api_key)

    def save_to_config_file(self, api_key: str):
        """Save to local config as fallback"""
        config_dir = Path.home() / ".fs25_translator"
        config_dir.mkdir(exist_ok=True)
        config_path = config_dir / "config.dat"
    
        encoded = base64.b64encode(api_key.encode('utf-8'))
        with open(config_path, 'wb') as f:
            f.write(encoded)
    
    def save_api_key(self, api_key: str):
        """Save API key to system keyring or fallback"""
        try:
            import keyring
            keyring.set_password(self.SERVICE_NAME, "deepl_api_key", api_key)
            self.add_log("API key saved to secure storage", "success")
        except (ImportError, Exception) as e:
            # Fallback to config file if keyring fails
            self.save_to_config_file(api_key)
            self.add_log("API key saved to local storage", "success")
    
    def prompt_for_api_key(self):
        """Show dialog to input API key"""
        dialog = ApiKeyDialog(self)
        if dialog.exec():
            api_key = dialog.get_api_key()
            if api_key:
                self.save_api_key(api_key)
                self.api_keys = {"deepl_api_key": api_key}
                self.update_api_status(True)
    
    def update_api_status(self, has_valid_key: bool):
        """Update the API status indicator"""
        if hasattr(self, 'api_status_label'):
            if has_valid_key:
                self.api_status_label.setText("⚡ DeepL + Google Ready")
                self.api_status_label.setStyleSheet("""
                    QLabel {
                        color: #4CAF50;
                        font-size: 12px;
                        font-weight: bold;
                        background: rgba(76, 175, 80, 0.1);
                        border: 1px solid #4CAF50;
                        border-radius: 10px;
                        padding: 4px 12px;
                    }
                """)
            else:
                self.api_status_label.setText("⚡ Google Translate Only")
                self.api_status_label.setStyleSheet("""
                    QLabel {
                        color: #FFC107;
                        font-size: 12px;
                        font-weight: bold;
                        background: rgba(255, 193, 7, 0.1);
                        border: 1px solid #FFC107;
                        border-radius: 10px;
                        padding: 4px 12px;
                    }
                """)
    
    def reload_api_keys(self):
        """Reload API keys or prompt for new ones"""
        existing_key = keyring.get_password(self.SERVICE_NAME, "deepl_api_key")
        
        if existing_key:
            # Key exists, offer to update
            reply = QMessageBox.question(
                self,
                "Update API Key",
                "An API key is already stored. Do you want to update it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.prompt_for_api_key()
            else:
                self.add_log("Using existing API key", "info")
                self.api_keys = {"deepl_api_key": existing_key}
                self.update_api_status(True)
        else:
            # No key stored, prompt for one
            self.prompt_for_api_key()
    
    def showEvent(self, event):
        super().showEvent(event)
        if self.ultrawide_positioning and self.target_x is not None:
            QTimer.singleShot(0, lambda: self.move(self.target_x, self.target_y))
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("FS25 Language Translator")
        
        # Get screen information for adaptive sizing
        screen = QApplication.primaryScreen().geometry()
        screen_width = screen.width()
        screen_height = screen.height()
        aspect_ratio = screen_width / screen_height
        
        # Detect screen type
        is_ultrawide = aspect_ratio > 2.0
        
        # Determine window size based on screen type
        if is_ultrawide:
            window_width = 1500
            window_height = min(1000, int(screen_height * 0.75))
            min_width = 1200
            min_height = 800
            left_panel_width = 700
        elif screen_width >= 3840:  # 4K
            window_width = 1600
            window_height = 1000
            min_width = 1200
            min_height = 800
            left_panel_width = 700
        elif screen_width >= 2560:  # 1440p
            window_width = 1400
            window_height = 900
            min_width = 1100
            min_height = 750
            left_panel_width = 700
        elif screen_width >= 1920:  # 1080p
            window_width = 1200
            window_height = 800
            min_width = 1000
            min_height = 700
            left_panel_width = 650
        else:  # Smaller screens
            window_width = min(screen_width - 100, 1000)
            window_height = min(screen_height - 100, 700)
            min_width = min(950, window_width)
            min_height = min(650, window_height)
            left_panel_width = 550
        
        # Safety check - ensure window fits on screen
        window_width = min(window_width, int(screen_width * 0.8))
        window_height = min(window_height, int(screen_height * 0.9))
        
        # Center the window - EXACTLY like main_window.py
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        if is_ultrawide and window_width < 1600:
            x = screen_width // 3 - window_width // 2
            self.ultrawide_positioning = True
            self.target_x = x
            self.target_y = y
        
        self.setGeometry(x, y, window_width, window_height)
        self.setMinimumSize(min_width, min_height)
        
        # Store window dimensions and left panel width for later use
        self.window_width = window_width
        self.window_height = window_height
        self.left_panel_width = left_panel_width
        
        # Set custom window icon
        icon_path = resource_path("icons/icon.ico")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        
        # Enable drag and drop
        self.setAcceptDrops(True)
        
        # Central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 10)
        
        # Enhanced Header with gradient effect
        header_widget = QWidget()
        header_widget.setFixedHeight(150)  # Further increased height
        header_widget.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #2a2a2a, stop: 0.5 #3d3d3d, stop: 1 #2a2a2a);
                border: 2px solid #4CAF50;
                border-radius: 15px;
            }
        """)
        header_layout = QVBoxLayout(header_widget)
        header_layout.setSpacing(8)
        header_layout.setContentsMargins(10, 15, 10, 10)  # More top margin

        # Main title
        header_label = QLabel("🌍 FS25 Language Translator")
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_font = QFont("Arial", 26, QFont.Weight.Bold)
        header_label.setFont(header_font)
        header_label.setStyleSheet("""
            QLabel {
                color: #4CAF50;
                background: transparent;
                padding: 8px;
                border: none;
                min-height: 35px;
            }
        """)
        
        # Subtitle
        subtitle_label = QLabel("Professional XML Translation Tool for Farming Simulator 25")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 14px;
                font-weight: 500;
                background: transparent;
                padding: 1px;
                border: none;
            }
        """)
        
        # API Status with better styling
        self.api_status_label = QLabel("⚡ Checking API Status...")
        self.api_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.api_status_label.setStyleSheet("""
            QLabel {
                color: #FFC107;
                font-size: 12px;
                font-weight: bold;
                background: rgba(255, 193, 7, 0.1);
                border: 1px solid #FFC107;
                border-radius: 10px;
                padding: 5px 15px;
                min-height: 20px;
            }
        """)
        self.api_status_label.setMinimumWidth(200)
        
        # Create horizontal layout for status
        status_layout = QHBoxLayout()
        status_layout.addStretch()
        status_layout.addWidget(self.api_status_label)
        status_layout.addStretch()
        
        header_layout.addWidget(header_label)
        header_layout.addWidget(subtitle_label)
        header_layout.addLayout(status_layout)
        main_layout.addWidget(header_widget)
        
        # Enhanced File selection group
        file_group = QGroupBox("📂 SOURCE FILE SELECTION")
        file_group.setFixedHeight(140)
        file_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #4CAF50;
                border-radius: 12px;
                margin-top: 15px;
                padding-top: 35px;
                padding-bottom: 15px;
                background-color: #2a2a2a;
                color: #4CAF50;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 25px;
                padding: 5px 15px;
                color: #ffffff;
                background: #4CAF50;
                border-radius: 8px;
                font-size: 13px;
            }
        """)
        
        # Main vertical layout for centering
        file_main_layout = QVBoxLayout()
        file_main_layout.setContentsMargins(15, 5, 15, 5)
        file_main_layout.setSpacing(0)
        
        # Add stretch to center vertically (equal stretches for perfect centering)
        file_main_layout.addStretch(1)
        
        # Horizontal layout for the actual content
        file_layout = QHBoxLayout()
        file_layout.setSpacing(15)
        
        # Drag & Drop area - much better design
        self.file_label = QLabel("📁 Drag & Drop your l10n_*.xml file here or click Browse Files")
        self.file_label.setStyleSheet("""
            QLabel { 
                padding: 0px 30px; 
                border: 2px dashed #4CAF50; 
                border-radius: 10px; 
                background-color: #1e1e1e;
                color: #4CAF50;
                font-size: 15px;
                font-weight: 600;
            }
            QLabel:hover {
                border-color: #66BB6A;
                background-color: rgba(76, 175, 80, 0.05);
                color: #66BB6A;
            }
        """)
        self.file_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.file_label.setFixedHeight(60)
        file_layout.addWidget(self.file_label, 1)
        
        # Browse button - better proportions
        self.browse_btn = QPushButton("Browse Files")
        self.browse_btn.setFixedSize(150, 45)
        self.browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.browse_btn.setStyleSheet("""
            QPushButton {
                background: #4CAF50;
                border: none;
                border-radius: 8px;
                color: white;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #5cbf60;
            }
            QPushButton:pressed {
                background: #45a049;
            }
        """)
        self.browse_btn.clicked.connect(self.browse_file)
        file_layout.addWidget(self.browse_btn)
        
        file_main_layout.addLayout(file_layout)
        
        # Add equal stretch after to center vertically
        file_main_layout.addStretch(1)
        
        file_group.setLayout(file_main_layout)
        main_layout.addWidget(file_group)
        
        # Create splitter for main content
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #3a3a3a, stop: 0.5 #4a4a4a, stop: 1 #3a3a3a);
                width: 3px;
                border-radius: 2px;
            }
            QSplitter::handle:hover {
                background: #4CAF50;
            }
        """)
        
        # Left panel - Language selection
        left_panel = QWidget()
        left_panel.setFixedWidth(self.left_panel_width)  # Use dynamic width based on screen size
        left_layout = QVBoxLayout(left_panel)
        
        lang_group = QGroupBox("🌐 LANGUAGES TO TRANSLATE")
        lang_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 13px;
                border: 2px solid #4CAF50;
                border-radius: 10px;
                margin-top: 20px;
                padding-top: 25px;
                background-color: #2a2a2a;
                color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 20px;
                padding: 5px 15px;
                color: #ffffff;
                background: #4CAF50;
                border-radius: 8px;
            }
        """)
        lang_layout = QVBoxLayout()
        
        # Select/Deselect all buttons with better styling
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        self.select_all_btn = QPushButton("✅ Select All")
        self.select_all_btn.setFixedHeight(35)
        self.select_all_btn.setStyleSheet("""
            QPushButton {
                background: #4CAF50;
                border: none;
                border-radius: 8px;
                color: white;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #5cbf60;
            }
        """)
        self.select_all_btn.clicked.connect(self.select_all_languages)
        
        self.deselect_all_btn = QPushButton("❌ Deselect All")
        self.deselect_all_btn.setFixedHeight(35)
        self.deselect_all_btn.setStyleSheet("""
            QPushButton {
                background: #666666;
                border: none;
                border-radius: 8px;
                color: white;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #777777;
            }
        """)
        self.deselect_all_btn.clicked.connect(self.deselect_all_languages)
        
        btn_layout.addWidget(self.select_all_btn)
        btn_layout.addWidget(self.deselect_all_btn)
        lang_layout.addLayout(btn_layout)
        
        # Language table
        self.lang_table = QTableWidget()

        ROW_H = 40
        vh = self.lang_table.verticalHeader()
        vh.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        vh.setDefaultSectionSize(ROW_H)
        vh.setMinimumSectionSize(ROW_H)
        vh.setMaximumSectionSize(ROW_H)

        # Normalize any already calculated/drawn rows
        for r in range(self.lang_table.rowCount()):
            self.lang_table.setRowHeight(r, ROW_H)

        self.lang_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.lang_table.setColumnCount(4)
        self.lang_table.setHorizontalHeaderLabels(["Select", "Language", "Status", "Service"])

        header = self.lang_table.horizontalHeader()

        # 0: Select - liten, fast
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.lang_table.setColumnWidth(0, 70)

        # 1: Language - can stretch out
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        # 2: Status - content-based
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)

        # 3: Service - content-based
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

        self.lang_table.setAlternatingRowColors(True)
        self.lang_table.setStyleSheet("""
            QTableWidget {
                background-color: #252525;
                alternate-background-color: #2a2a2a;
                color: #ffffff;
                gridline-color: #3a3a3a;
                border: 1px solid #3a3a3a;
                border-radius: 8px;
                selection-background-color: #4CAF50;
            }
            QTableWidget::item {
                padding: 8px;
                border: none;
            }
            QTableWidget::item:selected {
                background-color: #4CAF50;
                color: #ffffff;
            }
            QHeaderView::section {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #3a3a3a, stop: 1 #2d2d2d);
                color: #4CAF50;
                padding: 10px;
                border: none;
                font-weight: bold;
                font-size: 12px;
            }
        """)
        
        # --- Populate language table ---
        self.lang_checkboxes = {}
        self.lang_row_index = {}

        row_count = len(LANGUAGE_MAP)
        self.lang_table.setRowCount(row_count)

        for idx, (code, info) in enumerate(LANGUAGE_MAP.items()):
            self.lang_row_index[code] = idx

            # Column 0: checkbox
            checkbox_widget = QWidget()
            checkbox_layout = QHBoxLayout(checkbox_widget)
            checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)

            checkbox = QCheckBox()
            checkbox.setChecked(False)
            checkbox.setStyleSheet("""
                QCheckBox { spacing: 0px; }
                QCheckBox::indicator {
                    width: 20px;
                    height: 20px;
                    border-radius: 4px;
                }
                QCheckBox::indicator:unchecked {
                    background-color: #1e1e1e;
                    border: 2px solid #666666;
                }
                QCheckBox::indicator:unchecked:hover {
                    background-color: rgba(76, 175, 80, 0.1);
                    border: 2px solid #4CAF50;
                }
                QCheckBox::indicator:checked {
                    background-color: #4CAF50;
                    border: 2px solid #4CAF50;
                    image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxNiIgaGVpZ2h0PSIxNiIgdmlld0JveD0iMCAwIDE2IDE2Ij48cGF0aCBmaWxsPSJ3aGl0ZSIgZD0iTTEzLjM1NCAzLjY0NmEuNS41IDAgMCAxIDAgLjcwOGwtNyA3YS41LjUgMCAwIDEtLjcwOCAwbC0zLTNhLjUuNSAwIDEgMSAuNzA4LS43MDhMNiAxMC4yOTNsNi42NDYtNi42NDdhLjUuNSAwIDAgMSAuNzA4IDB6Ii8+PC9zdmc+);
                    image-position: center;
                }
                QCheckBox::indicator:checked:hover {
                    background-color: #5cbf60;
                    border: 2px solid #5cbf60;
                }
            """)
            self.lang_checkboxes[code] = checkbox
            checkbox_layout.addWidget(checkbox)
            self.lang_table.setCellWidget(idx, 0, checkbox_widget)

            # Column 1: language name + flag
            name_item = QTableWidgetItem(info['name'])
            name_item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            icon = self._icon_for_l10n(code)
            if icon:
                name_item.setIcon(icon)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.lang_table.setItem(idx, 1, name_item)

            # Column 2: NEUTRAL status from start
            status_item = QTableWidgetItem("-")
            status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.lang_table.setItem(idx, 2, status_item)

            # Column 3: service
            service_item = QTableWidgetItem("-")
            service_item.setFlags(service_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.lang_table.setItem(idx, 3, service_item)
        
        lang_layout.addWidget(self.lang_table)
        lang_group.setLayout(lang_layout)
        left_layout.addWidget(lang_group)
        
        # Right panel - Log and controls
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Progress group with better styling
        progress_group = QGroupBox("📊 PROGRESS")
        progress_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 13px;
                border: 2px solid #4CAF50;
                border-radius: 10px;
                margin-top: 20px;
                padding-top: 25px;
                background-color: #2a2a2a;
                color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 20px;
                padding: 5px 15px;
                color: #ffffff;
                background: #4CAF50;
                border-radius: 8px;
            }
        """)
        progress_layout = QVBoxLayout()
        
        self.status_label = QLabel("✨ Ready to translate")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #4CAF50;
                font-size: 14px;
                font-weight: bold;
                padding: 5px;
            }
        """)
        progress_layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFixedHeight(30)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #3a3a3a;
                border-radius: 10px;
                text-align: center;
                background-color: #1a1a1a;
                color: #ffffff;
                font-weight: bold;
                font-size: 12px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #45a049, stop: 0.5 #4CAF50, stop: 1 #45a049);
                border-radius: 8px;
            }
        """)
        progress_layout.addWidget(self.progress_bar)
        
        progress_group.setLayout(progress_layout)
        right_layout.addWidget(progress_group)
        
        # Log group
        log_group = QGroupBox("📝 TRANSLATION LOG")
        log_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 13px;
                border: 2px solid #4CAF50;
                border-radius: 10px;
                margin-top: 20px;
                padding-top: 25px;
                background-color: #2a2a2a;
                color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 20px;
                padding: 5px 15px;
                color: #ffffff;
                background: #4CAF50;
                border-radius: 8px;
            }
        """)
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 10))
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a1a;
                color: #ffffff;
                border: 2px solid #2a2a2a;
                border-radius: 8px;
                padding: 10px;
                selection-background-color: #4CAF50;
            }
        """)
        log_layout.addWidget(self.log_text)
        
        log_group.setLayout(log_layout)
        right_layout.addWidget(log_group)
        
        # Add panels to splitter with dynamic sizing
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        
        # Set initial splitter sizes based on window width
        right_panel_width = self.window_width - self.left_panel_width - 50  # 50px for margins and splitter
        splitter.setSizes([self.left_panel_width, right_panel_width])
        
        main_layout.addWidget(splitter)
        
        # Control buttons with modern styling
        control_layout = QHBoxLayout()
        control_layout.setSpacing(15)
        control_layout.setContentsMargins(0, 10, 0, 0)

        # --- Source language selector (UI) ---
        self.src_label = QLabel("Source language:")
        self.src_lang_combo = QComboBox()
        self.src_lang_combo.setFixedHeight(40)
        self.src_lang_combo.setIconSize(QSize(24, 18))
        self.src_lang_combo.setEditable(False)

        control_layout.addWidget(self.src_label)
        control_layout.addWidget(self.src_lang_combo)

        view = QListView()
        view.setSpacing(2)
        view.setUniformItemSizes(True)
        self.src_lang_combo.setView(view)
        self.src_lang_combo.setMaxVisibleItems(12)

        # Style (matches your dark theme)
        self.src_lang_combo.setStyleSheet("""
            QComboBox {
                padding: 6px 10px;
                border: 1px solid #2e7d32;
                border-radius: 8px;
                background: #1e1e1e;
                color: #e0ffe0;
                font-weight: 600;
            }
            QComboBox::drop-down { width: 28px; border: none; }
            QComboBox QAbstractItemView {
                background: #242424;
                color: #e0ffe0;
                padding: 6px 4px;
                border: 1px solid #2e7d32;
                selection-background-color: #355f3a;
                outline: 0;
            }
            QComboBox QAbstractItemView::item { min-height: 28px; }
        """)

        # Fill: Auto first
        self.src_lang_combo.addItem("🌐 Auto-detect", userData={"google": "auto", "deepl": None})

        # Then: one item per language in LANGUAGE_MAP (GIANTS languages only)
        for l10n_key, info in LANGUAGE_MAP.items():
            icon = self._icon_for_l10n(l10n_key)
            label = info["name"]
            data  = {"google": info.get("google"), "deepl": info.get("deepl")}
            if icon:
                self.src_lang_combo.addItem(icon, label, userData=data)
            else:
                self.src_lang_combo.addItem(label, userData=data)

        self.src_lang_combo.setCurrentIndex(0)        
        
        self.translate_btn = QPushButton("  ▶  Start Translation  ")
        self.translate_btn.setFixedHeight(50)
        self.translate_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #4CAF50, stop: 1 #45a049);
                border: none;
                border-radius: 10px;
                color: white;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #5cbf60, stop: 1 #4CAF50);
            }
            QPushButton:disabled {
                background: #3a3a3a;
                color: #666666;
            }
        """)
        self.translate_btn.clicked.connect(self.start_translation)
        self.translate_btn.setEnabled(False)
        control_layout.addWidget(self.translate_btn)
        
        self.stop_btn = QPushButton("  ⏹  Stop  ")
        self.stop_btn.setFixedHeight(50)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #f44336, stop: 1 #d32f2f);
                border: none;
                border-radius: 10px;
                color: white;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #ff5252, stop: 1 #f44336);
            }
            QPushButton:disabled {
                background: #3a3a3a;
                color: #666666;
            }
        """)
        self.stop_btn.clicked.connect(self.stop_translation)
        self.stop_btn.setEnabled(False)
        control_layout.addWidget(self.stop_btn)
        
        self.clear_log_btn = QPushButton("  🗑  Clear Log  ")
        self.clear_log_btn.setFixedHeight(50)
        self.clear_log_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #ff9800, stop: 1 #f57c00);
                border: none;
                border-radius: 10px;
                color: white;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #ffb74d, stop: 1 #ff9800);
            }
        """)
        self.clear_log_btn.clicked.connect(self.clear_log)
        control_layout.addWidget(self.clear_log_btn)
        
        self.reload_keys_btn = QPushButton("  🔄  Reload API Keys  ")
        self.reload_keys_btn.setFixedHeight(50)
        self.reload_keys_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #2196F3, stop: 1 #1976D2);
                border: none;
                border-radius: 10px;
                color: white;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #42A5F5, stop: 1 #2196F3);
            }
        """)
        self.reload_keys_btn.clicked.connect(self.reload_api_keys)
        control_layout.addWidget(self.reload_keys_btn)
        
        main_layout.addLayout(control_layout)

        # Copyright footer - nu verkligen längst ner
        footer_label = QLabel("Copyright © 2025 Piplarsson. All Rights Reserved.")
        footer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer_label.setFixedHeight(22)
        footer_label.setStyleSheet("""
            QLabel {
                color: #555555;
                font-size: 18px;
                font-style: italic;
                padding: 0px;
                margin-top: 0px;
                margin-bottom: 0px;
                background: transparent;
                border: none;
            }
        """)
        main_layout.addWidget(footer_label)
        
        # Apply global dark theme stylesheet
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QWidget {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QCheckBox {
                color: #ffffff;
                spacing: 8px;
                padding: 5px;
            }
            QCheckBox::indicator {
                width: 22px;
                height: 22px;
                border-radius: 4px;
                border: 2px solid #4CAF50;
                background-color: #1e1e1e;
            }
            QCheckBox::indicator:unchecked {
                background-color: #1e1e1e;
                border: 2px solid #666666;
            }
            QCheckBox::indicator:unchecked:hover {
                border: 2px solid #4CAF50;
                background-color: rgba(76, 175, 80, 0.1);
            }
            QCheckBox::indicator:checked {
                background-color: #4CAF50;
                border: 2px solid #4CAF50;
            }
            QCheckBox::indicator:checked:hover {
                background-color: #5cbf60;
                border: 2px solid #5cbf60;
            }
            QScrollBar:vertical {
                background-color: #2d2d2d;
                width: 14px;
                border-radius: 7px;
            }
            QScrollBar::handle:vertical {
                background: #4a4a4a;
                min-height: 30px;
                border-radius: 7px;
            }
            QScrollBar::handle:vertical:hover {
                background: #5a5a5a;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
    
    def _icon_for_l10n(self, l10n_key: str) -> QIcon | None:
        code = FLAG_BY_L10N.get(l10n_key)
        if not code:
            return None
        p = resource_path(f"icons/flags/{code}.png")
        return QIcon(str(p)) if p.exists() else None    
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Accept drags that contain a single XML file"""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls and urls[0].toLocalFile().lower().endswith(".xml"):
                event.acceptProposedAction()
                return
        event.ignore()
            
    def dropEvent(self, event: QDropEvent):
        """Handle drop event"""
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if not files:
            QMessageBox.warning(self, "Invalid file", "Please drop an XML file.")
            return

        file_path = files[0]
        if file_path.lower().endswith(".xml"):
            self.load_source_file(file_path)
        else:
            QMessageBox.warning(self, "Invalid file", "Please drop an XML file.")
                
    def browse_file(self):
        """Browse for source XML file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select l10n XML file",
            "",
            "XML Files (*.xml)"
        )
        if file_path:
            self.load_source_file(file_path)
            
    def load_source_file(self, file_path: str):
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
        except ET.ParseError as e:
            QMessageBox.warning(self, "Invalid XML", f"XML syntax error: {e}")
            self.add_log(f"Invalid XML syntax in {file_path}: {e}", "error")
            return
        except FileNotFoundError:
            QMessageBox.warning(self, "File Not Found", f"The file {file_path} was not found")
            self.add_log(f"File not found: {file_path}", "error")
            return
        except PermissionError:
            QMessageBox.warning(self, "Permission Denied", f"Cannot read file: {file_path}")
            self.add_log(f"Permission denied: {file_path}", "error")
            return
        except Exception as e:
            QMessageBox.warning(self, "Unknown Error", f"Could not read the file: {e}")
            self.add_log(f"Unexpected error reading {file_path}: {e}", "error")
            return

        # Decide and create output folder next to the source file
        src_dir = Path(file_path).resolve().parent
        if src_dir.name.lower() == "l10n":
            output_dir = src_dir
        else:
            output_dir = src_dir / "l10n"

        output_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir = str(output_dir)

        self.add_log(f"Output folder set to: {self.output_dir}", "info")
        
        # 2) Update UI since the file is OK
        self.source_file = file_path
        filename = os.path.basename(file_path)

        # Auto-select source language based on l10n_XX in the file name (can be changed manually in the UI)
        self._auto_select_source_from_filename(file_path)

        # Show filename in the box and full path as tooltip
        self.file_label.setText(f"✅ {filename}")
        self.file_label.setToolTip(file_path)
        self.file_label.setStyleSheet("""
            QLabel { 
                padding: 20px 30px; 
                border: 2px solid #4CAF50; 
                border-radius: 10px; 
                background-color: rgba(76, 175, 80, 0.1);
                color: #4CAF50;
                font-size: 15px;
                font-weight: bold;
            }
        """)

        # Enable the translate button and log success
        self.translate_btn.setEnabled(True)
        self.add_log(f"Successfully loaded: {file_path}", "success")
    
    def _auto_select_source_from_filename(self, file_path: str):
        """
        Select source language automatically i comboboxen utifrån filnamn, t.ex. l10n_sv.xml -> Swedish.
        Använder LANGUAGE_MAP och matchar på userData (google/deepl) i comboboxen.
        """
        try:
            stem = Path(file_path).stem.lower()  # t.ex. "l10n_sv"
            # Find the l10n key in the name (robust även om filen heter l10n_sv_custom.xml)
            m = re.search(r'(l10n_[a-z]{2,3})', stem)
            l10n_key = m.group(1) if m else stem

            info = LANGUAGE_MAP.get(l10n_key)
            if not info:
                # unknown language → leave it on Auto
                self.src_lang_combo.setCurrentIndex(0)
                return

            # We try to find exact entry i comboboxen som har samma google/deepl-koder
            target_google = info.get("google") or "auto"
            target_deepl  = info.get("deepl")  # None means auto for DeepL

            for i in range(self.src_lang_combo.count()):
                data = self.src_lang_combo.itemData(i)
                if not isinstance(data, dict):
                    continue
                g = data.get("google")
                d = data.get("deepl")
                # Match google code and deepl code (hantera None som auto)
                if g == target_google and ((d or None) == (target_deepl or None)):
                    self.src_lang_combo.setCurrentIndex(i)
                    self.add_log(f"Source language auto-selected: {info['name']}", "info")
                    return

            # Fallback: match on text (namnet)
            for i in range(self.src_lang_combo.count()):
                if self.src_lang_combo.itemText(i) == info["name"]:
                    self.src_lang_combo.setCurrentIndex(i)
                    self.add_log(f"Source language auto-selected: {info['name']}", "info")
                    return

            # If nothing found, keep Auto
            self.src_lang_combo.setCurrentIndex(0)

        except Exception as e:
            # If for some reason it fails, keep Auto and log
            self.src_lang_combo.setCurrentIndex(0)
            self.add_log(f"Auto-select source failed: {e}", "warning")
    
    def select_all_languages(self):
        """Select all languages"""
        for checkbox in self.lang_checkboxes.values():
            checkbox.setChecked(True)
            
    def deselect_all_languages(self):
        """Deselect all languages"""
        for checkbox in self.lang_checkboxes.values():
            checkbox.setChecked(False)
            
    def add_log(self, message: str, level: str = "info"):
        """Add a message to the log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Enhanced color scheme for dark theme
        color_map = {
            "info": "#00BCD4",      # Cyan
            "success": "#4CAF50",   # Green
            "warning": "#FFC107",   # Amber
            "error": "#F44336"      # Red
        }
        
        # Icons for different log levels
        icon_map = {
            "info": "ℹ",
            "success": "✓",
            "warning": "⚠",
            "error": "✗"
        }
        
        color = color_map.get(level, "#FFFFFF")
        icon = icon_map.get(level, "•")
        
        formatted_message = f'<span style="color: {color}; font-size: 12px;"><b>[{timestamp}] {icon}</b> {message}</span>'
        
        self.log_text.append(formatted_message)
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )
        
    def clear_log(self):
        """Clear the log text"""
        self.log_text.clear()
        self.add_log("Log cleared", "info")
        
    def get_selected_languages(self) -> List[str]:
        """Get list of selected languages"""
        selected = []
        for code, checkbox in self.lang_checkboxes.items():
            if checkbox.isChecked():
                selected.append(code)
        return selected
        
    def reset_language_statuses(self):
        """Reset all language statuses in the table"""
        for i in range(self.lang_table.rowCount()):
            self.lang_table.item(i, 2).setText("⏳ Pending")
            self.lang_table.item(i, 3).setText("-")
            
    def start_translation(self):
        """Start the translation process"""
        if not self.source_file:
            QMessageBox.warning(self, "Warning", "Please select a source XML file first")
            return
            
        selected_languages = self.get_selected_languages()
        if not selected_languages:
            QMessageBox.warning(self, "Warning", "Please select at least one language to translate")
            return
            
        # Check API keys
        if not self.api_keys.get('deepl_api_key') or self.api_keys['deepl_api_key'] == "YOUR_DEEPL_API_KEY_HERE":
            reply = QMessageBox.question(
                self, 
                "No DeepL API Key",
                "No valid DeepL API key found. Continue with Google Translate only?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
                
        # Create output directory
        src_dir = Path(self.source_file).parent
        output_dir = src_dir if src_dir.name.lower() == "l10n" else src_dir / "l10n"
        output_dir.mkdir(exist_ok=True)
        
        # Reset UI
        self.reset_language_statuses()
        self.progress_bar.setValue(0)
        self.translate_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        # Get selected languages
        selected = [code for code, cb in self.lang_checkboxes.items() if cb.isChecked()]
        if not selected:
            QMessageBox.information(self, "No languages", "Please select at least one language.")
            return
        self.selected_languages = selected

        # --- Mark initial status now (not when the table is built) ---
        for code, cb in self.lang_checkboxes.items():
            row = self.lang_row_index.get(code)
            if row is None:
                continue
            status_item  = self.lang_table.item(row, 2)
            service_item = self.lang_table.item(row, 3)
            if cb.isChecked():
                status_item.setText("⏳ Pending")
            else:
                status_item.setText("-")
            service_item.setText("-")

        # Ensure output_dir is set and exists
        if not getattr(self, "output_dir", None):
            src_dir = Path(self.source_file).resolve().parent
            out = src_dir if src_dir.name.lower() == "l10n" else src_dir / "l10n"
            out.mkdir(parents=True, exist_ok=True)
            self.output_dir = str(out)
        
        # Create and start worker thread
        self.worker = TranslationWorker(
            self.source_file,
            str(output_dir),
            self.api_keys,
            selected_languages
        )

        # Pass selected source language to the worker (Google + DeepL)
        src_data = self.src_lang_combo.currentData()
        self.worker.source_google = (src_data or {}).get("google", "auto")
        self.worker.source_deepl  = (src_data or {}).get("deepl", None)
        
        # Connect signals
        self.worker.progress_update.connect(self.update_progress)
        self.worker.status_update.connect(self.update_status)
        self.worker.log_message.connect(self.add_log)
        self.worker.language_completed.connect(self.update_language_status)
        self.worker.finished_all.connect(self.translation_finished)
        
        # Start translation
        self.worker.start()
        
    def stop_translation(self):
        """Stop the translation process"""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.add_log("Stopping translation process...", "warning")
            
    def update_progress(self, current: int, total: int):
        """Update progress bar"""
        progress = int((current / total) * 100)
        self.progress_bar.setValue(progress)
        self.progress_bar.setFormat(f"{current}/{total} languages ({progress}%)")
        
    def update_status(self, status: str):
        """Update status label"""
        self.status_label.setText(f"✨ {status}")
        
    def update_language_status(self, lang_code: str, success: bool, service_used: str):
        row = self.lang_row_index.get(lang_code)
        if row is None:
            return
        self.lang_table.item(row, 2).setText("✅ Complete" if success else "❌ Failed")
        self.lang_table.item(row, 2).setForeground(QColor("#4CAF50" if success else "#F44336"))
        self.lang_table.item(row, 3).setText(service_used)
                    
    def translation_finished(self):
        """Handle translation completion with proper cleanup"""
        self.translate_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
    
        if self.worker:
            # Disconnect all signals safely
            try:
                self.worker.progress_update.disconnect()
                self.worker.status_update.disconnect()
                self.worker.log_message.disconnect()
                self.worker.language_completed.disconnect()
                self.worker.finished_all.disconnect()
            except TypeError:
                pass  # Already disconnected
        
            # Ensure thread is stopped
            if self.worker.isRunning():
                self.worker.stop()
                self.worker.quit()
                if not self.worker.wait(3000):  # 3 second timeout
                    self.worker.terminate()  # Force terminate if needed
        
            self.worker.deleteLater()
            self.worker = None
        
            # Force garbage collection
            import gc
            gc.collect()

        if self.progress_bar.value() == 100:
            QMessageBox.information(
                self,
                "Success",
                "Translation completed successfully!\nFiles saved in the 'l10n' folder."
            )
        
    def closeEvent(self, event):
        """Handle window close event"""
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self,
                "Confirm Exit",
                "Translation is in progress. Are you sure you want to exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.worker.stop()
                self.worker.wait()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # Fix SSL certificate issues for googletrans in EXE - ONLY if frozen
    if getattr(sys, 'frozen', False):
        os.environ['SSL_CERT_FILE'] = certifi.where()
        os.environ['SSL_CERT_DIR'] = os.path.dirname(certifi.where())
    
    # Set application icon (shows in taskbar)
    icon_path = resource_path("icons/icon.ico")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()