"""
Enhanced slider widget with arrow buttons for precise control
"""

import tkinter as tk
from tkinter import ttk


class EnhancedSlider(ttk.Frame):
    """Slider with arrow buttons and improved value display"""
    
    def __init__(self, parent, from_=0, to=100, variable=None, resolution=0.01, 
                 width=150, label="", command=None, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.from_ = from_
        self.to = to
        self.resolution = resolution
        self.variable = variable or tk.DoubleVar()
        self.command = command
        
        # Create the widgets
        self._create_widgets(width, label)
        
        # Bind variable changes
        self.variable.trace('w', self._on_variable_change)
        
    def _create_widgets(self, width, label):
        """Create the slider widgets"""
        # Left arrow button
        self.left_btn = ttk.Button(self, text="◀", width=3, 
                                  command=self._decrease_value)
        self.left_btn.pack(side=tk.LEFT, padx=(0, 2))
        
        # Scale widget
        self.scale = ttk.Scale(self, from_=self.from_, to=self.to, 
                              variable=self.variable, orient=tk.HORIZONTAL, 
                              length=width)
        self.scale.pack(side=tk.LEFT, padx=2)
        
        # Right arrow button
        self.right_btn = ttk.Button(self, text="▶", width=3,
                                   command=self._increase_value)
        self.right_btn.pack(side=tk.LEFT, padx=(2, 5))
        
        # Value display label
        self.value_label = ttk.Label(self, text="0.00", width=6)
        self.value_label.pack(side=tk.LEFT)
        
        # Update display
        self._update_display()
        
    def _decrease_value(self):
        """Decrease value by resolution"""
        current = self.variable.get()
        new_value = max(self.from_, current - self.resolution)
        self.variable.set(new_value)
        
    def _increase_value(self):
        """Increase value by resolution"""
        current = self.variable.get()
        new_value = min(self.to, current + self.resolution)
        self.variable.set(new_value)
        
    def _on_variable_change(self, *args):
        """Handle variable changes"""
        self._update_display()
        if self.command:
            self.command(self.variable.get())
            
    def _update_display(self):
        """Update the value display"""
        value = self.variable.get()
        # Format based on resolution
        if self.resolution >= 1:
            display_text = f"{int(value)}"
        elif self.resolution >= 0.1:
            display_text = f"{value:.1f}"
        else:
            display_text = f"{value:.2f}"
        
        self.value_label.config(text=display_text)
        
    def get(self):
        """Get current value"""
        return self.variable.get()
        
    def set(self, value):
        """Set current value"""
        self.variable.set(value)
        
    def configure(self, **kwargs):
        """Configure the slider"""
        if 'command' in kwargs:
            self.command = kwargs.pop('command')
        if 'state' in kwargs:
            state = kwargs.pop('state')
            self.scale.config(state=state)
            self.left_btn.config(state=state)
            self.right_btn.config(state=state)
        
        super().configure(**kwargs)