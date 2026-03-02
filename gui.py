#!/usr/bin/env python3
"""
GUI for Bonus Hedge Finder
Uses tkinter to provide a user-friendly interface for the bonus hedge finder
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import json
import os
import threading
from pathlib import Path
from datetime import datetime
import sys
import traceback

# Import from main.py
from main import (
    BOOK_ALIASES,
    SPORT_KEYS,
    parse_books,
    get_regions_needed,
    collect_all_odds,
    find_all_opportunities,
    select_best_opportunity,
    find_qualifying_opportunities,
    select_best_qualifying_opportunity,
    calculate_hedge,
    calculate_qualifying_hedge,
    Logger,
)


class HedgeFinderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Bonus Hedge Finder")
        self.root.geometry("900x900")
        
        # Setup logger for GUI
        self.logger = Logger("debug.log")

        # Mode: "bonus" or "qualifying"
        self.mode_var = tk.StringVar(value="bonus")

        # Load configuration
        self.config = self.load_config()

        # Setup UI
        self.setup_ui()
        
        # Threading
        self.search_thread = None
        self.is_searching = False
    
    def load_config(self):
        """Load configuration from config.json"""
        config_path = Path("config.json")
        
        if not config_path.exists():
            # Create default config
            default_config = {
                "api_key": "",
                "allowed_books": [
                    "fanduel",
                    "draftkings",
                    "williamhill_us",
                    "betrivers",
                    "fanatics",
                    "betmgm",
                    "ballybet",
                    "espnbet",
                    "betparx",
                    "fliff",
                    "hardrockbet"
                ],
                "sports": [
                    "NBA",
                    "NCAAB",
                    "NCAAF",
                    "Euro Basketball",
                    "NFL",
                    "MLB",
                    "NHL"
                ]
            }
            with open(config_path, 'w') as f:
                json.dump(default_config, f, indent=4)
            return default_config
        
        with open(config_path, 'r') as f:
            return json.load(f)
    
    def save_config(self):
        """Save configuration to config.json"""
        with open("config.json", 'w') as f:
            json.dump(self.config, f, indent=4)
    
    def setup_ui(self):
        """Setup the main UI components"""
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(6, weight=1)

        # Title
        title_label = ttk.Label(
            main_frame,
            text="Bonus Hedge Finder",
            font=('Arial', 16, 'bold')
        )
        title_label.grid(row=0, column=0, pady=(0, 20))

        # Configuration Frame
        self.setup_config_frame(main_frame)

        # Sports Selection Frame
        self.setup_sports_frame(main_frame)

        # Books Selection Frame
        self.setup_books_frame(main_frame)

        # Control Frame
        self.setup_control_frame(main_frame)

        # Manual Calculator Frame
        self.setup_manual_frame(main_frame)

        # Results Frame
        self.setup_results_frame(main_frame)

        # Status Bar
        self.setup_status_bar(main_frame)
    
    def setup_config_frame(self, parent):
        """Setup configuration input frame"""
        config_frame = ttk.LabelFrame(parent, text="Configuration", padding="10")
        config_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        config_frame.columnconfigure(1, weight=1)

        # Mode selection
        ttk.Label(config_frame, text="Mode:").grid(row=0, column=0, sticky=tk.W, pady=5)
        mode_frame = ttk.Frame(config_frame)
        mode_frame.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        ttk.Radiobutton(mode_frame, text="Bonus Bet", variable=self.mode_var,
                        value="bonus", command=self.on_mode_change).grid(row=0, column=0, padx=(0, 15))
        ttk.Radiobutton(mode_frame, text="Qualifying Bet", variable=self.mode_var,
                        value="qualifying", command=self.on_mode_change).grid(row=0, column=1)

        # API Key
        ttk.Label(config_frame, text="API Key:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.api_key_var = tk.StringVar(value=self.config.get('api_key', ''))
        api_entry = ttk.Entry(config_frame, textvariable=self.api_key_var, width=50, show='*')
        api_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=5)

        # Source book (label changes based on mode)
        self.source_book_label = ttk.Label(config_frame, text="Bonus Book:")
        self.source_book_label.grid(row=2, column=0, sticky=tk.W, pady=5)
        self.bonus_book_var = tk.StringVar()
        bonus_books = sorted([k.title() for k in BOOK_ALIASES.keys()])
        bonus_combo = ttk.Combobox(
            config_frame,
            textvariable=self.bonus_book_var,
            values=bonus_books,
            state='readonly',
            width=20
        )
        bonus_combo.grid(row=2, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        if bonus_books:
            bonus_combo.current(0)

        # Stake
        ttk.Label(config_frame, text="Stake ($):").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.stake_var = tk.StringVar(value="250")
        stake_entry = ttk.Entry(config_frame, textvariable=self.stake_var, width=15)
        stake_entry.grid(row=3, column=1, sticky=tk.W, padx=(10, 0), pady=5)

        # Threshold (label changes based on mode)
        self.threshold_label = ttk.Label(config_frame, text="Min Efficiency (%):")
        self.threshold_label.grid(row=4, column=0, sticky=tk.W, pady=5)
        self.min_eff_var = tk.StringVar(value="0")
        eff_entry = ttk.Entry(config_frame, textvariable=self.min_eff_var, width=15)
        eff_entry.grid(row=4, column=1, sticky=tk.W, padx=(10, 0), pady=5)

        # Warning label
        warning_label = ttk.Label(
            config_frame,
            text="⚠ Each sport takes ~30 seconds to fetch. Fewer selections = faster results.",
            foreground="orange",
            font=('Arial', 8)
        )
        warning_label.grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=(10, 0))

    def on_mode_change(self):
        """Update labels when mode radio button changes"""
        if self.mode_var.get() == "bonus":
            self.source_book_label.config(text="Bonus Book:")
            self.threshold_label.config(text="Min Efficiency (%):")
        else:
            self.source_book_label.config(text="Qualifying Book:")
            self.threshold_label.config(text="Max Loss (%):")
    
    def setup_sports_frame(self, parent):
        """Setup sports selection frame"""
        sports_frame = ttk.LabelFrame(parent, text="Sports", padding="10")
        sports_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Map display names to internal keys
        self.sport_map = {
            "NBA": "nba",
            "NCAAB": "ncaab",
            "NCAAF": "ncaaf",
            "Euro Basketball": "eurobasketball",
            "NFL": "nfl",
            "MLB": "mlb",
            "NHL": "nhl"
        }
        
        # Get configured sports (default to all if not specified)
        configured_sports = self.config.get('sports', list(self.sport_map.keys()))
        
        self.sport_vars = {}
        col = 0
        for sport_display in self.sport_map.keys():
            # Check if this sport is in the configured list
            is_selected = sport_display in configured_sports
            var = tk.BooleanVar(value=is_selected)
            self.sport_vars[sport_display] = var
            cb = ttk.Checkbutton(sports_frame, text=sport_display, variable=var)
            cb.grid(row=0, column=col, padx=10, pady=5, sticky=tk.W)
            col += 1
    
    def setup_books_frame(self, parent):
        """Setup books selection frame"""
        books_frame = ttk.LabelFrame(parent, text="Hedge Books", padding="10")
        books_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Create a scrollable frame for books
        canvas = tk.Canvas(books_frame, height=100)
        scrollbar = ttk.Scrollbar(books_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Book checkboxes
        self.book_vars = {}
        allowed_books = self.config.get('allowed_books', [])
        
        row = 0
        col = 0
        for book in sorted(BOOK_ALIASES.keys()):
            var = tk.BooleanVar(value=(book in allowed_books))
            self.book_vars[book] = var
            cb = ttk.Checkbutton(
                scrollable_frame,
                text=book.title(),
                variable=var
            )
            cb.grid(row=row, column=col, padx=10, pady=2, sticky=tk.W)
            col += 1
            if col > 3:  # 4 columns
                col = 0
                row += 1
        
        canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        books_frame.columnconfigure(0, weight=1)
        
        # Select/Deselect All buttons
        button_frame = ttk.Frame(books_frame)
        button_frame.grid(row=1, column=0, columnspan=2, pady=(10, 0))
        
        ttk.Button(
            button_frame,
            text="Select All",
            command=self.select_all_books
        ).grid(row=0, column=0, padx=5)
        
        ttk.Button(
            button_frame,
            text="Deselect All",
            command=self.deselect_all_books
        ).grid(row=0, column=1, padx=5)
    
    def setup_manual_frame(self, parent):
        """Setup manual hedge calculator frame"""
        manual_frame = ttk.LabelFrame(parent, text="Manual Calculator", padding="10")
        manual_frame.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        # Inputs row
        inputs_frame = ttk.Frame(manual_frame)
        inputs_frame.grid(row=0, column=0, sticky=tk.W)

        ttk.Label(inputs_frame, text="Stake ($):").grid(row=0, column=0, padx=(0, 4))
        self.manual_stake_var = tk.StringVar(value="100")
        ttk.Entry(inputs_frame, textvariable=self.manual_stake_var, width=8).grid(row=0, column=1, padx=(0, 14))

        ttk.Label(inputs_frame, text="Your odds:").grid(row=0, column=2, padx=(0, 4))
        self.manual_odds_a_var = tk.StringVar(value="+200")
        ttk.Entry(inputs_frame, textvariable=self.manual_odds_a_var, width=8).grid(row=0, column=3, padx=(0, 14))

        ttk.Label(inputs_frame, text="Hedge odds:").grid(row=0, column=4, padx=(0, 4))
        self.manual_odds_b_var = tk.StringVar(value="-250")
        ttk.Entry(inputs_frame, textvariable=self.manual_odds_b_var, width=8).grid(row=0, column=5, padx=(0, 14))

        ttk.Button(inputs_frame, text="Calculate", command=self.run_manual_calc).grid(row=0, column=6)

        # Results labels
        self.manual_bonus_label = ttk.Label(manual_frame, text="", font=('Courier', 9))
        self.manual_bonus_label.grid(row=1, column=0, sticky=tk.W, pady=(6, 0))

        self.manual_qual_label = ttk.Label(manual_frame, text="", font=('Courier', 9))
        self.manual_qual_label.grid(row=2, column=0, sticky=tk.W)

    def run_manual_calc(self):
        """Compute and display hedge results from manually entered odds"""
        try:
            stake = float(self.manual_stake_var.get())
            odds_a = float(self.manual_odds_a_var.get())
            odds_b = float(self.manual_odds_b_var.get())
        except ValueError:
            messagebox.showerror("Error", "Stake and odds must be numbers (e.g. 100, +200, -110)")
            return

        bonus_hedge, bonus_profit, bonus_eff = calculate_hedge(stake, odds_a, odds_b)
        qual_hedge, qual_loss, qual_loss_pct = calculate_qualifying_hedge(stake, odds_a, odds_b)

        self.manual_bonus_label.config(
            text=f"Bonus:      Hedge ${bonus_hedge:.2f}  |  Profit ${bonus_profit:.2f}  |  Efficiency {bonus_eff*100:.2f}%"
        )
        qlabel = "Profit" if qual_loss < 0 else "Loss"
        self.manual_qual_label.config(
            text=f"Qualifying: Hedge ${qual_hedge:.2f}  |  {qlabel} ${abs(qual_loss):.2f}  |  Loss {qual_loss_pct*100:.2f}%"
        )

    def setup_control_frame(self, parent):
        """Setup control buttons frame"""
        control_frame = ttk.Frame(parent)
        control_frame.grid(row=4, column=0, pady=(0, 10))
        
        # Find Hedges Button
        self.find_button = ttk.Button(
            control_frame,
            text="Find Hedges",
            command=self.start_search,
            width=20
        )
        self.find_button.grid(row=0, column=0, padx=5)
        
        # Stop Button
        self.stop_button = ttk.Button(
            control_frame,
            text="Stop",
            command=self.stop_search,
            state='disabled',
            width=20
        )
        self.stop_button.grid(row=0, column=1, padx=5)
        
        # Save Config Button
        ttk.Button(
            control_frame,
            text="Save Config",
            command=self.save_config_ui,
            width=20
        ).grid(row=0, column=2, padx=5)
    
    def setup_results_frame(self, parent):
        """Setup results display frame"""
        results_frame = ttk.LabelFrame(parent, text="Results", padding="10")
        results_frame.grid(row=6, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)
        
        # Results text area with scrollbar
        self.results_text = scrolledtext.ScrolledText(
            results_frame,
            wrap=tk.WORD,
            width=80,
            height=35,
            font=('Courier', 9)
        )
        self.results_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure text tags for formatting
        self.results_text.tag_configure("header", font=('Courier', 10, 'bold'))
        self.results_text.tag_configure("event", font=('Courier', 9, 'bold'))
        self.results_text.tag_configure("success", foreground="green")
        self.results_text.tag_configure("error", foreground="red")
    
    def setup_status_bar(self, parent):
        """Setup status bar"""
        status_frame = ttk.Frame(parent)
        status_frame.grid(row=7, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(status_frame, textvariable=self.status_var)
        status_label.grid(row=0, column=0, sticky=tk.W)
        
        self.progress = ttk.Progressbar(
            status_frame,
            mode='indeterminate',
            length=200
        )
        self.progress.grid(row=0, column=1, padx=(20, 0))
    
    def select_all_books(self):
        """Select all books"""
        for var in self.book_vars.values():
            var.set(True)
    
    def deselect_all_books(self):
        """Deselect all books"""
        for var in self.book_vars.values():
            var.set(False)
    
    def save_config_ui(self):
        """Save current configuration"""
        try:
            self.config['api_key'] = self.api_key_var.get()
            self.config['allowed_books'] = [
                book for book, var in self.book_vars.items() if var.get()
            ]
            self.config['sports'] = [
                sport for sport, var in self.sport_vars.items() if var.get()
            ]
            self.save_config()
            messagebox.showinfo("Success", "Configuration saved successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration: {str(e)}")
    
    def validate_inputs(self):
        """Validate user inputs"""
        # Check API key
        if not self.api_key_var.get().strip():
            messagebox.showerror("Error", "Please enter an API key")
            return False
        
        # Check bonus book
        if not self.bonus_book_var.get():
            messagebox.showerror("Error", "Please select a bonus book")
            return False
        
        # Check stake
        try:
            stake = float(self.stake_var.get())
            if stake <= 0:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Error", "Stake must be a positive number")
            return False
        
        # Check threshold (min efficiency or max loss)
        try:
            threshold = float(self.min_eff_var.get())
            if threshold < 0 or threshold > 100:
                raise ValueError()
        except ValueError:
            if self.mode_var.get() == "bonus":
                messagebox.showerror("Error", "Min efficiency must be between 0 and 100")
            else:
                messagebox.showerror("Error", "Max loss must be between 0 and 100")
            return False
        
        # Check selected sports
        selected_sports = [
            sport for sport, var in self.sport_vars.items() if var.get()
        ]
        if not selected_sports:
            messagebox.showerror("Error", "Please select at least one sport")
            return False
        
        # Check selected books
        selected_books = [
            book for book, var in self.book_vars.items() if var.get()
        ]
        if not selected_books:
            messagebox.showerror("Error", "Please select at least one hedge book")
            return False
        
        return True
    
    def start_search(self):
        """Start the hedge search in a separate thread"""
        self.logger.debug("\n[GUI] start_search called")
        
        try:
            self.logger.debug("[GUI] About to validate inputs")
            if not self.validate_inputs():
                self.logger.debug("[GUI] Validation failed")
                return
            self.logger.debug("[GUI] Validation passed")
        except Exception as e:
            self.logger.debug(f"[GUI] Exception during validation: {e}")
            self.logger.debug(f"[GUI] Traceback: {traceback.format_exc()}")
            messagebox.showerror("Validation Error", f"Error during validation: {str(e)}")
            return
        
        if self.is_searching:
            self.logger.debug("[GUI] Already searching, returning")
            return
        
        try:
            self.logger.debug("[GUI] Setting up search state")
            self.is_searching = True
            self.find_button.config(state='disabled')
            self.stop_button.config(state='normal')
            self.progress.start()
            self.status_var.set("Searching for hedge opportunities...")
            
            # Clear results
            self.results_text.delete(1.0, tk.END)
            
            self.logger.debug("[GUI] About to start thread")
            # Start search thread
            self.search_thread = threading.Thread(target=self.run_search, daemon=True)
            self.search_thread.start()
            self.logger.debug("[GUI] Thread started successfully")
            
        except Exception as e:
            self.logger.debug(f"[GUI] Exception in start_search: {e}")
            self.logger.debug(f"[GUI] Traceback: {traceback.format_exc()}")
            messagebox.showerror("Start Error", f"Failed to start search: {str(e)}")
            self.search_complete()
    
    def stop_search(self):
        """Stop the search (note: this is a soft stop, thread will complete)"""
        self.is_searching = False
        self.status_var.set("Stopping search...")
        self.logger.debug("[GUI] User requested search stop")
    
    def run_search(self):
        """Run the hedge search (runs in separate thread)"""
        self.logger.debug("\n[GUI] run_search thread started")
        
        try:
            # Get inputs with debugging
            self.logger.debug("[GUI] Getting API key")
            api_key = self.api_key_var.get().strip()
            self.logger.debug(f"[GUI] API key length: {len(api_key)}")
            
            self.logger.debug("[GUI] Getting bonus book")
            bonus_book_display = self.bonus_book_var.get()
            self.logger.debug(f"[GUI] bonus_book_display = '{bonus_book_display}'")
            
            # Make sure we handle the case properly
            bonus_book_key = bonus_book_display.lower().strip()
            self.logger.debug(f"[GUI] Looking up '{bonus_book_key}' in BOOK_ALIASES")
            self.logger.debug(f"[GUI] Available keys: {list(BOOK_ALIASES.keys())}")
            
            if bonus_book_key not in BOOK_ALIASES:
                raise ValueError(f"Invalid bonus book: '{bonus_book_display}'. Available: {list(BOOK_ALIASES.keys())}")
            
            bonus_book = BOOK_ALIASES[bonus_book_key]
            self.logger.debug(f"[GUI] Resolved to: {bonus_book}")
            
            self.logger.debug("[GUI] Getting stake")
            stake = float(self.stake_var.get())
            self.logger.debug(f"[GUI] stake = {stake}")
            
            self.logger.debug("[GUI] Getting mode and threshold")
            mode = self.mode_var.get()
            threshold = float(self.min_eff_var.get()) / 100.0
            self.logger.debug(f"[GUI] mode = {mode}, threshold = {threshold}")
            
            # Get selected sports
            self.logger.debug("[GUI] Getting selected sports")
            selected_sports = [
                self.sport_map[sport] for sport, var in self.sport_vars.items() if var.get()
            ]
            self.logger.debug(f"[GUI] selected_sports = {selected_sports}")
            
            # Get selected books
            self.logger.debug("[GUI] Getting selected books")
            selected_books = [
                book for book, var in self.book_vars.items() if var.get()
            ]
            self.logger.debug(f"[GUI] selected_books = {selected_books}")
            
            self.logger.debug("[GUI] Parsing books")
            hedge_books = parse_books(','.join(selected_books))
            self.logger.debug(f"[GUI] hedge_books = {hedge_books}")
            
            # All books (bonus + hedge)
            all_books = hedge_books | {bonus_book}
            regions = get_regions_needed(all_books)
            
            self.logger.debug(f"[GUI] all_books = {all_books}")
            self.logger.debug(f"[GUI] regions = {regions}")
            
            # Calculate total API calls for better progress
            total_calls = len(selected_sports) * len(regions)
            
            # Update status with initial info
            self.root.after(0, lambda: self.status_var.set(
                f"Fetching odds for {len(selected_sports)} sports ({total_calls} API calls)..."
            ))
            
            self.logger.debug("[GUI] About to call collect_all_odds")
            
            # Progress callback function
            def update_progress(sport_name, current, total):
                if self.is_searching:
                    pct = int((current / total) * 100)
                    msg = f"Fetching {sport_name} odds... ({current}/{total} - {pct}%)"
                    self.root.after(0, lambda m=msg: self.status_var.set(m))
            
            # Collect odds with progress updates
            try:
                odds_rows = collect_all_odds(
                    api_key, 
                    selected_sports, 
                    regions, 
                    all_books,
                    progress_callback=update_progress
                )
                self.logger.debug(f"[GUI] Got {len(odds_rows)} odds rows")
            except Exception as e:
                self.logger.debug(f"[GUI] Exception in collect_all_odds: {e}")
                self.logger.debug(f"[GUI] Traceback: {traceback.format_exc()}")
                error_msg = f"Failed to fetch odds: {str(e)}\n\nCheck debug.log for details."
                self.root.after(0, lambda: self.display_error(error_msg))
                return
            
            if not self.is_searching:
                self.logger.debug("[GUI] Search cancelled by user")
                self.root.after(0, self.search_complete)
                return
            
            # Update status
            self.root.after(0, lambda: self.status_var.set(
                f"Analyzing {len(odds_rows)} odds entries..."
            ))
            
            if len(odds_rows) == 0:
                self.logger.debug("[GUI] No odds rows retrieved")
                error_msg = "No odds data retrieved. This could mean:\n"
                error_msg += "• No games available for selected sports\n"
                error_msg += "• Invalid API key\n"
                error_msg += "• Selected books not available in your region\n"
                error_msg += "\nCheck debug.log for detailed diagnostics."
                self.root.after(0, lambda: self.display_error(error_msg))
                return
            
            self.logger.debug("[GUI] Finding opportunities")

            # Find opportunities
            if mode == "bonus":
                opportunities = find_all_opportunities(odds_rows, bonus_book, stake, threshold)
            else:
                opportunities = find_qualifying_opportunities(odds_rows, bonus_book, stake, threshold)

            self.logger.debug(f"[GUI] Found {len(opportunities)} opportunities")

            if not self.is_searching:
                self.logger.debug("[GUI] Search cancelled by user")
                self.root.after(0, self.search_complete)
                return

            # Display results
            if mode == "bonus":
                self.root.after(0, lambda: self.display_results(
                    opportunities, stake, bonus_book, len(odds_rows)
                ))
            else:
                self.root.after(0, lambda: self.display_qualifying_results(
                    opportunities, stake, len(odds_rows)
                ))
            
        except Exception as e:
            self.logger.debug(f"[GUI] Exception in run_search: {type(e).__name__}: {e}")
            self.logger.debug(f"[GUI] Traceback: {traceback.format_exc()}")
            error_msg = f"{type(e).__name__}: {str(e)}\n\nCheck debug.log for full traceback."
            self.root.after(0, lambda: self.display_error(error_msg))
        finally:
            self.logger.debug("[GUI] run_search finally block")
            self.root.after(0, self.search_complete)
    
    def display_results(self, opportunities, stake, bonus_book, odds_count):
        """Display search results in the text area"""
        self.logger.debug(f"[GUI] Displaying results: {len(opportunities)} opportunities")
        
        self.results_text.delete(1.0, tk.END)
        
        # Header
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.results_text.insert(tk.END, f"Search completed at {timestamp}\n", "header")
        self.results_text.insert(tk.END, f"Analyzed {odds_count} odds entries\n\n", "header")
        
        if not opportunities:
            self.results_text.insert(
                tk.END,
                "No valid bonus hedge opportunities found.\n",
                "error"
            )
            self.results_text.insert(
                tk.END,
                "Try adjusting the minimum efficiency threshold or checking more sports.\n"
            )
            self.status_var.set("Search complete - No opportunities found")
            return
        
        # Best opportunity
        best = select_best_opportunity(opportunities)
        
        self.results_text.insert(tk.END, "=" * 80 + "\n", "header")
        self.results_text.insert(tk.END, "BEST BONUS HEDGE OPPORTUNITY\n", "header")
        self.results_text.insert(tk.END, "=" * 80 + "\n\n", "header")
        
        self.results_text.insert(tk.END, f"Event: {best.event}\n\n", "event")
        
        self.results_text.insert(
            tk.END,
            f"Bonus Bet ({best.bonus_book}):\n"
        )
        self.results_text.insert(
            tk.END,
            f"  {best.selection} @ {best.bonus_odds:+}\n"
        )
        self.results_text.insert(tk.END, f"  Stake: ${stake:.2f}\n\n")
        
        self.results_text.insert(
            tk.END,
            f"Hedge Bet ({best.hedge_book}):\n"
        )
        self.results_text.insert(
            tk.END,
            f"  {best.opposite} @ {best.hedge_odds:+}\n"
        )
        self.results_text.insert(tk.END, f"  Stake: ${best.hedge_stake:.2f}\n\n")
        
        self.results_text.insert(tk.END, "RESULT:\n", "success")
        self.results_text.insert(
            tk.END,
            f"  Locked Profit: ${best.profit:.2f}\n",
            "success"
        )
        self.results_text.insert(
            tk.END,
            f"  Efficiency: {best.efficiency*100:.2f}%\n",
            "success"
        )
        
        self.results_text.insert(tk.END, "\n" + "=" * 80 + "\n\n")
        
        # All opportunities
        if len(opportunities) > 1:
            self.results_text.insert(
                tk.END,
                f"\nAll {len(opportunities)} Opportunities:\n",
                "header"
            )
            self.results_text.insert(tk.END, "-" * 80 + "\n")
            
            # Sort by efficiency
            sorted_opps = sorted(opportunities, key=lambda x: x.efficiency, reverse=True)
            
            for i, opp in enumerate(sorted_opps[:20], 1):  # Show top 20
                self.results_text.insert(tk.END, f"\n#{i}. {opp.event}\n")
                self.results_text.insert(
                    tk.END,
                    f"   {opp.bonus_book}: {opp.selection} @ {opp.bonus_odds:+} | "
                    f"{opp.hedge_book}: {opp.opposite} @ {opp.hedge_odds:+}\n"
                )
                self.results_text.insert(
                    tk.END,
                    f"   Hedge: ${opp.hedge_stake:.2f} | "
                    f"Profit: ${opp.profit:.2f} | "
                    f"Efficiency: {opp.efficiency*100:.2f}%\n"
                )
            
            if len(opportunities) > 20:
                self.results_text.insert(
                    tk.END,
                    f"\n... and {len(opportunities) - 20} more opportunities\n"
                )
        
        self.status_var.set(
            f"Search complete - Found {len(opportunities)} opportunities"
        )
        self.logger.debug(f"[GUI] Results displayed successfully")

    def display_qualifying_results(self, opportunities, stake, odds_count):
        """Display qualifying hedge search results"""
        self.logger.debug(f"[GUI] Displaying qualifying results: {len(opportunities)} opportunities")

        self.results_text.delete(1.0, tk.END)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.results_text.insert(tk.END, f"Search completed at {timestamp}\n", "header")
        self.results_text.insert(tk.END, f"Analyzed {odds_count} odds entries\n\n", "header")

        if not opportunities:
            self.results_text.insert(tk.END, "No qualifying hedge opportunities found.\n", "error")
            self.results_text.insert(
                tk.END,
                "Try increasing Max Loss % or checking more sports/books.\n"
            )
            self.status_var.set("Search complete - No opportunities found")
            return

        best = select_best_qualifying_opportunity(opportunities)

        self.results_text.insert(tk.END, "=" * 80 + "\n", "header")
        self.results_text.insert(tk.END, "BEST QUALIFYING BET HEDGE\n", "header")
        self.results_text.insert(tk.END, "=" * 80 + "\n\n", "header")

        self.results_text.insert(tk.END, f"Event: {best.event}\n\n", "event")

        self.results_text.insert(tk.END, f"Qualifying Bet ({best.qual_book}):\n")
        self.results_text.insert(tk.END, f"  {best.selection} @ {best.qual_odds:+}\n")
        self.results_text.insert(tk.END, f"  Stake: ${stake:.2f}\n\n")

        self.results_text.insert(tk.END, f"Hedge Bet ({best.hedge_book}):\n")
        self.results_text.insert(tk.END, f"  {best.opposite} @ {best.hedge_odds:+}\n")
        self.results_text.insert(tk.END, f"  Stake: ${best.hedge_stake:.2f}\n\n")

        result_label = "Guaranteed Profit" if best.loss < 0 else "Guaranteed Loss"
        result_color = "success" if best.loss < 0 else "error"
        self.results_text.insert(tk.END, "RESULT:\n", "header")
        self.results_text.insert(tk.END, f"  {result_label}: ${abs(best.loss):.2f}\n", result_color)
        self.results_text.insert(tk.END, f"  Loss: {best.loss_pct*100:.2f}% of stake\n", result_color)

        self.results_text.insert(tk.END, "\n" + "=" * 80 + "\n\n")

        if len(opportunities) > 1:
            self.results_text.insert(
                tk.END,
                f"\nAll {len(opportunities)} Opportunities (sorted by loss):\n",
                "header"
            )
            self.results_text.insert(tk.END, "-" * 80 + "\n")

            sorted_opps = sorted(opportunities, key=lambda x: x.loss_pct)

            for i, opp in enumerate(sorted_opps[:20], 1):
                label = "Profit" if opp.loss < 0 else "Loss"
                self.results_text.insert(tk.END, f"\n#{i}. {opp.event}\n")
                self.results_text.insert(
                    tk.END,
                    f"   {opp.qual_book}: {opp.selection} @ {opp.qual_odds:+} | "
                    f"{opp.hedge_book}: {opp.opposite} @ {opp.hedge_odds:+}\n"
                )
                self.results_text.insert(
                    tk.END,
                    f"   Hedge: ${opp.hedge_stake:.2f} | "
                    f"{label}: ${abs(opp.loss):.2f} | "
                    f"Loss: {opp.loss_pct*100:.2f}%\n"
                )

            if len(opportunities) > 20:
                self.results_text.insert(
                    tk.END,
                    f"\n... and {len(opportunities) - 20} more opportunities\n"
                )

        self.status_var.set(f"Search complete - Found {len(opportunities)} qualifying hedges")
        self.logger.debug("[GUI] Qualifying results displayed successfully")

    def display_error(self, error_msg):
        """Display error message"""
        self.logger.debug(f"[GUI] Displaying error: {error_msg}")
        
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, "ERROR\n", "error")
        self.results_text.insert(tk.END, f"\n{error_msg}\n")
        self.status_var.set("Search failed")
        messagebox.showerror("Search Error", error_msg)
    
    def search_complete(self):
        """Reset UI after search completes"""
        self.logger.debug("[GUI] Search complete, resetting UI")
        self.is_searching = False
        self.find_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.progress.stop()


def main():
    root = tk.Tk()
    app = HedgeFinderGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()