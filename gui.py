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

# Import from main.py
from main import (
    BOOK_ALIASES,
    SPORT_KEYS,
    parse_books,
    get_regions_needed,
    collect_all_odds,
    find_all_opportunities,
    select_best_opportunity,
    Logger,
)


class HedgeFinderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Bonus Hedge Finder")
        self.root.geometry("900x900")
        
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
        main_frame.rowconfigure(5, weight=1)
        
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
        
        # Results Frame
        self.setup_results_frame(main_frame)
        
        # Status Bar
        self.setup_status_bar(main_frame)
    
    def setup_config_frame(self, parent):
        """Setup configuration input frame"""
        config_frame = ttk.LabelFrame(parent, text="Configuration", padding="10")
        config_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        config_frame.columnconfigure(1, weight=1)
        
        # API Key
        ttk.Label(config_frame, text="API Key:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.api_key_var = tk.StringVar(value=self.config.get('api_key', ''))
        api_entry = ttk.Entry(config_frame, textvariable=self.api_key_var, width=50, show='*')
        api_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=5)
        
        # Bonus Book
        ttk.Label(config_frame, text="Bonus Book:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.bonus_book_var = tk.StringVar()
        bonus_books = sorted([k.title() for k in BOOK_ALIASES.keys()])
        bonus_combo = ttk.Combobox(
            config_frame,
            textvariable=self.bonus_book_var,
            values=bonus_books,
            state='readonly',
            width=20
        )
        bonus_combo.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        if bonus_books:
            bonus_combo.current(0)
        
        # Stake
        ttk.Label(config_frame, text="Stake ($):").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.stake_var = tk.StringVar(value="250")
        stake_entry = ttk.Entry(config_frame, textvariable=self.stake_var, width=15)
        stake_entry.grid(row=2, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        
        # Minimum Efficiency
        ttk.Label(config_frame, text="Min Efficiency (%):").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.min_eff_var = tk.StringVar(value="0")
        eff_entry = ttk.Entry(config_frame, textvariable=self.min_eff_var, width=15)
        eff_entry.grid(row=3, column=1, sticky=tk.W, padx=(10, 0), pady=5)
    
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
        results_frame.grid(row=5, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
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
        status_frame.grid(row=6, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        
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
        
        # Check min efficiency
        try:
            min_eff = float(self.min_eff_var.get())
            if min_eff < 0 or min_eff > 100:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Error", "Min efficiency must be between 0 and 100")
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
        if not self.validate_inputs():
            return
        
        if self.is_searching:
            return
        
        self.is_searching = True
        self.find_button.config(state='disabled')
        self.stop_button.config(state='normal')
        self.progress.start()
        self.status_var.set("Searching for hedge opportunities...")
        
        # Clear results
        self.results_text.delete(1.0, tk.END)
        
        # Start search thread
        self.search_thread = threading.Thread(target=self.run_search, daemon=True)
        self.search_thread.start()
    
    def stop_search(self):
        """Stop the search (note: this is a soft stop, thread will complete)"""
        self.is_searching = False
        self.status_var.set("Stopping search...")
    
    def run_search(self):
        """Run the hedge search (runs in separate thread)"""
        try:
            # Get inputs
            api_key = self.api_key_var.get().strip()
            bonus_book_display = self.bonus_book_var.get()
            bonus_book = BOOK_ALIASES[bonus_book_display.lower()]
            stake = float(self.stake_var.get())
            min_eff = float(self.min_eff_var.get()) / 100.0
            
            # Get selected sports
            selected_sports = [
                self.sport_map[sport] for sport, var in self.sport_vars.items() if var.get()
            ]
            
            # Get selected books
            selected_books = [
                book for book, var in self.book_vars.items() if var.get()
            ]
            hedge_books = parse_books(','.join(selected_books))
            
            # All books (bonus + hedge)
            all_books = hedge_books | {bonus_book}
            regions = get_regions_needed(all_books)
            
            # Update status
            self.root.after(0, lambda: self.status_var.set(
                f"Fetching odds for {len(selected_sports)} sports..."
            ))
            
            # Collect odds
            odds_rows = collect_all_odds(api_key, selected_sports, regions, all_books)
            
            if not self.is_searching:
                self.root.after(0, self.search_complete)
                return
            
            # Update status
            self.root.after(0, lambda: self.status_var.set(
                f"Analyzing {len(odds_rows)} odds entries..."
            ))
            
            # Find opportunities
            opportunities = find_all_opportunities(
                odds_rows,
                bonus_book,
                stake,
                min_eff
            )
            
            if not self.is_searching:
                self.root.after(0, self.search_complete)
                return
            
            # Display results
            self.root.after(0, lambda: self.display_results(
                opportunities, stake, bonus_book, len(odds_rows)
            ))
            
        except Exception as e:
            self.root.after(0, lambda: self.display_error(str(e)))
        finally:
            self.root.after(0, self.search_complete)
    
    def display_results(self, opportunities, stake, bonus_book, odds_count):
        """Display search results in the text area"""
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
    
    def display_error(self, error_msg):
        """Display error message"""
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, "ERROR\n", "error")
        self.results_text.insert(tk.END, f"\n{error_msg}\n")
        self.status_var.set("Search failed")
        messagebox.showerror("Search Error", error_msg)
    
    def search_complete(self):
        """Reset UI after search completes"""
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