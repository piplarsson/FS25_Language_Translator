🌍 FS25 Language Translator

![GitHub release](https://img.shields.io/github/v/release/piplarsson/FS25_Language_Translator)
![GitHub stars](https://img.shields.io/github/stars/piplarsson/FS25_Language_Translator)
![GitHub issues](https://img.shields.io/github/issues/piplarsson/FS25_Language_Translator)
![GitHub license](https://img.shields.io/github/license/piplarsson/FS25_Language_Translator)

A professional translation tool for Farming Simulator 25 XML language files. Automatically translate your mod's language files to 26 different languages using DeepL and Google Translate.

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)

## ✨ Features

- **🚀 Dual Translation Engines**: Uses DeepL for high-quality translations with Google Translate as automatic fallback
- **🌐 26 Languages Supported**: All official Farming Simulator 25 languages
- **🔒 Secure API Storage**: API keys stored securely in your system's credential manager
- **🎨 Modern Dark UI**: Professional interface with real-time progress tracking
- **📁 Smart File Handling**: Drag & drop support with automatic source language detection
- **⚡ Batch Processing**: Translate to multiple languages simultaneously
- **🛡️ Placeholder Protection**: Preserves XML placeholders and format strings
- **📊 Live Progress**: Real-time translation status and detailed logging

## 📋 Supported Languages

All official FS25 languages are supported:

| Language | Code | Language | Code |
|----------|------|----------|------|
| 🇧🇷 Portuguese (Brazil) | l10n_br | 🇳🇱 Dutch | l10n_nl |
| 🇨🇿 Czech | l10n_cs | 🇳🇴 Norwegian | l10n_no |
| 🇦🇩 Catalan | l10n_ct | 🇵🇱 Polish | l10n_pl |
| 🇩🇰 Danish | l10n_da | 🇵🇹 Portuguese (Portugal) | l10n_pt |
| 🇩🇪 German | l10n_de | 🇷🇴 Romanian | l10n_ro |
| 🇲🇽 Spanish (Latin America) | l10n_ea | 🇷🇺 Russian | l10n_ru |
| 🇺🇸 English | l10n_en | 🇸🇪 Swedish | l10n_sv |
| 🇪🇸 Spanish (Spain) | l10n_es | 🇹🇷 Turkish | l10n_tr |
| 🇨🇦 French (Canada) | l10n_fc | 🇺🇦 Ukrainian | l10n_uk |
| 🇫🇮 Finnish | l10n_fi | 🇻🇳 Vietnamese | l10n_vi |
| 🇫🇷 French (France) | l10n_fr | 🇭🇺 Hungarian | l10n_hu |
| 🇮🇩 Indonesian | l10n_id | 🇮🇹 Italian | l10n_it |
| 🇯🇵 Japanese | l10n_jp | 🇰🇷 Korean | l10n_kr |

## 🚀 Quick Start

### Prerequisites

- Python 3.9 or higher
- Windows, macOS, or Linux

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/piplarsson/FS25_Language_Translator.git
cd FS25_Language_Translator

2. Install dependencies:

bashpip install -r requirements.txt

3. Run the application:

bashpython fs25_translator.py

📖 How to Use
First Time Setup

Launch the application
You'll be prompted to enter your DeepL API key (optional but recommended)
The key is securely saved to your system's credential manager

Translating Files

Load your source file:

Drag & drop your l10n_*.xml file onto the application, or
Click "Browse Files" to select your XML file


Select target languages:

Click "Select All" to translate to all languages, or
Choose specific languages by checking their boxes


Start translation:

Click "▶ Start Translation"
Monitor progress in real-time
Translations are saved to the l10n folder



Source Language
The tool automatically detects the source language from your filename (e.g., l10n_en.xml → English). You can manually override this using the dropdown menu.

🔑 API Keys
DeepL API (Recommended)
For best translation quality, get a free DeepL API key:

Visit DeepL Pro API
Sign up for a free account (500,000 characters/month)
Copy your API key
Enter it when prompted by the application

Google Translate
Google Translate works automatically as a fallback - no API key required!
Security
Your API keys are stored securely using:

Windows: Windows Credential Manager
macOS: macOS Keychain
Linux: Secret Service API

See README_SECURITY.md for detailed security information.

📁 Project Structure
FS25_Language_Translator/
├── fs25_translator.py       # Main application
├── api_key_dialog.py        # API key input dialog
├── api_key_manager.py       # Standalone key management tool
├── requirements.txt         # Python dependencies
├── README.md               # This file
├── README_SECURITY.md      # Security documentation
└── icons/                  # Application icons
    ├── icon.ico           # Main icon
    └── flags/             # Country flag icons

🛠️ Building Executable (Optional)
To create a standalone executable:
bashpip install pyinstaller
pyinstaller --onefile --windowed --icon=icons/icon.ico fs25_translator.py
The executable will be created in the dist folder.

🤝 Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

Fork the repository
Create your feature branch (git checkout -b feature/AmazingFeature)
Commit your changes (git commit -m 'Add some AmazingFeature')
Push to the branch (git push origin feature/AmazingFeature)
Open a Pull Request

📝 License
This project is licensed under the MIT License - see the LICENSE file for details.

🙏 Acknowledgments

DeepL for excellent translation API
Google Translate for fallback translations
GIANTS Software for Farming Simulator 25
The modding community for inspiration and support

🐛 Troubleshooting
Common Issues
"Failed to access secure storage"

Ensure your system's credential manager service is running
On Windows: Check that Windows Credential Manager is enabled
On macOS: Ensure Keychain Access is unlocked

"Translation failed" errors

Check your internet connection
Verify your DeepL API key is valid
Ensure you haven't exceeded API limits

XML parsing errors

Ensure your source XML file is valid
Check for proper UTF-8 encoding
Verify XML structure matches FS25 format

Getting Help

Create an Issue for bugs
Check existing issues for solutions
Read README_SECURITY.md for API key issues

📊 Performance

Translates approximately 100-200 strings per minute
DeepL provides higher quality for European languages
Google Translate offers broader language support
Batch processing reduces API calls

🔄 Updates
Check the Releases page for updates.

Made with ❤️ for the Farming Simulator modding community

Not affiliated with GIANTS Software GmbH
