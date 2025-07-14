# Multitask Helper

An experimental project – a multi-tasking helper powered by an on-device LLM. This Windows application intelligently suggests the best application to switch to based on your clipboard content, helping you stay productive by reducing context-switching time.

## 🧑‍💻 Development Team

- Boxun Yan - boxun@qti.qualcomm.com
- Tiffany Fu - tifffu@qti.qualcomm.com
- Ho Man Kwan  - hkwan@qti.qualcomm.com
- Wenxin Ding - wenxind@qti.qualcomm.com
- Balaji Natarajan Balaji Shankar - balanata@qti.qualcomm.com

## 🛠️ Setup Instructions

**⚠️ Note: This is a Windows-only application**

### Prerequisites
- Windows 10/11
- Python 3.11 or higher
- Qualcomm Snapdragon processor (for NPU acceleration)

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd multitask_helper
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Download and setup LLM library:**
   - Download the LLM library from: https://github.com/DerrickJ1612/qnn_sample_apps
   - Extract/place the downloaded `qnn_sample_apps` folder in the project directory
   - Follow the instructions in the GitHub repository to download the required LLM models
   - Ensure the `qnn_sample_apps-main` directory contains the DeepSeek model files

## 🚀 Usage

### Basic Usage

Run the application with GUI:
```bash
python main.py
```

### How It Works

1. **Clipboard Monitoring**: The app continuously monitors your clipboard for changes
2. **Content Analysis**: When new content is detected, it analyzes the content type (code, web URL, email, file path, etc.)
3. **Smart Suggestions**: Using both rule-based logic and on-device LLM, it suggests the 3 most relevant applications to switch to
4. **One-Click Switching**: Click any suggestion button to instantly switch to that application

### Supported Content Types

- **CODE**: Programming code, scripts, configurations
- **WEB**: URLs, web addresses, web content  
- **EMAIL**: Email addresses, email content
- **FILE_PATH**: File and directory paths
- **DATA**: Spreadsheet data, CSV content, tables
- **PASSWORD**: Passwords and sensitive credentials
- **TEXT**: General text content

### Example Scenarios

- Copy `def hello_world():` → Suggests VS Code, PyCharm, Notepad++
- Copy `https://github.com` → Suggests Chrome, Edge, Firefox
- Copy `user@example.com` → Suggests Outlook, Thunderbird, Gmail
- Copy `C:\Users\Documents\file.txt` → Suggests File Explorer, text editors

## ⚠️ Current Limitations

**Note**: Current accuracy is limited by the lightweight LLM without finetuning. The DeepSeek 1.5B model provides basic suggestions but may not always perfectly match user intent. Future improvements could include model finetuning on user-specific patterns for better accuracy.

## 📋 Features

- ✅ Real-time clipboard monitoring
- ✅ Intelligent content classification
- ✅ On-device LLM processing (DeepSeek 1.5B)
- ✅ Rule-based fallback system
- ✅ One-click application switching

## 🔧 Architecture

The application follows a clean modular architecture:

- **`main.py`**: Entry point and CLI handling
- **`gui.py`**: Tkinter-based user interface
- **`controller.py`**: Business logic coordinator
- **`windows.py`**: Window management and enumeration
- **`rule.py`**: Rule-based content classification
- **`llm.py`**: LLM integration and inference

## 🤖 Built with AI Assistance

This application was built with the assistance of **Claude Code**.