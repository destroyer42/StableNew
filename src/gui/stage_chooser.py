"""Stage chooser modal for per-image pipeline stage selection."""

import logging
import queue
import tkinter as tk
from collections.abc import Callable
from enum import Enum
from pathlib import Path
from tkinter import ttk

from PIL import Image, ImageTk

logger = logging.getLogger(__name__)


class StageChoice(Enum):
    """Available stage choices for processing."""

    IMG2IMG = "img2img"
    ADETAILER = "adetailer"
    UPSCALE = "upscale"
    NONE = "none"


class StageChooser:
    """Non-blocking modal for choosing next pipeline stage per image.

    This modal displays after txt2img generation and allows the user to choose
    which processing stages to apply to each image. Communication happens via
    a Queue to avoid blocking the main Tk event loop.
    """

    def __init__(
        self,
        # Prefer the more typical tkinter "parent" naming used by tests,
        # but keep backward compatibility with code that passed "root".
        parent: tk.Misc | None = None,
        image_path: Path | None = None,
        image_index: int = 1,
        total_images: int = 1,
        result_queue: queue.Queue | None = None,
        on_retune: Callable | None = None,
        # Back-compat: allow callers to still pass root, but tests use parent
        root: tk.Misc | None = None,
    ):
        """Initialize stage chooser modal.

        Args:
            parent: Parent Tk widget/window (preferred)
            image_path: Path to the generated image to preview
            image_index: Current image number (1-based)
            total_images: Total number of images in batch
            result_queue: Queue to send choice results to
            on_retune: Optional callback for re-tuning settings
        """
        # Resolve parent/root with backwards compatibility
        self.root = parent or root  # type: ignore[assignment]
        if self.root is None:
            # Create a default root if none provided (useful for ad-hoc calls/tests)
            self.root = tk.Tk()

        # Store core parameters (with sensible defaults for tests)
        self.image_path = image_path or Path("")
        self.image_index = image_index
        self.total_images = total_images
        self.result_queue = result_queue or queue.Queue()
        self.on_retune_callback = on_retune

        self.selected_choice: StageChoice | None = None
        self.apply_to_batch: bool = False

        # Create modal window
        self.window = tk.Toplevel(self.root)
        self.window.title(f"Choose Next Stage - Image {image_index} of {total_images}")
        self.window.geometry("700x600")
        self.window.configure(bg='#2b2b2b')

        # Make modal
        self.window.transient(root)
        self.window.grab_set()

        # Batch toggle variable
        self.batch_var = tk.BooleanVar(value=False)

        # Build UI
        self._build_ui()

        # Load and display preview
        self._load_preview()

        # Center window
        self._center_window()

        # Handle window close
        self.window.protocol("WM_DELETE_WINDOW", self._on_cancel)

    def _build_ui(self):
        """Build the chooser UI."""
        main_frame = ttk.Frame(self.window, style='Dark.TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Apply dark theme
        self._apply_dark_theme()

        # Header
        self._build_header(main_frame)

        # Preview area
        self._build_preview(main_frame)

        # Choice buttons
        self._build_choices(main_frame)

        # Batch toggle
        self._build_batch_toggle(main_frame)

        # Action buttons
        self._build_actions(main_frame)

    def _apply_dark_theme(self):
        """Apply dark theme to widgets."""
        style = ttk.Style()
        style.theme_use('clam')

        style.configure('Dark.TFrame', background='#2b2b2b')
        style.configure('Dark.TLabel', background='#2b2b2b', foreground='white')
        style.configure('Dark.TButton', background='#404040', foreground='white')
        style.configure('Dark.TCheckbutton', background='#2b2b2b', foreground='white')

    def _build_header(self, parent):
        """Build header with title and info."""
        header_frame = ttk.Frame(parent, style='Dark.TFrame')
        header_frame.pack(fill=tk.X, pady=(0, 15))

        title = ttk.Label(
            header_frame,
            text="Choose Next Processing Stage",
            style='Dark.TLabel',
            font=('Segoe UI', 14, 'bold')
        )
        title.pack(anchor=tk.W)

        info = ttk.Label(
            header_frame,
            text=f"Select how to process this image (Image {self.image_index} of {self.total_images})",
            style='Dark.TLabel',
            font=('Segoe UI', 10)
        )
        info.pack(anchor=tk.W, pady=(5, 0))

    def _build_preview(self, parent):
        """Build image preview area."""
        preview_frame = ttk.Frame(parent, style='Dark.TFrame')
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        # Preview label
        self.preview_label = ttk.Label(
            preview_frame,
            text="Loading preview...",
            style='Dark.TLabel',
            anchor=tk.CENTER
        )
        self.preview_label.pack(fill=tk.BOTH, expand=True)

    def _build_choices(self, parent):
        """Build stage choice buttons."""
        choices_frame = ttk.LabelFrame(
            parent,
            text="Processing Options",
            style='Dark.TFrame'
        )
        choices_frame.pack(fill=tk.X, pady=(0, 15))

        # Grid layout for buttons
        btn_frame = ttk.Frame(choices_frame, style='Dark.TFrame')
        btn_frame.pack(padx=10, pady=10)

        # img2img button
        img2img_btn = tk.Button(
            btn_frame,
            text="🎨 img2img\n(Cleanup/Refine)",
            bg='#0078d4',
            fg='white',
            font=('Segoe UI', 11, 'bold'),
            width=18,
            height=3,
            command=lambda: self._select_choice(StageChoice.IMG2IMG)
        )
        img2img_btn.grid(row=0, column=0, padx=5, pady=5)

        # ADetailer button
        adetailer_btn = tk.Button(
            btn_frame,
            text="✨ ADetailer\n(Face/Detail Fix)",
            bg='#7c4dff',
            fg='white',
            font=('Segoe UI', 11, 'bold'),
            width=18,
            height=3,
            command=lambda: self._select_choice(StageChoice.ADETAILER)
        )
        adetailer_btn.grid(row=0, column=1, padx=5, pady=5)

        # Upscale button
        upscale_btn = tk.Button(
            btn_frame,
            text="🔍 Upscale\n(Enhance Quality)",
            bg='#00897b',
            fg='white',
            font=('Segoe UI', 11, 'bold'),
            width=18,
            height=3,
            command=lambda: self._select_choice(StageChoice.UPSCALE)
        )
        upscale_btn.grid(row=1, column=0, padx=5, pady=5)

        # None button
        none_btn = tk.Button(
            btn_frame,
            text="⏭️ None\n(Skip to Next)",
            bg='#5d4037',
            fg='white',
            font=('Segoe UI', 11, 'bold'),
            width=18,
            height=3,
            command=lambda: self._select_choice(StageChoice.NONE)
        )
        none_btn.grid(row=1, column=1, padx=5, pady=5)

    def _build_batch_toggle(self, parent):
        """Build batch application toggle."""
        batch_frame = ttk.Frame(parent, style='Dark.TFrame')
        batch_frame.pack(fill=tk.X, pady=(0, 15))

        batch_check = ttk.Checkbutton(
            batch_frame,
            text="Apply this choice to all remaining images in this batch",
            variable=self.batch_var,
            style='Dark.TCheckbutton'
        )
        batch_check.pack(anchor=tk.W)

        # Show only if there are more images
        if self.image_index >= self.total_images:
            batch_check.configure(state='disabled')

    def _build_actions(self, parent):
        """Build action buttons."""
        action_frame = ttk.Frame(parent, style='Dark.TFrame')
        action_frame.pack(fill=tk.X)

        # Re-tune settings link (if callback provided)
        if self.on_retune_callback:
            retune_btn = tk.Button(
                action_frame,
                text="⚙️ Re-tune Settings",
                bg='#2b2b2b',
                fg='#42a5f5',
                font=('Segoe UI', 10, 'underline'),
                relief=tk.FLAT,
                cursor='hand2',
                command=self._on_retune
            )
            retune_btn.pack(side=tk.LEFT)

        # Cancel button
        cancel_btn = tk.Button(
            action_frame,
            text="Cancel Remaining",
            bg='#d32f2f',
            fg='white',
            font=('Segoe UI', 10),
            command=self._on_cancel
        )
        cancel_btn.pack(side=tk.RIGHT, padx=(10, 0))

    def _load_preview(self):
        """Load and display image preview."""
        try:
            if not self.image_path.exists():
                self.preview_label.config(text="Image not found")
                return

            # Load image
            img = Image.open(self.image_path)

            # Calculate scaling to fit in preview area (max 400x400)
            max_size = 400
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(img)

            # Update label
            self.preview_label.config(image=photo, text="")
            self.preview_label.image = photo  # Keep reference

        except Exception as e:
            logger.error(f"Error loading preview image: {e}")
            self.preview_label.config(text="Error loading preview")

    def _center_window(self):
        """Center window on screen."""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f'{width}x{height}+{x}+{y}')

    def _select_choice(self, choice: StageChoice):
        """Handle stage choice selection.

        Args:
            choice: Selected stage choice
        """
        self.selected_choice = choice
        self.apply_to_batch = self.batch_var.get()

        # Send result to queue
        result = {
            "choice": choice,
            "apply_to_batch": self.apply_to_batch,
            "cancelled": False,
            "image_index": self.image_index
        }
        self.result_queue.put(result)

        logger.info(
            f"Stage choice: {choice.value} "
            f"(batch={self.apply_to_batch}, image={self.image_index})"
        )

        # Close window
        self._close()

    def _on_cancel(self):
        """Handle cancel action."""
        result = {
            "choice": None,
            "apply_to_batch": False,
            "cancelled": True,
            "image_index": self.image_index
        }
        self.result_queue.put(result)

        logger.info("Stage chooser cancelled")
        self._close()

    def _on_retune(self):
        """Handle re-tune settings action."""
        if self.on_retune_callback:
            self.on_retune_callback()

        # Don't close window - let user adjust and come back

    def _close(self):
        """Close the modal window."""
        try:
            self.window.grab_release()
            self.window.destroy()
        except Exception as e:
            logger.error(f"Error closing stage chooser window: {e}")
