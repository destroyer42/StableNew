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
from ..utils.webui_discovery import find_webui_api_port, launch_webui_safely, validate_webui_health
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
        
        # Initialize GUI variables early
        self.api_url_var = tk.StringVar(value="http://127.0.0.1:7860")
        
        # Initialize other GUI variables that are used before UI building
        self.txt2img_enabled = tk.BooleanVar(value=True)
        self.img2img_enabled = tk.BooleanVar(value=True)
        self.upscale_enabled = tk.BooleanVar(value=True)
        self.video_enabled = tk.BooleanVar(value=False)
        self.loop_type_var = tk.StringVar(value="single")
        self.loop_count_var = tk.StringVar(value="1")
        self.pack_mode_var = tk.StringVar(value="selected")
        self.images_per_prompt_var = tk.StringVar(value="1")
        self.saved_lists_var = tk.StringVar()
        
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
        """Auto-launch Stable Diffusion WebUI with improved detection"""
        webui_path = Path("C:/Users/rober/stable-diffusion-webui/webui-user.bat")
        
        # First check if WebUI is already running
        existing_url = find_webui_api_port()
        if existing_url:
            logger.info(f"WebUI already running at {existing_url}")
            self.api_url_var.set(existing_url)
            self.root.after(2000, self._check_api_connection)
            return
        
        # Try to launch WebUI
        if webui_path.exists():
            self.log_message("🚀 Launching Stable Diffusion WebUI...", "INFO")
            
            # Launch in separate thread to avoid blocking UI
            def launch_thread():
                success = launch_webui_safely(webui_path, wait_time=15)
                if success:
                    # Find the actual URL and update UI
                    api_url = find_webui_api_port()
                    if api_url:
                        self.root.after(0, lambda: self.api_url_var.set(api_url))
                        self.root.after(1000, self._check_api_connection)
                    else:
                        self.root.after(0, lambda: self.log_message("⚠️ WebUI launched but API not found", "WARNING"))
                else:
                    self.root.after(0, lambda: self.log_message("❌ WebUI launch failed", "ERROR"))
            
            threading.Thread(target=launch_thread, daemon=True).start()
        else:
            logger.warning("WebUI not found at expected location")
            self.log_message("⚠️ WebUI not found - please start manually", "WARNING")
            messagebox.showinfo("WebUI Not Found", 
                              f"WebUI not found at: {webui_path}\n\n"
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
        """Build interactive configuration tabs"""
        
        # Create nested notebook for stage-specific configurations
        config_notebook = ttk.Notebook(notebook, style='Dark.TNotebook')
        notebook.add(config_notebook, text="⚙️ Configuration")
        
        # Create individual tabs for each stage
        self._build_txt2img_config_tab(config_notebook)
        self._build_img2img_config_tab(config_notebook)
        self._build_upscale_config_tab(config_notebook)
        self._build_api_config_tab(config_notebook)
        
        # Add buttons for save/load/reset
        config_buttons = ttk.Frame(notebook, style='Dark.TFrame')
        config_buttons.pack(side=tk.BOTTOM, fill=tk.X, pady=10)
        
        ttk.Button(config_buttons, text="� Save All Changes", command=self._save_all_config,
                  style='Dark.TButton').pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(config_buttons, text="↺ Reset All", command=self._reset_all_config,
                  style='Dark.TButton').pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(config_buttons, text="📁 Load Preset", command=self._load_preset_config,
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
        """Check API connection status with improved diagnostics"""
        def check_in_thread():
            api_url = self.api_url_var.get()
            
            # Try the specified URL first
            self.log_message("🔍 Checking API connection...", "INFO")
            
            # First try direct connection
            client = SDWebUIClient(api_url)
            if client.check_api_ready():
                # Perform health check
                health = validate_webui_health(api_url)
                
                self.api_connected = True
                self.client = client
                self.pipeline = Pipeline(client, self.structured_logger)
                
                self.root.after(0, lambda: self._update_api_status(True, api_url))
                
                if health['models_loaded']:
                    self.log_message(f"✅ API connected! Found {health.get('model_count', 0)} models", "SUCCESS")
                else:
                    self.log_message("⚠️ API connected but no models loaded", "WARNING")
                return
            
            # If direct connection failed, try port discovery
            self.log_message("🔍 Trying port discovery...", "INFO")
            discovered_url = find_webui_api_port()
            
            if discovered_url:
                # Test the discovered URL
                client = SDWebUIClient(discovered_url)
                if client.check_api_ready():
                    health = validate_webui_health(discovered_url)
                    
                    self.api_connected = True
                    self.client = client
                    self.pipeline = Pipeline(client, self.structured_logger)
                    
                    # Update URL field and status
                    self.root.after(0, lambda: self.api_url_var.set(discovered_url))
                    self.root.after(0, lambda: self._update_api_status(True, discovered_url))
                    
                    if health['models_loaded']:
                        self.log_message(f"✅ API found at {discovered_url}! Found {health.get('model_count', 0)} models", "SUCCESS")
                    else:
                        self.log_message("⚠️ API found but no models loaded", "WARNING")
                    return
            
            # Connection failed
            self.api_connected = False
            self.root.after(0, lambda: self._update_api_status(False))
            self.log_message("❌ API connection failed. Please ensure WebUI is running with --api", "ERROR")
            self.log_message("💡 Tip: Check ports 7860-7864, restart WebUI if needed", "INFO")
        
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
            
        # Refresh configuration for selected pack
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
        
        # Select first pack if available
        if hasattr(self, 'packs_listbox') and self.packs_listbox.size() > 0:
            self.packs_listbox.selection_set(0)
            self.packs_listbox.activate(0)
            # Trigger selection change to update config
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
        """Refresh configuration from selected pack"""
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
        
        # Load config into forms if they exist
        if hasattr(self, 'txt2img_vars'):
            self._load_config_into_forms(self.current_config)

    
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
                    
                    # Get configuration - use current form values if available
                    if hasattr(self, 'txt2img_vars') and self.current_config:
                        config = self.current_config
                    else:
                        # Fall back to file-based config
                        pack_overrides = self.config_manager.get_pack_overrides(pack_file.stem)
                        config = self.config_manager.resolve_config(
                            preset_name="default",
                            pack_overrides=pack_overrides
                        )
                    
                    # Process each prompt in the pack
                    images_generated = 0
                    for i, prompt_data in enumerate(prompts):
                        try:
                            self.log_message(f"Processing prompt {i+1}/{len(prompts)}: {prompt_data['positive'][:50]}...", "INFO")
                            
                            # Run full pipeline for this prompt
                            result = self.pipeline.run_full_pipeline(
                                prompt=prompt_data['positive'],
                                config=config,
                                run_name=f"{pack_file.stem}_{int(time.time())}",
                                batch_size=int(self.images_per_prompt_var.get())
                            )
                            
                            if result and result.get('summary'):
                                images_generated += len(result['summary'])
                                self.log_message(f"✅ Generated {len(result['summary'])} images for prompt {i+1}", "SUCCESS")
                            else:
                                self.log_message(f"❌ Failed to generate images for prompt {i+1}", "ERROR")
                                
                        except Exception as e:
                            self.log_message(f"❌ Error processing prompt {i+1}: {str(e)}", "ERROR")
                            continue
                    
                    self.log_message(f"Completed pack {pack_file.name}: {images_generated} images", "SUCCESS")
                
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
        
        self.log_message("🎨 Running txt2img only...", "INFO")
        
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
                    self.log_message(f"Processing pack: {pack_name}", "INFO")
                    
                    # Load prompts from pack
                    pack_path = Path("packs") / pack_name
                    prompts = read_prompt_pack(pack_path)
                    
                    if not prompts:
                        self.log_message(f"No prompts found in {pack_name}", "WARNING")
                        continue
                    
                    # Get pack-specific overrides
                    pack_overrides = self.config_manager.get_pack_overrides(pack_path.stem)
                    pack_config = self.config_manager.resolve_config("default", pack_overrides)
                    
                    # Generate images for each prompt
                    for i, prompt_data in enumerate(prompts):
                        try:
                            self.log_message(f"Generating image {i+1}/{len(prompts)}: {prompt_data['positive'][:50]}...", "INFO")
                            
                            # Run txt2img using the pipeline
                            results = self.pipeline.run_txt2img(
                                prompt=prompt_data['positive'],
                                config=pack_config.get('txt2img', {}),
                                run_dir=run_dir,
                                batch_size=1
                            )
                            
                            if results:
                                self.log_message(f"✅ Generated {len(results)} images", "SUCCESS")
                            else:
                                self.log_message(f"❌ Failed to generate image {i+1}", "ERROR")
                                
                        except Exception as e:
                            self.log_message(f"❌ Error generating image {i+1}: {str(e)}", "ERROR")
                            continue
                
                self.log_message("🎉 Txt2img generation completed!", "SUCCESS")
                
            except Exception as e:
                self.log_message(f"❌ Txt2img generation failed: {str(e)}", "ERROR")
        
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
    
    def _build_txt2img_config_tab(self, notebook):
        """Build txt2img configuration form"""
        tab_frame = ttk.Frame(notebook, style='Dark.TFrame')
        notebook.add(tab_frame, text="🎨 txt2img")
        
        # Create scrollable frame
        canvas = tk.Canvas(tab_frame, bg='#2b2b2b')
        scrollbar = ttk.Scrollbar(tab_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, style='Dark.TFrame')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Initialize config variables
        self.txt2img_vars = {}
        
        # Steps
        steps_frame = ttk.LabelFrame(scrollable_frame, text="Generation Steps", style='Dark.TFrame', padding=10)
        steps_frame.pack(fill=tk.X, pady=5)
        ttk.Label(steps_frame, text="Steps:", style='Dark.TLabel').pack(side=tk.LEFT)
        self.txt2img_vars['steps'] = tk.IntVar(value=20)
        steps_spin = ttk.Spinbox(steps_frame, from_=1, to=150, width=10, textvariable=self.txt2img_vars['steps'])
        steps_spin.pack(side=tk.LEFT, padx=5)
        
        # Sampler
        sampler_frame = ttk.LabelFrame(scrollable_frame, text="Sampler", style='Dark.TFrame', padding=10)
        sampler_frame.pack(fill=tk.X, pady=5)
        ttk.Label(sampler_frame, text="Sampler:", style='Dark.TLabel').pack(side=tk.LEFT)
        self.txt2img_vars['sampler_name'] = tk.StringVar(value="Euler a")
        sampler_combo = ttk.Combobox(sampler_frame, textvariable=self.txt2img_vars['sampler_name'], 
                                   values=["Euler a", "Euler", "LMS", "Heun", "DPM2", "DPM2 a", "DPM++ 2S a", "DPM++ 2M", "DPM++ SDE", "DPM fast", "DPM adaptive", "LMS Karras", "DPM2 Karras", "DPM2 a Karras", "DPM++ 2S a Karras", "DPM++ 2M Karras", "DPM++ SDE Karras", "DDIM", "PLMS"])
        sampler_combo.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # CFG Scale
        cfg_frame = ttk.LabelFrame(scrollable_frame, text="CFG Scale", style='Dark.TFrame', padding=10)
        cfg_frame.pack(fill=tk.X, pady=5)
        ttk.Label(cfg_frame, text="CFG Scale:", style='Dark.TLabel').pack(side=tk.LEFT)
        self.txt2img_vars['cfg_scale'] = tk.DoubleVar(value=7.0)
        cfg_scale = ttk.Scale(cfg_frame, from_=1.0, to=20.0, variable=self.txt2img_vars['cfg_scale'], orient=tk.HORIZONTAL)
        cfg_scale.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        cfg_label = ttk.Label(cfg_frame, text="7.0", style='Dark.TLabel')
        cfg_label.pack(side=tk.LEFT, padx=5)
        cfg_scale.configure(command=lambda val: cfg_label.configure(text=f"{float(val):.1f}"))
        
        # Dimensions
        dims_frame = ttk.LabelFrame(scrollable_frame, text="Image Dimensions", style='Dark.TFrame', padding=10)
        dims_frame.pack(fill=tk.X, pady=5)
        ttk.Label(dims_frame, text="Width:", style='Dark.TLabel').grid(row=0, column=0, sticky=tk.W)
        self.txt2img_vars['width'] = tk.IntVar(value=512)
        width_combo = ttk.Combobox(dims_frame, textvariable=self.txt2img_vars['width'], 
                                 values=[256, 320, 384, 448, 512, 576, 640, 704, 768, 832, 896, 960, 1024], width=10)
        width_combo.grid(row=0, column=1, padx=5, sticky=tk.W)
        
        ttk.Label(dims_frame, text="Height:", style='Dark.TLabel').grid(row=0, column=2, padx=(20,5), sticky=tk.W)
        self.txt2img_vars['height'] = tk.IntVar(value=512)
        height_combo = ttk.Combobox(dims_frame, textvariable=self.txt2img_vars['height'],
                                  values=[256, 320, 384, 448, 512, 576, 640, 704, 768, 832, 896, 960, 1024], width=10)
        height_combo.grid(row=0, column=3, padx=5, sticky=tk.W)
        
        # Negative Prompt
        neg_frame = ttk.LabelFrame(scrollable_frame, text="Negative Prompt", style='Dark.TFrame', padding=10)
        neg_frame.pack(fill=tk.X, pady=5)
        self.txt2img_vars['negative_prompt'] = tk.StringVar(value="blurry, bad quality, distorted, ugly, malformed")
        neg_text = tk.Text(neg_frame, height=3, bg='#3d3d3d', fg='#ffffff', wrap=tk.WORD)
        neg_text.pack(fill=tk.X, pady=5)
        neg_text.insert(1.0, self.txt2img_vars['negative_prompt'].get())
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def _build_img2img_config_tab(self, notebook):
        """Build img2img configuration form"""
        tab_frame = ttk.Frame(notebook, style='Dark.TFrame')
        notebook.add(tab_frame, text="🧹 img2img")
        
        # Create scrollable frame
        canvas = tk.Canvas(tab_frame, bg='#2b2b2b')
        scrollable_frame = ttk.Frame(canvas, style='Dark.TFrame')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        # Initialize config variables
        self.img2img_vars = {}
        
        # Steps
        steps_frame = ttk.LabelFrame(scrollable_frame, text="Cleanup Steps", style='Dark.TFrame', padding=10)
        steps_frame.pack(fill=tk.X, pady=5)
        ttk.Label(steps_frame, text="Steps:", style='Dark.TLabel').pack(side=tk.LEFT)
        self.img2img_vars['steps'] = tk.IntVar(value=15)
        steps_spin = ttk.Spinbox(steps_frame, from_=1, to=150, width=10, textvariable=self.img2img_vars['steps'])
        steps_spin.pack(side=tk.LEFT, padx=5)
        
        # Denoising Strength
        denoise_frame = ttk.LabelFrame(scrollable_frame, text="Denoising Strength", style='Dark.TFrame', padding=10)
        denoise_frame.pack(fill=tk.X, pady=5)
        ttk.Label(denoise_frame, text="Denoising:", style='Dark.TLabel').pack(side=tk.LEFT)
        self.img2img_vars['denoising_strength'] = tk.DoubleVar(value=0.3)
        denoise_scale = ttk.Scale(denoise_frame, from_=0.0, to=1.0, variable=self.img2img_vars['denoising_strength'], orient=tk.HORIZONTAL)
        denoise_scale.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        denoise_label = ttk.Label(denoise_frame, text="0.3", style='Dark.TLabel')
        denoise_label.pack(side=tk.LEFT, padx=5)
        denoise_scale.configure(command=lambda val: denoise_label.configure(text=f"{float(val):.2f}"))
        
        canvas.pack(fill="both", expand=True)
    
    def _build_upscale_config_tab(self, notebook):
        """Build upscale configuration form"""
        tab_frame = ttk.Frame(notebook, style='Dark.TFrame')
        notebook.add(tab_frame, text="📈 Upscale")
        
        # Create scrollable frame
        canvas = tk.Canvas(tab_frame, bg='#2b2b2b')
        scrollable_frame = ttk.Frame(canvas, style='Dark.TFrame')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        # Initialize config variables
        self.upscale_vars = {}
        
        # Upscaler selection
        upscaler_frame = ttk.LabelFrame(scrollable_frame, text="Upscaler Model", style='Dark.TFrame', padding=10)
        upscaler_frame.pack(fill=tk.X, pady=5)
        ttk.Label(upscaler_frame, text="Upscaler:", style='Dark.TLabel').pack(side=tk.LEFT)
        self.upscale_vars['upscaler'] = tk.StringVar(value="R-ESRGAN 4x+")
        upscaler_combo = ttk.Combobox(upscaler_frame, textvariable=self.upscale_vars['upscaler'],
                                    values=["R-ESRGAN 4x+", "R-ESRGAN 4x+ Anime6B", "ESRGAN_4x", "LDSR", "ScuNET GAN", "ScuNET PSNR", "SwinIR 4x"])
        upscaler_combo.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Scale factor
        scale_frame = ttk.LabelFrame(scrollable_frame, text="Scale Factor", style='Dark.TFrame', padding=10)
        scale_frame.pack(fill=tk.X, pady=5)
        ttk.Label(scale_frame, text="Scale:", style='Dark.TLabel').pack(side=tk.LEFT)
        self.upscale_vars['upscaling_resize'] = tk.DoubleVar(value=2.0)
        scale_combo = ttk.Combobox(scale_frame, textvariable=self.upscale_vars['upscaling_resize'],
                                 values=[1.5, 2.0, 3.0, 4.0], width=10)
        scale_combo.pack(side=tk.LEFT, padx=5)
        
        canvas.pack(fill="both", expand=True)
    
    def _build_api_config_tab(self, notebook):
        """Build API configuration form"""
        tab_frame = ttk.Frame(notebook, style='Dark.TFrame')
        notebook.add(tab_frame, text="🔌 API")
        
        # API settings
        api_frame = ttk.LabelFrame(tab_frame, text="API Connection", style='Dark.TFrame', padding=10)
        api_frame.pack(fill=tk.X, pady=5)
        
        # Base URL
        url_frame = ttk.Frame(api_frame, style='Dark.TFrame')
        url_frame.pack(fill=tk.X, pady=5)
        ttk.Label(url_frame, text="Base URL:", style='Dark.TLabel').pack(side=tk.LEFT)
        self.api_vars = {}
        self.api_vars['base_url'] = self.api_url_var  # Use the same variable
        url_entry = ttk.Entry(url_frame, textvariable=self.api_vars['base_url'], width=30)
        url_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Timeout
        timeout_frame = ttk.Frame(api_frame, style='Dark.TFrame')
        timeout_frame.pack(fill=tk.X, pady=5)
        ttk.Label(timeout_frame, text="Timeout (s):", style='Dark.TLabel').pack(side=tk.LEFT)
        self.api_vars['timeout'] = tk.IntVar(value=300)
        timeout_spin = ttk.Spinbox(timeout_frame, from_=30, to=3600, width=10, textvariable=self.api_vars['timeout'])
        timeout_spin.pack(side=tk.LEFT, padx=5)
    
    def _save_all_config(self):
        """Save all configuration changes"""
        try:
            # Build config from form values
            config = {
                "txt2img": {
                    "steps": self.txt2img_vars['steps'].get(),
                    "sampler_name": self.txt2img_vars['sampler_name'].get(),
                    "cfg_scale": self.txt2img_vars['cfg_scale'].get(),
                    "width": self.txt2img_vars['width'].get(),
                    "height": self.txt2img_vars['height'].get(),
                    "negative_prompt": self.txt2img_vars['negative_prompt'].get()
                },
                "img2img": {
                    "steps": self.img2img_vars['steps'].get(),
                    "denoising_strength": self.img2img_vars['denoising_strength'].get(),
                },
                "upscale": {
                    "upscaler": self.upscale_vars['upscaler'].get(),
                    "upscaling_resize": self.upscale_vars['upscaling_resize'].get()
                },
                "api": {
                    "base_url": self.api_vars['base_url'].get(),
                    "timeout": self.api_vars['timeout'].get()
                }
            }
            
            # Save as current config
            self.current_config = config
            
            # Optionally save as preset
            preset_name = tk.simpledialog.askstring("Save Preset", "Enter preset name (optional):")
            if preset_name:
                self.config_manager.save_preset(preset_name, config)
                self.log_message(f"Saved configuration as preset: {preset_name}", "SUCCESS")
            else:
                self.log_message("Configuration updated (not saved as preset)", "INFO")
                
        except Exception as e:
            self.log_message(f"Failed to save configuration: {e}", "ERROR")
    
    def _reset_all_config(self):
        """Reset all configuration to defaults"""
        defaults = self.config_manager.get_default_config()
        self._load_config_into_forms(defaults)
        self.log_message("Configuration reset to defaults", "INFO")
    
    def _load_preset_config(self):
        """Load configuration from preset"""
        presets = self.config_manager.list_presets()
        if not presets:
            messagebox.showinfo("No Presets", "No configuration presets found")
            return
            
        preset_name = tk.simpledialog.askstring("Load Preset", f"Available presets: {', '.join(presets)}\nEnter preset name:")
        if preset_name and preset_name in presets:
            config = self.config_manager.load_preset(preset_name)
            if config:
                self._load_config_into_forms(config)
                self.current_config = config
                self.log_message(f"Loaded preset: {preset_name}", "SUCCESS")
            else:
                self.log_message(f"Failed to load preset: {preset_name}", "ERROR")
    
    def _load_config_into_forms(self, config):
        """Load configuration values into form widgets"""
        try:
            # txt2img config
            txt2img_config = config.get("txt2img", {})
            if hasattr(self, 'txt2img_vars'):
                self.txt2img_vars['steps'].set(txt2img_config.get('steps', 20))
                self.txt2img_vars['sampler_name'].set(txt2img_config.get('sampler_name', 'Euler a'))
                self.txt2img_vars['cfg_scale'].set(txt2img_config.get('cfg_scale', 7.0))
                self.txt2img_vars['width'].set(txt2img_config.get('width', 512))
                self.txt2img_vars['height'].set(txt2img_config.get('height', 512))
                self.txt2img_vars['negative_prompt'].set(txt2img_config.get('negative_prompt', ''))
            
            # img2img config
            img2img_config = config.get("img2img", {})
            if hasattr(self, 'img2img_vars'):
                self.img2img_vars['steps'].set(img2img_config.get('steps', 15))
                self.img2img_vars['denoising_strength'].set(img2img_config.get('denoising_strength', 0.3))
            
            # upscale config
            upscale_config = config.get("upscale", {})
            if hasattr(self, 'upscale_vars'):
                self.upscale_vars['upscaler'].set(upscale_config.get('upscaler', 'R-ESRGAN 4x+'))
                self.upscale_vars['upscaling_resize'].set(upscale_config.get('upscaling_resize', 2.0))
            
            # api config
            api_config = config.get("api", {})
            if hasattr(self, 'api_vars'):
                self.api_vars['base_url'].set(api_config.get('base_url', 'http://127.0.0.1:7860'))
                self.api_vars['timeout'].set(api_config.get('timeout', 300))
                
        except Exception as e:
            self.log_message(f"Error loading config into forms: {e}", "ERROR")
    
    def _build_pipeline_tab(self, parent):
        """Build pipeline execution tab"""
        # API Connection Frame
        api_frame = ttk.LabelFrame(parent, text="API Connection", padding=10)
        api_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(api_frame, text="API URL:").grid(row=0, column=0, sticky=tk.W, padx=5)
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
