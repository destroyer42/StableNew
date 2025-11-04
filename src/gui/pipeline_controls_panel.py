"""
Pipeline Controls Panel - UI component for configuring pipeline execution.
"""
import tkinter as tk
from tkinter import ttk
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class PipelineControlsPanel(ttk.Frame):
    def get_settings(self) -> Dict[str, Any]:
        """
        Return current toggles and loop/batch settings as a dictionary.
        """
        return {
            'txt2img_enabled': bool(self.txt2img_enabled.get()),
            'img2img_enabled': bool(self.img2img_enabled.get()),
            'upscale_enabled': bool(self.upscale_enabled.get()),
            'video_enabled': bool(self.video_enabled.get()),
            'loop_type': self.loop_type_var.get(),
            'loop_count': int(self.loop_count_var.get()),
            'pack_mode': self.pack_mode_var.get(),
            'images_per_prompt': int(self.images_per_prompt_var.get()),
        }
    def get_state(self) -> dict:
        """
        Return the current state of the panel as a dictionary.
        Includes stage toggles, loop config, and batch config.
        """
        return {
            'txt2img_enabled': bool(self.txt2img_enabled.get()),
            'img2img_enabled': bool(self.img2img_enabled.get()),
            'upscale_enabled': bool(self.upscale_enabled.get()),
            'video_enabled': bool(self.video_enabled.get()),
            'loop_type': self.loop_type_var.get(),
            'loop_count': int(self.loop_count_var.get()),
            'pack_mode': self.pack_mode_var.get(),
            'images_per_prompt': int(self.images_per_prompt_var.get()),
        }

    def set_state(self, state: dict) -> None:
        """
        Restore the panel state from a dictionary.
        Ignores missing keys and type errors.
        """
        try:
            if 'txt2img_enabled' in state:
                self.txt2img_enabled.set(bool(state['txt2img_enabled']))
            if 'img2img_enabled' in state:
                self.img2img_enabled.set(bool(state['img2img_enabled']))
            if 'upscale_enabled' in state:
                self.upscale_enabled.set(bool(state['upscale_enabled']))
            if 'video_enabled' in state:
                self.video_enabled.set(bool(state['video_enabled']))
            if 'loop_type' in state:
                self.loop_type_var.set(str(state['loop_type']))
            if 'loop_count' in state:
                self.loop_count_var.set(int(state['loop_count']))
            if 'pack_mode' in state:
                self.pack_mode_var.set(str(state['pack_mode']))
            if 'images_per_prompt' in state:
                self.images_per_prompt_var.set(int(state['images_per_prompt']))
        except Exception as e:
            logger.warning(f"PipelineControlsPanel: Failed to restore state: {e}")
    """
    A UI panel for pipeline execution controls.
    
    This panel handles:
    - Stage enable/disable toggles (txt2img, img2img, upscale, video)
    - Loop configuration (single/stages/pipeline)
    - Loop count settings
    - Batch configuration (pack mode selection)
    - Images per prompt setting
    
    It exposes a get_settings() method to retrieve current configuration.
    """
    
    def __init__(self, parent: tk.Widget, **kwargs):
        """
        Initialize the PipelineControlsPanel.
        
        Args:
            parent: Parent widget
            **kwargs: Additional frame options
        """
        super().__init__(parent, **kwargs)
        self.parent = parent
        
        # Initialize control variables
        self._init_variables()
        
        # Build UI
        self._build_ui()
        
    def _init_variables(self):
        """Initialize all control variables with defaults."""
        # Stage toggles
        self.txt2img_enabled = tk.BooleanVar(value=True)
        self.img2img_enabled = tk.BooleanVar(value=True)
        self.upscale_enabled = tk.BooleanVar(value=True)
        self.video_enabled = tk.BooleanVar(value=False)
        
        # Loop configuration
        self.loop_type_var = tk.StringVar(value="single")
        self.loop_count_var = tk.StringVar(value="1")
        
        # Batch configuration
        self.pack_mode_var = tk.StringVar(value="selected")
        self.images_per_prompt_var = tk.StringVar(value="1")
        
    def _build_ui(self):
        """Build the panel UI."""
        # Pipeline controls frame
        pipeline_frame = ttk.LabelFrame(
            self, text="🚀 Pipeline Controls", style='Dark.TFrame', padding=5
        )
        pipeline_frame.pack(fill=tk.BOTH, expand=True)
        
        # Stage selection - compact
        self._build_stage_toggles(pipeline_frame)
        
        # Loop configuration - compact
        self._build_loop_config(pipeline_frame)
        
        # Batch configuration - compact
        self._build_batch_config(pipeline_frame)
        
    def _build_stage_toggles(self, parent):
        """Build stage enable/disable toggles with logging."""
        stages_frame = ttk.LabelFrame(
            parent, text="Stages", style='Dark.TFrame', padding=5
        )
        stages_frame.pack(fill=tk.X, pady=(0, 5))
        
        def log_toggle(name, var):
            logger.info(f"PipelineControlsPanel: {name} set to {var.get()}")
        
        ttk.Checkbutton(
            stages_frame,
            text="🎨 txt2img",
            variable=self.txt2img_enabled,
            style='Dark.TCheckbutton',
            command=lambda: log_toggle('txt2img_enabled', self.txt2img_enabled)
        ).pack(anchor=tk.W, pady=1)
        
        ttk.Checkbutton(
            stages_frame,
            text="🧹 img2img",
            variable=self.img2img_enabled,
            style='Dark.TCheckbutton',
            command=lambda: log_toggle('img2img_enabled', self.img2img_enabled)
        ).pack(anchor=tk.W, pady=1)
        
        ttk.Checkbutton(
            stages_frame,
            text="📈 Upscale",
            variable=self.upscale_enabled,
            style='Dark.TCheckbutton',
            command=lambda: log_toggle('upscale_enabled', self.upscale_enabled)
        ).pack(anchor=tk.W, pady=1)
        
        ttk.Checkbutton(
            stages_frame,
            text="🎬 Video",
            variable=self.video_enabled,
            style='Dark.TCheckbutton',
            command=lambda: log_toggle('video_enabled', self.video_enabled)
        ).pack(anchor=tk.W, pady=1)
        
    def _build_loop_config(self, parent):
        """Build loop configuration controls with logging."""
        loop_frame = ttk.LabelFrame(
            parent, text="Loop Config", style='Dark.TFrame', padding=5
        )
        loop_frame.pack(fill=tk.X, pady=(0, 5))
        
        def log_loop_type():
            logger.info(f"PipelineControlsPanel: loop_type set to {self.loop_type_var.get()}")
        
        ttk.Radiobutton(
            loop_frame,
            text="Single",
            variable=self.loop_type_var,
            value="single",
            style='Dark.TRadiobutton',
            command=log_loop_type
        ).pack(anchor=tk.W, pady=1)
        
        ttk.Radiobutton(
            loop_frame,
            text="Loop stages",
            variable=self.loop_type_var,
            value="stages",
            style='Dark.TRadiobutton',
            command=log_loop_type
        ).pack(anchor=tk.W, pady=1)
        
        ttk.Radiobutton(
            loop_frame,
            text="Loop pipeline",
            variable=self.loop_type_var,
            value="pipeline",
            style='Dark.TRadiobutton',
            command=log_loop_type
        ).pack(anchor=tk.W, pady=1)
        
        # Loop count - inline
        count_frame = ttk.Frame(loop_frame, style='Dark.TFrame')
        count_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(
            count_frame, text="Count:", style='Dark.TLabel', width=6
        ).pack(side=tk.LEFT)
        
        def log_loop_count(*_):
            logger.info(f"PipelineControlsPanel: loop_count set to {self.loop_count_var.get()}")
        self.loop_count_var.trace_add('write', log_loop_count)
        count_spin = ttk.Spinbox(
            count_frame,
            from_=1,
            to=100,
            width=4,
            textvariable=self.loop_count_var,
            style='Dark.TSpinbox'
        )
        count_spin.pack(side=tk.LEFT, padx=2)
        
    def _build_batch_config(self, parent):
        """Build batch configuration controls with logging."""
        batch_frame = ttk.LabelFrame(
            parent, text="Batch Config", style='Dark.TFrame', padding=5
        )
        batch_frame.pack(fill=tk.X, pady=(0, 5))
        
        def log_pack_mode():
            logger.info(f"PipelineControlsPanel: pack_mode set to {self.pack_mode_var.get()}")
        
        ttk.Radiobutton(
            batch_frame,
            text="Selected packs",
            variable=self.pack_mode_var,
            value="selected",
            style='Dark.TRadiobutton',
            command=log_pack_mode
        ).pack(anchor=tk.W, pady=1)
        
        ttk.Radiobutton(
            batch_frame,
            text="All packs",
            variable=self.pack_mode_var,
            value="all",
            style='Dark.TRadiobutton',
            command=log_pack_mode
        ).pack(anchor=tk.W, pady=1)
        
        ttk.Radiobutton(
            batch_frame,
            text="Custom list",
            variable=self.pack_mode_var,
            value="custom",
            style='Dark.TRadiobutton',
            command=log_pack_mode
        ).pack(anchor=tk.W, pady=1)
        
        # Images per prompt - inline
        images_frame = ttk.Frame(batch_frame, style='Dark.TFrame')
        images_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(
            images_frame, text="Images:", style='Dark.TLabel', width=6
        ).pack(side=tk.LEFT)
        
        def log_images_per_prompt(*_):
            logger.info(f"PipelineControlsPanel: images_per_prompt set to {self.images_per_prompt_var.get()}")
        self.images_per_prompt_var.trace_add('write', log_images_per_prompt)
        images_spin = ttk.Spinbox(
            images_frame,
            from_=1,
            to=10,
            width=4,
            textvariable=self.images_per_prompt_var,
            style='Dark.TSpinbox'
        )
        images_spin.pack(side=tk.LEFT, padx=2)
        
    def get_settings(self) -> Dict[str, Any]:
        """
        Get current pipeline control settings.
        
        Returns:
            Dictionary containing all pipeline control settings
        """
        try:
            loop_count = int(self.loop_count_var.get())
        except ValueError:
            loop_count = 1
            
        try:
            images_per_prompt = int(self.images_per_prompt_var.get())
        except ValueError:
            images_per_prompt = 1
            
        return {
            # Stage toggles
            'txt2img_enabled': self.txt2img_enabled.get(),
            'img2img_enabled': self.img2img_enabled.get(),
            'upscale_enabled': self.upscale_enabled.get(),
            'video_enabled': self.video_enabled.get(),
            
            # Loop configuration
            'loop_type': self.loop_type_var.get(),
            'loop_count': loop_count,
            
            # Batch configuration
            'pack_mode': self.pack_mode_var.get(),
            'images_per_prompt': images_per_prompt,
        }
        
    def set_settings(self, settings: Dict[str, Any]):
        """
        Set pipeline control settings from a dictionary.
        
        Args:
            settings: Dictionary containing pipeline settings
        """
        if 'txt2img_enabled' in settings:
            self.txt2img_enabled.set(settings['txt2img_enabled'])
        if 'img2img_enabled' in settings:
            self.img2img_enabled.set(settings['img2img_enabled'])
        if 'upscale_enabled' in settings:
            self.upscale_enabled.set(settings['upscale_enabled'])
        if 'video_enabled' in settings:
            self.video_enabled.set(settings['video_enabled'])
            
        if 'loop_type' in settings:
            self.loop_type_var.set(settings['loop_type'])
        if 'loop_count' in settings:
            self.loop_count_var.set(str(settings['loop_count']))
            
        if 'pack_mode' in settings:
            self.pack_mode_var.set(settings['pack_mode'])
        if 'images_per_prompt' in settings:
            self.images_per_prompt_var.set(str(settings['images_per_prompt']))
