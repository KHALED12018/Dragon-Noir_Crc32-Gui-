import os
import binascii
import struct
import random
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

class DragonNoirGX6605S:
    def __init__(self, root):
        self.root = root
        self.root.title("DRAGON_NOIR_GX6605S-GUI_FIXED")
        self.root.geometry("700x650")
        self.root.configure(bg="#0f172a")
        self.root.resizable(True, True)
        
        self.modified_path = tk.StringVar()
        self.original_path = tk.StringVar()
        self.modified_crc_str = tk.StringVar(value="00000000")
        self.original_crc_str = tk.StringVar(value="00000000")
        self.diff_crc_str = tk.StringVar(value="00000000")
        
        self.create_ui()

    def create_ui(self):
        title_bg = tk.Frame(self.root, bg="#1e293b", bd=2, relief="raised")
        title_bg.pack(pady=20, fill="x", padx=20)
        
        title_label = tk.Label(
            title_bg, 
            text="DRAGON NOIR GX6605S FIXED", 
            font=("Courier New", 22, "bold"), 
            fg="#38bdf8", 
            bg="#0f172a",
            bd=4,
            relief="sunken",
            padx=10,
            pady=10
        )
        title_label.pack(fill="x", padx=4, pady=4)
        
        file_frame = tk.LabelFrame(
            self.root, 
            text=" FILE MANAGEMENT ", 
            font=("Arial", 10, "bold"),
            fg="#38bdf8", 
            bg="#1e293b", 
            bd=2, 
            relief="groove"
        )
        file_frame.pack(pady=10, fill="x", padx=20, ipady=10)
        
        mod_btn = tk.Button(
            file_frame, 
            text="Open Modified File", 
            command=self.load_modified,
            bg="#0284c7", 
            fg="white", 
            font=("Arial", 10, "bold"),
            activebackground="#0369a1",
            activeforeground="white",
            bd=3,
            relief="raised"
        )
        mod_btn.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        
        mod_entry = tk.Entry(
            file_frame, 
            textvariable=self.modified_path, 
            width=50, 
            bg="#334155", 
            fg="#f8fafc",
            insertbackground="white"
        )
        mod_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        
        orig_btn = tk.Button(
            file_frame, 
            text="Open Original File", 
            command=self.load_original,
            bg="#0284c7", 
            fg="white", 
            font=("Arial", 10, "bold"),
            activebackground="#0369a1",
            activeforeground="white",
            bd=3,
            relief="raised"
        )
        orig_btn.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        
        orig_entry = tk.Entry(
            file_frame, 
            textvariable=self.original_path, 
            width=50, 
            bg="#334155", 
            fg="#f8fafc",
            insertbackground="white"
        )
        orig_entry.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
        
        file_frame.columnconfigure(1, weight=1)
        
        crc_frame = tk.LabelFrame(
            self.root, 
            text=" CRYPTOGRAPHIC INTEGRITY CHECK (CRC32 S1) ", 
            font=("Arial", 10, "bold"),
            fg="#38bdf8", 
            bg="#1e293b", 
            bd=2, 
            relief="groove"
        )
        crc_frame.pack(pady=10, fill="x", padx=20, ipady=10)
        
        tk.Label(crc_frame, text="Modified File CRC32:", font=("Arial", 10, "bold"), fg="#94a3b8", bg="#1e293b").grid(row=0, column=0, padx=15, pady=5, sticky="w")
        tk.Entry(crc_frame, textvariable=self.modified_crc_str, font=("Courier New", 11, "bold"), fg="#ef4444", bg="#0f172a", state="readonly", width=20, justify="center").grid(row=0, column=1, padx=15, pady=5)
        
        tk.Label(crc_frame, text="Original File CRC32:", font=("Arial", 10, "bold"), fg="#94a3b8", bg="#1e293b").grid(row=1, column=0, padx=15, pady=5, sticky="w")
        tk.Entry(crc_frame, textvariable=self.original_crc_str, font=("Courier New", 11, "bold"), fg="#22c55e", bg="#0f172a", state="readonly", width=20, justify="center").grid(row=1, column=1, padx=15, pady=5)
        
        tk.Label(crc_frame, text="XOR Injection Delta:", font=("Arial", 10, "bold"), fg="#38bdf8", bg="#1e293b").grid(row=2, column=0, padx=15, pady=5, sticky="w")
        tk.Entry(crc_frame, textvariable=self.diff_crc_str, font=("Courier New", 11, "bold"), fg="#eab308", bg="#0f172a", state="readonly", width=20, justify="center").grid(row=2, column=1, padx=15, pady=5)
        
        process_frame = tk.Frame(self.root, bg="#0f172a")
        process_frame.pack(pady=25, fill="x", padx=20)
        
        match_btn = tk.Button(
            process_frame, 
            text="EXECUTE DUAL-BLOCK MATCHING & INJECTION", 
            command=self.execute_patch,
            bg="#10b981", 
            fg="white", 
            font=("Arial", 12, "bold"),
            activebackground="#059669",
            activeforeground="white",
            bd=5,
            relief="raised",
            pady=8
        )
        match_btn.pack(fill="x")

    def calculate_crc32(self, data):
        return binascii.crc32(data) & 0xFFFFFFFF

    def find_end_of_data(self, data):
        idx = len(data) - 1
        while idx >= 0 and data[idx] == 0xFF:
            idx -= 1
        return idx + 1

    def load_modified(self):
        path = filedialog.askopenfilename()
        if path:
            self.modified_path.set(path)
            with open(path, "rb") as f:
                data = f.read()
            crc = self.calculate_crc32(data)
            self.modified_crc_str.set(f"{crc:08X}")
            self.update_delta()

    def load_original(self):
        path = filedialog.askopenfilename()
        if path:
            self.original_path.set(path)
            with open(path, "rb") as f:
                data = f.read()
            crc = self.calculate_crc32(data)
            self.original_crc_str.set(f"{crc:08X}")
            self.update_delta()

    def update_delta(self):
        try:
            m_crc = int(self.modified_crc_str.get(), 16)
            o_crc = int(self.original_crc_str.get(), 16)
            delta = m_crc ^ o_crc
            self.diff_crc_str.set(f"{delta:08X}")
        except ValueError:
            pass

    def execute_patch(self):
        mod_p = self.modified_path.get()
        orig_p = self.original_path.get()
        
        if not mod_p or not orig_p:
            messagebox.showerror("Error", "Please select both Modified and Original files.")
            return
            
        try:
            with open(mod_p, "rb") as f:
                mod_data = bytearray(f.read())
            with open(orig_p, "rb") as f:
                orig_data = bytearray(f.read())
                
            target_crc = self.calculate_crc32(orig_data)
            target_size = len(orig_data)
            
            clean_end = self.find_end_of_data(mod_data)
            base_payload = mod_data[:clean_end]
            
            block_a = bytearray(random.getrandbits(8) for _ in range(1024))
            block_b = bytearray(block_a)
            
            ff_padding_size = target_size - (len(base_payload) + 1024 + 1024 + 1024 + 4)
            if ff_padding_size < 0:
                messagebox.showerror("Error", "Modified firmware payload size exceeds original structure constraint.")
                return
                
            final_bin = bytearray()
            final_bin.extend(base_payload)
            final_bin.extend(block_a)
            
            rem_size = target_size - (len(final_bin) + len(block_b) + 1024 + 4)
            if rem_size > 0:
                final_bin.extend(b'\xFF' * rem_size)
            else:
                final_bin.extend(b'\xFF' * ff_padding_size)
                
            final_bin.extend(block_b)
            
            block_c = bytearray(random.getrandbits(8) for _ in range(1024))
            final_bin.extend(block_c)
            final_bin.extend(b'\x00\x00\x00\x00')
            
            if len(final_bin) != target_size:
                final_bin = final_bin[:target_size-4] + b'\x00\x00\x00\x00'
                
            final_bin = self.apply_crc32_reverse_forge(final_bin, target_crc)
            
            save_path = filedialog.asksaveasfilename(defaultextension=".bin", filetypes=[("Binary files", "*.bin")])
            if save_path:
                with open(save_path, "wb") as f:
                    f.write(final_bin)
                messagebox.showinfo("Success", f"Firmware structure successfully structured and synchronized!\nHex Workshop Target CRC32: {target_crc:08X}")
                
        except Exception as e:
            messagebox.showerror("Processing Error", str(e))

    def apply_crc32_reverse_forge(self, buffer, target_crc):
        size = len(buffer)
        if size < 4:
            return buffer
            
        poly = 0xEDB88320
        
        table = []
        for i in range(256):
            c = i
            for _ in range(8):
                if c & 1:
                    c = poly ^ (c >> 1)
                else:
                    c = c >> 1
            table.append(c)
            
        buffer[size-4:] = b'\x00\x00\x00\x00'
        
        current_crc = 0xFFFFFFFF
        for x in buffer[:-4]:
            current_crc = (current_crc >> 8) ^ table[(current_crc ^ x) & 0xFF]
            
        target_state = target_crc ^ 0xFFFFFFFF
        
        for i in range(4):
            last_byte = (target_state >> (i * 8)) & 0xFF
            for b in range(256):
                if (table[b] >> 24) == (current_crc >> 24):
                    buffer[size - 4 + i] = b
                    current_crc = ((current_crc ^ table[b]) << 8) & 0xFFFFFFFF
                    break
                    
        crc_reverse = target_crc ^ 0xFFFFFFFF
        for i in range(4):
            top = crc_reverse >> 24
            for b in range(256):
                if (table[b] >> 24) == top:
                    crc_reverse = ((crc_reverse ^ table[b]) << 8) & 0xFFFFFFFF
                    crc_reverse |= b
                    break
                    
        current_crc = 0xFFFFFFFF
        for x in buffer[:-4]:
            current_crc = (current_crc >> 8) ^ table[(current_crc ^ x) & 0xFF]
            
        res = current_crc ^ 0xFFFFFFFF
        
        for i in range(4):
            buffer[size - 4 + i] = 0x00
            
        crc = 0xFFFFFFFF
        for x in buffer[:-4]:
            crc = (crc >> 8) ^ table[(crc ^ x) & 0xFF]
            
        needed = target_crc
        
        for i in range(4):
            for b in range(256):
                temp_crc = (crc >> 8) ^ table[(crc ^ b) & 0xFF]
                temp_needed = needed
                
        final_bytes = bytearray(4)
        t_crc = target_crc ^ 0xFFFFFFFF
        
        for i in range(4):
            for b in range(256):
                if (table[b] >> 24) == (t_crc >> 24):
                    final_bytes[3-i] = b
                    t_crc = ((t_crc ^ table[b]) << 8) & 0xFFFFFFFF
                    break
                    
        crc_accum = 0xFFFFFFFF
        for x in buffer[:-4]:
            crc_accum = (crc_accum >> 8) ^ table[(crc_accum ^ x) & 0xFF]
            
        for i in range(4):
            buffer[size - 4 + i] = final_bytes[i] ^ (crc_accum & 0xFF)
            crc_accum = (crc_accum >> 8) ^ table[(crc_accum & 0xFF) ^ buffer[size - 4 + i]]
            
        return buffer

if __name__ == "__main__":
    root = tk.Tk()
    app = DragonNoirGX6605S(root)
    root.mainloop()
