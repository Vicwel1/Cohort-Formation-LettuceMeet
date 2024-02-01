# This file contains the code for the GUI of the Cohort Formation Tool. Simply run this file to start the GUI. You do not need to modify this file.

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import data_processing_for_GUI as data_processing
import json
import os

# Variables to store file paths and facilitator capacity entries
file_path = ""
facilitator_file_path = ""
facilitator_capacity_entries = {}
participant_file_label = None
facilitator_file_label = None


def load_file():
    """Function to load participant JSON file"""

    global file_path, participant_file_label
    file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
    if file_path:
        messagebox.showinfo("File Loaded", "Participant JSON file loaded successfully.")
        participant_file_label.config(text="Loaded: " + os.path.basename(file_path))


def load_facilitator_file():
    """Function to load facilitator JSON file and display their capacity inputs"""

    global facilitator_file_path, facilitator_file_label
    facilitator_file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
    if facilitator_file_path:
        messagebox.showinfo("File Loaded", "Facilitator JSON file loaded successfully.")
        display_facilitator_capacity_inputs()
        facilitator_file_label.config(text="Loaded: " + os.path.basename(facilitator_file_path))


def display_facilitator_capacity_inputs():
    """Function to display facilitator capacity inputs"""
    global facilitator_capacity_entries
    try:
        with open(facilitator_file_path, 'r') as file:
            data = json.load(file)
        facilitator_names = data_processing.extract_facilitator_availabilities(data, [], only_names=True)
        for widget in facilitator_frame.winfo_children():
            widget.destroy()
        for name in facilitator_names:
            tk.Label(facilitator_frame, text=name).pack(side=tk.LEFT)
            capacity_entry = tk.Entry(facilitator_frame, width=5)
            capacity_entry.pack(side=tk.LEFT)
            facilitator_capacity_entries[name] = capacity_entry
    except Exception as e:
        messagebox.showerror("Error", f"Failed to load facilitator data: {e}")


def run_analysis():
    """Function to run the cohort analysis"""
    global file_path, facilitator_file_path
    if not file_path:
        messagebox.showwarning("Warning", "Please load a JSON file first.")
        return
    try:
        num_cohorts = int(num_cohorts_entry.get())
        min_size = int(min_size_entry.get())
        max_size = int(max_size_entry.get())
        time_block = float(time_block_entry.get())
        data = data_processing.process_data(file_path, num_cohorts, min_size, max_size, time_block, facilitator_file_path, facilitator_capacity_entries)
        result_text.delete('1.0', tk.END)
        for i, cohort in enumerate(data["cohorts"], start=1):
            start, end, participants, facilitator = cohort
            start_str = start.strftime('%A, %H:%M')
            end_str = end.strftime('%H:%M')
            result_text.insert(tk.END, f"Cohort {i}, {start_str} to {end_str}\n", 'bold')
            result_text.insert(tk.END, ", ".join(participants) + f"\n")
            result_text.insert(tk.END, f"Facilitator: ", 'bold')
            result_text.insert(tk.END, f"{facilitator}\n\n")
        if data["not_selected"]:
            result_text.insert(tk.END, "Applicants not included in cohorts:\n", 'bold')
            for applicant in data["not_selected"]:
                result_text.insert(tk.END, f"{applicant}\n")
        if data["not_available"]:
            result_text.insert(tk.END, f"\nApplicants skipped due to low availability (available less than {time_block} hours consecutively):\n", 'bold')
            for applicant in data["not_available"]:
                result_text.insert(tk.END, f"{applicant}\n")
        result_text.tag_configure('bold', font=('Arial', 10, 'bold'))
    except ValueError as e:
        messagebox.showerror("Error", str(e))
    except Exception as e:
        messagebox.showerror("Error", str(e))

# GUI setup
app = tk.Tk()
app.title("Cohort Analysis Tool")

# File upload buttons and labels
load_button = tk.Button(app, text="Load Participant JSON File", command=load_file)
load_button.pack()
participant_file_label = tk.Label(app, text="No file loaded")
participant_file_label.pack()

load_facilitator_button = tk.Button(app, text="Load Facilitator JSON File", command=load_facilitator_file)
load_facilitator_button.pack()
facilitator_file_label = tk.Label(app, text="No file loaded")
facilitator_file_label.pack()

# Input fields for analysis parameters
tk.Label(app, text="Number of Cohorts:").pack()
num_cohorts_entry = tk.Entry(app)
num_cohorts_entry.pack()

tk.Label(app, text="Minimum Size:").pack()
min_size_entry = tk.Entry(app)
min_size_entry.pack()

tk.Label(app, text="Maximum Size:").pack()
max_size_entry = tk.Entry(app)
max_size_entry.pack()

tk.Label(app, text="Time Block (hours):").pack()
time_block_entry = tk.Entry(app)
time_block_entry.pack()

# Frame for displaying facilitator capacity inputs
facilitator_frame = tk.Frame(app)
facilitator_frame.pack()

# Button to initiate analysis
run_button = tk.Button(app, text="Run Analysis", command=run_analysis)
run_button.pack()

# Text box for displaying analysis results
result_text = scrolledtext.ScrolledText(app, wrap=tk.WORD)
result_text.pack(expand=True, fill='both')

# Start the GUI event loop
app.mainloop()

