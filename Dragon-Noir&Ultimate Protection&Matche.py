import os
import struct
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

class AdvancedProtectionEngine:
    def __init__(self):
        pass

    def calculate_checksum32(self, data: bytes, complement: str = "none") -> int:
        total = sum(data) & 0xFFFFFFFF
        if complement == "s1":
            total = (~total) & 0xFFFFFFFF
        elif complement == "s2":
            total = ((~total) + 1) & 0xFFFFFFFF
        return total

    def calculate_crc32_custom(self, data: bytes, poly: int, init_val: int, xor_out: int, 
                               ref_in: bool, ref_out: bool, complement: str = "none") -> int:
        crc = init_val
        
        if ref_in:
            lookup_poly = 0
            for i in range(32):
                if (poly >> (31 - i)) & 1:
                    lookup_poly |= (1 << i)
            
            table = [0] * 256
            for i in range(256):
                fwd = i
                for _ in range(8):
                    if fwd & 1:
                        fwd = (fwd >> 1) ^ lookup_poly
                    else:
                        fwd >>= 1
                table[i] = fwd & 0xFFFFFFFF
                
            for byte in data:
                crc = (crc >> 8) ^ table[(crc ^ byte) & 0xFF]
        else:
            for byte in data:
                crc ^= (byte << 24)
                for _ in range(8):
                    if crc & 0x80000000:
                        crc = ((crc << 1) ^ poly) & 0xFFFFFFFF
                    else:
                        crc = (crc << 1) & 0xFFFFFFFF
                        
        if ref_out ^ ref_in:
            res = 0
            for i in range(32):
                if (crc >> i) & 1:
                    res |= (1 << (31 - i))
            crc = res

        crc ^= xor_out
        if complement == "s1":
            crc = (~crc) & 0xFFFFFFFF
        elif complement == "s2":
            crc = ((~crc) + 1) & 0xFFFFFFFF
        return crc

    def forge_checksum32(self, data: bytes, wanted_sum: int, complement: str = "none") -> bytes:
        if len(data) < 4:
            raise ValueError("Data block size must be at least 4 bytes.")
        
        prefix_data = data[:-4]
        prefix_sum = sum(prefix_data) & 0xFFFFFFFF
        
        target = wanted_sum
        if complement == "s1":
            target = (~target) & 0xFFFFFFFF
        elif complement == "s2":
            target = (~(target - 1)) & 0xFFFFFFFF
            
        needed_val = (target - prefix_sum) & 0xFFFFFFFF
        return prefix_data + struct.pack('<L', needed_val)

    def forge_crc32_custom(self, data: bytes, wanted_crc: int, poly: int, init_val: int, xor_out: int,
                           ref_in: bool, ref_out: bool, complement: str = "none") -> bytes:
        if len(data) < 4:
            raise ValueError("Data block size must be at least 4 bytes.")
            
        target = wanted_crc
        if complement == "s2":
            target = (~(target - 1)) & 0xFFFFFFFF
        elif complement == "s1":
            target = (~target) & 0xFFFFFFFF
        target ^= xor_out

        if ref_out ^ ref_in:
            res = 0
            for i in range(32):
                if (target >> i) & 1:
                    res |= (1 << (31 - i))
            target = res

        prefix_data = data[:-4]
        
        fwd_crc = init_val
        if ref_in:
            r_poly = 0
            for i in range(32):
                if (poly >> (31 - i)) & 1:
                    r_poly |= (1 << i)
            
            f_table = [0] * 256
            for i in range(256):
                fwd = i
                for _ in range(8):
                    if fwd & 1:
                        fwd = (fwd >> 1) ^ r_poly
                    else:
                        fwd >>= 1
                f_table[i] = fwd & 0xFFFFFFFF
                
            for byte in prefix_data:
                fwd_crc = (fwd_crc >> 8) ^ f_table[(fwd_crc ^ byte) & 0xFF]
        else:
            for byte in prefix_data:
                fwd_crc ^= (byte << 24)
                for _ in range(8):
                    if fwd_crc & 0x80000000:
                        fwd_crc = ((fwd_crc << 1) ^ poly) & 0xFFFFFFFF
                    else:
                        fwd_crc = (fwd_crc << 1) & 0xFFFFFFFF

        r_poly = 0
        for i in range(32):
            if (poly >> (31 - i)) & 1:
                r_poly |= (1 << i)

        reverse_table = [0] * 256
        for i in range(256):
            rev = i << 24
            for _ in range(8):
                if rev & 0x80000000:
                    rev = ((rev ^ poly) << 1) | 1
                else:
                    rev <<= 1
                rev &= 0xFFFFFFFF
            reverse_table[i] = rev

        bkd_crc = target
        
        if ref_in:
            f_table_rev = [0] * 256
            for i in range(256):
                rev = i << 24
                for _ in range(8):
                    if rev & 0x80000000:
                        rev = ((rev ^ r_poly) << 1) | 1
                    else:
                        rev <<= 1
                    rev &= 0xFFFFFFFF
                f_table_rev[i] = rev
                
            for byte in struct.pack('<L', fwd_crc)[::-1]:
                bkd_crc = ((bkd_crc << 8) & 0xFFFFFFFF) ^ f_table_rev[bkd_crc >> 24] ^ byte
            return prefix_data + struct.pack('<L', bkd_crc)
        else:
            for byte in struct.pack('>L', fwd_crc):
                bkd_crc = ((bkd_crc << 8) & 0xFFFFFFFF) ^ reverse_table[bkd_crc >> 24] ^ byte
            return prefix_data + struct.pack('>L', bkd_crc)

class AdvancedCRCManipGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Dragon-Noir  Protection Sync Engine v4.0.0")
        self.root.geometry("820x650")
        self.root.configure(bg="#0f172a")
        
        self.engine = AdvancedProtectionEngine()
        self.target_file_path = ""
        self.original_file_path = ""
        self.original_calculated_val = None

        self._create_widgets()
        self._on_preset_change()

    def _create_widgets(self):
        title_lbl = tk.Label(self.root, text="Dragon-Noir $ Ultimate Protection Matcher", font=("Consolas", 15, "bold"), fg="#38bdf8", bg="#0f172a")
        title_lbl.pack(pady=12)

        config_frame = tk.LabelFrame(self.root, text=" Engine Protection Vector Configuration ", font=("Helvetica", 10, "bold"), bg="#1e293b", fg="#f8fafc", bd=1, relief="solid")
        config_frame.pack(fill="x", padx=20, pady=5)

        tk.Label(config_frame, text="Preset:", bg="#1e293b", fg="#94a3b8", font=("Helvetica", 9, "bold")).grid(row=0, column=0, padx=8, pady=8, sticky="e")
        self.combo_preset = ttk.Combobox(config_frame, values=["HexWorkshop Standard CRC32", "Custom CRC32", "Checksum32"], width=26, state="readonly")
        self.combo_preset.grid(row=0, column=1, columnspan=2, padx=8, pady=8, sticky="w")
        self.combo_preset.set("HexWorkshop Standard CRC32")
        self.combo_preset.bind("<<ComboboxSelected>>", self._on_preset_change)

        tk.Label(config_frame, text="Complement:", bg="#1e293b", fg="#94a3b8", font=("Helvetica", 9, "bold")).grid(row=0, column=3, padx=8, pady=8, sticky="e")
        self.combo_comp = ttk.Combobox(config_frame, values=["none", "s1", "s2"], width=10, state="readonly")
        self.combo_comp.grid(row=0, column=4, padx=8, pady=8, sticky="w")
        self.combo_comp.set("none")
        self.combo_comp.bind("<<ComboboxSelected>>", self._trigger_recalc)

        tk.Label(config_frame, text="Polynomial:", bg="#1e293b", fg="#94a3b8", font=("Helvetica", 9, "bold")).grid(row=1, column=0, padx=8, pady=8, sticky="e")
        self.entry_poly = tk.Entry(config_frame, width=14, font=("Consolas", 10), bg="#0f172a", fg="#f8fafc", bd=1, relief="solid", insertbackground="white")
        self.entry_poly.grid(row=1, column=1, padx=8, pady=8, sticky="w")
        self.entry_poly.bind("<FocusOut>", self._trigger_recalc)

        tk.Label(config_frame, text="Initial Value:", bg="#1e293b", fg="#94a3b8", font=("Helvetica", 9, "bold")).grid(row=1, column=2, padx=8, pady=8, sticky="e")
        self.entry_init = tk.Entry(config_frame, width=14, font=("Consolas", 10), bg="#0f172a", fg="#f8fafc", bd=1, relief="solid", insertbackground="white")
        self.entry_init.grid(row=1, column=3, padx=8, pady=8, sticky="w")
        self.entry_init.bind("<FocusOut>", self._trigger_recalc)

        tk.Label(config_frame, text="Xor Output:", bg="#1e293b", fg="#94a3b8", font=("Helvetica", 9, "bold")).grid(row=1, column=4, padx=8, pady=8, sticky="e")
        self.entry_xor = tk.Entry(config_frame, width=14, font=("Consolas", 10), bg="#0f172a", fg="#f8fafc", bd=1, relief="solid", insertbackground="white")
        self.entry_xor.grid(row=1, column=5, padx=8, pady=8, sticky="w")
        self.entry_xor.bind("<FocusOut>", self._trigger_recalc)

        self.var_ref_in = tk.BooleanVar(value=True)
        self.check_ref_in = tk.Checkbutton(config_frame, text="Reflect Input Data", variable=self.var_ref_in, bg="#1e293b", fg="#f8fafc", activebackground="#1e293b", activeforeground="#f8fafc", selectcolor="#0f172a", font=("Helvetica", 9), command=self._trigger_recalc)
        self.check_ref_in.grid(row=2, column=1, columnspan=2, padx=8, pady=8, sticky="w")

        self.var_ref_out = tk.BooleanVar(value=True)
        self.check_ref_out = tk.Checkbutton(config_frame, text="Reflect Output CRC", variable=self.var_ref_out, bg="#1e293b", fg="#f8fafc", activebackground="#1e293b", activeforeground="#f8fafc", selectcolor="#0f172a", font=("Helvetica", 9), command=self._trigger_recalc)
        self.check_ref_out.grid(row=2, column=3, columnspan=2, padx=8, pady=8, sticky="w")

        target_frame = tk.LabelFrame(self.root, text=" Target Binary Block File (To Be Modified) ", font=("Helvetica", 10, "bold"), bg="#1e293b", fg="#f8fafc", bd=1, relief="solid")
        target_frame.pack(fill="x", padx=20, pady=8)

        self.entry_target = tk.Entry(target_frame, width=60, bd=1, relief="solid", font=("Consolas", 10), bg="#0f172a", fg="#f8fafc", insertbackground="white")
        self.entry_target.pack(side="left", padx=10, pady=10, expand=True, fill="x")

        btn_browse_target = tk.Button(target_frame, text="Browse Target...", bg="#38bdf8", fg="#0f172a", activebackground="#0ea5e9", font=("Helvetica", 9, "bold"), relief="flat", padx=12, command=self._browse_target)
        btn_browse_target.pack(side="right", padx=10, pady=10)

        orig_frame = tk.LabelFrame(self.root, text=" Reference Original Hex Master File (Source Truth) ", font=("Helvetica", 10, "bold"), bg="#1e293b", fg="#f8fafc", bd=1, relief="solid")
        orig_frame.pack(fill="x", padx=20, pady=8)

        self.entry_orig = tk.Entry(orig_frame, width=60, bd=1, relief="solid", font=("Consolas", 10), bg="#0f172a", fg="#f8fafc", insertbackground="white")
        self.entry_orig.pack(side="left", padx=10, pady=10, expand=True, fill="x")

        btn_browse_orig = tk.Button(orig_frame, text="Browse Master...", bg="#64748b", fg="#f8fafc", activebackground="#475569", font=("Helvetica", 9, "bold"), relief="flat", padx=12, command=self._browse_original)
        btn_browse_orig.pack(side="right", padx=10, pady=10)

        info_frame = tk.LabelFrame(self.root, text=" Matrix Calculation State Monitor ", font=("Helvetica", 10, "bold"), bg="#1e293b", fg="#f8fafc", bd=1, relief="solid")
        info_frame.pack(fill="x", padx=20, pady=8)

        tk.Label(info_frame, text="Target File Protection Hash:", font=("Helvetica", 10, "bold"), bg="#1e293b", fg="#94a3b8").grid(row=0, column=0, sticky="e", padx=15, pady=8)
        self.lbl_target_crc = tk.Label(info_frame, text="00000000", font=("Consolas", 14, "bold"), fg="#ef4444", bg="#1e293b")
        self.lbl_target_crc.grid(row=0, column=1, sticky="w", padx=15, pady=8)

        tk.Label(info_frame, text="Master File Expected Hash:", font=("Helvetica", 10, "bold"), bg="#1e293b", fg="#94a3b8").grid(row=1, column=0, sticky="e", padx=15, pady=8)
        self.lbl_orig_crc = tk.Label(info_frame, text="--------", font=("Consolas", 14, "bold"), fg="#22c55e", bg="#1e293b")
        self.lbl_orig_crc.grid(row=1, column=1, sticky="w", padx=15, pady=8)

        tk.Label(info_frame, text="Target Injection Vector (Hex):", font=("Helvetica", 10, "bold"), bg="#1e293b", fg="#94a3b8").grid(row=2, column=0, sticky="e", padx=15, pady=8)
        self.entry_wanted_crc = tk.Entry(info_frame, font=("Consolas", 13, "bold"), width=16, bd=1, relief="solid", justify="center", bg="#0f172a", fg="#38bdf8", insertbackground="white")
        self.entry_wanted_crc.grid(row=2, column=1, sticky="w", padx=15, pady=8)
        self.entry_wanted_crc.insert(0, "0x00000000")

        btn_frame = tk.Frame(self.root, bg="#0f172a")
        btn_frame.pack(fill="x", padx=20, pady=15)

        self.btn_match = tk.Button(btn_frame, text="Clone & Sync Master Hash Matrix", bg="#0d9488", fg="#f8fafc", activebackground="#0f766e", font=("Helvetica", 11, "bold"), relief="flat", height=2, command=self._auto_match_value)
        self.btn_match.pack(side="left", expand=True, fill="x", padx=8)

        self.btn_patch = tk.Button(btn_frame, text="Patch Last 4 Bytes Array (In-Place Fix)", bg="#2563eb", fg="#f8fafc", activebackground="#1d4ed8", font=("Helvetica", 11, "bold"), relief="flat", height=2, command=self._patch_in_place)
        self.btn_patch.pack(side="right", expand=True, fill="x", padx=8)

    def _on_preset_change(self, event=None):
        preset = self.combo_preset.get()
        if preset == "HexWorkshop Standard CRC32":
            self.entry_poly.config(state="normal")
            self.entry_init.config(state="normal")
            self.entry_xor.config(state="normal")
            self.entry_poly.delete(0, tk.END)
            self.entry_poly.insert(0, "0x04C11DB7")
            self.entry_init.delete(0, tk.END)
            self.entry_init.insert(0, "0xFFFFFFFF")
            self.entry_xor.delete(0, tk.END)
            self.entry_xor.insert(0, "0xFFFFFFFF")
            self.var_ref_in.set(True)
            self.var_ref_out.set(True)
            self.check_ref_in.config(state="disabled")
            self.check_ref_out.config(state="disabled")
            self.entry_poly.config(state="disabled")
            self.entry_init.config(state="disabled")
            self.entry_xor.config(state="disabled")
        elif preset == "Checksum32":
            self.entry_poly.config(state="disabled")
            self.entry_init.config(state="disabled")
            self.entry_xor.config(state="disabled")
            self.check_ref_in.config(state="disabled")
            self.check_ref_out.config(state="disabled")
        else:
            self.entry_poly.config(state="normal")
            self.entry_init.config(state="normal")
            self.entry_xor.config(state="normal")
            self.check_ref_in.config(state="normal")
            self.check_ref_out.config(state="normal")
            
        self._trigger_recalc()

    def _trigger_recalc(self, event=None):
        self._update_target_crc()
        self._update_original_crc()

    def _parse_numeric_input(self, val_str):
        try:
            s = val_str.strip()
            if s.lower().startswith("0x"):
                return int(s, 16)
            return int(s, 10)
        except ValueError:
            return 0

    def _execute_calculation(self, data):
        preset = self.combo_preset.get()
        comp = self.combo_comp.get()
        
        if preset == "Checksum32":
            return self.engine.calculate_checksum32(data, comp)
        else:
            poly = self._parse_numeric_input(self.entry_poly.get())
            init = self._parse_numeric_input(self.entry_init.get())
            xor = self._parse_numeric_input(self.entry_xor.get())
            r_in = self.var_ref_in.get()
            r_out = self.var_ref_out.get()
            return self.engine.calculate_crc32_custom(data, poly, init, xor, r_in, r_out, comp)

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
            val = self._execute_calculation(data)
            self.lbl_target_crc.config(text=f"0x{val:08X}")
        except Exception:
            self.lbl_target_crc.config(text="ERROR")

    def _update_original_crc(self):
        if not self.original_file_path or not os.path.exists(self.original_file_path):
            return
        try:
            with open(self.original_file_path, "rb") as f:
                data = f.read()
            self.original_calculated_val = self._execute_calculation(data)
            self.lbl_orig_crc.config(text=f"0x{self.original_calculated_val:08X}")
        except Exception:
            self.lbl_orig_crc.config(text="ERROR")

    def _auto_match_value(self):
        if self.original_calculated_val is not None:
            self.entry_wanted_crc.delete(0, tk.END)
            self.entry_wanted_crc.insert(0, f"0x{self.original_calculated_val:08X}")
        else:
            messagebox.showwarning("System Constraint", "Failed to resolve master hash vector. Please load Master file.")

    def _patch_in_place(self):
        if not self.target_file_path or not os.path.exists(self.target_file_path):
            messagebox.showerror("IO Failure", "Target manipulation vector target path empty.")
            return

        hex_str = self.entry_wanted_crc.get().strip().lower().replace("0x", "")
        if len(hex_str) != 8:
            messagebox.showerror("Hex Structural Error", "Hex structure must explicitly contain 8 characters (32-bit register limit).")
            return

        try:
            wanted_val = int(hex_str, 16)
        except ValueError:
            messagebox.showerror("Conversion Fault", "Invalid HEX base representation system configuration.")
            return

        try:
            with open(self.target_file_path, "rb") as f:
                data = f.read()

            if len(data) < 4:
                messagebox.showerror("Bounds Overflow", "Data block structure lacks necessary offset bounds (min 4 bytes).")
                return

            preset = self.combo_preset.get()
            comp = self.combo_comp.get()

            if preset == "Checksum32":
                patched_data = self.engine.forge_checksum32(data, wanted_val, comp)
            else:
                poly = self._parse_numeric_input(self.entry_poly.get())
                init = self._parse_numeric_input(self.entry_init.get())
                xor = self._parse_numeric_input(self.entry_xor.get())
                r_in = self.var_ref_in.get()
                r_out = self.var_ref_out.get()
                patched_data = self.engine.forge_crc32_custom(data, wanted_val, poly, init, xor, r_in, r_out, comp)

            with open(self.target_file_path, "wb") as f:
                f.write(patched_data)

            self._update_target_crc()
            messagebox.showinfo("Execution Terminal", "Reverse matrix mapping succeeded. Hex block alignment complete.")
        except Exception as e:
            messagebox.showerror("Execution Fault Trace", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = AdvancedCRCManipGUI(root)
    root.mainloop()