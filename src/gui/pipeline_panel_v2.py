"""Pipeline panel composed of modular stage cards."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from . import theme as theme_mod
from .pipeline_command_bar_v2 import PipelineCommandBarV2
from .advanced_prompt_editor import AdvancedPromptEditorV2
from src.gui.stage_cards_v2.advanced_txt2img_stage_card_v2 import AdvancedTxt2ImgStageCardV2
from src.gui.stage_cards_v2.advanced_img2img_stage_card_v2 import AdvancedImg2ImgStageCardV2
from src.gui.stage_cards_v2.advanced_upscale_stage_card_v2 import AdvancedUpscaleStageCardV2
from src.gui.stage_cards_v2.validation_result import ValidationResult


class PipelinePanelV2(ttk.Frame):
    """Container for pipeline stage cards."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        controller=None,
        theme=None,
        config_manager=None,
        **kwargs,
    ) -> None:
        style_name = getattr(theme, "SURFACE_FRAME_STYLE", theme_mod.SURFACE_FRAME_STYLE)
        super().__init__(master, style=style_name, padding=theme_mod.PADDING_MD, **kwargs)
        self.controller = controller
        self.theme = theme
        self.config_manager = config_manager

        header_style = getattr(theme, "STATUS_STRONG_LABEL_STYLE", theme_mod.STATUS_STRONG_LABEL_STYLE)
        ttk.Label(self, text="Pipeline", style=header_style).pack(anchor=tk.W, pady=(0, 4))

        self.command_bar = PipelineCommandBarV2(self, theme=theme)
        self.command_bar.pack(fill=tk.X, pady=(0, theme_mod.PADDING_SM))
        self.run_button = self.command_bar.run_button
        self.stop_button = self.command_bar.stop_button

        prompt_style = getattr(theme, "SURFACE_FRAME_STYLE", theme_mod.SURFACE_FRAME_STYLE)
        prompt_frame = ttk.Frame(self, style=prompt_style)
        prompt_frame.pack(fill=tk.X, pady=(0, theme_mod.PADDING_SM))

        ttk.Label(prompt_frame, text="Prompt", style=header_style).pack(anchor=tk.W, pady=(0, 2))
        self.prompt_text = tk.Text(prompt_frame, height=3, wrap="word")
        self.prompt_text.pack(fill=tk.X, expand=True, padx=2)

        prompt_controls = ttk.Frame(prompt_frame, style=prompt_style)
        prompt_controls.pack(fill=tk.X, pady=(4, 0))

        self.prompt_status_var = tk.StringVar(value=self._build_prompt_status())
        self.prompt_status_label = ttk.Label(prompt_controls, textvariable=self.prompt_status_var)
        self.prompt_status_label.pack(side=tk.RIGHT)

        self.open_editor_button = ttk.Button(
            prompt_controls, text="Open Advanced Editor", command=self._open_advanced_editor
        )
        self.open_editor_button.pack(side=tk.LEFT)

        self.prompt_text.bind("<<Modified>>", self._handle_prompt_modified)

        self._editor_window: tk.Toplevel | None = None
        self._editor: AdvancedPromptEditorV2 | None = None

        body_style = getattr(theme, "SURFACE_FRAME_STYLE", theme_mod.SURFACE_FRAME_STYLE)
        self.body = ttk.Frame(self, style=body_style)
        self.body.pack(fill=tk.BOTH, expand=True)

        self._txt2img_change_callback = None

        self.txt2img_card = AdvancedTxt2ImgStageCardV2(self.body, controller=controller, theme=theme)
        self.txt2img_card.pack(fill=tk.BOTH, expand=True, pady=(0, 6))
        try:
            self.txt2img_card.set_on_change(self._handle_txt2img_change)
        except Exception:
            pass
        self.img2img_card = AdvancedImg2ImgStageCardV2(self.body, controller=controller, theme=theme)
        self.img2img_card.pack(fill=tk.BOTH, expand=True, pady=(0, 6))

        self.upscale_card = AdvancedUpscaleStageCardV2(self.body, controller=controller, theme=theme)
        self.upscale_card.pack(fill=tk.BOTH, expand=True)

    def _build_prompt_status(self) -> str:
        return f"{len(self.get_prompt())} chars"

    def _handle_prompt_modified(self, event) -> None:
        widget = event.widget
        try:
            widget.edit_modified(False)
        except Exception:
            pass
        self.prompt_status_var.set(self._build_prompt_status())

    def get_prompt(self) -> str:
        return self.prompt_text.get("1.0", tk.END).strip()

    def set_prompt(self, prompt: str) -> None:
        self.prompt_text.delete("1.0", tk.END)
        if prompt:
            self.prompt_text.insert("1.0", prompt)
        self.prompt_status_var.set(self._build_prompt_status())

    def _open_advanced_editor(self) -> None:
        if self._editor_window and self._editor_window.winfo_exists():
            if self._editor is not None:
                self._editor.prompt_text.delete("1.0", tk.END)
                self._editor.prompt_text.insert("1.0", self.get_prompt())
            try:
                self._editor_window.lift()
            except Exception:
                pass
            return

        parent = self.winfo_toplevel()
        self._editor_window = tk.Toplevel(parent)
        self._editor_window.title("Advanced Prompt Editor")
        self._editor = AdvancedPromptEditorV2(
            self._editor_window,
            initial_prompt=self.get_prompt(),
            on_apply=self._apply_prompt_from_editor,
            on_cancel=self._close_advanced_editor,
        )
        self._editor.pack(fill=tk.BOTH, expand=True)
        try:
            self._editor_window.transient(parent)
            self._editor_window.grab_set()
        except Exception:
            pass
        self._editor_window.protocol("WM_DELETE_WINDOW", self._close_advanced_editor)

    def _apply_prompt_from_editor(self, prompt_text: str, _negative_prompt: str | None) -> None:
        self.set_prompt(prompt_text)
        self._close_advanced_editor()

    def _close_advanced_editor(self) -> None:
        if self._editor_window and self._editor_window.winfo_exists():
            try:
                self._editor_window.destroy()
            except Exception:
                pass
        self._editor_window = None
        self._editor = None

    def load_from_config(self, config: dict | None) -> None:
        data = config or {}
        self.txt2img_card.load_from_config(data)
        self.img2img_card.load_from_config(data)
        self.upscale_card.load_from_config(data)

    def to_config_delta(self) -> dict:
        delta: dict[str, dict[str, object]] = {}
        for card in (self.txt2img_card, self.img2img_card, self.upscale_card):
            section_delta = card.to_config_dict()
            for section, values in section_delta.items():
                if not values:
                    continue
                delta.setdefault(section, {}).update(values)
        return delta

    def get_txt2img_form_view(self) -> dict:
        return self.txt2img_card.to_config_dict().get("txt2img", {})

    def validate_txt2img(self) -> ValidationResult:
        return self.txt2img_card.validate()

    def set_txt2img_change_callback(self, callback) -> None:
        self._txt2img_change_callback = callback

    def _handle_txt2img_change(self) -> None:
        if self._txt2img_change_callback:
            self._txt2img_change_callback()

    def validate_full_pipeline(self) -> ValidationResult:
        for card in (self.txt2img_card, self.img2img_card, self.upscale_card):
            result = card.validate()
            if not result.ok:
                return result
        return ValidationResult(True, None)
