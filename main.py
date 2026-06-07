import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import pyperclip
import json
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import csv
import os
import re
from collections import defaultdict
import webbrowser


# CONFIGURATION & CONSTANTS

class Config:
    
    APP_NAME = "Smart Clipboard Manager Pro"
    APP_VERSION = "1.0.0"
    WINDOW_WIDTH = 1200
    WINDOW_HEIGHT = 800
    DATA_DIR = Path.home() / ".clipboard_manager_pro"
    HISTORY_FILE = DATA_DIR / "history.json"
    SETTINGS_FILE = DATA_DIR / "settings.json"
    
    # Ensure data directory exists
    DATA_DIR.mkdir(exist_ok=True)
    
    # UI Colors - Modern Dark Theme
    COLORS = {
        "dark_bg": "#1e1e1e",
        "darker_bg": "#121212",
        "light_bg": "#2d2d2d",
        "text_primary": "#e8e8e8",
        "text_secondary": "#a8a8a8",
        "accent": "#00d4ff",
        "accent_hover": "#00e8ff",
        "success": "#4ade80",
        "warning": "#facc15",
        "error": "#ef4444",
        "sidebar_bg": "#0f0f0f",
        "border": "#3d3d3d",
    }
    
    # UI Fonts
    FONTS = {
        "title": ("Segoe UI", 16, "bold"),
        "heading": ("Segoe UI", 12, "bold"),
        "body": ("Segoe UI", 10),
        "mono": ("Consolas", 9),
        "small": ("Segoe UI", 9),
    }
    
    # Settings defaults
    DEFAULT_SETTINGS = {
        "monitor_enabled": True,
        "max_history": 1000,
        "auto_start": True,
        "theme": "dark",
        "auto_save_interval": 60,
        "remove_duplicates": True,
        "show_timestamp": True,
    }


# DATA MANAGEMENT

