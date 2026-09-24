"""
Tkinter app: Convert images in subfolders into PDFs with folder selection dialogs.

Features:
- Browse buttons to select both root and output directories
- Option to recurse into nested subfolders
- Natural sorting of images (1, 2, ..., 10)
- Progress bar and status log

Requirements:
- Python 3.x
- Pillow: pip install pillow

Run:
python pngs_to_pdfs_tkinter.py
"""

import os
import re
import threading
import traceback
from PIL import Image
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

IMG_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff'}

def natural_sort_key(s):
    parts = re.split(r'(\d+)', s)
    return [int(p) if p.isdigit() else p.lower() for p in parts]

def images_to_pdf(folder_path, folder_name, out_dir, log_fn):
    try:
        files = [f for f in os.listdir(folder_path)
                 if os.path.isfile(os.path.join(folder_path, f)) and os.path.splitext(f)[1].lower() in IMG_EXTS]
        if not files:
            log_fn(f"  - No images found in '{folder_name}' - skipping")
            return False, 0

        files.sort(key=natural_sort_key)
        full_paths = [os.path.join(folder_path, f) for f in files]

        first_img = Image.open(full_paths[0]).convert('RGB')
        rest_imgs = []
        for p in full_paths[1:]:
            try:
                rest_imgs.append(Image.open(p).convert('RGB'))
            except Exception as e:
                log_fn(f"    ! Could not open {os.path.basename(p)}: {e}")

        out_path = os.path.join(out_dir, f"{folder_name}.pdf")
        first_img.save(out_path, save_all=True, append_images=rest_imgs)
        log_fn(f"  -> Saved PDF: {out_path} ({1 + len(rest_imgs)} pages)")
        return True, 1 + len(rest_imgs)

    except Exception as exc:
        log_fn(f"  ! Failed to create PDF for '{folder_name}': {exc}")
        return False, 0

class ConverterApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Images → PDFs Converter")
        self.geometry("800x500")
        self.resizable(False, False)

        self.root_dir = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.recurse = tk.BooleanVar(value=False)

        self._build_ui()

    def _build_ui(self):
        frame = ttk.Frame(self, padding=12)
        frame.pack(fill='both', expand=True)

        # Root Directory
        row1 = ttk.Frame(frame)
        row1.pack(fill='x', pady=6)
        ttk.Label(row1, text="Root Directory (contains subfolders):").pack(side='left')
        ttk.Entry(row1, textvariable=self.root_dir, width=37).pack(side='left', padx=8)
        ttk.Button(row1, text="Browse", command=self.browse_root).pack(side='left')

        # Output Directory
        row2 = ttk.Frame(frame)
        row2.pack(fill='x', pady=6)
        ttk.Label(row2, text="Output Directory (PDFs saved here):").pack(side='left')
        ttk.Entry(row2, textvariable=self.output_dir, width=37).pack(side='left', padx=8)
        ttk.Button(row2, text="Browse", command=self.browse_output).pack(side='left')

        # Options
        opts = ttk.Frame(frame)
        opts.pack(fill='x', pady=6)
        ttk.Checkbutton(opts, text="Recurse into nested folders", variable=self.recurse).pack(side='left')

        # Buttons
        btns = ttk.Frame(frame)
        btns.pack(fill='x', pady=10)
        self.start_btn = ttk.Button(btns, text="Start Conversion", command=self.on_start)
        self.start_btn.pack(side='left', padx=5)
        ttk.Button(btns, text="Open Output Folder", command=self.open_output).pack(side='left', padx=5)
        ttk.Button(btns, text="Quit", command=self.quit).pack(side='right', padx=5)

        # Progress + Log
        log_frame = ttk.LabelFrame(frame, text="Progress Log", padding=8)
        log_frame.pack(fill='both', expand=True)

        self.progress = ttk.Progressbar(log_frame, orient='horizontal', mode='determinate')
        self.progress.pack(fill='x', pady=(0,8))

        self.log = tk.Text(log_frame, height=18, wrap='word')
        self.log.pack(fill='both', expand=True)
        self.log.config(state='disabled')

    def browse_root(self):
        d = filedialog.askdirectory(title="Select Root Folder")
        if d:
            self.root_dir.set(d)

    def browse_output(self):
        d = filedialog.askdirectory(title="Select Output Folder")
        if d:
            self.output_dir.set(d)

    def open_output(self):
        out = self.output_dir.get()
        if out and os.path.isdir(out):
            try:
                os.startfile(out)
            except Exception:
                messagebox.showinfo("Open Folder", f"Open this folder manually: {out}")
        else:
            messagebox.showwarning("Warning", "Select a valid output folder first.")

    def log_msg(self, msg):
        self.log.config(state='normal')
        self.log.insert('end', msg + '\n')
        self.log.see('end')
        self.log.config(state='disabled')

    def on_start(self):
        root = self.root_dir.get().strip()
        out = self.output_dir.get().strip()

        if not root or not os.path.isdir(root):
            messagebox.showerror("Error", "Please select a valid root directory.")
            return
        if not out:
            messagebox.showerror("Error", "Please select a valid output directory.")
            return

        os.makedirs(out, exist_ok=True)
        self.start_btn.config(state='disabled')
        self.progress['value'] = 0
        self.log.config(state='normal')
        self.log.delete('1.0', 'end')
        self.log.config(state='disabled')

        t = threading.Thread(target=self._run_conversion, args=(root, out, self.recurse.get()), daemon=True)
        t.start()

    def _run_conversion(self, root, out, recurse):
        try:
            self.log_msg(f"Starting conversion from: {root}\nOutput: {out}\nRecurse: {recurse}\n")

            if recurse:
                folders = set()
                for dirpath, _, filenames in os.walk(root):
                    if any(os.path.splitext(f)[1].lower() in IMG_EXTS for f in filenames):
                        folders.add(dirpath)
                folders = sorted(list(folders), key=natural_sort_key)
            else:
                folders = [os.path.join(root, d) for d in os.listdir(root) if os.path.isdir(os.path.join(root, d))]
                folders = sorted(folders, key=lambda p: natural_sort_key(os.path.basename(p)))

            if not folders:
                self.log_msg("No folders with images found.")
                return

            total = len(folders)
            self.progress['maximum'] = total

            for i, folder_path in enumerate(folders, start=1):
                folder_name = os.path.basename(folder_path.rstrip(os.sep))
                self.log_msg(f"Processing ({i}/{total}): {folder_name}")
                images_to_pdf(folder_path, folder_name, out, self.log_msg)
                self.progress['value'] = i

            self.log_msg("Conversion completed successfully.")
        except Exception as e:
            self.log_msg("Error:\n" + traceback.format_exc())
        finally:
            self.start_btn.config(state='normal')

if __name__ == '__main__':
    app = ConverterApp()
    app.mainloop()