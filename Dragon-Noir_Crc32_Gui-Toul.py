import os
import struct
import tkinter as tk
from tkinter import filedialog, messagebox

class CRC32Engine:
    POLY = 0xEDB88320

    def __init__(self):
        self.table = [0] * 256
        self.reverse_table = [0] * 256
        self._build_tables()

    def _build_tables(self):
        for i in range(256):
            fwd = i
            for _ in range(8):
                if fwd & 1:
                    fwd = (fwd >> 1) ^ self.POLY
                else:
                    fwd >>= 1
            self.table[i] = fwd & 0xFFFFFFFF

            rev = i << 24
            for _ in range(8):
                if rev & 0x80000000:
                    rev = ((rev ^ self.POLY) << 1) | 1
                else:
                    rev <<= 1
                rev &= 0xFFFFFFFF
            self.reverse_table[i] = rev

    def calculate(self, data: bytes) -> int:
        crc = 0xFFFFFFFF
        for byte in data:
            crc = (crc >> 8) ^ self.table[(crc ^ byte) & 0xFF]
        return crc ^ 0xFFFFFFFF

    def forge_in_place(self, data: bytes, wanted_crc: int) -> bytes:
        if len(data) < 4:
            raise ValueError("File is too small")
        prefix_data = data[:-4]
        fwd_crc = 0xFFFFFFFF
        for byte in prefix_data:
            fwd_crc = (fwd_crc >> 8) ^ self.table[(fwd_crc ^ byte) & 0xFF]
        bkd_crc = wanted_crc ^ 0xFFFFFFFF
        for byte in struct.pack('<L', fwd_crc)[::-1]:
            bkd_crc = ((bkd_crc << 8) & 0xFFFFFFFF) ^ self.reverse_table[bkd_crc >> 24] ^ byte
        return prefix_data + struct.pack('<L', bkd_crc)

class CRCManipGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Dragon-Noir_CRC-manipulator Professional v0.6.0")
        self.root.geometry("680x420")
        self.root.configure(bg="#1e293b")
        
        self.engine = CRC32Engine()
        self.target_file_path = ""
        self.original_file_path = ""
        self.original_crc_val = None

        self._create_widgets()

    def _create_widgets(self):
        title_lbl = tk.Label(self.root, text="Dragon-Noir $ CRC-Manipulator &  Professional", font=("Helvetica", 14, "bold"), fg="#38bdf8", bg="#1e293b")
        title_lbl.pack(pady=15)

        target_frame = tk.LabelFrame(self.root, text=" Target File ", font=("Helvetica", 10, "bold"), bg="#0f172a", fg="#f8fafc", bd=1, relief="solid")
        target_frame.pack(fill="x", padx=20, pady=10)

        self.entry_target = tk.Entry(target_frame, width=55, bd=1, relief="solid", font=("Consolas", 10), bg="#1e293b", fg="#f8fafc", insertbackground="white")
        self.entry_target.pack(side="left", padx=10, pady=10, expand=True, fill="x")

        btn_browse_target = tk.Button(target_frame, text="Browse...", bg="#38bdf8", fg="#0f172a", activebackground="#0ea5e9", font=("Helvetica", 9, "bold"), relief="flat", padx=10, command=self._browse_target)
        btn_browse_target.pack(side="right", padx=10, pady=10)

        orig_frame = tk.LabelFrame(self.root, text=" Reference Original File ", font=("Helvetica", 10, "bold"), bg="#0f172a", fg="#f8fafc", bd=1, relief="solid")
        orig_frame.pack(fill="x", padx=20, pady=10)

        self.entry_orig = tk.Entry(orig_frame, width=55, bd=1, relief="solid", font=("Consolas", 10), bg="#1e293b", fg="#f8fafc", insertbackground="white")
        self.entry_orig.pack(side="left", padx=10, pady=10, expand=True, fill="x")

        btn_browse_orig = tk.Button(orig_frame, text="Browse...", bg="#64748b", fg="#f8fafc", activebackground="#475569", font=("Helvetica", 9, "bold"), relief="flat", padx=10, command=self._browse_original)
        btn_browse_orig.pack(side="right", padx=10, pady=10)

        info_frame = tk.Frame(self.root, bg="#1e293b")
        info_frame.pack(fill="x", padx=25, pady=10)

        tk.Label(info_frame, text="Target File CRC32:", font=("Helvetica", 10, "bold"), bg="#1e293b", fg="#94a3b8").grid(row=0, column=0, sticky="w", pady=5)
        self.lbl_target_crc = tk.Label(info_frame, text="00000000", font=("Consolas", 12, "bold"), fg="#ef4444", bg="#1e293b")
        self.lbl_target_crc.grid(row=0, column=1, sticky="w", padx=15)

        tk.Label(info_frame, text="Original File CRC32:", font=("Helvetica", 10, "bold"), bg="#1e293b", fg="#94a3b8").grid(row=1, column=0, sticky="w", pady=5)
        self.lbl_orig_crc = tk.Label(info_frame, text="--------", font=("Consolas", 12, "bold"), fg="#22c55e", bg="#1e293b")
        self.lbl_orig_crc.grid(row=1, column=1, sticky="w", padx=15)

        tk.Label(info_frame, text="Desired CRC32 (Hex):", font=("Helvetica", 10, "bold"), bg="#1e293b", fg="#94a3b8").grid(row=2, column=0, sticky="w", pady=5)
        self.entry_wanted_crc = tk.Entry(info_frame, font=("Consolas", 12, "bold"), width=12, bd=1, relief="solid", justify="center", bg="#0f172a", fg="#38bdf8", insertbackground="white")
        self.entry_wanted_crc.grid(row=2, column=1, sticky="w", padx=15)
        self.entry_wanted_crc.insert(0, "DEADBEEF")

        btn_frame = tk.Frame(self.root, bg="#1e293b")
        btn_frame.pack(fill="x", padx=20, pady=15)

        self.btn_match = tk.Button(btn_frame, text="Auto Match From Original", bg="#0d9488", fg="#f8fafc", activebackground="#0f766e", font=("Helvetica", 10, "bold"), relief="flat", height=2, command=self._auto_match_value)
        self.btn_match.pack(side="left", expand=True, fill="x", padx=5)

        self.btn_patch = tk.Button(btn_frame, text="Patch Last 4 Bytes (In-Place)", bg="#2563eb", fg="#f8fafc", activebackground="#1d4ed8", font=("Helvetica", 10, "bold"), relief="flat", height=2, command=self._patch_in_place)
        self.btn_patch.pack(side="right", expand=True, fill="x", padx=5)

    def _browse_target(self):
        path = filedialog.askopenfilename()
        if path:
            self.target_file_path = path
            self.entry_target.delete(0, tk.END)
            self.entry_target.insert(0, path)
            self._update_target_crc()

    def _browse_original(self):
        path = filedialog.askopenfilename()
        if path:
            self.original_file_path = path
            self.entry_orig.delete(0, tk.END)
            self.entry_orig.insert(0, path)
            self._update_original_crc()

    def _update_target_crc(self):
        if not self.target_file_path or not os.path.exists(self.target_file_path):
            return
        try:
            with open(self.target_file_path, "rb") as f:
                data = f.read()
            crc = self.engine.calculate(data)
            self.lbl_target_crc.config(text=f"{crc:08X}")
        except Exception:
            self.lbl_target_crc.config(text="ERROR")

    def _update_original_crc(self):
        if not self.original_file_path or not os.path.exists(self.original_file_path):
            return
        try:
            with open(self.original_file_path, "rb") as f:
                data = f.read()
            self.original_crc_val = self.engine.calculate(data)
            self.lbl_orig_crc.config(text=f"{self.original_crc_val:08X}")
        except Exception:
            self.lbl_orig_crc.config(text="ERROR")

    def _auto_match_value(self):
        if self.original_crc_val is not None:
            self.entry_wanted_crc.delete(0, tk.END)
            self.entry_wanted_crc.insert(0, f"{self.original_crc_val:08X}")
        else:
            messagebox.showwarning("Warning", "Select reference file first.")

    def _patch_in_place(self):
        if not self.target_file_path or not os.path.exists(self.target_file_path):
            messagebox.showerror("Error", "Select target file.")
            return

        hex_str = self.entry_wanted_crc.get().strip().replace("0x", "").replace("0X", "")
        if len(hex_str) != 8:
            messagebox.showerror("Error", "Must be 8 hex characters.")
            return

        try:
            wanted_crc = int(hex_str, 16)
        except ValueError:
            messagebox.showerror("Error", "Invalid hex.")
            return

        try:
            with open(self.target_file_path, "rb") as f:
                data = f.read()

            if len(data) < 4:
                messagebox.showerror("Error", "File too small.")
                return

            patched_data = self.engine.forge_in_place(data, wanted_crc)

            with open(self.target_file_path, "wb") as f:
                f.write(patched_data)

            self._update_target_crc()
            messagebox.showinfo("Success", "File patched in-place.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = CRCManipGUI(root)
    root.mainloop()