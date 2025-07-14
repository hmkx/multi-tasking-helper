"""
GUI module for multitask_helper.
Clean interface using tkinter with controller integration.
"""

import tkinter as tk
from tkinter import ttk
from typing import List, Tuple, Optional

from controller import MultitaskController, Config
from windows import WindowInfo


class GuiConfig:
    """GUI Configuration constants"""
    WINDOW_WIDTH = 350
    WINDOW_HEIGHT = 200
    WINDOW_TITLE = "MultiTask Helper"
    
    # Colors
    BG_COLOR = "#f0f0f0"
    BUTTON_COLOR = "#4CAF50"
    BUTTON_HOVER = "#45a049"
    TEXT_COLOR = "#333333"
    
    # Fonts - smaller for more suggestions
    TITLE_FONT = ("Segoe UI", 9, "bold")
    NORMAL_FONT = ("Segoe UI", 8)
    SMALL_FONT = ("Segoe UI", 7)
    
    # Button configuration - smaller for more suggestions
    BUTTON_HEIGHT = 1
    BUTTON_RELIEF = tk.FLAT


class MultitaskGUI:
    """Main GUI application using clean controller pattern"""
    
    def __init__(self, enable_llm: bool = True):
        # Initialize controller
        self.controller = MultitaskController(enable_llm=enable_llm)
        
        # GUI state
        self.root = None
        self.status_label = None
        self.suggestion_buttons = []
        self.current_suggestions = []
        
        # Initialize GUI
        self._create_gui()
        self._setup_controller_callbacks()
        
        print("[GUI] Initialized successfully")
    
    def run(self):
        """Start the GUI application"""
        self.controller.start_monitoring()
        self._update_status("Ready - Copy content to see suggestions")
        
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.stop()
    
    def stop(self):
        """Stop the application"""
        self.controller.stop_monitoring()
        if self.root:
            self.root.destroy()
        print("[GUI] Application stopped")
    
    def _create_gui(self):
        """Create the main GUI interface"""
        self.root = tk.Tk()
        self._configure_window()
        self._create_widgets()
        self._position_window()
    
    def _configure_window(self):
        """Configure main window properties"""
        self.root.title(GuiConfig.WINDOW_TITLE)
        self.root.geometry(f"{GuiConfig.WINDOW_WIDTH}x{GuiConfig.WINDOW_HEIGHT}")
        self.root.configure(bg=GuiConfig.BG_COLOR)
        self.root.resizable(False, False)
        
        # Keep window on top
        self.root.attributes("-topmost", True)
    
    def _create_widgets(self):
        """Create all GUI widgets"""
        # Main frame
        main_frame = tk.Frame(self.root, bg=GuiConfig.BG_COLOR)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Title
        title_label = tk.Label(
            main_frame,
            text="MultiTask Helper",
            font=GuiConfig.TITLE_FONT,
            fg=GuiConfig.TEXT_COLOR,
            bg=GuiConfig.BG_COLOR
        )
        title_label.pack(pady=(0, 5))
        
        # System info
        self._create_system_info(main_frame)
        
        # Status
        self.status_label = tk.Label(
            main_frame,
            text="Initializing...",
            font=GuiConfig.NORMAL_FONT,
            fg=GuiConfig.TEXT_COLOR,
            bg=GuiConfig.BG_COLOR
        )
        self.status_label.pack(pady=(5, 10))
        
        # Suggestion buttons
        self._create_suggestion_buttons(main_frame)
        
        # Control buttons
        self._create_control_buttons(main_frame)
    
    def _create_system_info(self, parent):
        """Create system information display"""
        info_frame = tk.Frame(parent, bg=GuiConfig.BG_COLOR)
        info_frame.pack(fill=tk.X, pady=(0, 5))
        
        system_info = self.controller.get_system_info()
        llm_status = "Enabled" if system_info['llm_status']['initialized'] else "Disabled"
        
        info_text = f"Windows: {system_info['total_windows']} | LLM: {llm_status}"
        info_label = tk.Label(
            info_frame,
            text=info_text,
            font=GuiConfig.SMALL_FONT,
            fg="#666666",
            bg=GuiConfig.BG_COLOR
        )
        info_label.pack()
    
    def _create_suggestion_buttons(self, parent):
        """Create suggestion buttons"""
        suggestions_frame = tk.Frame(parent, bg=GuiConfig.BG_COLOR)
        suggestions_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.suggestion_buttons = []
        for i in range(5):  # Create 5 buttons for more suggestions
            btn = tk.Button(
                suggestions_frame,
                text="",
                font=GuiConfig.NORMAL_FONT,
                fg="white",
                bg="#cccccc",
                relief=GuiConfig.BUTTON_RELIEF,
                state=tk.DISABLED,
                height=GuiConfig.BUTTON_HEIGHT,
                command=lambda idx=i: self._switch_to_suggestion(idx)
            )
            btn.pack(fill=tk.X, pady=2)
            self.suggestion_buttons.append(btn)
    
    def _create_control_buttons(self, parent):
        """Create control buttons"""
        control_frame = tk.Frame(parent, bg=GuiConfig.BG_COLOR)
        control_frame.pack(fill=tk.X)
        
        # Toggle monitoring button
        self.monitor_button = tk.Button(
            control_frame,
            text="Stop Monitoring",
            font=GuiConfig.SMALL_FONT,
            command=self._toggle_monitoring,
            bg=GuiConfig.BUTTON_COLOR,
            fg="white",
            relief=GuiConfig.BUTTON_RELIEF
        )
        self.monitor_button.pack(side=tk.LEFT)
        
        # Exit button
        exit_button = tk.Button(
            control_frame,
            text="Exit",
            font=GuiConfig.SMALL_FONT,
            command=self.stop,
            bg="#f44336",
            fg="white",
            relief=GuiConfig.BUTTON_RELIEF
        )
        exit_button.pack(side=tk.RIGHT)
    
    def _position_window(self):
        """Position window in bottom-right corner"""
        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Calculate position (bottom-right with margin)
        margin = 50
        x = screen_width - GuiConfig.WINDOW_WIDTH - margin
        y = screen_height - GuiConfig.WINDOW_HEIGHT - margin - 40  # Account for taskbar
        
        self.root.geometry(f"{GuiConfig.WINDOW_WIDTH}x{GuiConfig.WINDOW_HEIGHT}+{x}+{y}")
        print(f"[GUI] Positioned at: {x}, {y}")
    
    def _setup_controller_callbacks(self):
        """Setup controller callbacks for GUI updates"""
        self.controller.set_callbacks(
            on_clipboard_change=self._on_clipboard_change,
            on_suggestions_ready=self._on_suggestions_ready,
            on_status_change=self._on_status_change
        )
    
    def _on_clipboard_change(self, content: str):
        """Handle clipboard change event"""
        # Run on GUI thread
        self.root.after(0, lambda: self._update_status("Analyzing..."))
        
        preview = content[:30] + "..." if len(content) > 30 else content
        print(f"[GUI] Clipboard: {preview}")
    
    def _on_suggestions_ready(self, suggestions: List[Tuple[str, WindowInfo, str]]):
        """Handle suggestions ready event"""
        # Run on GUI thread
        self.root.after(0, lambda: self._update_suggestions(suggestions))
    
    def _on_status_change(self, status: str):
        """Handle status change event"""
        # Run on GUI thread
        self.root.after(0, lambda: self._update_status(status))
    
    def _update_suggestions(self, suggestions: List[Tuple[str, WindowInfo, str]]):
        """Update suggestion buttons with new suggestions"""
        self.current_suggestions = suggestions
        
        # Update buttons
        for i, btn in enumerate(self.suggestion_buttons):
            if i < len(suggestions):
                reason, window, confidence = suggestions[i]
                
                # Create button text
                app_name = window.process_name.replace('.exe', '')
                title_short = window.title[:20] + "..." if len(window.title) > 20 else window.title
                button_text = f"{i+1}. {app_name}\n{title_short}"
                
                # Update button
                btn.config(
                    text=button_text,
                    state=tk.NORMAL,
                    bg=GuiConfig.BUTTON_COLOR
                )
                
                # Add hover effects
                self._add_button_hover_effects(btn)
                
            else:
                # Disable unused buttons
                btn.config(
                    text="",
                    state=tk.DISABLED,
                    bg="#cccccc"
                )
        
        print(f"[GUI] Updated {len(suggestions)} suggestions")
    
    def _add_button_hover_effects(self, button):
        """Add hover effects to suggestion buttons"""
        def on_enter(e):
            button.config(bg=GuiConfig.BUTTON_HOVER)
        
        def on_leave(e):
            button.config(bg=GuiConfig.BUTTON_COLOR)
        
        button.bind("<Enter>", on_enter)
        button.bind("<Leave>", on_leave)
    
    def _update_status(self, status: str):
        """Update status label"""
        if self.status_label:
            self.status_label.config(text=status)
    
    def _switch_to_suggestion(self, index: int):
        """Switch to the selected window suggestion"""
        if index < len(self.current_suggestions):
            reason, window, confidence = self.current_suggestions[index]
            
            success = self.controller.switch_to_window(window)
            
            if success:
                self._update_status(f"Switched to {window.process_name}")
                print(f"[GUI] Switched to: {window.process_name}")
            else:
                self._update_status("Failed to switch window")
                print(f"[GUI] Failed to switch to: {window.process_name}")
    
    def _toggle_monitoring(self):
        """Toggle clipboard monitoring"""
        if self.controller.is_monitoring:
            self.controller.stop_monitoring()
            self.monitor_button.config(text="Start Monitoring")
            self._update_status("Monitoring stopped")
        else:
            self.controller.start_monitoring()
            self.monitor_button.config(text="Stop Monitoring")
            self._update_status("Monitoring started")


def create_gui(enable_llm: bool = True) -> MultitaskGUI:
    """Factory function to create GUI instance"""
    return MultitaskGUI(enable_llm=enable_llm)