import os
import ujson
import time
from utils import wait_for_press
from components.Switch import Button
from machine import Pin
from menu import Menu

class History:
    def __init__(self, display, switch, rot, history_dir="history"):
        self.display = display
        self.switch = switch
        self.rot = rot
        self.next_page_loader = Button(9, Pin.IN, Pin.PULL_UP)
        self.history_dir = history_dir
        
        self.entries_per_page = 5
        self.entries = self.load_entries()
        self.total_pages = self.get_page_count()
        self.page = 0

    def load_entries(self):
        try:
            files = sorted(os.listdir(self.history_dir), reverse=True)
            
            if len(files) < 1:
                return []
            
            return files
        except Exception as e:
            print(f"Error loading history: {e}")
            return []
    
    def show_entry(self, filename):
        # unwanted fields in the json, not shown in the history entry
        unwanted_fields = ("id", "timestamp", "type")
        
        try:
            with open(f"{self.history_dir}/{filename}") as f:
                data = ujson.load(f)
            
            self.display.fill(0)
            
            # handle the timestamp and set it as a heading
            timestamp = data["timestamp"]
            formatted_time = self.format_timestamp(timestamp) if timestamp else "Unknown Time"
            self.display.text(formatted_time, 0, 0, 1)
            
            y = 10 # start the values at y=10
            for key, value in data.items():
                if key in unwanted_fields:
                    continue # dont display unwanted fields
                parsed_key = key.replace("_", " ").upper()
                self.display.text(f"{parsed_key}: {value}", 0, y, 1)
                y += 10
                if y > 54:  # stop overflow
                    break
                
            self.display.show()
            
            wait_for_press(self.switch)

        except Exception as e:
            print(f"Error reading {filename}: {e}")
            self.display.fill(0)
            self.display.text("Read error", 0, 20, 1)
            self.display.show()
            
    def get_page_count(self):
        if not self.entries:
            return 0
        
        return (len(self.entries) + self.entries_per_page - 1) // self.entries_per_page
    
    def format_timestamp(self, timestamp):
        """helper to turn a timestamp into a readable date"""
        
        local_time = time.localtime(timestamp)
        
        # grab the correct date parameters
        day = local_time[2]
        month = local_time[1]
        year = local_time[0]
        hour = local_time[3]
        minute = local_time[4]
        
        formatted_time = f"{day}.{month}.{year} {hour:02d}:{minute:02d}"
        
        return formatted_time
        
    def run(self):
        self.entries = self.load_entries()
        
        self.display.centered_texts([
            "Show history",
            "5 Scans / page",
            "SW0 changes page", " ",
            "Press to show",
        ])
        
        wait_for_press(self.switch)
                
        if not self.entries:
            self.display.centered_texts([
                "History",
                "No history yet",
                " ",
                "Press to exit",
            ])
            
            wait_for_press(self.switch)
                
            return
        
        self.page = 0
        while True:
            # calc paging values
            start = self.page * self.entries_per_page
            end = start + self.entries_per_page
            page_entries = self.entries[start:end]
            
            options = [f"Measurement {len(self.entries) - (start + i)}" for i in range(len(page_entries))]
            actions = [lambda i = i: self.show_entry(page_entries[i]) for i in range(len(page_entries))]
            
            self.display.heading("History", f"{self.page + 1}/{self.total_pages}", y = 0, clear = True)
            menu = Menu(
                display = self.display,
                options = options,
                actions = actions,
                text_size = 10,
                start_y = 12,
            )
            menu.show(clear = False)
            
            while True:
                if self.rot.fifo.has_data():
                    delta = self.rot.fifo.get()
                    menu.move_pointer(delta)
                    menu.show()
                    
                if self.switch.single_press():
                    menu.actions[menu.pointer]()
                    return # exit to main menu

                if self.next_page_loader.single_press():
                    self.page = (self.page + 1) % self.total_pages
                    break