class DataManager:
    """Manages clipboard history and settings persistence"""
    
    def __init__(self):
        self.history: List[Dict] = []
        self.settings: Dict = Config.DEFAULT_SETTINGS.copy()
        self.load_history()
        self.load_settings()
    
    def load_history(self) -> None:
        """Load clipboard history from JSON file"""
        try:
            if Config.HISTORY_FILE.exists():
                with open(Config.HISTORY_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.history = data if isinstance(data, list) else []
        except Exception as e:
            print(f"Error loading history: {e}")
            self.history = []
    
    def save_history(self) -> None:
        """Save clipboard history to JSON file"""
        try:
            with open(Config.HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving history: {e}")
    
    def load_settings(self) -> None:
        """Load settings from JSON file"""
        try:
            if Config.SETTINGS_FILE.exists():
                with open(Config.SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    saved_settings = json.load(f)
                    self.settings.update(saved_settings)
        except Exception as e:
            print(f"Error loading settings: {e}")
    
    def save_settings(self) -> None:
        """Save settings to JSON file"""
        try:
            with open(Config.SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    def add_to_history(self, text: str) -> bool:
        """Add item to history, avoiding consecutive duplicates"""
        if not text or not isinstance(text, str):
            return False
        
        text = text.strip()
        if not text:
            return False
        
        # Check for consecutive duplicates
        if self.history and self.history[-1]["content"] == text:
            return False
        
        # Add to history
        entry = {
            "content": text,
            "timestamp": datetime.now().isoformat(),
            "is_favorite": False,
            "is_pinned": False,
            "category": self._detect_category(text),
        }
        
        self.history.append(entry)
        
        # Enforce max history limit
        max_history = self.settings.get("max_history", 1000)
        if len(self.history) > max_history:
            self.history = self.history[-max_history:]
        
        self.save_history()
        return True
    
    def _detect_category(self, text: str) -> str:
        """Auto-detect category of clipboard content"""
        text_lower = text.lower()
        
        # Email detection
        if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', text):
            return "Email"
        
        # URL detection
        if re.match(r'^https?://', text):
            return "URL"
        
        # Phone number detection
        if re.match(r'^[\+]?[(]?[0-9]{3}[)]?[-\s\.]?[0-9]{3}[-\s\.]?[0-9]{4,6}$', text):
            return "Phone"
        
        # Code detection
        if any(keyword in text_lower for keyword in ['def ', 'function', 'const ', 'class ', '<html', 'import ']):
            return "Code"
        
        # JSON detection
        try:
            json.loads(text)
            return "JSON"
        except:
            pass
        
        return "Text"
    
    def get_history(self, filter_type: str = "all", search_query: str = "") -> List[Dict]:
        """Get filtered history"""
        filtered = self.history.copy()
        
        # Apply filter type
        if filter_type == "favorites":
            filtered = [item for item in filtered if item.get("is_favorite", False)]
        elif filter_type == "recent":
            cutoff_time = datetime.now() - timedelta(days=1)
            filtered = [item for item in filtered 
                       if datetime.fromisoformat(item["timestamp"]) > cutoff_time]
        
        # Apply search query
        if search_query:
            query_lower = search_query.lower()
            filtered = [item for item in filtered 
                       if query_lower in item["content"].lower()]
        
        return list(reversed(filtered))
    
    def get_statistics(self) -> Dict:
        """Generate clipboard statistics"""
        if not self.history:
            return {
                "total_items": 0,
                "favorites_count": 0,
                "today_copies": 0,
                "file_size_kb": 0,
                "categories": {},
                "most_copied": "",
            }
        
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_items = [item for item in self.history 
                      if datetime.fromisoformat(item["timestamp"]) >= today_start]
        
        # Count categories
        categories = defaultdict(int)
        for item in self.history:
            cat = item.get("category", "Text")
            categories[cat] += 1
        
        # Calculate file size
        file_size = 0
        if Config.HISTORY_FILE.exists():
            file_size = Config.HISTORY_FILE.stat().st_size / 1024
        
        # Find most copied
        most_copied = ""
        if self.history:
            most_copied = self.history[-1].get("content", "")[:50]
        
        return {
            "total_items": len(self.history),
            "favorites_count": sum(1 for item in self.history if item.get("is_favorite")),
            "today_copies": len(today_items),
            "file_size_kb": round(file_size, 2),
            "categories": dict(categories),
            "most_copied": most_copied,
        }
    
    def export_to_txt(self, filepath: str) -> bool:
        """Export history to TXT file"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"Clipboard History Export - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 80 + "\n\n")
                
                for i, item in enumerate(self.history, 1):
                    timestamp = datetime.fromisoformat(item["timestamp"]).strftime('%Y-%m-%d %H:%M:%S')
                    content = item["content"][:200]
                    fav_mark = "⭐ " if item.get("is_favorite") else ""
                    
                    f.write(f"{i}. [{timestamp}] {fav_mark}\n")
                    f.write(f"   Category: {item.get('category', 'Text')}\n")
                    f.write(f"   Content: {content}\n")
                    if len(item["content"]) > 200:
                        f.write(f"   ... (truncated, {len(item['content'])} chars total)\n")
                    f.write("\n")
            return True
        except Exception as e:
            print(f"Error exporting to TXT: {e}")
            return False
    
    def export_to_csv(self, filepath: str) -> bool:
        """Export history to CSV file"""
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Timestamp', 'Content', 'Category', 'Favorite', 'Pinned'])
                
                for item in self.history:
                    timestamp = datetime.fromisoformat(item["timestamp"]).strftime('%Y-%m-%d %H:%M:%S')
                    writer.writerow([
                        timestamp,
                        item["content"],
                        item.get("category", "Text"),
                        "Yes" if item.get("is_favorite") else "No",
                        "Yes" if item.get("is_pinned") else "No",
                    ])
            return True
        except Exception as e:
            print(f"Error exporting to CSV: {e}")
            return False
    
    def export_to_json(self, filepath: str) -> bool:
        """Export history to JSON file"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error exporting to JSON: {e}")
            return False
    
    def import_from_json(self, filepath: str) -> bool:
        """Import history from JSON file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                imported = json.load(f)
                if isinstance(imported, list):
                    self.history.extend(imported)
                    self.save_history()
                    return True
        except Exception as e:
            print(f"Error importing from JSON: {e}")
        return False


# CLIPBOARD MONITORING

class ClipboardMonitor:
    """Monitors system clipboard for changes"""
    
    def __init__(self, data_manager: DataManager, callback=None):
        self.data_manager = data_manager
        self.callback = callback
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.last_content = ""
    
    def start(self) -> None:
        """Start clipboard monitoring"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
    
    def stop(self) -> None:
        """Stop clipboard monitoring"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
    
    def _monitor_loop(self) -> None:
        """Monitor clipboard in background thread"""
        while self.running:
            try:
                current_content = pyperclip.paste()
                
                # Check if content changed
                if current_content != self.last_content:
                    self.last_content = current_content
                    
                    # Add to history
                    if self.data_manager.add_to_history(current_content):
                        # Notify UI
                        if self.callback:
                            self.callback(current_content)
                
                time.sleep(0.5)  # Check clipboard every 500ms
            
            except Exception as e:
                print(f"Clipboard monitoring error: {e}")
                time.sleep(1)
    
    def manual_capture(self) -> bool:
        """Manually capture current clipboard content"""
        try:
            current_content = pyperclip.paste()
            return self.data_manager.add_to_history(current_content)
        except Exception as e:
            print(f"Manual capture error: {e}")
            return False


# UI COMPONENTS

class UIStyles:
    """Custom styles for Tkinter widgets"""
    
    @staticmethod
    def setup_styles():
        """Configure ttk styles"""
        style = ttk.Style()
        
        # Configure theme
        style.theme_use('clam')
        
        # Colors
        bg = Config.COLORS["dark_bg"]
        fg = Config.COLORS["text_primary"]
        accent = Config.COLORS["accent"]
        light_bg = Config.COLORS["light_bg"]
        border = Config.COLORS["border"]
        
        # Configure TFrame
        style.configure('TFrame', background=bg, foreground=fg)
        style.configure('Sidebar.TFrame', background=Config.COLORS["sidebar_bg"])
        style.configure('Light.TFrame', background=light_bg)
        
        # Configure TLabel
        style.configure('TLabel', background=bg, foreground=fg, font=Config.FONTS["body"])
        style.configure('Title.TLabel', background=bg, foreground=fg, font=Config.FONTS["title"])
        style.configure('Heading.TLabel', background=bg, foreground=fg, font=Config.FONTS["heading"])
        style.configure('Small.TLabel', background=bg, foreground=Config.COLORS["text_secondary"], 
                       font=Config.FONTS["small"])
        
        # Configure TButton
        style.configure('TButton', background=light_bg, foreground=fg, 
                       font=Config.FONTS["body"], padding=8, relief='flat',
                       borderwidth=1)
        style.map('TButton',
                 background=[('active', accent), ('pressed', Config.COLORS["accent_hover"])],
                 foreground=[('active', Config.COLORS["darker_bg"])])
        
        # Accent button style
        style.configure('Accent.TButton', background=accent, foreground=Config.COLORS["darker_bg"])
        style.map('Accent.TButton',
                 background=[('active', Config.COLORS["accent_hover"])])
        
        # Configure TEntry
        style.configure('TEntry', background=light_bg, foreground=fg,
                       fieldbackground=light_bg, font=Config.FONTS["body"])
        
        # Configure Treeview
        style.configure('Treeview', background=light_bg, foreground=fg,
                       fieldbackground=light_bg, font=Config.FONTS["body"],
                       rowheight=30, borderwidth=0)
        style.configure('Treeview.Heading', background=Config.COLORS["darker_bg"],
                       foreground=accent, font=Config.FONTS["heading"])
        style.map('Treeview', background=[('selected', accent)])
        
        # Configure Scrollbar
        style.configure('Vertical.TScrollbar', background=light_bg, troughcolor=Config.COLORS["darker_bg"],
                       bordercolor=border, arrowcolor=fg)


# MAIN APPLICATION

class ClipboardManagerApp:
    """Main application class"""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.data_manager = DataManager()
        self.clipboard_monitor = ClipboardMonitor(
            self.data_manager,
            callback=self.on_clipboard_change
        )
        
        # Setup window
        self.root.title(f"{Config.APP_NAME} v{Config.APP_VERSION}")
        self.root.geometry(f"{Config.WINDOW_WIDTH}x{Config.WINDOW_HEIGHT}")
        self.root.configure(bg=Config.COLORS["dark_bg"])
        
        # Configure styles
        UIStyles.setup_styles()
        
        # Variables
        self.current_filter = tk.StringVar(value="all")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.on_search_change())
        
        # Auto-save timer
        self.auto_save_timer = None
        
        # Build UI
        self.setup_ui()
        self.refresh_history()
        
        # Start clipboard monitoring
        if self.data_manager.settings.get("monitor_enabled", True):
            self.clipboard_monitor.start()
        
        # Setup auto-save
        self.setup_auto_save()
        
        # Keyboard shortcuts
        self.setup_shortcuts()
        
        # Window close handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_ui(self) -> None:
        """Setup main UI"""
        # Main container
        main_container = ttk.Frame(self.root, style='TFrame')
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Configure grid
        main_container.grid_rowconfigure(0, weight=1)
        main_container.grid_columnconfigure(0, weight=0)
        main_container.grid_columnconfigure(1, weight=1)
        
        # Sidebar
        self.setup_sidebar(main_container)
        
        # Main content area
        content_frame = ttk.Frame(main_container, style='TFrame')
        content_frame.grid(row=0, column=1, sticky='nsew', padx=10, pady=10)
        content_frame.grid_rowconfigure(1, weight=1)
        content_frame.grid_columnconfigure(0, weight=1)
        
        # Header
        self.setup_header(content_frame)
        
        # Main content (tabbed interface)
        self.setup_notebook(content_frame)
        
        # Status bar
        self.setup_status_bar(self.root)
    
    def setup_sidebar(self, parent: ttk.Frame) -> None:
        """Setup sidebar navigation"""
        sidebar = ttk.Frame(parent, style='Sidebar.TFrame', width=220)
        sidebar.grid(row=0, column=0, sticky='ns', padx=0, pady=0)
        sidebar.grid_propagate(False)
        
        # Logo/Title
        title_frame = ttk.Frame(sidebar, style='Sidebar.TFrame')
        title_frame.pack(fill=tk.X, padx=15, pady=20)
        
        title_label = ttk.Label(title_frame, text="📋 Manager", style='Heading.TLabel')
        title_label.configure(background=Config.COLORS["sidebar_bg"], foreground=Config.COLORS["accent"])
        title_label.pack()
        
        version_label = ttk.Label(title_frame, text=f"v{Config.APP_VERSION}", style='Small.TLabel')
        version_label.configure(background=Config.COLORS["sidebar_bg"])
        version_label.pack()
        
        # Separator
        separator = ttk.Frame(sidebar, height=1)
        separator.pack(fill=tk.X, padx=10, pady=10)
        
        # Navigation buttons
        nav_buttons = [
            ("📋 All Items", "all"),
            ("⭐ Favorites", "favorites"),
            ("🕐 Recent", "recent"),
        ]
        
        for label, filter_type in nav_buttons:
            btn = ttk.Button(sidebar, text=label, 
                           command=lambda ft=filter_type: self.set_filter(ft))
            btn.pack(fill=tk.X, padx=10, pady=5)
        
        # Separator
        separator = ttk.Frame(sidebar, height=1)
        separator.pack(fill=tk.X, padx=10, pady=15)
        
        # Quick actions
        action_buttons = [
            ("📊 Statistics", self.show_statistics),
            ("⚙️ Settings", self.show_settings),
            ("📤 Export", self.show_export),
            ("📥 Import", self.show_import),
        ]
        
        for label, command in action_buttons:
            btn = ttk.Button(sidebar, text=label, command=command)
            btn.pack(fill=tk.X, padx=10, pady=5)
        
        # Separator
        separator = ttk.Frame(sidebar, height=1)
        separator.pack(fill=tk.X, padx=10, pady=15)
        
        # Status indicator
        status_frame = ttk.Frame(sidebar, style='Sidebar.TFrame')
        status_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.monitor_indicator = ttk.Label(status_frame, text="● Monitoring", style='Small.TLabel')
        self.monitor_indicator.configure(background=Config.COLORS["sidebar_bg"],
                                        foreground=Config.COLORS["success"])
        self.monitor_indicator.pack(anchor='w')
        
        # Bottom buttons
        bottom_frame = ttk.Frame(sidebar, style='Sidebar.TFrame')
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)
        
        clear_btn = ttk.Button(bottom_frame, text="🗑️ Clear All", command=self.clear_all_history)
        clear_btn.pack(fill=tk.X, pady=3)
    
    def setup_header(self, parent: ttk.Frame) -> None:
        """Setup header with search and filters"""
        header = ttk.Frame(parent, style='Light.TFrame')
        header.grid(row=0, column=0, sticky='ew', pady=(0, 15))
        header.grid_columnconfigure(1, weight=1)
        
        # Title
        title = ttk.Label(header, text="Clipboard History", style='Title.TLabel')
        title.configure(background=Config.COLORS["light_bg"])
        title.grid(row=0, column=0, sticky='w', padx=15, pady=15)
        
        # Search bar
        search_frame = ttk.Frame(header, style='Light.TFrame')
        search_frame.grid(row=0, column=1, sticky='e', padx=15, pady=15)
        
        search_label = ttk.Label(search_frame, text="🔍 Search:", style='Small.TLabel')
        search_label.configure(background=Config.COLORS["light_bg"])
        search_label.pack(side=tk.LEFT, padx=(0, 8))
        
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        search_entry.pack(side=tk.LEFT)
    
    def setup_notebook(self, parent: ttk.Frame) -> None:
        """Setup tabbed interface"""
        self.notebook = ttk.Notebook(parent)
        self.notebook.grid(row=1, column=0, sticky='nsew')
        
        # History tab
        self.history_frame = ttk.Frame(self.notebook, style='TFrame')
        self.notebook.add(self.history_frame, text="📋 History")
        self.setup_history_tab(self.history_frame)
        
        # Quick notes tab
        notes_frame = ttk.Frame(self.notebook, style='TFrame')
        self.notebook.add(notes_frame, text="📝 Quick Notes")
        self.setup_notes_tab(notes_frame)
        
        # Templates tab
        templates_frame = ttk.Frame(self.notebook, style='TFrame')
        self.notebook.add(templates_frame, text="📋 Templates")
        self.setup_templates_tab(templates_frame)
    
    def setup_history_tab(self, parent: ttk.Frame) -> None:
        """Setup history display tab"""
        parent.grid_rowconfigure(0, weight=1)
        parent.grid_columnconfigure(0, weight=1)
        
        # Create treeview
        tree_frame = ttk.Frame(parent, style='TFrame')
        tree_frame.grid(row=0, column=0, sticky='nsew', pady=10, padx=10)
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame)
        scrollbar.grid(row=0, column=1, sticky='ns')
        
        # Treeview
        columns = ('Timestamp', 'Category', 'Preview', 'Actions')
        self.history_tree = ttk.Treeview(tree_frame, columns=columns, height=20,
                                         show='tree headings', yscrollcommand=scrollbar.set)
        self.history_tree.grid(row=0, column=0, sticky='nsew')
        scrollbar.config(command=self.history_tree.yview)
        
        # Define columns
        self.history_tree.column('#0', width=0, stretch=tk.NO)
        self.history_tree.column('Timestamp', anchor=tk.W, width=180)
        self.history_tree.column('Category', anchor=tk.W, width=100)
        self.history_tree.column('Preview', anchor=tk.W, width=400)
        self.history_tree.column('Actions', anchor=tk.CENTER, width=150)
        
        # Headings
        self.history_tree.heading('#0', text='', anchor=tk.W)
        self.history_tree.heading('Timestamp', text='Timestamp', anchor=tk.W)
        self.history_tree.heading('Category', text='Category', anchor=tk.W)
        self.history_tree.heading('Preview', text='Content Preview', anchor=tk.W)
        self.history_tree.heading('Actions', text='Actions', anchor=tk.CENTER)
        
        # Bindings
        self.history_tree.bind('<Double-1>', self.on_tree_double_click)
        self.history_tree.bind('<Button-3>', self.on_tree_right_click)
        
        # Buttons
        button_frame = ttk.Frame(parent, style='TFrame')
        button_frame.grid(row=1, column=0, sticky='ew', padx=10, pady=10)
        
        copy_btn = ttk.Button(button_frame, text="📋 Copy Selected", command=self.copy_selected)
        copy_btn.pack(side=tk.LEFT, padx=5)
        
        delete_btn = ttk.Button(button_frame, text="🗑️ Delete", command=self.delete_selected)
        delete_btn.pack(side=tk.LEFT, padx=5)
        
        favorite_btn = ttk.Button(button_frame, text="⭐ Toggle Favorite", command=self.toggle_favorite)
        favorite_btn.pack(side=tk.LEFT, padx=5)
        
        refresh_btn = ttk.Button(button_frame, text="🔄 Refresh", command=self.refresh_history)
        refresh_btn.pack(side=tk.LEFT, padx=5)
    
    def setup_notes_tab(self, parent: ttk.Frame) -> None:
        """Setup quick notes tab"""
        parent.grid_rowconfigure(0, weight=1)
        parent.grid_columnconfigure(0, weight=1)
        
        # Instructions
        info_label = ttk.Label(parent, text="Quick Notes - Save temporary notes here",
                              style='Heading.TLabel')
        info_label.configure(background=Config.COLORS["dark_bg"])
        info_label.pack(pady=10)
        
        # Text area
        text_frame = ttk.Frame(parent, style='TFrame')
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.notes_text = tk.Text(text_frame, bg=Config.COLORS["light_bg"],
                                 fg=Config.COLORS["text_primary"],
                                 font=Config.FONTS["mono"],
                                 yscrollcommand=scrollbar.set,
                                 wrap=tk.WORD, insertbackground=Config.COLORS["accent"])
        self.notes_text.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.notes_text.yview)
        
        # Buttons
        button_frame = ttk.Frame(parent, style='TFrame')
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        copy_btn = ttk.Button(button_frame, text="📋 Copy Notes", command=self.copy_notes)
        copy_btn.pack(side=tk.LEFT, padx=5)
        
        clear_btn = ttk.Button(button_frame, text="🗑️ Clear", command=lambda: self.notes_text.delete('1.0', tk.END))
        clear_btn.pack(side=tk.LEFT, padx=5)
    
    def setup_templates_tab(self, parent: ttk.Frame) -> None:
        """Setup templates tab"""
        parent.grid_rowconfigure(0, weight=1)
        parent.grid_columnconfigure(0, weight=1)
        
        # Instructions
        info_label = ttk.Label(parent, text="Quick Paste Templates",
                              style='Heading.TLabel')
        info_label.configure(background=Config.COLORS["dark_bg"])
        info_label.pack(pady=10)
        
        # Templates
        templates = [
            ("📧 Email Template", """Dear [Name],

Thank you for your email. I appreciate your inquiry.

Best regards,
[Your Name]"""),
            ("🏠 Address Template", """[Street Address]
[City], [State] [ZIP Code]
[Country]"""),
            ("☎️ Phone Template", """+1 (XXX) XXX-XXXX"""),
            ("📝 Meeting Notes", """Meeting Date: [Date]
Attendees: [Names]
Topics:
1. [Topic 1]
2. [Topic 2]

Action Items:
- [Action 1]
- [Action 2]
- [Action 3]"""),
        ]
        
        template_frame = ttk.Frame(parent, style='TFrame')
        template_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        template_frame.grid_rowconfigure(0, weight=1)
        template_frame.grid_columnconfigure(0, weight=1)
        
        # Scrollable frame for templates
        canvas = tk.Canvas(template_frame, bg=Config.COLORS["dark_bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(template_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, style='TFrame')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Enable mousewheel scrolling
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind_all("<MouseWheel>", on_mousewheel)
        scrollable_frame.bind_all("<MouseWheel>", on_mousewheel)
        
        # Add template buttons
        for template_name, template_content in templates:
            def make_copy_func(content):
                return lambda: self.copy_to_clipboard(content)
            
            btn_frame = ttk.Frame(scrollable_frame, style='Light.TFrame')
            btn_frame.pack(fill=tk.X, pady=8)
            
            btn = ttk.Button(btn_frame, text=f"{template_name} → Copy",
                           command=make_copy_func(template_content), style='Accent.TButton')
            btn.pack(fill=tk.X, padx=5, pady=5)
            
            preview = ttk.Label(btn_frame, text=template_content.split('\n')[0],
                              style='Small.TLabel')
            preview.configure(background=Config.COLORS["light_bg"])
            preview.pack(fill=tk.X, padx=10, pady=3)
    
    def setup_status_bar(self, parent: tk.Tk) -> None:
        """Setup status bar"""
        status_frame = ttk.Frame(parent, style='Light.TFrame')
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.status_label = ttk.Label(status_frame, text="Ready", style='Small.TLabel')
        self.status_label.configure(background=Config.COLORS["light_bg"])
        self.status_label.pack(side=tk.LEFT, padx=10, pady=5)
        
        self.info_label = ttk.Label(status_frame, text="", style='Small.TLabel')
        self.info_label.configure(background=Config.COLORS["light_bg"])
        self.info_label.pack(side=tk.RIGHT, padx=10, pady=5)
        self.update_status_info()
    
    def setup_shortcuts(self) -> None:
        """Setup keyboard shortcuts"""
        self.root.bind('<Control-c>', lambda e: self.copy_selected())
        self.root.bind('<Control-f>', lambda e: self.focus_search())
        self.root.bind('<Control-d>', lambda e: self.delete_selected())
        self.root.bind('<Control-s>', lambda e: self.show_export())
        self.root.bind('<Control-l>', lambda e: self.clear_all_history())
    
    def setup_auto_save(self) -> None:
        """Setup auto-save functionality"""
        def auto_save():
            self.data_manager.save_history()
            interval = self.data_manager.settings.get("auto_save_interval", 60)
            self.auto_save_timer = self.root.after(interval * 1000, auto_save)
        
        auto_save()
    
    # EVENT HANDLERS
    
    def on_clipboard_change(self, content: str) -> None:
        """Callback when clipboard changes"""
        self.root.after(0, self.refresh_history)
        self.root.after(0, self.update_status_info)
    
    def on_search_change(self) -> None:
        """Handle search input changes"""
        self.refresh_history()
    
    def on_tree_double_click(self, event) -> None:
        """Handle tree double-click"""
        selection = self.history_tree.selection()
        if selection:
            self.copy_selected()
    
    def on_tree_right_click(self, event) -> None:
        """Handle tree right-click context menu"""
        selection = self.history_tree.selection()
        if not selection:
            return
        
        menu = tk.Menu(self.root, bg=Config.COLORS["light_bg"],
                      fg=Config.COLORS["text_primary"], tearoff=0,
                      activebg=Config.COLORS["accent"],
                      activeforeground=Config.COLORS["darker_bg"])
        
        menu.add_command(label="📋 Copy", command=self.copy_selected)
        menu.add_command(label="⭐ Toggle Favorite", command=self.toggle_favorite)
        menu.add_command(label="✏️ Edit", command=self.edit_selected)
        menu.add_command(label="🗑️ Delete", command=self.delete_selected)
        menu.add_separator()
        menu.add_command(label="Cancel", command=menu.quit)
        
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
    
    def set_filter(self, filter_type: str) -> None:
        """Set current filter"""
        self.current_filter.set(filter_type)
        self.refresh_history()
    
    def refresh_history(self) -> None:
        """Refresh history display"""
        # Clear existing items
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        
        # Get filtered data
        filter_type = self.current_filter.get()
        search_query = self.search_var.get()
        history = self.data_manager.get_history(filter_type, search_query)
        
        # Populate tree
        for item in history:
            timestamp = datetime.fromisoformat(item["timestamp"]).strftime('%Y-%m-%d %H:%M:%S')
            category = item.get("category", "Text")
            content = item["content"][:80].replace('\n', ' ')
            fav_mark = "⭐" if item.get("is_favorite") else "○"
            
            tag = 'favorite' if item.get("is_favorite") else ''
            self.history_tree.insert('', tk.END, values=(timestamp, category, content, fav_mark))
        
        # Update status
        self.update_status_info()
    
    def copy_selected(self) -> None:
        """Copy selected item to clipboard"""
        selection = self.history_tree.selection()
        if not selection:
            messagebox.showwarning("Info", "Please select an item first")
            return
        
        item_idx = self.history_tree.index(selection[0])
        filter_type = self.current_filter.get()
        search_query = self.search_var.get()
        history = self.data_manager.get_history(filter_type, search_query)
        
        if item_idx < len(history):
            content = history[item_idx]["content"]
            try:
                pyperclip.copy(content)
                self.update_status("✓ Copied to clipboard")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to copy: {e}")
    
    def copy_to_clipboard(self, content: str) -> None:
        """Copy specific content to clipboard"""
        try:
            pyperclip.copy(content)
            self.update_status("✓ Copied to clipboard")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to copy: {e}")
    
    def copy_notes(self) -> None:
        """Copy quick notes to clipboard"""
        content = self.notes_text.get('1.0', tk.END)
        if content.strip():
            self.copy_to_clipboard(content)
        else:
            messagebox.showinfo("Info", "Notes are empty")
    
    def delete_selected(self) -> None:
        """Delete selected item"""
        selection = self.history_tree.selection()
        if not selection:
            messagebox.showwarning("Info", "Please select an item to delete")
            return
        
        if messagebox.askyesno("Confirm", "Delete selected item?"):
            item_idx = self.history_tree.index(selection[0])
            filter_type = self.current_filter.get()
            search_query = self.search_var.get()
            history = self.data_manager.get_history(filter_type, search_query)
            
            if item_idx < len(history):
                # Find and remove from main history
                content = history[item_idx]["content"]
                self.data_manager.history = [h for h in self.data_manager.history 
                                           if h["content"] != content]
                self.data_manager.save_history()
                self.refresh_history()
                self.update_status("✓ Item deleted")
    
    def toggle_favorite(self) -> None:
        """Toggle favorite status"""
        selection = self.history_tree.selection()
        if not selection:
            messagebox.showwarning("Info", "Please select an item first")
            return
        
        item_idx = self.history_tree.index(selection[0])
        filter_type = self.current_filter.get()
        search_query = self.search_var.get()
        history = self.data_manager.get_history(filter_type, search_query)
        
        if item_idx < len(history):
            content = history[item_idx]["content"]
            for h in self.data_manager.history:
                if h["content"] == content:
                    h["is_favorite"] = not h.get("is_favorite", False)
                    self.data_manager.save_history()
                    self.refresh_history()
                    status = "⭐ Added to favorites" if h["is_favorite"] else "○ Removed from favorites"
                    self.update_status(status)
                    break
    
    def edit_selected(self) -> None:
        """Edit selected item"""
        selection = self.history_tree.selection()
        if not selection:
            messagebox.showwarning("Info", "Please select an item first")
            return
        
        item_idx = self.history_tree.index(selection[0])
        filter_type = self.current_filter.get()
        search_query = self.search_var.get()
        history = self.data_manager.get_history(filter_type, search_query)
        
        if item_idx < len(history):
            content = history[item_idx]["content"]
            
            # Create edit window
            edit_window = tk.Toplevel(self.root)
            edit_window.title("Edit Item")
            edit_window.geometry("600x400")
            edit_window.configure(bg=Config.COLORS["dark_bg"])
            
            # Text area
            text_frame = ttk.Frame(edit_window, style='TFrame')
            text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            text_widget = tk.Text(text_frame, bg=Config.COLORS["light_bg"],
                                 fg=Config.COLORS["text_primary"],
                                 font=Config.FONTS["body"],
                                 wrap=tk.WORD)
            text_widget.pack(fill=tk.BOTH, expand=True)
            text_widget.insert('1.0', content)
            
            # Buttons
            button_frame = ttk.Frame(edit_window, style='TFrame')
            button_frame.pack(fill=tk.X, padx=10, pady=10)
            
            def save_edit():
                new_content = text_widget.get('1.0', tk.END).strip()
                if new_content:
                    for h in self.data_manager.history:
                        if h["content"] == content:
                            h["content"] = new_content
                            self.data_manager.save_history()
                            self.refresh_history()
                            edit_window.destroy()
                            self.update_status("✓ Item updated")
                            break
            
            save_btn = ttk.Button(button_frame, text="Save", command=save_edit)
            save_btn.pack(side=tk.LEFT, padx=5)
            
            cancel_btn = ttk.Button(button_frame, text="Cancel", command=edit_window.destroy)
            cancel_btn.pack(side=tk.LEFT, padx=5)
    
    def clear_all_history(self) -> None:
        """Clear all history"""
        if messagebox.askyesno("Confirm", "Clear ALL clipboard history? This cannot be undone."):
            self.data_manager.history = []
            self.data_manager.save_history()
            self.refresh_history()
            self.update_status("✓ History cleared")
    
    def focus_search(self) -> None:
        """Focus search bar"""
        # Implementation depends on your search widget structure
        pass
    
    # DIALOGS & PANELS
    
    def show_statistics(self) -> None:
        """Show statistics window"""
        stats = self.data_manager.get_statistics()
        
        stats_window = tk.Toplevel(self.root)
        stats_window.title("Clipboard Statistics")
        stats_window.geometry("600x500")
        stats_window.configure(bg=Config.COLORS["dark_bg"])
        
        # Title
        title = ttk.Label(stats_window, text="📊 Clipboard Statistics", style='Title.TLabel')
        title.configure(background=Config.COLORS["dark_bg"])
        title.pack(pady=15)
        
        # Stats display
        stats_frame = ttk.Frame(stats_window, style='Light.TFrame')
        stats_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        stat_items = [
            (f"Total Items", f"{stats['total_items']}"),
            (f"Favorites", f"{stats['favorites_count']}"),
            (f"Today's Copies", f"{stats['today_copies']}"),
            (f"Storage Size", f"{stats['file_size_kb']} KB"),
            (f"Most Recently Copied", f"{stats['most_copied']}"),
        ]
        
        for label, value in stat_items:
            stat_row = ttk.Frame(stats_frame, style='Light.TFrame')
            stat_row.pack(fill=tk.X, pady=10)
            
            label_widget = ttk.Label(stat_row, text=label, style='Heading.TLabel')
            label_widget.configure(background=Config.COLORS["light_bg"])
            label_widget.pack(side=tk.LEFT, padx=10)
            
            value_widget = ttk.Label(stat_row, text=value, style='Small.TLabel')
            value_widget.configure(background=Config.COLORS["light_bg"],
                                  foreground=Config.COLORS["accent"])
            value_widget.pack(side=tk.RIGHT, padx=10)
        
        # Categories
        if stats['categories']:
            ttk.Separator(stats_frame).pack(fill=tk.X, pady=15)
            
            cat_title = ttk.Label(stats_frame, text="Categories", style='Heading.TLabel')
            cat_title.configure(background=Config.COLORS["light_bg"])
            cat_title.pack(pady=10)
            
            for category, count in sorted(stats['categories'].items(), key=lambda x: x[1], reverse=True):
                cat_row = ttk.Frame(stats_frame, style='Light.TFrame')
                cat_row.pack(fill=tk.X, pady=5)
                
                cat_label = ttk.Label(cat_row, text=f"{category}: {count}", style='Small.TLabel')
                cat_label.configure(background=Config.COLORS["light_bg"])
                cat_label.pack(side=tk.LEFT, padx=10)
    
    def show_settings(self) -> None:
        """Show settings window"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Settings")
        settings_window.geometry("500x600")
        settings_window.configure(bg=Config.COLORS["dark_bg"])
        
        # Title
        title = ttk.Label(settings_window, text="⚙️ Settings", style='Title.TLabel')
        title.configure(background=Config.COLORS["dark_bg"])
        title.pack(pady=15)
        
        # Settings frame
        settings_frame = ttk.Frame(settings_window, style='Light.TFrame')
        settings_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Monitor enabled
        monitor_var = tk.BooleanVar(value=self.data_manager.settings.get("monitor_enabled", True))
        monitor_check = ttk.Checkbutton(settings_frame, text="Enable Clipboard Monitoring",
                                       variable=monitor_var)
        monitor_check.pack(anchor='w', pady=10)
        
        # Auto-start
        auto_start_var = tk.BooleanVar(value=self.data_manager.settings.get("auto_start", True))
        auto_start_check = ttk.Checkbutton(settings_frame, text="Auto-start Monitoring",
                                          variable=auto_start_var)
        auto_start_check.pack(anchor='w', pady=10)
        
        # Remove duplicates
        dup_var = tk.BooleanVar(value=self.data_manager.settings.get("remove_duplicates", True))
        dup_check = ttk.Checkbutton(settings_frame, text="Remove Consecutive Duplicates",
                                   variable=dup_var)
        dup_check.pack(anchor='w', pady=10)
        
        # Show timestamp
        timestamp_var = tk.BooleanVar(value=self.data_manager.settings.get("show_timestamp", True))
        timestamp_check = ttk.Checkbutton(settings_frame, text="Show Timestamps",
                                         variable=timestamp_var)
        timestamp_check.pack(anchor='w', pady=10)
        
        # Max history
        ttk.Label(settings_frame, text="Maximum History Size:", style='Heading.TLabel').configure(
            background=Config.COLORS["light_bg"])
        ttk.Label(settings_frame, text="Maximum History Size:", style='Heading.TLabel').pack(anchor='w', pady=(10, 5))
        
        max_history_var = tk.StringVar(value=str(self.data_manager.settings.get("max_history", 1000)))
        max_history_entry = ttk.Entry(settings_frame, textvariable=max_history_var, width=10)
        max_history_entry.pack(anchor='w', pady=5)
        
        # Auto-save interval
        ttk.Label(settings_frame, text="Auto-save Interval (seconds):", style='Heading.TLabel').configure(
            background=Config.COLORS["light_bg"])
        ttk.Label(settings_frame, text="Auto-save Interval (seconds):", style='Heading.TLabel').pack(anchor='w', pady=(10, 5))
        
        auto_save_var = tk.StringVar(value=str(self.data_manager.settings.get("auto_save_interval", 60)))
        auto_save_entry = ttk.Entry(settings_frame, textvariable=auto_save_var, width=10)
        auto_save_entry.pack(anchor='w', pady=5)
        
        # Buttons
        button_frame = ttk.Frame(settings_window, style='TFrame')
        button_frame.pack(fill=tk.X, padx=20, pady=20)
        
        def save_settings():
            try:
                self.data_manager.settings["monitor_enabled"] = monitor_var.get()
                self.data_manager.settings["auto_start"] = auto_start_var.get()
                self.data_manager.settings["remove_duplicates"] = dup_var.get()
                self.data_manager.settings["show_timestamp"] = timestamp_var.get()
                self.data_manager.settings["max_history"] = int(max_history_var.get())
                self.data_manager.settings["auto_save_interval"] = int(auto_save_var.get())
                
                self.data_manager.save_settings()
                messagebox.showinfo("Success", "Settings saved successfully")
                settings_window.destroy()
            except ValueError:
                messagebox.showerror("Error", "Invalid values entered")
        
        save_btn = ttk.Button(button_frame, text="Save Settings", command=save_settings)
        save_btn.pack(side=tk.LEFT, padx=5)
        
        cancel_btn = ttk.Button(button_frame, text="Cancel", command=settings_window.destroy)
        cancel_btn.pack(side=tk.LEFT, padx=5)
    
    def show_export(self) -> None:
        """Show export dialog"""
        export_window = tk.Toplevel(self.root)
        export_window.title("Export Clipboard History")
        export_window.geometry("400x300")
        export_window.configure(bg=Config.COLORS["dark_bg"])
        
        # Title
        title = ttk.Label(export_window, text="📤 Export History", style='Title.TLabel')
        title.configure(background=Config.COLORS["dark_bg"])
        title.pack(pady=15)
        
        # Export options
        options_frame = ttk.Frame(export_window, style='Light.TFrame')
        options_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        formats = [
            ("JSON Format", "json"),
            ("CSV Format", "csv"),
            ("Text Format", "txt"),
        ]
        
        selected_format = tk.StringVar(value="json")
        
        for label, value in formats:
            radio = ttk.Radiobutton(options_frame, text=label, variable=selected_format, value=value)
            radio.pack(anchor='w', pady=10)
        
        # Buttons
        button_frame = ttk.Frame(export_window, style='TFrame')
        button_frame.pack(fill=tk.X, padx=20, pady=20)
        
        def do_export():
            file_ext = selected_format.get()
            if file_ext == "json":
                filepath = filedialog.asksaveasfilename(defaultextension=".json",
                                                       filetypes=[("JSON files", "*.json")])
                if filepath:
                    if self.data_manager.export_to_json(filepath):
                        messagebox.showinfo("Success", f"History exported to {filepath}")
            elif file_ext == "csv":
                filepath = filedialog.asksaveasfilename(defaultextension=".csv",
                                                       filetypes=[("CSV files", "*.csv")])
                if filepath:
                    if self.data_manager.export_to_csv(filepath):
                        messagebox.showinfo("Success", f"History exported to {filepath}")
            else:  # txt
                filepath = filedialog.asksaveasfilename(defaultextension=".txt",
                                                       filetypes=[("Text files", "*.txt")])
                if filepath:
                    if self.data_manager.export_to_txt(filepath):
                        messagebox.showinfo("Success", f"History exported to {filepath}")
        
        export_btn = ttk.Button(button_frame, text="Export", command=do_export, style='Accent.TButton')
        export_btn.pack(fill=tk.X, pady=5)
        
        cancel_btn = ttk.Button(button_frame, text="Cancel", command=export_window.destroy)
        cancel_btn.pack(fill=tk.X, pady=5)
    
    def show_import(self) -> None:
        """Show import dialog"""
        filepath = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if filepath:
            if self.data_manager.import_from_json(filepath):
                self.refresh_history()
                messagebox.showinfo("Success", "History imported successfully")
            else:
                messagebox.showerror("Error", "Failed to import history")
    
    # UTILITY METHODS
    
    def update_status(self, message: str) -> None:
        """Update status bar message"""
        self.status_label.configure(text=message)
        self.root.after(3000, lambda: self.update_status("Ready"))
    
    def update_status_info(self) -> None:
        """Update status info"""
        total = len(self.data_manager.history)
        today = len(self.data_manager.get_history("recent"))
        info_text = f"Total: {total} | Today: {today}"
        self.info_label.configure(text=info_text)
    
    def on_closing(self) -> None:
        """Handle window closing"""
        self.clipboard_monitor.stop()
        self.data_manager.save_history()
        self.data_manager.save_settings()
        if self.auto_save_timer:
            self.root.after_cancel(self.auto_save_timer)
        self.root.destroy()


# MAIN ENTRY POINT

def main():
    """Main entry point"""
    root = tk.Tk()
    app = ClipboardManagerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()