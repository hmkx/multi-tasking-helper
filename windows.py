"""
Windows management module for multitask_helper.
Handles window enumeration, information extraction, and categorization.
"""

import win32gui
import win32process
import psutil
from typing import List, NamedTuple, Optional


class WindowInfo(NamedTuple):
    """Window information container"""
    hwnd: int
    title: str
    process_name: str
    pid: int
    is_visible: bool
    is_minimized: bool


class WindowManager:
    """Manages window enumeration and categorization"""
    
    def __init__(self):
        self.excluded_processes = {
            'dwm.exe', 'winlogon.exe', 'csrss.exe', 'smss.exe',
            'wininit.exe', 'services.exe', 'lsass.exe', 'explorer.exe',
            'svchost.exe', 'taskhost.exe', 'dllhost.exe', 'conhost.exe',
            'clicktodo.exe'
        }
        self.excluded_titles = {
            'Program Manager', 'Desktop', '', 'Default IME', 'MSCTFIME UI',
            'Hidden Window', 'GDI+ Window', 'DirectUIHWND', 'Shell_TrayWnd',
            'Button', 'Scrollbar', 'ComboBox', 'Edit', 'Static', 'Window'
        }
        
        # Additional filters for real application windows
        self.min_window_size = (100, 50)  # Minimum width, height
    
    def get_all_windows(self) -> List[WindowInfo]:
        """Get all relevant windows"""
        windows = []
        
        def enum_windows_callback(hwnd, _):
            if self._is_valid_window(hwnd):
                window_info = self._get_window_info(hwnd)
                if window_info:
                    windows.append(window_info)
            return True
        
        win32gui.EnumWindows(enum_windows_callback, None)
        return windows
    
    def get_filtered_windows(self, exclude_titles: Optional[List[str]] = None) -> List[WindowInfo]:
        """Get filtered windows excluding specified titles"""
        windows = self.get_application_windows()
        if exclude_titles:
            windows = [w for w in windows if not any(exclude in w.title.lower() 
                                                   for exclude in exclude_titles)]
        return windows
    
    def get_application_windows(self) -> List[WindowInfo]:
        """Get only real application windows with additional filtering"""
        windows = self.get_all_windows()
        
        # Additional filtering for application windows
        app_windows = []
        for window in windows:
            # Skip windows with generic or empty titles
            if len(window.title.strip()) < 3:
                continue
            
            # Skip obvious system/background windows and UI elements
            skip_words = ['notification', 'tooltip', 'popup', 'menu', 'context', 
                         'gdi+', 'dde server', 'broadcast', 'xaml', 'hardware', 'power', 'paste options',
                         'listener', 'monitor', 'systray', 'system', 'background', 'service',
                         'trackmonitors', 'endsession', 'resourcenotify', 'activity center',
                         'task host window', 'input experience', 'handwriting canvas', 'clicktodo']
            if any(skip_word in window.title.lower() for skip_word in skip_words):
                continue
            
            # Only include processes that are likely user applications
            if self._is_user_application(window):
                app_windows.append(window)
        
        # Sort alphabetically by process name (treat all windows equally)
        app_windows.sort(key=lambda w: w.process_name.lower())
        
        return app_windows
    
    def _is_user_application(self, window: WindowInfo) -> bool:
        """Check if window belongs to a user application"""
        process_lower = window.process_name.lower()
        
        # Common user applications
        user_apps = {
            'chrome.exe', 'firefox.exe', 'edge.exe', 'safari.exe', 'opera.exe',
            'code.exe', 'notepad.exe', 'notepad++.exe', 'sublime_text.exe',
            'pycharm64.exe', 'idea64.exe', 'devenv.exe', 'atom.exe',
            'cmd.exe', 'powershell.exe', 'windowsterminal.exe', 'wt.exe',
            'excel.exe', 'winword.exe', 'powerpnt.exe', 'outlook.exe',
            'msedge.exe', 'msaccess.exe', 'mspub.exe', 'winmail.exe',
            'hxmail.exe', 'hxoutlook.exe', 'outlookforwindows.exe',  # Modern Outlook
            'thunderbird.exe', 'mailspring.exe', 'spark.exe',  # Other email clients
            'olk.exe',
            'vlc.exe', 'spotify.exe', 'discord.exe', 'teams.exe', 'zoom.exe',
            'photoshop.exe', 'illustrator.exe', 'figma.exe',
            'steam.exe', 'calculator.exe', 'mspaint.exe'
        }
        
        # Check if it's a known user application
        if process_lower in user_apps:
            return True
        
        # Check if it has characteristics of a user application
        # - Has a meaningful title (not just process name)
        # - Title is different from process name
        process_name_clean = window.process_name.replace('.exe', '').lower()
        title_lower = window.title.lower()
        
        # If title contains more than just the process name, likely a user app
        if len(window.title) > len(process_name_clean) + 5:
            return True
        
        # If window title suggests it's a document/file viewer
        if any(indicator in title_lower for indicator in 
               ['.txt', '.doc', '.pdf', '.jpg', '.png', '.mp4', '.mp3', 
                'untitled', 'document', 'sheet', 'presentation']):
            return True
        
        return False
    
    def categorize_windows(self, windows: List[WindowInfo]) -> dict:
        """Categorize windows by type"""
        categories = {
            'browsers': [],
            'editors': [],
            'terminals': [],
            'office': [],
            'media': [],
            'other': []
        }
        
        for window in windows:
            process_lower = window.process_name.lower()
            title_lower = window.title.lower()
            
            if any(browser in process_lower for browser in 
                   ['chrome', 'firefox', 'edge', 'safari', 'opera', 'brave']):
                categories['browsers'].append(window)
            elif any(editor in process_lower for editor in 
                     ['code', 'notepad', 'sublime', 'atom', 'vim', 'emacs', 'pycharm', 'idea']):
                categories['editors'].append(window)
            elif any(terminal in process_lower for terminal in 
                     ['cmd', 'powershell', 'terminal', 'bash', 'wt']):
                categories['terminals'].append(window)
            elif any(office in process_lower for office in 
                     ['word', 'excel', 'powerpoint', 'outlook', 'onenote']):
                categories['office'].append(window)
            elif any(media in process_lower for media in 
                     ['vlc', 'spotify', 'discord', 'teams', 'zoom']):
                categories['media'].append(window)
            else:
                categories['other'].append(window)
        
        return categories
    
    def switch_to_window(self, hwnd: int) -> bool:
        """Switch to the specified window"""
        try:
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, 9)  # SW_RESTORE
            win32gui.SetForegroundWindow(hwnd)
            return True
        except Exception as e:
            print(f"[ERROR] Failed to switch to window {hwnd}: {e}")
            return False
    
    def _is_valid_window(self, hwnd: int) -> bool:
        """Check if window is valid - simplified detection"""
        if not win32gui.IsWindow(hwnd):
            return False
        
        title = win32gui.GetWindowText(hwnd)
        if not title or len(title.strip()) < 3:
            return False
            
        # Skip obvious system windows
        if title in self.excluded_titles:
            return False
        
        return True
    
    def _get_window_info(self, hwnd: int) -> Optional[WindowInfo]:
        """Extract window information"""
        try:
            title = win32gui.GetWindowText(hwnd)
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            
            try:
                process = psutil.Process(pid)
                process_name = process.name()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                process_name = "Unknown"
            
            if process_name.lower() in self.excluded_processes:
                return None
            
            is_visible = win32gui.IsWindowVisible(hwnd)
            is_minimized = win32gui.IsIconic(hwnd)
            
            return WindowInfo(
                hwnd=hwnd,
                title=title,
                process_name=process_name,
                pid=pid,
                is_visible=is_visible,
                is_minimized=is_minimized
            )
        except Exception:
            return None