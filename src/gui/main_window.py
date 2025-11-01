"""Tkinter GUI for Stable Diffusion pipeline"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import threading

from ..api import SDWebUIClient
from ..pipeline import Pipeline, VideoCreator
from ..utils import ConfigManager, StructuredLogger, setup_logging

logger = logging.getLogger(__name__)


class StableNewGUI:
    """Main GUI application"""
    
    def __init__(self):
        """Initialize GUI"""
        self.root = tk.Tk()
        self.root.title("StableNew - SD WebUI Automation")
        self.root.geometry("900x700")
        
        # Initialize components
        self.config_manager = ConfigManager()
        self.structured_logger = StructuredLogger()
        self.client = None
        self.pipeline = None
        self.video_creator = VideoCreator()
        
        # Load or create default preset
        self._ensure_default_preset()
        
        # Build UI
        self._build_ui()
        
        # Setup logging redirect
        setup_logging("INFO")
        
    def _ensure_default_preset(self):
        """Ensure default preset exists"""
        if "default" not in self.config_manager.list_presets():
            default_config = self.config_manager.get_default_config()
            self.config_manager.save_preset("default", default_config)
    
    def _build_ui(self):
        """Build the user interface"""
        # Create notebook (tabs)
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Pipeline tab
        pipeline_frame = ttk.Frame(notebook)
        notebook.add(pipeline_frame, text="Pipeline")
        self._build_pipeline_tab(pipeline_frame)
        
        # Settings tab
        settings_frame = ttk.Frame(notebook)
        notebook.add(settings_frame, text="Settings")
        self._build_settings_tab(settings_frame)
        
        # Log tab
        log_frame = ttk.Frame(notebook)
        notebook.add(log_frame, text="Logs")
        self._build_log_tab(log_frame)
    
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
