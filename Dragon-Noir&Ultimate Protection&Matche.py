import os
import struct
import random
import time
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
        if complement == "s2":
            target = (~(target - 1)) & 0xFFFFFFFF
        needed_val = (target - prefix_sum) & 0xFFFFFFFF
        return prefix_data + struct.pack('<L', needed_val)

    def forge_crc32_custom(self, data: bytes, wanted_crc: int, poly: int, init_val: int, xor_out: int,
                           ref_in: bool, ref_out: bool, complement: str = "none") -> bytes:
        if len(data) < 4:
            raise ValueError("Data block size must be at least 4 bytes.")
        target = wanted_crc
        if complement == "s1":
            target = (~target) & 0xFFFFFFFF
        elif complement == "s2":
            target = (~(target - 1)) & 0xFFFFFFFF
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
        self.root.title("Dragon-Noir Protection Sync Engine v6.5.0")
        self.root.geometry("860x700")
        self.root.configure(bg="#050811")
        
        self.engine = AdvancedProtectionEngine()
        self.target_file_path = ""
        self.original_file_path = ""
        self.original_calculated_val = None

        self._create_widgets()
        self._on_preset_change()

    def _create_widgets(self):
        title_lbl = tk.Label(self.root, text="DRAGON-NOIR | IN-PLACE PADDING COMPILER", font=("Segoe UI", 16, "bold"), fg="#3b82f6", bg="#050811")
        title_lbl.pack(pady=20)

        config_frame = tk.LabelFrame(self.root, text=" Core Config Matrix ", font=("Segoe UI", 9, "bold"), bg="#0c1220", fg="#4b5563", bd=1, relief="solid")
        config_frame.pack(fill="x", padx=24, pady=6)

        tk.Label(config_frame, text="Preset Core:", bg="#0c1220", fg="#9ca3af", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, padx=8, pady=10, sticky="e")
        self.combo_preset = ttk.Combobox(config_frame, values=["HexWorkshop Standard CRC32", "Custom CRC32", "Checksum32"], width=26, state="readonly")
        self.combo_preset.grid(row=0, column=1, columnspan=2, padx=8, pady=10, sticky="w")
        self.combo_preset.set("HexWorkshop Standard CRC32")
        self.combo_preset.bind("<<ComboboxSelected>>", self._on_preset_change)

        tk.Label(config_frame, text="Complement:", bg="#0c1220", fg="#9ca3af", font=("Segoe UI", 9, "bold")).grid(row=0, column=3, padx=8, pady=10, sticky="e")
        self.combo_comp = ttk.Combobox(config_frame, values=["none", "s1", "s2"], width=10, state="readonly")
        self.combo_comp.grid(row=0, column=4, padx=8, pady=10, sticky="w")
        self.combo_comp.set("s1")
        self.combo_comp.bind("<<ComboboxSelected>>", self._trigger_recalc)

        tk.Label(config_frame, text="Polynomial:", bg="#0c1220", fg="#9ca3af", font=("Segoe UI", 9, "bold")).grid(row=1, column=0, padx=8, pady=10, sticky="e")
        self.entry_poly = tk.Entry(config_frame, width=14, font=("Consolas", 10), bg="#1f2937", fg="#ffffff", bd=1, relief="solid", insertbackground="white")
        self.entry_poly.grid(row=1, column=1, padx=8, pady=10, sticky="w")
        self.entry_poly.bind("<FocusOut>", self._trigger_recalc)

        tk.Label(config_frame, text="Initial Value:", bg="#0c1220", fg="#9ca3af", font=("Segoe UI", 9, "bold")).grid(row=1, column=2, padx=8, pady=10, sticky="e")
        self.entry_init = tk.Entry(config_frame, width=14, font=("Consolas", 10), bg="#1f2937", fg="#ffffff", bd=1, relief="solid", insertbackground="white")
        self.entry_init.grid(row=1, column=3, padx=8, pady=10, sticky="w")
        self.entry_init.bind("<FocusOut>", self._trigger_recalc)

        tk.Label(config_frame, text="Xor Output:", bg="#0c1220", fg="#9ca3af", font=("Segoe UI", 9, "bold")).grid(row=1, column=4, padx=8, pady=10, sticky="e")
        self.entry_xor = tk.Entry(config_frame, width=14, font=("Consolas", 10), bg="#1f2937", fg="#ffffff", bd=1, relief="solid", insertbackground="white")
        self.entry_xor.grid(row=1, column=5, padx=8, pady=10, sticky="e")
        self.entry_xor.bind("<FocusOut>", self._trigger_recalc)

        self.var_ref_in = tk.BooleanVar(value=True)
        self.check_ref_in = tk.Checkbutton(config_frame, text="Reflect Input", variable=self.var_ref_in, bg="#0c1220", fg="#ffffff", activebackground="#0c1220", activeforeground="#ffffff", selectcolor="#050811", font=("Segoe UI", 9), command=self._trigger_recalc)
        self.check_ref_in.grid(row=2, column=1, columnspan=2, padx=8, pady=8, sticky="w")

        self.var_ref_out = tk.BooleanVar(value=True)
        self.check_ref_out = tk.Checkbutton(config_frame, text="Reflect Output", variable=self.var_ref_out, bg="#0c1220", fg="#ffffff", activebackground="#0c1220", activeforeground="#ffffff", selectcolor="#050811", font=("Segoe UI", 9), command=self._trigger_recalc)
        self.check_ref_out.grid(row=2, column=3, columnspan=2, padx=8, pady=8, sticky="w")

        target_frame = tk.LabelFrame(self.root, text=" Target Workspace (Modification Matrix) ", font=("Segoe UI", 10, "bold"), bg="#0c1220", fg="#4b5563", bd=1, relief="solid")
        target_frame.pack(fill="x", padx=24, pady=10)

        self.entry_target = tk.Entry(target_frame, width=60, bd=1, relief="solid", font=("Consolas", 10), bg="#1f2937", fg="#ffffff", insertbackground="white")
        self.entry_target.pack(side="left", padx=12, pady=12, expand=True, fill="x")

        btn_browse_target = tk.Button(target_frame, text="Load Target File...", bg="#2563eb", fg="#ffffff", activebackground="#1d4ed8", font=("Segoe UI", 9, "bold"), relief="flat", padx=14, command=self._browse_target)
        btn_browse_target.pack(side="right", padx=12, pady=12)

        orig_frame = tk.LabelFrame(self.root, text=" Master Workspace (Original Template Base) ", font=("Segoe UI", 10, "bold"), bg="#0c1220", fg="#4b5563", bd=1, relief="solid")
        orig_frame.pack(fill="x", padx=24, pady=10)

        self.entry_orig = tk.Entry(orig_frame, width=60, bd=1, relief="solid", font=("Consolas", 10), bg="#1f2937", fg="#ffffff", insertbackground="white")
        self.entry_orig.pack(side="left", padx=12, pady=12, expand=True, fill="x")

        btn_browse_orig = tk.Button(orig_frame, text="Load Master File...", bg="#4b5563", fg="#ffffff", activebackground="#374151", font=("Segoe UI", 9, "bold"), relief="flat", padx=14, command=self._browse_original)
        btn_browse_orig.pack(side="right", padx=12, pady=12)

        info_frame = tk.LabelFrame(self.root, text=" System Telemetry Data ", font=("Segoe UI", 10, "bold"), bg="#0c1220", fg="#4b5563", bd=1, relief="solid")
        info_frame.pack(fill="x", padx=24, pady=10)

        tk.Label(info_frame, text="Target File Active Hash:", font=("Segoe UI", 10, "bold"), bg="#0c1220", fg="#9ca3af").grid(row=0, column=0, sticky="e", padx=20, pady=10)
        self.lbl_target_crc = tk.Label(info_frame, text="--------", font=("Consolas", 14, "bold"), fg="#ef4444", bg="#0c1220")
        self.lbl_target_crc.grid(row=0, column=1, sticky="w", padx=20, pady=10)

        tk.Label(info_frame, text="Master Expected Target:", font=("Segoe UI", 10, "bold"), bg="#0c1220", fg="#9ca3af").grid(row=1, column=0, sticky="e", padx=20, pady=10)
        self.lbl_orig_crc = tk.Label(info_frame, text="--------", font=("Consolas", 14, "bold"), fg="#10b981", bg="#0c1220")
        self.lbl_orig_crc.grid(row=1, column=1, sticky="w", padx=20, pady=10)

        tk.Label(info_frame, text="Forced Target Vector:", font=("Segoe UI", 10, "bold"), bg="#0c1220", fg="#9ca3af").grid(row=2, column=0, sticky="e", padx=20, pady=10)
        self.entry_wanted_crc = tk.Entry(info_frame, font=("Consolas", 13, "bold"), width=16, bd=1, relief="solid", justify="center", bg="#1f2937", fg="#06b6d4", insertbackground="white")
        self.entry_wanted_crc.grid(row=2, column=1, sticky="w", padx=20, pady=10)
        self.entry_wanted_crc.insert(0, "0x00000000")

        btn_frame = tk.Frame(self.root, bg="#050811")
        btn_frame.pack(fill="x", padx=24, pady=20)

        self.btn_match = tk.Button(btn_frame, text="Synchronize Master Hash Vector", bg="#0284c7", fg="#ffffff", activebackground="#0369a1", font=("Segoe UI", 11, "bold"), relief="flat", height=2, command=self._auto_match_value)
        self.btn_match.pack(side="left", expand=True, fill="x", padx=10)

        self.btn_patch = tk.Button(btn_frame, text="Overwrite Padding Zone & Apply Matrix", bg="#059669", fg="#ffffff", activebackground="#047857", font=("Segoe UI", 11, "bold"), relief="flat", height=2, command=self._patch_with_random_padding)
        self.btn_patch.pack(side="right", expand=True, fill="x", padx=10)

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
            self.lbl_target_crc.config(text="--------")
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
            self.lbl_orig_crc.config(text="--------")
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

    def _generate_deterministic_random_block(self) -> bytes:
        random.seed(int(time.time() * 1000000))
        block1 = bytes([random.randint(0, 255) for _ in range(1024)])
        block2 = bytes([random.randint(0, 255) for _ in range(2048)])
        return block1 + block2

    def _patch_with_random_padding(self):
        if not self.target_file_path or not os.path.exists(self.target_file_path):
            messagebox.showerror("IO Failure", "Target manipulation vector target path empty.")
            return

        hex_str = self.entry_wanted_crc.get().strip().lower().replace("0x", "")
        if len(hex_str) != 8:
            messagebox.showerror("Hex Structural Error", "Hex structure must explicitly contain 8 characters.")
            return

        try:
            wanted_val = int(hex_str, 16)
        except ValueError:
            messagebox.showerror("Conversion Fault", "Invalid HEX base representation system configuration.")
            return

        try:
            with open(self.target_file_path, "rb") as f:
                base_target_data = f.read()

            if len(base_target_data) < 3076:
                messagebox.showerror("File Bounds Error", "File size is too small to overwrite 3076 bytes.")
                return

            firmware_body = base_target_data[:-3076]
            
            random_padding = self._generate_deterministic_random_block()
            
            raw_appended_structure = firmware_body + random_padding + b"\x00\x00\x00\x00"

            preset = self.combo_preset.get()
            comp = self.combo_comp.get()

            if preset == "Checksum32":
                patched_data = self.engine.forge_checksum32(raw_appended_structure, wanted_val, comp)
            else:
                poly = self._parse_numeric_input(self.entry_poly.get())
                init = self._parse_numeric_input(self.entry_init.get())
                xor = self._parse_numeric_input(self.entry_xor.get())
                r_in = self.var_ref_in.get()
                r_out = self.var_ref_out.get()
                patched_data = self.engine.forge_crc32_custom(raw_appended_structure, wanted_val, poly, init, xor, r_in, r_out, comp)

            out_dir = os.path.dirname(self.target_file_path)
            out_name = "patched_" + os.path.basename(self.target_file_path)
            destination_path = os.path.join(out_dir, out_name)

            with open(destination_path, "wb") as f:
                f.write(patched_data)

            self.target_file_path = destination_path
            self.entry_target.delete(0, tk.END)
            self.entry_target.insert(0, destination_path)
            self._update_target_crc()

            messagebox.showinfo("Execution Terminal", "DRAGON_NOIR _DZ FILE OK!!!!!!!!!")
        except Exception as e:
            messagebox.showerror("Execution Fault Trace", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = AdvancedCRCManipGUI(root)
    root.mainloop()
