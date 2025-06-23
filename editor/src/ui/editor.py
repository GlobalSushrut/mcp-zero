"""
Editor UI for MCP Zero Editor

A lightweight but powerful code editor UI built with tkinter.
Follows resilience patterns with offline-first capability.
"""

import os
import sys
import time
import logging
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, font
from tkinter.scrolledtext import ScrolledText
from typing import Optional, Dict, Any

# Add parent directory to path to import MCP Zero components
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Import MCP Zero resilient components
from src.api import telemetry_collector

# Import local components
from api.llm_service import LLMService

logger = logging.getLogger("mcp_zero.editor.ui")

class EditorApp:
    """
    Main editor application UI.
    
    A lightweight but powerful code editor that integrates with LLM services
    while maintaining offline-first capability.
    """
    
    def __init__(self, llm_service: LLMService):
        """
        Initialize editor application.
        
        Args:
            llm_service: LLM service for AI assistance
        """
        self.llm_service = llm_service
        self.current_file = None
        self.modified = False
        
        # Record telemetry
        telemetry_collector.record("editor.ui.start")
        
        # Initialize UI components
        self.root = tk.Tk()
        self.root.title("MCP Zero Editor")
        self.root.geometry("1200x800")
        
        # Configure style
        self._setup_style()
        
        # Create layout
        self._create_menu()
        self._create_layout()
        
        # Set up keyboard shortcuts
        self._setup_shortcuts()
        
        # Setup file change tracking
        self._setup_change_tracking()
        
        logger.info("Editor UI initialized")
    
    def _setup_style(self):
        """Configure application style."""
        if os.name == 'nt':  # Windows
            self.root.iconbitmap(default='')
        
        # Configure fonts
        self.code_font = font.Font(family="Consolas", size=12)
        
        # Configure ttk style
        style = ttk.Style()
        style.theme_use('clam')  # Use a clean theme
        
        # Custom styles
        style.configure('TButton', padding=6, relief="flat")
        style.configure('TFrame', background='#f0f0f0')
        style.configure('TLabel', background='#f0f0f0')
    
    def _create_menu(self):
        """Create application menu."""
        self.menu = tk.Menu(self.root)
        self.root.config(menu=self.menu)
        
        # File menu
        file_menu = tk.Menu(self.menu, tearoff=0)
        self.menu.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New", command=self.new_file, accelerator="Ctrl+N")
        file_menu.add_command(label="Open", command=self.open_file, accelerator="Ctrl+O")
        file_menu.add_command(label="Save", command=self.save_file, accelerator="Ctrl+S")
        file_menu.add_command(label="Save As", command=self.save_file_as, accelerator="Ctrl+Shift+S")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.exit, accelerator="Alt+F4")
        
        # Edit menu
        edit_menu = tk.Menu(self.menu, tearoff=0)
        self.menu.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Undo", command=self.undo, accelerator="Ctrl+Z")
        edit_menu.add_command(label="Redo", command=self.redo, accelerator="Ctrl+Y")
        edit_menu.add_separator()
        edit_menu.add_command(label="Cut", command=self.cut, accelerator="Ctrl+X")
        edit_menu.add_command(label="Copy", command=self.copy, accelerator="Ctrl+C")
        edit_menu.add_command(label="Paste", command=self.paste, accelerator="Ctrl+V")
        
        # AI menu
        ai_menu = tk.Menu(self.menu, tearoff=0)
        self.menu.add_cascade(label="AI", menu=ai_menu)
        ai_menu.add_command(label="Get Suggestions", command=self.get_ai_help, accelerator="Ctrl+Space")
        ai_menu.add_command(label="Explain Code", command=self.explain_code, accelerator="Ctrl+E")
        ai_menu.add_command(label="Generate Code", command=self.generate_code, accelerator="Ctrl+G")
        
        # View menu
        view_menu = tk.Menu(self.menu, tearoff=0)
        self.menu.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Increase Font Size", command=self.increase_font, accelerator="Ctrl++")
        view_menu.add_command(label="Decrease Font Size", command=self.decrease_font, accelerator="Ctrl+-")
    
    def _create_layout(self):
        """Create main application layout."""
        # Main container frame
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Status bar
        self.status_bar = ttk.Frame(self.root, relief=tk.SUNKEN)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.status_label = ttk.Label(self.status_bar, text="Ready")
        self.status_label.pack(side=tk.LEFT, padx=5)
        
        self.position_label = ttk.Label(self.status_bar, text="Ln 1, Col 1")
        self.position_label.pack(side=tk.RIGHT, padx=5)
        
        self.mode_label = ttk.Label(
            self.status_bar, 
            text=f"LLM: {self.llm_service.mode.value}"
        )
        self.mode_label.pack(side=tk.RIGHT, padx=5)
        
        # Editor pane with line numbers
        self.editor_frame = ttk.Frame(self.main_frame)
        self.editor_frame.pack(fill=tk.BOTH, expand=True)
        
        self.line_numbers = tk.Text(
            self.editor_frame, width=4, padx=3, takefocus=0,
            border=0, background='#f0f0f0', 
            state='disabled', wrap='none'
        )
        self.line_numbers.pack(side=tk.LEFT, fill=tk.Y)
        
        self.editor = ScrolledText(
            self.editor_frame, wrap=tk.NONE,
            undo=True, font=self.code_font
        )
        self.editor.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Horizontal scrollbar
        h_scroll = ttk.Scrollbar(
            self.main_frame, orient=tk.HORIZONTAL, 
            command=self.editor.xview
        )
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.editor['xscrollcommand'] = h_scroll.set
        
        # AI suggestion panel (initially hidden)
        self.ai_frame = ttk.Frame(self.main_frame)
        self.ai_label = ttk.Label(self.ai_frame, text="AI Suggestions")
        self.ai_label.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)
        
        self.ai_text = ScrolledText(
            self.ai_frame, height=10, wrap=tk.WORD,
            font=self.code_font
        )
        self.ai_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.ai_frame.pack(fill=tk.X, side=tk.BOTTOM)
        self.ai_frame.pack_forget()  # Initially hidden
    
    def _setup_shortcuts(self):
        """Set up keyboard shortcuts."""
        self.root.bind('<Control-n>', lambda e: self.new_file())
        self.root.bind('<Control-o>', lambda e: self.open_file())
        self.root.bind('<Control-s>', lambda e: self.save_file())
        self.root.bind('<Control-Shift-S>', lambda e: self.save_file_as())
        
        self.root.bind('<Control-z>', lambda e: self.undo())
        self.root.bind('<Control-y>', lambda e: self.redo())
        
        self.root.bind('<Control-space>', lambda e: self.get_ai_help())
        self.root.bind('<Control-e>', lambda e: self.explain_code())
        self.root.bind('<Control-g>', lambda e: self.generate_code())
        
        # Track cursor position
        self.editor.bind('<KeyRelease>', self._update_position)
        self.editor.bind('<ButtonRelease-1>', self._update_position)
    
    def _setup_change_tracking(self):
        """Set up tracking for file changes."""
        def on_edit(*args):
            if not self.modified:
                self.modified = True
                self._update_title()
        
        # Track changes for modified flag
        self.editor.bind('<<Modified>>', on_edit)
    
    def _update_position(self, event=None):
        """Update cursor position display."""
        position = self.editor.index(tk.INSERT).split('.')
        line, column = position[0], position[1]
        self.position_label.config(text=f"Ln {line}, Col {column}")
    
    def _update_title(self):
        """Update window title based on current file."""
        title = "MCP Zero Editor"
        if self.current_file:
            filename = os.path.basename(self.current_file)
            title = f"{filename} {'*' if self.modified else ''} - {title}"
        self.root.title(title)
    
    def new_file(self):
        """Create a new file."""
        if self.modified and messagebox.askyesno(
            "Save Changes?", 
            "Save changes before creating new file?"
        ):
            self.save_file()
            
        self.editor.delete(1.0, tk.END)
        self.current_file = None
        self.modified = False
        self._update_title()
        
        # Record telemetry
        telemetry_collector.record("editor.file.new")
    
    def open_file(self, filepath=None):
        """
        Open a file for editing.
        
        Args:
            filepath: Path to file to open (None to show dialog)
        """
        if self.modified and messagebox.askyesno(
            "Save Changes?", 
            "Save changes before opening another file?"
        ):
            self.save_file()
            
        if not filepath:
            filepath = filedialog.askopenfilename(
                filetypes=[
                    ("Python files", "*.py"),
                    ("All files", "*.*")
                ]
            )
            
        if filepath:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    self.editor.delete(1.0, tk.END)
                    self.editor.insert(1.0, content)
                    self.current_file = filepath
                    self.modified = False
                    self._update_title()
                    
                    # Reset undo/redo stack
                    self.editor.edit_reset()
                    
                    # Record telemetry
                    telemetry_collector.record(
                        "editor.file.open",
                        file_type=os.path.splitext(filepath)[1]
                    )
                    
                    self.status_label.config(text=f"Opened: {os.path.basename(filepath)}")
            except Exception as e:
                messagebox.showerror("Error", f"Could not open file: {str(e)}")
                logger.error(f"Error opening file: {str(e)}")

    def save_file(self):
        """Save the current file."""
        if not self.current_file:
            return self.save_file_as()
            
        try:
            content = self.editor.get(1.0, tk.END)
            with open(self.current_file, 'w', encoding='utf-8') as f:
                f.write(content)
                
            self.modified = False
            self._update_title()
            self.status_label.config(text=f"Saved: {os.path.basename(self.current_file)}")
            
            # Record telemetry
            telemetry_collector.record("editor.file.save")
            
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Could not save file: {str(e)}")
            logger.error(f"Error saving file: {str(e)}")
            return False
            
    def save_file_as(self):
        """Save the current file with a new name."""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".py",
            filetypes=[
                ("Python files", "*.py"),
                ("All files", "*.*")
            ]
        )
        
        if filepath:
            self.current_file = filepath
            return self.save_file()
        
        return False
    
    def exit(self):
        """Exit the application."""
        if self.modified and messagebox.askyesno(
            "Save Changes?", 
            "Save changes before exiting?"
        ):
            self.save_file()
            
        # Record telemetry before exit
        telemetry_collector.record("editor.exit")
        telemetry_collector.flush()  # Ensure telemetry is sent
        
        # Exit application
        self.root.quit()
    
    def undo(self):
        """Undo last edit."""
        try:
            self.editor.edit_undo()
        except tk.TclError:  # No more undo history
            pass
    
    def redo(self):
        """Redo last undone edit."""
        try:
            self.editor.edit_redo()
        except tk.TclError:  # No more redo history
            pass
    
    def cut(self):
        """Cut selected text."""
        self.editor.event_generate("<<Cut>>")
    
    def copy(self):
        """Copy selected text."""
        self.editor.event_generate("<<Copy>>")
    
    def paste(self):
        """Paste from clipboard."""
        self.editor.event_generate("<<Paste>>")
    
    def increase_font(self):
        """Increase editor font size."""
        size = self.code_font['size']
        self.code_font.configure(size=size + 1)
    
    def decrease_font(self):
        """Decrease editor font size."""
        size = self.code_font['size']
        if size > 6:  # Don't go too small
            self.code_font.configure(size=size - 1)
            
    def get_ai_help(self):
        """Get AI suggestions for current code."""
        # Show the AI panel
        self.ai_frame.pack(fill=tk.X, side=tk.BOTTOM, before=self.main_frame)
        self.ai_text.delete(1.0, tk.END)
        self.ai_text.insert(1.0, "Getting suggestions...")
        
        # Get current code and cursor position
        code = self.editor.get(1.0, tk.END)
        cursor_pos = self.editor.index(tk.INSERT)
        
        # Process in background to avoid UI freeze
        self.root.after(50, lambda: self._process_ai_request(
            prompt="Give me suggestions for the next code I should write.",
            context=f"Code:\n\n{code}\n\nCursor position: {cursor_pos}"
        ))
    
    def explain_code(self):
        """Get explanation for selected code."""
        self.ai_frame.pack(fill=tk.X, side=tk.BOTTOM, before=self.main_frame)
        self.ai_text.delete(1.0, tk.END)
        self.ai_text.insert(1.0, "Analyzing code...")
        
        # Get selected code or current line
        selection = self.editor.get(tk.SEL_FIRST, tk.SEL_LAST) if self.editor.tag_ranges(tk.SEL) else \
                   self.editor.get(f"{int(self.editor.index(tk.INSERT).split('.')[0])}.0", \
                                   f"{int(self.editor.index(tk.INSERT).split('.')[0])}.end")
        
        # Process in background
        self.root.after(50, lambda: self._process_ai_request(
            prompt="Explain this code in detail:",
            context=selection
        ))
    
    def generate_code(self):
        """Generate code based on a comment."""
        # Get selected text or line as prompt
        if self.editor.tag_ranges(tk.SEL):
            prompt = self.editor.get(tk.SEL_FIRST, tk.SEL_LAST)
        else:
            # Get current line
            line_num = int(self.editor.index(tk.INSERT).split('.')[0])
            prompt = self.editor.get(f"{line_num}.0", f"{line_num}.end")
        
        if not prompt.strip():
            messagebox.showinfo("Hint", "Select a comment or write a prompt first")
            return
        
        # Show AI panel
        self.ai_frame.pack(fill=tk.X, side=tk.BOTTOM, before=self.main_frame)
        self.ai_text.delete(1.0, tk.END)
        self.ai_text.insert(1.0, "Generating code...")
        
        # Get some context
        code = self.editor.get(1.0, tk.END)
        
        # Process in background
        self.root.after(50, lambda: self._process_ai_request(
            prompt=f"Generate code for this: {prompt}",
            context=f"Existing code context:\n{code}"
        ))
    
    def _process_ai_request(self, prompt, context=None):
        """Process AI request in a way that doesn't freeze the UI."""
        try:
            # Following offline-first pattern like Traffic Agent:
            # Only attempt API call once, then fall back to local processing if unavailable
            response = self.llm_service.complete(prompt, context)
            
            # Update the AI response panel
            self.ai_text.delete(1.0, tk.END)
            self.ai_text.insert(1.0, response.get('text', 'No response'))
            
            # Update mode label to show current LLM mode
            self.mode_label.config(text=f"LLM: {self.llm_service.mode.value}")
            
        except Exception as e:
            self.ai_text.delete(1.0, tk.END)
            self.ai_text.insert(1.0, f"Error: {str(e)}")
            logger.error(f"AI processing error: {str(e)}")
    
    def _update_line_numbers(self, event=None):
        """Update the line numbers display."""
        # Get visible lines
        first_line = self.editor.index("@0,0")
        last_line = self.editor.index(f"@0,{self.editor.winfo_height()}")
        
        first_line_num = int(first_line.split('.')[0])
        last_line_num = int(last_line.split('.')[0])
        
        # Generate line numbers text
        line_numbers_text = '\n'.join(str(i) for i in range(first_line_num, last_line_num + 1))
        
        # Update line numbers
        self.line_numbers.config(state='normal')
        self.line_numbers.delete(1.0, tk.END)
        self.line_numbers.insert(1.0, line_numbers_text)
        self.line_numbers.config(state='disabled')
    
    def run(self):
        """Start the main application loop."""
        # Configure scrolling to update line numbers
        self.editor.bind("<<ScrollbarRedirect>>", self._update_line_numbers)
        self.editor.bind("<Configure>", self._update_line_numbers)
        
        # Update line numbers initially
        self._update_line_numbers()
        
        # Start main loop
        self.root.mainloop()
