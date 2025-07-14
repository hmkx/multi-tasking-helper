"""
Controller module for multitask_helper.
Orchestrates business logic between GUI, LLM, rule engine, and window management.
"""

import time
import threading
import pyperclip
from typing import List, Tuple, Optional, Callable

from windows import WindowManager, WindowInfo
from rule import RuleBasedSuggestionEngine
from llm import LLMSuggestionEngine


class Config:
    """Configuration constants"""
    CLIPBOARD_CHECK_INTERVAL = 0.5  # seconds
    THREAD_JOIN_TIMEOUT = 1.0       # seconds
    MAX_CONTENT_PREVIEW = 50        # characters
    
    # Exclude patterns for window filtering
    EXCLUDED_TITLES = ['multitask helper', 'multi-task helper']
    
    # Status messages
    STATUS_MONITORING = "Monitoring clipboard..."
    STATUS_STOPPED = "Monitoring stopped"
    STATUS_AI_ANALYZING = "AI analyzing..."
    STATUS_RULE_ANALYZING = "Using rule-based suggestions..."
    STATUS_READY = "Ready"


class MultitaskController:
    """Main controller orchestrating all components"""
    
    def __init__(self, enable_llm: bool = True):
        # Initialize components
        self.window_manager = WindowManager()
        self.rule_engine = RuleBasedSuggestionEngine()
        self.llm_engine = LLMSuggestionEngine() if enable_llm else None
        
        # State
        self.clipboard_content = ""
        self.last_clipboard = ""
        self.current_suggestions = []
        self.is_monitoring = False
        self.monitor_thread = None
        
        # Callbacks for GUI updates
        self.on_clipboard_change: Optional[Callable] = None
        self.on_suggestions_ready: Optional[Callable] = None
        self.on_status_change: Optional[Callable] = None
        
        self._log_initialization()
    
    def start_monitoring(self):
        """Start clipboard monitoring"""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_clipboard, daemon=True)
        self.monitor_thread.start()
        
        self._update_status(Config.STATUS_MONITORING)
        self._log("Clipboard monitoring started")
    
    def stop_monitoring(self):
        """Stop clipboard monitoring"""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=Config.THREAD_JOIN_TIMEOUT)
        
        self._update_status(Config.STATUS_STOPPED)
        self._log("Clipboard monitoring stopped")
    
    def get_suggestions_for_content(self, content: str) -> List[Tuple[str, WindowInfo, str]]:
        """Get window suggestions for clipboard content"""
        if not content.strip():
            return []
        
        # Get available windows
        available_windows = self.window_manager.get_filtered_windows(
            exclude_titles=Config.EXCLUDED_TITLES
        )
        
        # Debug: Print all available windows
        self._log(f"DEBUG: Available windows ({len(available_windows)}):")
        for i, window in enumerate(available_windows):
            title_safe = window.title.encode('ascii', 'ignore').decode('ascii')[:40]
            self._log(f"  {i+1}. {window.process_name} - {title_safe}")
        
        if not available_windows:
            return []
        
        current_window = self._get_current_window()
        
        # Try LLM first if available
        suggestions = self._try_llm_suggestions(content, current_window, available_windows)
        
        # Fallback to rule-based if needed
        if not suggestions:
            suggestions = self._try_rule_suggestions(content, current_window, available_windows)
        
        self._update_final_status(suggestions)
        return suggestions
    
    def switch_to_window(self, window_info: WindowInfo) -> bool:
        """Switch to the specified window"""
        success = self.window_manager.switch_to_window(window_info.hwnd)
        
        if success:
            self._log(f"Switched to: {window_info.process_name} - {window_info.title[:30]}")
        else:
            self._log(f"Failed to switch to: {window_info.process_name}")
        
        return success
    
    def get_system_info(self) -> dict:
        """Get system information"""
        windows = self.window_manager.get_all_windows()
        categories = self.window_manager.categorize_windows(windows)
        
        llm_info = self.llm_engine.get_model_info() if self.llm_engine else {
            'available': False, 'initialized': False
        }
        
        return {
            'total_windows': len(windows),
            'window_categories': {k: len(v) for k, v in categories.items()},
            'llm_status': llm_info,
            'monitoring': self.is_monitoring
        }
    
    def set_callbacks(self, on_clipboard_change: Callable = None, 
                     on_suggestions_ready: Callable = None,
                     on_status_change: Callable = None):
        """Set GUI callback functions"""
        self.on_clipboard_change = on_clipboard_change
        self.on_suggestions_ready = on_suggestions_ready
        self.on_status_change = on_status_change
    
    # Private methods
    def _try_llm_suggestions(self, content: str, current_window: Optional[WindowInfo], 
                           available_windows: List[WindowInfo]) -> Optional[List[Tuple[str, WindowInfo, str]]]:
        """Try to get LLM suggestions"""
        if not (self.llm_engine and self.llm_engine.is_ready()):
            return None
        
        self._update_status(Config.STATUS_AI_ANALYZING)
        suggestions = self.llm_engine.get_suggestions(content, current_window, available_windows)
        
        if suggestions:
            self._log(f"LLM provided {len(suggestions)} suggestions")
        else:
            self._log("LLM failed, falling back to rules")
        
        return suggestions
    
    def _try_rule_suggestions(self, content: str, current_window: Optional[WindowInfo], 
                            available_windows: List[WindowInfo]) -> List[Tuple[str, WindowInfo, str]]:
        """Try to get rule-based suggestions"""
        self._update_status(Config.STATUS_RULE_ANALYZING)
        suggestions = self.rule_engine.get_suggestions(content, current_window, available_windows)
        
        if suggestions:
            self._log(f"Rule engine provided {len(suggestions)} suggestions")
        else:
            self._log("No suggestions available")
            suggestions = []
        
        return suggestions
    
    def _monitor_clipboard(self):
        """Monitor clipboard for changes"""
        while self.is_monitoring:
            try:
                current_clipboard = pyperclip.paste()
                
                if self._clipboard_changed(current_clipboard):
                    self._handle_clipboard_change(current_clipboard)
                
                time.sleep(Config.CLIPBOARD_CHECK_INTERVAL)
                
            except Exception as e:
                self._log(f"Clipboard monitoring error: {e}")
                time.sleep(1.0)
    
    def _clipboard_changed(self, current_clipboard: str) -> bool:
        """Check if clipboard content changed"""
        return (current_clipboard != self.last_clipboard and 
                current_clipboard.strip())
    
    def _handle_clipboard_change(self, current_clipboard: str):
        """Handle clipboard content change"""
        self.last_clipboard = current_clipboard
        self.clipboard_content = current_clipboard
        
        preview = current_clipboard[:Config.MAX_CONTENT_PREVIEW]
        self._log(f"Clipboard changed: {preview}...")
        
        # Notify GUI
        if self.on_clipboard_change:
            self.on_clipboard_change(current_clipboard)
        
        # Get and notify suggestions
        suggestions = self.get_suggestions_for_content(current_clipboard)
        self.current_suggestions = suggestions
        
        if self.on_suggestions_ready:
            self.on_suggestions_ready(suggestions)
    
    def _get_current_window(self) -> Optional[WindowInfo]:
        """Get currently active window"""
        try:
            import win32gui
            hwnd = win32gui.GetForegroundWindow()
            
            all_windows = self.window_manager.get_all_windows()
            for window in all_windows:
                if window.hwnd == hwnd:
                    return window
        except Exception:
            pass
        
        return None
    
    def _log_initialization(self):
        """Log controller initialization"""
        llm_status = "Enabled" if self.llm_engine and self.llm_engine.is_ready() else "Disabled"
        print(f"[CONTROLLER] Initialized - LLM: {llm_status}")
    
    def _update_status(self, status: str):
        """Update status via callback"""
        if self.on_status_change:
            self.on_status_change(status)
    
    def _update_final_status(self, suggestions: List):
        """Update final status based on suggestions"""
        if suggestions:
            status = f"{Config.STATUS_READY} - {len(suggestions)} suggestions"
        else:
            status = f"{Config.STATUS_READY} - No suggestions"
        
        self._update_status(status)
    
    def _log(self, message: str):
        """Log message with controller prefix"""
        print(f"[CONTROLLER] {message}")