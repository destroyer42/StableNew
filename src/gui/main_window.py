"""Modern Tkinter GUI for Stable Diffusion pipeline with dark theme"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
import threading
import json
import subprocess
import sys
import time
import tkinter.simpledialog

from ..api import SDWebUIClient
from ..pipeline import Pipeline, VideoCreator
from ..utils import ConfigManager, StructuredLogger, setup_logging
from ..utils.file_io import get_prompt_packs, read_prompt_pack

logger = logging.getLogger(__name__)


class StableNewGUI:
    """Main GUI application with modern dark theme"""
    
    def __init__(self):
        """Initialize GUI"""
        self.root = tk.Tk()
        self.root.title("StableNew - Stable Diffusion WebUI Automation")
        self.root.geometry("1200x800")
        self.root.configure(bg='#2b2b2b')
        
        # Initialize components
        self.config_manager = ConfigManager()
        self.structured_logger = StructuredLogger()
        self.client = None
        self.pipeline = None
        self.video_creator = VideoCreator()
        
        # GUI state
        self.selected_packs = []
        self.custom_lists = {}
        self.current_config = None
        self.api_connected = False
        
        # Apply dark theme
        self._setup_dark_theme()
        
        # Load or create default preset
        self._ensure_default_preset()
        
        # Auto-launch WebUI
        self._launch_webui()
        
        # Build UI
        self._build_ui()
        
        # Setup logging redirect
        setup_logging("INFO")
        
    def _setup_dark_theme(self):
        """Setup dark theme for the application"""
        style = ttk.Style()
        
        # Configure dark theme colors
        bg_color = '#2b2b2b'
        fg_color = '#ffffff'
        select_bg = '#404040'
        select_fg = '#ffffff'
        button_bg = '#404040'
        button_active = '#505050'
        entry_bg = '#3d3d3d'
        
        self.root.configure(bg=bg_color)
        
        # Configure ttk styles
        style.theme_use('clam')
        
        style.configure('Dark.TFrame', background=bg_color, borderwidth=1, relief='flat')
        style.configure('Dark.TLabel', background=bg_color, foreground=fg_color, font=('Segoe UI', 9))
        style.configure('Dark.TButton', background=button_bg, foreground=fg_color, 
                       borderwidth=1, focuscolor='none', font=('Segoe UI', 9))
        style.configure('Dark.TEntry', background=entry_bg, foreground=fg_color, 
                       borderwidth=1, insertcolor=fg_color, font=('Segoe UI', 9))
        style.configure('Dark.TCombobox', background=entry_bg, foreground=fg_color,
                       borderwidth=1, selectbackground=select_bg, font=('Segoe UI', 9))
        style.configure('Dark.TCheckbutton', background=bg_color, foreground=fg_color,
                       focuscolor='none', font=('Segoe UI', 9))
        style.configure('Dark.TRadiobutton', background=bg_color, foreground=fg_color,
                       focuscolor='none', font=('Segoe UI', 9))
        style.configure('Dark.TNotebook', background=bg_color, borderwidth=0)
        style.configure('Dark.TNotebook.Tab', background=button_bg, foreground=fg_color,
                       padding=[20, 8], borderwidth=0)
        
        # Map states
        style.map('Dark.TButton',
                 background=[('active', button_active), ('pressed', select_bg)],
                 foreground=[('active', fg_color)])
        
        style.map('Dark.TNotebook.Tab',
                 background=[('selected', select_bg), ('active', button_active)])
        
    def _launch_webui(self):
        """Auto-launch Stable Diffusion WebUI"""
        webui_path = Path("C:/Users/rober/stable-diffusion-webui/webui-user.bat")
        
        if webui_path.exists():
            try:
                # Launch WebUI in background
                subprocess.Popen([str(webui_path), "--api"], 
                               cwd=webui_path.parent,
                               creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0)
                logger.info("Launched Stable Diffusion WebUI")
                
                # Start API checking after a delay
                self.root.after(5000, self._check_api_connection)
                
            except Exception as e:
                logger.error(f"Failed to launch WebUI: {e}")
                messagebox.showwarning("WebUI Launch", 
                                     f"Failed to auto-launch WebUI: {e}\n\n"
                                     "Please start it manually and click 'Check API'")
        else:
            logger.warning("WebUI not found at expected location")
            messagebox.showinfo("WebUI Not Found", 
                              "Please start Stable Diffusion WebUI manually\n"
                              "with --api flag and click 'Check API'")
        
    def _ensure_default_preset(self):
        """Ensure default preset exists"""
        if "default" not in self.config_manager.list_presets():
            default_config = self.config_manager.get_default_config()
            self.config_manager.save_preset("default", default_config)
    
    def _build_ui(self):
        """Build the modern user interface"""
        # Create main container with dark theme
        main_frame = ttk.Frame(self.root, style='Dark.TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Top frame for API status
        self._build_api_status_frame(main_frame)
        
        # Middle frame with left panel (prompt packs) and right panel (config/pipeline)
        middle_frame = ttk.Frame(main_frame, style='Dark.TFrame')
        middle_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Left panel - Prompt pack selection
        self._build_prompt_pack_panel(middle_frame)
        
        # Right panel - Configuration and pipeline controls
        self._build_config_pipeline_panel(middle_frame)
        
        # Bottom frame - Live log and action buttons
        self._build_bottom_panel(main_frame)
        
        # Initialize UI state
        self._initialize_ui_state()
    
    def _build_api_status_frame(self, parent):
        """Build API connection status frame"""
        api_frame = ttk.LabelFrame(parent, text="🔌 API Connection", style='Dark.TFrame', padding=10)
        api_frame.pack(fill=tk.X, pady=(0, 10))
        
        # API URL
        url_frame = ttk.Frame(api_frame, style='Dark.TFrame')
        url_frame.pack(fill=tk.X)
        
        ttk.Label(url_frame, text="WebUI API URL:", style='Dark.TLabel').pack(side=tk.LEFT)
        self.api_url_var = tk.StringVar(value="http://127.0.0.1:7860")
        api_entry = ttk.Entry(url_frame, textvariable=self.api_url_var, style='Dark.TEntry', width=40)
        api_entry.pack(side=tk.LEFT, padx=(10, 10))
        
        # Check API button
        self.check_api_btn = ttk.Button(url_frame, text="🔄 Check API", 
                                       command=self._check_api_connection, style='Dark.TButton')
        self.check_api_btn.pack(side=tk.LEFT, padx=(5, 10))
        
        # Status indicator
        self.api_status_label = ttk.Label(url_frame, text="● Disconnected", 
                                         style='Dark.TLabel', foreground='#ff6b6b')
        self.api_status_label.pack(side=tk.LEFT)
        
    def _build_prompt_pack_panel(self, parent):
        """Build prompt pack selection panel"""
        # Left panel container
        left_panel = ttk.Frame(parent, style='Dark.TFrame')
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # Prompt packs section
        packs_frame = ttk.LabelFrame(left_panel, text="📝 Prompt Packs", style='Dark.TFrame', padding=10)
        packs_frame.pack(fill=tk.BOTH, expand=True)
        
        # List management dropdown
        list_mgmt_frame = ttk.Frame(packs_frame, style='Dark.TFrame')
        list_mgmt_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(list_mgmt_frame, text="Saved Lists:", style='Dark.TLabel').pack(side=tk.LEFT)
        
        self.saved_lists_var = tk.StringVar()
        self.saved_lists_combo = ttk.Combobox(list_mgmt_frame, textvariable=self.saved_lists_var,
                                             style='Dark.TCombobox', width=20, state='readonly')
        self.saved_lists_combo.pack(side=tk.LEFT, padx=(5, 5))
        
        ttk.Button(list_mgmt_frame, text="📁 Load", command=self._load_pack_list, 
                  style='Dark.TButton').pack(side=tk.LEFT, padx=2)
        ttk.Button(list_mgmt_frame, text="💾 Save", command=self._save_pack_list, 
                  style='Dark.TButton').pack(side=tk.LEFT, padx=2)
        ttk.Button(list_mgmt_frame, text="✏️ Edit", command=self._edit_pack_list, 
                  style='Dark.TButton').pack(side=tk.LEFT, padx=2)
        ttk.Button(list_mgmt_frame, text="🗑️ Delete", command=self._delete_pack_list, 
                  style='Dark.TButton').pack(side=tk.LEFT, padx=2)
        
        # Multi-select listbox for prompt packs
        packs_list_frame = ttk.Frame(packs_frame, style='Dark.TFrame')
        packs_list_frame.pack(fill=tk.BOTH, expand=True)
        
        # Listbox with scrollbar
        listbox_frame = tk.Frame(packs_list_frame, bg='#2b2b2b')
        listbox_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(listbox_frame, bg='#404040', troughcolor='#2b2b2b')
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.packs_listbox = tk.Listbox(listbox_frame, selectmode=tk.EXTENDED,
                                       yscrollcommand=scrollbar.set,
                                       bg='#3d3d3d', fg='#ffffff', 
                                       selectbackground='#0078d4',
                                       selectforeground='#ffffff',
                                       font=('Segoe UI', 9, 'bold'),
                                       borderwidth=2, highlightthickness=1,
                                       highlightcolor='#0078d4',
                                       activestyle='dotbox')
        self.packs_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.packs_listbox.yview)
        
        # Bind selection events for dynamic config updates
        self.packs_listbox.bind('<<ListboxSelect>>', self._on_pack_selection_changed)
        
        # Refresh packs button
        ttk.Button(packs_frame, text="🔄 Refresh Packs", command=self._refresh_prompt_packs,
                  style='Dark.TButton').pack(pady=(10, 0))
        
        # Load prompt packs (defer logging until log widget is ready)
        self._refresh_prompt_packs_silent()
        
    def _build_config_pipeline_panel(self, parent):
        """Build configuration and pipeline control panel"""
        # Right panel container
        right_panel = ttk.Frame(parent, style='Dark.TFrame')
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Configuration notebook
        config_notebook = ttk.Notebook(right_panel, style='Dark.TNotebook')
        config_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Configuration display tab
        self._build_config_display_tab(config_notebook)
        
        # Pipeline controls tab  
        self._build_pipeline_controls_tab(config_notebook)
        
    def _build_config_display_tab(self, notebook):
        """Build configuration display/edit tab"""
        config_frame = ttk.Frame(notebook, style='Dark.TFrame')
        notebook.add(config_frame, text="⚙️ Configuration")
        
        # Config mode toggle
        mode_frame = ttk.Frame(config_frame, style='Dark.TFrame')
        mode_frame.pack(fill=tk.X, pady=(10, 10))
        
        self.config_mode_var = tk.StringVar(value="display")
        display_radio = ttk.Radiobutton(mode_frame, text="📄 Display Mode", variable=self.config_mode_var,
                       value="display", command=self._update_config_display,
                       style='Dark.TRadiobutton')
        display_radio.pack(side=tk.LEFT, padx=(0, 20))
        ttk.Radiobutton(mode_frame, text="✏️ Edit Mode", variable=self.config_mode_var,
                       value="edit", command=self._update_config_display,
                       style='Dark.TRadiobutton').pack(side=tk.LEFT)
        
        # Config display area
        config_display_frame = ttk.Frame(config_frame, style='Dark.TFrame')
        config_display_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Scrolled text widget for config
        self.config_text = scrolledtext.ScrolledText(config_display_frame, 
                                                    height=20, wrap=tk.WORD,
                                                    bg='#3d3d3d', fg='#ffffff',
                                                    font=('Consolas', 9),
                                                    insertbackground='#ffffff',
                                                    selectbackground='#404040')
        self.config_text.pack(fill=tk.BOTH, expand=True)
        
        # Config action buttons
        config_buttons = ttk.Frame(config_frame, style='Dark.TFrame')
        config_buttons.pack(fill=tk.X)
        
        ttk.Button(config_buttons, text="🔄 Refresh", command=self._refresh_config,
                  style='Dark.TButton').pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(config_buttons, text="💾 Save Changes", command=self._save_config,
                  style='Dark.TButton').pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(config_buttons, text="↺ Reset", command=self._reset_config,
                  style='Dark.TButton').pack(side=tk.LEFT)
    
    def _build_pipeline_controls_tab(self, notebook):
        """Build pipeline execution controls tab"""
        pipeline_frame = ttk.Frame(notebook, style='Dark.TFrame')
        notebook.add(pipeline_frame, text="🚀 Pipeline Controls")
        
        # Pipeline execution options
        exec_options_frame = ttk.LabelFrame(pipeline_frame, text="Execution Options", 
                                          style='Dark.TFrame', padding=10)
        exec_options_frame.pack(fill=tk.X, pady=(10, 10))
        
        # Stage selection
        stages_frame = ttk.Frame(exec_options_frame, style='Dark.TFrame')
        stages_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(stages_frame, text="Pipeline Stages:", style='Dark.TLabel').pack(anchor=tk.W)
        
        stage_checks_frame = ttk.Frame(stages_frame, style='Dark.TFrame')
        stage_checks_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.txt2img_enabled = tk.BooleanVar(value=True)
        self.img2img_enabled = tk.BooleanVar(value=True)
        self.upscale_enabled = tk.BooleanVar(value=True)
        self.video_enabled = tk.BooleanVar(value=False)
        
        ttk.Checkbutton(stage_checks_frame, text="🎨 txt2img", variable=self.txt2img_enabled,
                       style='Dark.TCheckbutton').pack(side=tk.LEFT, padx=(0, 20))
        ttk.Checkbutton(stage_checks_frame, text="🧹 img2img cleanup", variable=self.img2img_enabled,
                       style='Dark.TCheckbutton').pack(side=tk.LEFT, padx=(0, 20))
        ttk.Checkbutton(stage_checks_frame, text="📈 Upscale", variable=self.upscale_enabled,
                       style='Dark.TCheckbutton').pack(side=tk.LEFT, padx=(0, 20))
        ttk.Checkbutton(stage_checks_frame, text="🎬 Create Video", variable=self.video_enabled,
                       style='Dark.TCheckbutton').pack(side=tk.LEFT)
        
        # Loop configuration
        loop_frame = ttk.Frame(exec_options_frame, style='Dark.TFrame')
        loop_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Label(loop_frame, text="Loop Configuration:", style='Dark.TLabel').pack(anchor=tk.W)
        
        loop_controls = ttk.Frame(loop_frame, style='Dark.TFrame')
        loop_controls.pack(fill=tk.X, pady=(5, 0))
        
        # Loop type
        self.loop_type_var = tk.StringVar(value="single")
        ttk.Radiobutton(loop_controls, text="Single run", variable=self.loop_type_var,
                       value="single", style='Dark.TRadiobutton').grid(row=0, column=0, sticky=tk.W)
        ttk.Radiobutton(loop_controls, text="Loop stages", variable=self.loop_type_var,
                       value="stages", style='Dark.TRadiobutton').grid(row=0, column=1, sticky=tk.W, padx=(20, 0))
        ttk.Radiobutton(loop_controls, text="Loop pipeline", variable=self.loop_type_var,
                       value="pipeline", style='Dark.TRadiobutton').grid(row=0, column=2, sticky=tk.W, padx=(20, 0))
        
        # Loop count
        loop_count_frame = ttk.Frame(loop_controls, style='Dark.TFrame')
        loop_count_frame.grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=(10, 0))
        
        ttk.Label(loop_count_frame, text="Loop count:", style='Dark.TLabel').pack(side=tk.LEFT)
        self.loop_count_var = tk.StringVar(value="1")
        loop_count_spin = ttk.Spinbox(loop_count_frame, from_=1, to=100, width=5,
                                     textvariable=self.loop_count_var, style='Dark.TEntry')
        loop_count_spin.pack(side=tk.LEFT, padx=(5, 0))
        
        # Batch configuration
        batch_frame = ttk.LabelFrame(pipeline_frame, text="Batch Configuration", 
                                   style='Dark.TFrame', padding=10)
        batch_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Pack selection mode
        pack_mode_frame = ttk.Frame(batch_frame, style='Dark.TFrame')
        pack_mode_frame.pack(fill=tk.X)
        
        self.pack_mode_var = tk.StringVar(value="selected")
        ttk.Radiobutton(pack_mode_frame, text="Selected packs only", variable=self.pack_mode_var,
                       value="selected", style='Dark.TRadiobutton').pack(side=tk.LEFT, padx=(0, 20))
        ttk.Radiobutton(pack_mode_frame, text="All packs", variable=self.pack_mode_var,
                       value="all", style='Dark.TRadiobutton').pack(side=tk.LEFT, padx=(0, 20))
        ttk.Radiobutton(pack_mode_frame, text="Custom list", variable=self.pack_mode_var,
                       value="custom", style='Dark.TRadiobutton').pack(side=tk.LEFT)
        
        # Images per prompt
        images_frame = ttk.Frame(batch_frame, style='Dark.TFrame')
        images_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Label(images_frame, text="Images per prompt:", style='Dark.TLabel').pack(side=tk.LEFT)
        self.images_per_prompt_var = tk.StringVar(value="1")
        images_spin = ttk.Spinbox(images_frame, from_=1, to=10, width=5,
                                 textvariable=self.images_per_prompt_var, style='Dark.TEntry')
        images_spin.pack(side=tk.LEFT, padx=(5, 0))
    
    def _build_bottom_panel(self, parent):
        """Build bottom panel with logs and action buttons"""
        bottom_frame = ttk.Frame(parent, style='Dark.TFrame')
        bottom_frame.pack(fill=tk.BOTH, expand=False, pady=(10, 0))
        
        # Action buttons frame
        actions_frame = ttk.Frame(bottom_frame, style='Dark.TFrame')
        actions_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Main execution buttons
        main_buttons = ttk.Frame(actions_frame, style='Dark.TFrame')
        main_buttons.pack(side=tk.LEFT)
        
        self.run_pipeline_btn = ttk.Button(main_buttons, text="🚀 Run Full Pipeline", 
                                          command=self._run_full_pipeline,
                                          style='Dark.TButton')
        self.run_pipeline_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(main_buttons, text="🎨 txt2img Only", command=self._run_txt2img_only,
                  style='Dark.TButton').pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(main_buttons, text="📈 Upscale Only", command=self._run_upscale_only,
                  style='Dark.TButton').pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(main_buttons, text="🎬 Create Video", command=self._create_video,
                  style='Dark.TButton').pack(side=tk.LEFT, padx=(0, 10))
        
        # Utility buttons
        util_buttons = ttk.Frame(actions_frame, style='Dark.TFrame')
        util_buttons.pack(side=tk.RIGHT)
        
        ttk.Button(util_buttons, text="📁 Open Output", command=self._open_output_folder,
                  style='Dark.TButton').pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(util_buttons, text="⏹️ Stop", command=self._stop_execution,
                  style='Dark.TButton').pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(util_buttons, text="❌ Exit", command=self._graceful_exit,
                  style='Dark.TButton').pack(side=tk.LEFT)
        
        # Live log panel
        log_frame = ttk.LabelFrame(bottom_frame, text="📋 Live Log", style='Dark.TFrame', padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        # Log text widget
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, wrap=tk.WORD,
                                                 bg='#1e1e1e', fg='#ffffff',
                                                 font=('Consolas', 9),
                                                 state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Configure log colors
        self.log_text.tag_configure("INFO", foreground="#4CAF50")
        self.log_text.tag_configure("WARNING", foreground="#FF9800")
        self.log_text.tag_configure("ERROR", foreground="#f44336")
        self.log_text.tag_configure("SUCCESS", foreground="#2196F3")
    
    def _check_api_connection(self):
        """Check API connection status"""
        def check_in_thread():
            api_url = self.api_url_var.get()
            
            # If using default port 7860, also try common incremented ports
            ports_to_try = [7860]
            if "7860" in api_url:
                ports_to_try.extend([7861, 7862, 7863, 7864])
            
            self.log_message("Checking API connection...", "INFO")
            
            successful_url = None
            for port in ports_to_try:
                # Construct URL with the test port
                import re
                test_url = re.sub(r':(\d+)(?=/|$)', f':{port}', api_url)
                client = SDWebUIClient(test_url)
                
                self.log_message(f"Trying port {port}...", "INFO")
                
                if client.check_api_ready():
                    successful_url = test_url
                    self.api_connected = True
                    self.client = client
                    self.pipeline = Pipeline(client, self.structured_logger)
                    
                    # Update UI on main thread with the working URL
                    self.root.after(0, lambda url=test_url: self._update_api_status(True, url))
                    self.log_message(f"✅ API connection successful on {test_url}! Ready to generate.", "SUCCESS")
                    break
            
            if not successful_url:
                self.api_connected = False
                self.root.after(0, lambda: self._update_api_status(False))
                self.log_message("❌ API connection failed on all ports. Please check WebUI is running with --api", "ERROR")
        
        threading.Thread(target=check_in_thread, daemon=True).start()
    
    def _update_api_status(self, connected: bool, url: str = None):
        """Update API status indicator"""
        if connected:
            self.api_status_label.config(text="● Connected", foreground="#4CAF50")
            self.run_pipeline_btn.config(state=tk.NORMAL)
            
            # Update URL field if we found a different working port
            if url and url != self.api_url_var.get():
                self.api_url_var.set(url)
                self.log_message(f"Updated API URL to working port: {url}", "INFO")
        else:
            self.api_status_label.config(text="● Disconnected", foreground="#f44336")
            self.run_pipeline_btn.config(state=tk.DISABLED)
    
    def _on_pack_selection_changed(self, event=None):
        """Handle prompt pack selection changes - update config display dynamically"""
        selected_indices = self.packs_listbox.curselection()
        if selected_indices:
            pack_name = self.packs_listbox.get(selected_indices[0])
            self._add_log_message(f"Selected pack: {pack_name}")
        else:
            self._add_log_message("No pack selected")
            
        if self.config_mode_var.get() == "display":
            self._add_log_message("Refreshing config display...")
            self._refresh_config()
            
        # Highlight selection with custom styling
        self._update_selection_highlights()
    
    def _update_selection_highlights(self):
        """Update visual highlighting for selected items"""
        # Reset all items to default background
        for i in range(self.packs_listbox.size()):
            self.packs_listbox.itemconfig(i, {'bg': '#3d3d3d'})
        
        # Highlight selected items
        for index in self.packs_listbox.curselection():
            self.packs_listbox.itemconfig(index, {'bg': '#0078d4'})
    
    def _initialize_ui_state(self):
        """Initialize UI to default state with first pack selected and display mode active."""
        # Load available packs
        self._refresh_prompt_packs_silent()
        
        # Set display mode as default (should already be set in _build_config_panel)
        self.config_mode_var.set("display")
        
        # Select first pack if available
        if hasattr(self, 'packs_listbox') and self.packs_listbox.size() > 0:
            self.packs_listbox.selection_set(0)
            self.packs_listbox.activate(0)
            # Trigger selection change to update config display
            self._on_pack_selection_changed(None)
        
        # Update log
        self._add_log_message("GUI initialized - ready for pipeline configuration")
    
    def _refresh_prompt_packs(self):
        """Refresh the prompt packs list"""
        packs_dir = Path("packs")
        pack_files = get_prompt_packs(packs_dir)
        
        self.packs_listbox.delete(0, tk.END)
        for pack_file in pack_files:
            self.packs_listbox.insert(tk.END, pack_file.name)
        
        self.log_message(f"Found {len(pack_files)} prompt packs", "INFO")
    
    def _refresh_prompt_packs_silent(self):
        """Refresh the prompt packs list without logging (for initialization)"""
        packs_dir = Path("packs")
        pack_files = get_prompt_packs(packs_dir)
        
        self.packs_listbox.delete(0, tk.END)
        for pack_file in pack_files:
            self.packs_listbox.insert(tk.END, pack_file.name)
    
    def _refresh_config(self):
        """Refresh configuration display"""
        selected_indices = self.packs_listbox.curselection()
        if selected_indices:
            pack_name = self.packs_listbox.get(selected_indices[0])
            pack_overrides = self.config_manager.get_pack_overrides(pack_name)
        else:
            pack_overrides = {}
        
        # Resolve configuration
        self.current_config = self.config_manager.resolve_config(
            preset_name="default",
            pack_overrides=pack_overrides
        )
        
        # Display in text widget
        config_text = json.dumps(self.current_config, indent=2, ensure_ascii=False)
        
        self.config_text.config(state=tk.NORMAL)
        self.config_text.delete(1.0, tk.END)
        self.config_text.insert(1.0, config_text)
        
        if self.config_mode_var.get() == "display":
            self.config_text.config(state=tk.DISABLED)
    
    def _update_config_display(self):
        """Update config display based on mode"""
        if self.config_mode_var.get() == "edit":
            self.config_text.config(state=tk.NORMAL, bg="#2d2d2d")
        else:
            self.config_text.config(state=tk.DISABLED, bg="#3d3d3d")
            self._refresh_config()
    
    def _save_config(self):
        """Save configuration changes"""
        if self.config_mode_var.get() != "edit":
            return
        
        try:
            config_str = self.config_text.get(1.0, tk.END)
            new_config = json.loads(config_str)
            
            selected_indices = self.packs_listbox.curselection()
            if selected_indices:
                pack_name = self.packs_listbox.get(selected_indices[0])
                # Save as pack override
                self.config_manager.save_pack_overrides(pack_name, new_config)
                self.log_message(f"Saved configuration for pack: {pack_name}", "SUCCESS")
            else:
                # Save as new preset
                preset_name = tk.simpledialog.askstring("Save Preset", "Enter preset name:")
                if preset_name:
                    self.config_manager.save_preset(preset_name, new_config)
                    self.log_message(f"Saved preset: {preset_name}", "SUCCESS")
            
        except json.JSONDecodeError as e:
            messagebox.showerror("Configuration Error", f"Invalid JSON: {e}")
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save configuration: {e}")
    
    def _reset_config(self):
        """Reset configuration to defaults"""
        self._refresh_config()
        self.log_message("Configuration reset to defaults", "INFO")
    
    def _load_pack_list(self):
        """Load saved pack list"""
        list_name = self.saved_lists_var.get()
        if not list_name or list_name not in self.custom_lists:
            return
        
        pack_list = self.custom_lists[list_name]
        
        # Clear current selection
        self.packs_listbox.selection_clear(0, tk.END)
        
        # Select packs in the list
        for i in range(self.packs_listbox.size()):
            pack_name = self.packs_listbox.get(i)
            if pack_name in pack_list:
                self.packs_listbox.selection_set(i)
        
        self.log_message(f"Loaded pack list: {list_name}", "INFO")
    
    def _save_pack_list(self):
        """Save current pack selection as list"""
        selected_indices = self.packs_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("No Selection", "Please select prompt packs first")
            return
        
        list_name = tk.simpledialog.askstring("Save List", "Enter list name:")
        if not list_name:
            return
        
        selected_packs = [self.packs_listbox.get(i) for i in selected_indices]
        self.custom_lists[list_name] = selected_packs
        
        # Save to file
        lists_file = Path("custom_pack_lists.json")
        try:
            with open(lists_file, 'w', encoding='utf-8') as f:
                json.dump(self.custom_lists, f, indent=2, ensure_ascii=False)
            
            # Update combo box
            self.saved_lists_combo['values'] = list(self.custom_lists.keys())
            
            self.log_message(f"Saved pack list: {list_name}", "SUCCESS")
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save list: {e}")
    
    def _edit_pack_list(self):
        """Edit existing pack list"""
        list_name = self.saved_lists_var.get()
        if not list_name:
            messagebox.showinfo("No List Selected", "Please select a list to edit")
            return
        
        # Load the list for editing (just load it into selection)
        self._load_pack_list()
        messagebox.showinfo("Edit Mode", f"List '{list_name}' loaded for editing.\n"
                                      "Modify selection and save to update.")
    
    def _delete_pack_list(self):
        """Delete saved pack list"""
        list_name = self.saved_lists_var.get()
        if not list_name:
            return
        
        if messagebox.askyesno("Confirm Delete", f"Delete list '{list_name}'?"):
            del self.custom_lists[list_name]
            
            # Save updated lists
            lists_file = Path("custom_pack_lists.json")
            try:
                with open(lists_file, 'w', encoding='utf-8') as f:
                    json.dump(self.custom_lists, f, indent=2, ensure_ascii=False)
                
                # Update combo box
                self.saved_lists_combo['values'] = list(self.custom_lists.keys())
                self.saved_lists_var.set("")
                
                self.log_message(f"Deleted pack list: {list_name}", "INFO")
            except Exception as e:
                messagebox.showerror("Delete Error", f"Failed to delete list: {e}")
    
    def log_message(self, message: str, level: str = "INFO"):
        """Add message to live log"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, log_entry, level)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        
        # Also log to Python logger
        if level == "ERROR":
            logger.error(message)
        elif level == "WARNING":
            logger.warning(message)
        else:
            logger.info(message)
    
    def _run_full_pipeline(self):
        """Run the complete pipeline"""
        if not self.api_connected:
            messagebox.showerror("API Error", "Please connect to API first")
            return
        
        def run_pipeline_thread():
            try:
                # Get selected prompt packs
                selected_packs = self._get_selected_packs()
                if not selected_packs:
                    self.log_message("No prompt packs selected", "WARNING")
                    return
                
                # Process each pack
                for pack_file in selected_packs:
                    self.log_message(f"Processing pack: {pack_file.name}", "INFO")
                    
                    # Read prompts from pack
                    prompts = read_prompt_pack(pack_file)
                    if not prompts:
                        self.log_message(f"No prompts found in {pack_file.name}", "WARNING")
                        continue
                    
                    # Get configuration for this pack
                    pack_overrides = self.config_manager.get_pack_overrides(pack_file.stem)
                    config = self.config_manager.resolve_config(
                        preset_name="default",
                        pack_overrides=pack_overrides
                    )
                    
                    # Run pipeline
                    results = self.pipeline.run_full_pipeline(
                        prompts=prompts,
                        config=config,
                        run_name=f"{pack_file.stem}_{int(time.time())}",
                        skip_img2img=not self.img2img_enabled.get(),
                        skip_upscale=not self.upscale_enabled.get()
                    )
                    
                    self.log_message(f"Completed pack {pack_file.name}: {results['images_generated']} images", "SUCCESS")
                
                self.log_message("🎉 Pipeline execution completed!", "SUCCESS")
                
            except Exception as e:
                self.log_message(f"Pipeline execution failed: {e}", "ERROR")
        
        # Run in separate thread to avoid blocking UI
        self.log_message("🚀 Starting pipeline execution...", "INFO")
        threading.Thread(target=run_pipeline_thread, daemon=True).start()
    
    def _run_txt2img_only(self):
        """Run only txt2img generation"""
        if not self.api_connected:
            messagebox.showerror("API Error", "Please connect to API first")
            return
        
        # Check if packs are selected
        selected_indices = self.packs_listbox.curselection()
        if not selected_indices:
            messagebox.showerror("Selection Error", "Please select at least one prompt pack")
            return
        
        self._add_log_message("🎨 Running txt2img only...")
        
        def txt2img_thread():
            try:
                # Get selected packs
                selected_packs = [self.packs_listbox.get(i) for i in selected_indices]
                
                # Create run directory
                run_dir = self.structured_logger.create_run_directory("txt2img_only")
                
                # Get configuration
                config = self.current_config or self.config_manager.get_default_config()
                
                # Run txt2img for selected packs
                for pack_name in selected_packs:
                    self._add_log_message(f"Processing pack: {pack_name}")
                    
                    # Load prompts from pack
                    prompts = self.config_manager.load_prompt_pack(pack_name)
                    
                    # Get pack-specific overrides
                    pack_overrides = self.config_manager.get_pack_overrides(pack_name)
                    pack_config = self.config_manager.resolve_config("default", pack_overrides)
                    
                    # Generate images for each prompt
                    for i, prompt_data in enumerate(prompts):
                        try:
                            self._add_log_message(f"Generating image {i+1}/{len(prompts)}: {prompt_data['prompt'][:50]}...")
                            
                            # Run txt2img
                            result = self.pipeline_executor.run_txt2img_stage(
                                prompt=prompt_data['prompt'],
                                negative_prompt=prompt_data.get('negative_prompt', ''),
                                config=pack_config,
                                output_dir=run_dir / "txt2img",
                                image_index=i
                            )
                            
                            if result:
                                self._add_log_message(f"✅ Generated: {result['output_path']}")
                            else:
                                self._add_log_message(f"❌ Failed to generate image {i+1}")
                                
                        except Exception as e:
                            self._add_log_message(f"❌ Error generating image {i+1}: {str(e)}")
                            continue
                
                self._add_log_message("🎉 Txt2img generation completed!")
                
            except Exception as e:
                self._add_log_message(f"❌ Txt2img generation failed: {str(e)}")
        
        # Run in background thread
        import threading
        thread = threading.Thread(target=txt2img_thread)
        thread.daemon = True
        thread.start()
    
    def _run_upscale_only(self):
        """Run upscaling on existing images"""
        if not self.api_connected:
            messagebox.showerror("API Error", "Please connect to API first")
            return
        
        # Open file dialog to select images
        file_paths = filedialog.askopenfilenames(
            title="Select Images to Upscale",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.tiff")]
        )
        
        if not file_paths:
            return
        
        def upscale_thread():
            try:
                config = self.current_config or self.config_manager.get_default_config()
                run_dir = self.structured_logger.create_run_directory("upscale_only")
                
                for file_path in file_paths:
                    image_path = Path(file_path)
                    self.log_message(f"Upscaling: {image_path.name}", "INFO")
                    
                    result = self.pipeline.run_upscale(image_path, config['upscale'], run_dir)
                    if result:
                        self.log_message(f"✅ Upscaled: {image_path.name}", "SUCCESS")
                    else:
                        self.log_message(f"❌ Failed to upscale: {image_path.name}", "ERROR")
                
                self.log_message("Upscaling completed!", "SUCCESS")
                
            except Exception as e:
                self.log_message(f"Upscaling failed: {e}", "ERROR")
        
        threading.Thread(target=upscale_thread, daemon=True).start()
    
    def _create_video(self):
        """Create video from image sequence"""
        # Open folder dialog to select image directory
        folder_path = filedialog.askdirectory(title="Select Image Directory")
        if not folder_path:
            return
        
        def video_thread():
            try:
                image_dir = Path(folder_path)
                image_files = []
                
                for ext in ['*.png', '*.jpg', '*.jpeg']:
                    image_files.extend(image_dir.glob(ext))
                
                if not image_files:
                    self.log_message("No images found in selected directory", "WARNING")
                    return
                
                # Create output video path
                video_path = image_dir / "output_video.mp4"
                
                self.log_message(f"Creating video from {len(image_files)} images...", "INFO")
                
                success = self.video_creator.create_video_from_images(
                    image_files, video_path, fps=24
                )
                
                if success:
                    self.log_message(f"✅ Video created: {video_path}", "SUCCESS")
                else:
                    self.log_message("❌ Video creation failed", "ERROR")
                
            except Exception as e:
                self.log_message(f"Video creation failed: {e}", "ERROR")
        
        threading.Thread(target=video_thread, daemon=True).start()
    
    def _get_selected_packs(self) -> List[Path]:
        """Get list of selected prompt pack files"""
        selected_indices = self.packs_listbox.curselection()
        if not selected_indices:
            return []
        
        packs_dir = Path("packs")
        selected_packs = []
        
        for index in selected_indices:
            pack_name = self.packs_listbox.get(index)
            pack_path = packs_dir / pack_name
            if pack_path.exists():
                selected_packs.append(pack_path)
        
        return selected_packs
    
    def _open_output_folder(self):
        """Open the output folder"""
        output_dir = Path("output")
        if output_dir.exists():
            if sys.platform == "win32":
                subprocess.run(["explorer", str(output_dir)])
            elif sys.platform == "darwin":
                subprocess.run(["open", str(output_dir)])
            else:
                subprocess.run(["xdg-open", str(output_dir)])
        else:
            messagebox.showinfo("No Output", "Output directory doesn't exist yet")
    
    def _stop_execution(self):
        """Stop current execution (placeholder)"""
        self.log_message("⏹️ Stop requested (not implemented)", "WARNING")
        messagebox.showinfo("Stop", "Stop functionality not implemented yet")
    
    def _graceful_exit(self):
        """Gracefully exit the application"""
        self.log_message("Shutting down gracefully...", "INFO")
        
        # Save any pending manifests
        try:
            # Finalize logs and manifests
            self.log_message("✅ Graceful shutdown complete", "SUCCESS")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
        
        self.root.quit()
        self.root.destroy()
    
    def run(self):
        """Start the GUI application"""
        # Load custom pack lists
        lists_file = Path("custom_pack_lists.json")
        if lists_file.exists():
            try:
                with open(lists_file, 'r', encoding='utf-8') as f:
                    self.custom_lists = json.load(f)
                self.saved_lists_combo['values'] = list(self.custom_lists.keys())
            except Exception as e:
                logger.error(f"Failed to load custom lists: {e}")
        
        # Start initial config refresh
        self._refresh_config()
        
        # Now refresh prompt packs with logging (log widget is ready)
        self._refresh_prompt_packs()
        
        # Set up proper window closing
        self.root.protocol("WM_DELETE_WINDOW", self._graceful_exit)
        
        self.log_message("🚀 StableNew GUI started", "SUCCESS")
        self.log_message("Please connect to WebUI API to begin", "INFO")
        
        # Start the GUI main loop
        self.root.mainloop()
    
    def _build_pipeline_tab(self, parent):
        """Build pipeline execution tab"""
        # API Connection Frame
        api_frame = ttk.LabelFrame(parent, text="API Connection", padding=10)
        api_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(api_frame, text="API URL:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.api_url_var = tk.StringVar(value="http://127.0.0.1:7860")
        ttk.Entry(api_frame, textvariable=self.api_url_var, width=40).grid(
            row=0, column=1, padx=5, pady=2
        )
        
        self.check_api_btn = ttk.Button(
            api_frame, text="Check API", command=self._check_api
        )
        self.check_api_btn.grid(row=0, column=2, padx=5)
        
        self.api_status_label = ttk.Label(api_frame, text="Not connected", foreground="red")
        self.api_status_label.grid(row=0, column=3, padx=5)
        
        # Prompt Frame
        prompt_frame = ttk.LabelFrame(parent, text="Prompt", padding=10)
        prompt_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        ttk.Label(prompt_frame, text="Enter your prompt:").pack(anchor=tk.W)
        self.prompt_text = scrolledtext.ScrolledText(
            prompt_frame, height=6, wrap=tk.WORD
        )
        self.prompt_text.pack(fill=tk.BOTH, expand=True, pady=5)
        self.prompt_text.insert(1.0, "a beautiful landscape, high quality, detailed")
        
        # Preset Frame
        preset_frame = ttk.LabelFrame(parent, text="Preset", padding=10)
        preset_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(preset_frame, text="Select preset:").grid(row=0, column=0, padx=5)
        self.preset_var = tk.StringVar()
        self.preset_combo = ttk.Combobox(
            preset_frame, textvariable=self.preset_var, state="readonly", width=20
        )
        self.preset_combo.grid(row=0, column=1, padx=5)
        self._refresh_presets()
        
        ttk.Button(
            preset_frame, text="Refresh", command=self._refresh_presets
        ).grid(row=0, column=2, padx=5)
        
        # Options Frame
        options_frame = ttk.LabelFrame(parent, text="Options", padding=10)
        options_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(options_frame, text="Batch size:").grid(row=0, column=0, padx=5)
        self.batch_size_var = tk.IntVar(value=1)
        ttk.Spinbox(
            options_frame, from_=1, to=10, textvariable=self.batch_size_var, width=10
        ).grid(row=0, column=1, padx=5)
        
        ttk.Label(options_frame, text="Run name (optional):").grid(row=0, column=2, padx=5)
        self.run_name_var = tk.StringVar()
        ttk.Entry(options_frame, textvariable=self.run_name_var, width=20).grid(
            row=0, column=3, padx=5
        )
        
        # Pipeline stages
        self.enable_img2img_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            options_frame, text="Enable img2img cleanup", 
            variable=self.enable_img2img_var
        ).grid(row=1, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)
        
        self.enable_upscale_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            options_frame, text="Enable upscaling", 
            variable=self.enable_upscale_var
        ).grid(row=1, column=2, columnspan=2, sticky=tk.W, padx=5, pady=2)
        
        # Execution Frame
        exec_frame = ttk.Frame(parent, padding=10)
        exec_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.run_pipeline_btn = ttk.Button(
            exec_frame, text="Run Pipeline", command=self._run_pipeline,
            style="Accent.TButton"
        )
        self.run_pipeline_btn.pack(side=tk.LEFT, padx=5)
        
        self.create_video_btn = ttk.Button(
            exec_frame, text="Create Video from Output", command=self._create_video
        )
        self.create_video_btn.pack(side=tk.LEFT, padx=5)
        
        self.progress_var = tk.StringVar(value="Ready")
        ttk.Label(exec_frame, textvariable=self.progress_var).pack(side=tk.LEFT, padx=10)
    
    def _build_settings_tab(self, parent):
        """Build settings tab"""
        settings_text = scrolledtext.ScrolledText(parent, wrap=tk.WORD)
        settings_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Show current preset
        presets = self.config_manager.list_presets()
        settings_text.insert(1.0, "Available Presets:\n\n")
        for preset in presets:
            settings_text.insert(tk.END, f"- {preset}\n")
        
        settings_text.insert(tk.END, "\n\nDefault Configuration:\n\n")
        import json
        default_config = self.config_manager.get_default_config()
        settings_text.insert(tk.END, json.dumps(default_config, indent=2))
        
        settings_text.config(state=tk.DISABLED)
    
    def _build_log_tab(self, parent):
        """Build log tab"""
        self.log_text = scrolledtext.ScrolledText(parent, wrap=tk.WORD, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Add a handler to redirect logs to the text widget
        # This is a simple implementation - could be enhanced
        self._add_log_message("Log viewer initialized")
    
    def _add_log_message(self, message: str):
        """Add message to log viewer"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def _refresh_presets(self):
        """Refresh preset list"""
        presets = self.config_manager.list_presets()
        self.preset_combo['values'] = presets
        if presets and not self.preset_var.get():
            self.preset_var.set(presets[0])
    
    def _check_api(self):
        """Check API connection"""
        self.progress_var.set("Checking API...")
        self._add_log_message("Checking SD WebUI API connection...")
        
        def check():
            url = self.api_url_var.get()
            client = SDWebUIClient(base_url=url)
            if client.check_api_ready():
                self.client = client
                self.pipeline = Pipeline(self.client, self.structured_logger)
                self.root.after(0, lambda: self.api_status_label.config(
                    text="Connected", foreground="green"
                ))
                self.root.after(0, lambda: self._add_log_message("✓ API is ready"))
                self.root.after(0, lambda: self.progress_var.set("API connected"))
            else:
                self.root.after(0, lambda: self.api_status_label.config(
                    text="Failed", foreground="red"
                ))
                self.root.after(0, lambda: self._add_log_message("✗ API not available"))
                self.root.after(0, lambda: self.progress_var.set("API check failed"))
        
        threading.Thread(target=check, daemon=True).start()
    
    def _run_pipeline(self):
        """Run the full pipeline"""
        if not self.client or not self.pipeline:
            messagebox.showerror("Error", "Please check API connection first")
            return
        
        prompt = self.prompt_text.get(1.0, tk.END).strip()
        if not prompt:
            messagebox.showerror("Error", "Please enter a prompt")
            return
        
        preset_name = self.preset_var.get()
        if not preset_name:
            messagebox.showerror("Error", "Please select a preset")
            return
        
        config = self.config_manager.load_preset(preset_name)
        if not config:
            messagebox.showerror("Error", f"Failed to load preset: {preset_name}")
            return
        
        # Modify config based on options
        if not self.enable_img2img_var.get():
            config.pop("img2img", None)
        if not self.enable_upscale_var.get():
            config.pop("upscale", None)
        
        batch_size = self.batch_size_var.get()
        run_name = self.run_name_var.get() or None
        
        self.progress_var.set("Running pipeline...")
        self.run_pipeline_btn.config(state=tk.DISABLED)
        self._add_log_message(f"Starting pipeline with prompt: {prompt[:50]}...")
        
        def run():
            try:
                results = self.pipeline.run_full_pipeline(
                    prompt, config, run_name, batch_size
                )
                
                output_dir = results.get("run_dir", "Unknown")
                num_images = len(results.get("summary", []))
                
                self.root.after(0, lambda: self._add_log_message(
                    f"✓ Pipeline completed: {num_images} images generated"
                ))
                self.root.after(0, lambda: self._add_log_message(
                    f"Output directory: {output_dir}"
                ))
                self.root.after(0, lambda: self.progress_var.set(
                    f"Completed: {num_images} images"
                ))
                self.root.after(0, lambda: messagebox.showinfo(
                    "Success", 
                    f"Pipeline completed!\n{num_images} images generated\nOutput: {output_dir}"
                ))
            except Exception as e:
                self.root.after(0, lambda: self._add_log_message(f"✗ Error: {str(e)}"))
                self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
                self.root.after(0, lambda: self.progress_var.set("Error"))
            finally:
                self.root.after(0, lambda: self.run_pipeline_btn.config(state=tk.NORMAL))
        
        threading.Thread(target=run, daemon=True).start()
    
    def _create_video(self):
        """Create video from output images"""
        # Ask user to select output directory
        output_dir = filedialog.askdirectory(
            title="Select output directory containing images"
        )
        
        if not output_dir:
            return
        
        output_path = Path(output_dir)
        
        # Try to find upscaled images first, then img2img, then txt2img
        for subdir in ["upscaled", "img2img", "txt2img"]:
            image_dir = output_path / subdir
            if image_dir.exists():
                video_path = output_path / "video" / f"{subdir}_video.mp4"
                video_path.parent.mkdir(exist_ok=True)
                
                self._add_log_message(f"Creating video from {subdir}...")
                
                if self.video_creator.create_video_from_directory(
                    image_dir, video_path
                ):
                    self._add_log_message(f"✓ Video created: {video_path}")
                    messagebox.showinfo("Success", f"Video created:\n{video_path}")
                else:
                    self._add_log_message(f"✗ Failed to create video from {subdir}")
                
                return
        
        messagebox.showerror("Error", "No image directories found")
    
    def run(self):
        """Run the GUI application"""
        self.root.mainloop()
