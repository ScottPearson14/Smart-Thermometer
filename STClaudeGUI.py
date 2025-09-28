import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.animation import FuncAnimation
# Serial handling removed from GUI (managed externally). The GUI exposes
# parse_serial_data() so an external serial manager can feed lines to it.
import threading
import time
import json
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from collections import deque
from datetime import datetime, timedelta
import numpy as np

class ThermometerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Smart Thermometer Control System")
        self.root.geometry("1200x800")
        self.root.configure(bg='#f0f0f0')
        
        # Communication/runtime variables
        # Serial/live-connection is handled externally; GUI only displays data.
        self.running = False
        
        # Temperature data storage (300 seconds of data)
        self.temp1_data = deque(maxlen=300)
        self.temp2_data = deque(maxlen=300)
        self.time_data = deque(maxlen=300)
        
        # Current temperature values
        self.current_temp1 = 0.0
        self.current_temp2 = 0.0
        self.sensor1_connected = True
        self.sensor2_connected = True
        # Hardware-reported sensor enabled state (from ESP32 buttons)
        self.sensor1_hw_enabled = False
        self.sensor2_hw_enabled = False
        self.third_box_on = True
        
        # Display settings
        self.temp_unit = tk.StringVar(value="C")  # C or F
        self.sensor1_display = tk.BooleanVar(value=False)
        self.sensor2_display = tk.BooleanVar(value=False)
        
        # Alert settings
        self.max_temp = tk.DoubleVar(value=30.0)
        self.min_temp = tk.DoubleVar(value=18.0)
        self.alert_email = tk.StringVar(value="")
        self.alert_phone = tk.StringVar(value="")
        
        # Email settings (for alerts)
        #TODO: Fill in with your email server details
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.email_username = ""
        self.email_password = ""
        
        self.setup_ui()
        self.setup_graph()
        self.start_data_simulation()  # For testing without hardware
        
    def setup_ui(self):
        # Main container
        main_frame = tk.Frame(self.root, bg='#f0f0f0')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
    # Connection frame removed (serial handled externally)
        
        # Temperature display frame
        self.setup_temperature_frame(main_frame)
        
        # Control frame
        self.setup_control_frame(main_frame)
        
        # Alert settings frame
        self.setup_alert_frame(main_frame)
        
        # Graph frame
        self.setup_graph_frame(main_frame)
        
    # Connection UI and serial-control removed. Use parse_serial_data(data)
    # from an external serial manager to feed hardware messages into the GUI.
        
    def setup_temperature_frame(self, parent):
        temp_frame = tk.LabelFrame(parent, text="Real-Time Temperature Display", 
                                  font=('Arial', 12, 'bold'), bg='#f0f0f0', fg='#333')
        temp_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Unit selection
        unit_frame = tk.Frame(temp_frame, bg='#f0f0f0')
        unit_frame.pack(pady=5)
        tk.Label(unit_frame, text="Unit:", bg='#f0f0f0', font=('Arial', 10)).pack(side=tk.LEFT)
        tk.Radiobutton(unit_frame, text="°C", variable=self.temp_unit, value="C", 
                      bg='#f0f0f0', font=('Arial', 10)).pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(unit_frame, text="°F", variable=self.temp_unit, value="F", 
                      bg='#f0f0f0', font=('Arial', 10)).pack(side=tk.LEFT, padx=5)
        
        # Temperature displays
        displays_frame = tk.Frame(temp_frame, bg='#f0f0f0')
        displays_frame.pack(expand=True, fill=tk.BOTH, pady=10)
        
        # Sensor 1 display
        sensor1_frame = tk.Frame(displays_frame, bg='white', relief=tk.RAISED, bd=2)
        sensor1_frame.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=(0, 5))
        
        tk.Label(sensor1_frame, text="Sensor 1", font=('Arial', 16, 'bold'), 
                bg='white', fg='#333').pack(pady=5)
        self.temp1_label = tk.Label(sensor1_frame, text="--°C", 
                                   font=('Arial', 36, 'bold'), bg='white', fg='#2196F3')
        self.temp1_label.pack(pady=10)
        self.status1_label = tk.Label(sensor1_frame, text="Connected", 
                                     font=('Arial', 12), bg='white', fg='green')
        self.status1_label.pack(pady=5)
        
        # Sensor 2 display
        sensor2_frame = tk.Frame(displays_frame, bg='white', relief=tk.RAISED, bd=2)
        sensor2_frame.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH, padx=(5, 0))
        
        tk.Label(sensor2_frame, text="Sensor 2", font=('Arial', 16, 'bold'), 
                bg='white', fg='#333').pack(pady=5)
        self.temp2_label = tk.Label(sensor2_frame, text="--°C", 
                                   font=('Arial', 36, 'bold'), bg='white', fg='#FF9800')
        self.temp2_label.pack(pady=10)
        self.status2_label = tk.Label(sensor2_frame, text="Connected", 
                                     font=('Arial', 12), bg='white', fg='green')
        self.status2_label.pack(pady=5)
        
    def setup_control_frame(self, parent):
        control_frame = tk.LabelFrame(parent, text="Sensor Control", 
                                     font=('Arial', 12, 'bold'), bg='#f0f0f0', fg='#333')
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Virtual button controls
        tk.Label(control_frame, text="Virtual Button Control (Remotely control third box display):", 
                bg='#f0f0f0', font=('Arial', 11)).pack(pady=5)
        
        button_frame = tk.Frame(control_frame, bg='#f0f0f0')
        button_frame.pack(pady=5)

        self.sensor1_btn = tk.Button(button_frame, text="Sensor 1 Display: OFF", 
                                   command=self.toggle_sensor1_display,
                                   bg='black', fg='white', font=('Arial', 12), width=20)
        self.sensor1_btn.pack(side=tk.LEFT, padx=10)

        self.sensor2_btn = tk.Button(button_frame, text="Sensor 2 Display: OFF", 
                                   command=self.toggle_sensor2_display,
                                   bg='black', fg='white', font=('Arial', 12), width=20)
        self.sensor2_btn.pack(side=tk.LEFT, padx=10)
        
    def setup_alert_frame(self, parent):
        alert_frame = tk.LabelFrame(parent, text="Temperature Alerts",
                                   font=('Arial', 12, 'bold'), bg='#f0f0f0', fg='#333')
        alert_frame.pack(fill=tk.X, pady=(0, 10))

        # Alert settings
        settings_frame = tk.Frame(alert_frame, bg='#f0f0f0')
        settings_frame.pack(pady=5)

        tk.Label(settings_frame, text="Max Temp:", bg='#f0f0f0').grid(row=0, column=0, padx=5)
        tk.Entry(settings_frame, textvariable=self.max_temp, width=8).grid(row=0, column=1, padx=5)

        tk.Label(settings_frame, text="Min Temp:", bg='#f0f0f0').grid(row=0, column=2, padx=5)
        tk.Entry(settings_frame, textvariable=self.min_temp, width=8).grid(row=0, column=3, padx=5)

        tk.Label(settings_frame, text="Email:", bg='#f0f0f0').grid(row=1, column=0, padx=5, pady=5)
        tk.Entry(settings_frame, textvariable=self.alert_email, width=25).grid(row=1, column=1, columnspan=2, padx=5, pady=5)

        tk.Label(settings_frame, text="Phone:", bg='#f0f0f0').grid(row=1, column=3, padx=5, pady=5)
        tk.Entry(settings_frame, textvariable=self.alert_phone, width=15).grid(row=1, column=4, padx=5, pady=5)

        # Configure email button
        tk.Button(alert_frame, text="Configure Email Settings", command=self.configure_email,
                  bg='black', fg='white', font=('Arial', 10)).pack(pady=5)
        
    def setup_graph_frame(self, parent):
        graph_frame = tk.LabelFrame(parent, text="Temperature History (Past 300 Seconds)", 
                                   font=('Arial', 12, 'bold'), bg='#f0f0f0', fg='#333')
        graph_frame.pack(fill=tk.BOTH, expand=True)
        
        # This will be set up in setup_graph()
        self.graph_frame = graph_frame
        
    def setup_graph(self):
        # Create matplotlib figure
        self.fig, self.ax = plt.subplots(figsize=(12, 4))
        self.fig.patch.set_facecolor('#f0f0f0')
        
        # Initialize empty plots
        self.line1, = self.ax.plot([], [], 'b-', linewidth=2, label='Sensor 1', marker='o', markersize=3)
        self.line2, = self.ax.plot([], [], 'orange', linewidth=2, label='Sensor 2', marker='s', markersize=3)
        
        # Configure axes
        self.ax.set_xlim(300, 0)  # 300 seconds ago to now
        self.ax.set_ylim(10, 50)  # 10°C to 50°C (will convert for °F)
        self.ax.set_xlabel('Seconds Ago')
        self.ax.set_ylabel('Temperature (°C)')
        self.ax.grid(True, alpha=0.3)
        self.ax.legend()
        self.ax.set_title('Temperature History - Chart Recorder Style')
        
        # Embed in tkinter
        # Use FigureCanvasTkAgg and pass the tkinter master (graph_frame)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.graph_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Start animation
        self.anim = FuncAnimation(self.fig, self.update_graph, interval=1000, blit=False)
        
    # Serial helper methods removed. External code should call parse_serial_data(line)
    # to feed incoming hardware messages into this GUI.
    
    def parse_serial_data(self, data):
        """Parse incoming serial data from ESP32"""
        try:
            # Handle display switch messages printed by the Arduino sketch
            # Example: "Display switch: ON" or "Display switch: OFF"
            if data.startswith("Display switch:"):
                try:
                    state = data.split(":", 1)[1].strip()
                    self.third_box_on = (state.upper() == "ON")
                    self.root.after(0, self.update_temperature_display)
                except Exception:
                    pass

            # Handle button press messages from hardware
            # Example: "Button 1 pressed - Sensor 1 toggled"
            elif "Button 1 pressed" in data:
                # Hardware toggled sensor1 enable; reflect in GUI
                self.sensor1_hw_enabled = not self.sensor1_hw_enabled
                # Update virtual button appearance to match hardware state
                if self.sensor1_hw_enabled:
                    self.sensor1_btn.config(text="Sensor 1 Display: ON", bg='#4CAF50', fg='white')
                else:
                    self.sensor1_btn.config(text="Sensor 1 Display: OFF", bg='#f44336', fg='white')

            elif "Button 2 pressed" in data:
                self.sensor2_hw_enabled = not self.sensor2_hw_enabled
                if self.sensor2_hw_enabled:
                    self.sensor2_btn.config(text="Sensor 2 Display: ON", bg='#4CAF50', fg='white')
                else:
                    self.sensor2_btn.config(text="Sensor 2 Display: OFF", bg='#f44336', fg='white')

            # Expected temperature format: "Temp1: 25.50°C, Temp2: 26.75°C"
            elif "Temp1:" in data and "Temp2:" in data:
                parts = data.split(", ")
                temp1_str = parts[0].split(": ")[1].replace("°C", "")
                temp2_str = parts[1].split(": ")[1].replace("°C", "")

                self.current_temp1 = float(temp1_str)
                self.current_temp2 = float(temp2_str)

                # Check for disconnected sensors (ESP32 returns -127 for disconnected)
                self.sensor1_connected = self.current_temp1 > -100
                self.sensor2_connected = self.current_temp2 > -100

                # Update display
                self.root.after(0, self.update_temperature_display)
                
        except Exception as e:
            print(f"Error parsing data: {e}")
    
    def start_data_simulation(self):
        """Simulate temperature data for testing without hardware"""
        def simulate():
            import random
            while True:
                # Simulate temperature readings
                self.current_temp1 = 22 + random.uniform(-2, 8)
                self.current_temp2 = 23 + random.uniform(-1, 7)

                # Randomly simulate disconnections
                self.sensor1_connected = random.random() > 0.05  # 5% chance of disconnection
                self.sensor2_connected = random.random() > 0.05
                self.third_box_on = random.random() > 0.02  # 2% chance of being off

                # Update display
                self.root.after(0, self.update_temperature_display)

                time.sleep(1)
        
        sim_thread = threading.Thread(target=simulate, daemon=True)
        sim_thread.start()
    
    def update_temperature_display(self):
        """Update the temperature display labels"""
        unit = self.temp_unit.get()
        
        # Convert temperatures if needed
        if unit == "F":
            temp1_display = self.celsius_to_fahrenheit(self.current_temp1) if self.sensor1_connected else 0
            temp2_display = self.celsius_to_fahrenheit(self.current_temp2) if self.sensor2_connected else 0
            temp_suffix = "°F"
            self.ax.set_ylabel('Temperature (°F)')
            self.ax.set_ylim(50, 122)  # 10°C to 50°C in Fahrenheit
        else:
            temp1_display = self.current_temp1 if self.sensor1_connected else 0
            temp2_display = self.current_temp2 if self.sensor2_connected else 0
            temp_suffix = "°C"
            self.ax.set_ylabel('Temperature (°C)')
            self.ax.set_ylim(10, 50)
        
        # Update sensor 1
        if not self.third_box_on:
            self.temp1_label.config(text="No Data Available", fg='gray')
            self.status1_label.config(text="Third Box Off", fg='red')
        elif not self.sensor1_connected:
            self.temp1_label.config(text="Sensor Unplugged", fg='red')
            self.status1_label.config(text="Disconnected", fg='red')
        else:
            # Respect hardware sensor enable state
            if not self.sensor1_hw_enabled:
                self.temp1_label.config(text="Sensor 1: OFF", fg='gray')
                self.status1_label.config(text="Disabled (HW)", fg='red')
            else:
                self.temp1_label.config(text=f"{temp1_display:.1f}{temp_suffix}", fg='#2196F3')
                self.status1_label.config(text="Connected", fg='green')
        
        # Update sensor 2
        if not self.third_box_on:
            self.temp2_label.config(text="No Data Available", fg='gray')
            self.status2_label.config(text="Third Box Off", fg='red')
        elif not self.sensor2_connected:
            self.temp2_label.config(text="Sensor Unplugged", fg='red')
            self.status2_label.config(text="Disconnected", fg='red')
        else:
            # Respect hardware sensor enable state
            if not self.sensor2_hw_enabled:
                self.temp2_label.config(text="Sensor 2: OFF", fg='gray')
                self.status2_label.config(text="Disabled (HW)", fg='red')
            else:
                self.temp2_label.config(text=f"{temp2_display:.1f}{temp_suffix}", fg='#FF9800')
                self.status2_label.config(text="Connected", fg='green')
        
        # Store data for graphing
        current_time = datetime.now()
        
        if self.third_box_on and self.sensor1_connected:
            if self.sensor1_hw_enabled:
                self.temp1_data.append(temp1_display)
                self.time_data.append(current_time)
            else:
                self.temp1_data.append(np.nan)
                if len(self.time_data) == 0 or (current_time - self.time_data[-1]).total_seconds() >= 1:
                    self.time_data.append(current_time)
        else:
            self.temp1_data.append(np.nan)  # Missing data
            if len(self.time_data) == 0 or (current_time - self.time_data[-1]).total_seconds() >= 1:
                self.time_data.append(current_time)
        
        if self.third_box_on and self.sensor2_connected:
            if len(self.temp2_data) < len(self.temp1_data):
                if self.sensor2_hw_enabled:
                    self.temp2_data.append(temp2_display)
                else:
                    self.temp2_data.append(np.nan)
        else:
            if len(self.temp2_data) < len(self.temp1_data):
                self.temp2_data.append(np.nan)  # Missing data
        
        # Check for temperature alerts
        self.check_temperature_alerts()
    
    def celsius_to_fahrenheit(self, celsius):
        return celsius * 9/5 + 32
    
    def fahrenheit_to_celsius(self, fahrenheit):
        return (fahrenheit - 32) * 5/9
    
    def update_graph(self, frame):
        """Update the temperature history graph"""
        if len(self.time_data) == 0:
            return self.line1, self.line2
        
        # Calculate seconds ago for x-axis
        current_time = datetime.now()
        seconds_ago = [(current_time - t).total_seconds() for t in self.time_data]
        
        # Reverse for chart recorder style (newest on right)
        seconds_ago = [300 - s for s in seconds_ago if s <= 300]
        temp1_plot = list(self.temp1_data)[-len(seconds_ago):]
        temp2_plot = list(self.temp2_data)[-len(seconds_ago):]
        
        # Update plot data
        self.line1.set_data(seconds_ago, temp1_plot)
        self.line2.set_data(seconds_ago, temp2_plot)
        
        # Update x-axis to show proper time labels
        if seconds_ago:
            self.ax.set_xlim(max(seconds_ago), 0)
        
        return self.line1, self.line2
    
    def toggle_sensor1_display(self):
        """Toggle sensor 1 display on third box (virtual button press)"""
        self.sensor1_display.set(not self.sensor1_display.get())
        if self.sensor1_display.get():
            self.sensor1_btn.config(text="Sensor 1 Display: ON", bg='#4CAF50', fg='white')
        else:
            self.sensor1_btn.config(text="Sensor 1 Display: OFF", bg='#f44336', fg='white')
        
        # Commands are handled externally; GUI only updates its display state.
    
    def toggle_sensor2_display(self):
        """Toggle sensor 2 display on third box (virtual button press)"""
        self.sensor2_display.set(not self.sensor2_display.get())
        if self.sensor2_display.get():
            self.sensor2_btn.config(text="Sensor 2 Display: ON", bg='#4CAF50', fg='white')
        else:
            self.sensor2_btn.config(text="Sensor 2 Display: OFF", bg='#f44336', fg='white')
        
        # Commands are handled externally; GUI only updates its display state.
    
    def configure_email(self):
        """Configure email settings for alerts"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Email Configuration")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()

        tk.Label(dialog, text="SMTP Server:", font=('Arial', 10)).pack(pady=5)
        server_entry = tk.Entry(dialog, width=40)
        server_entry.insert(0, self.smtp_server)
        server_entry.pack(pady=5)

        tk.Label(dialog, text="SMTP Port:", font=('Arial', 10)).pack(pady=5)
        port_entry = tk.Entry(dialog, width=40)
        port_entry.insert(0, str(self.smtp_port))
        port_entry.pack(pady=5)

        tk.Label(dialog, text="Email Username:", font=('Arial', 10)).pack(pady=5)
        username_entry = tk.Entry(dialog, width=40)
        username_entry.insert(0, self.email_username)
        username_entry.pack(pady=5)

        tk.Label(dialog, text="Email Password:", font=('Arial', 10)).pack(pady=5)
        password_entry = tk.Entry(dialog, width=40, show="*")
        password_entry.insert(0, self.email_password)
        password_entry.pack(pady=5)

        def save_settings():
            try:
                self.smtp_server = server_entry.get()
                self.smtp_port = int(port_entry.get())
            except Exception:
                messagebox.showerror("Error", "Please enter a valid SMTP port number")
                return
            self.email_username = username_entry.get()
            self.email_password = password_entry.get()
            dialog.destroy()
            messagebox.showinfo("Success", "Email settings saved!")

        tk.Button(dialog, text="Save Settings", command=save_settings,
                 bg='black', fg='white', font=('Arial', 12)).pack(pady=20)
    
    def check_temperature_alerts(self):
        """Check if temperatures exceed thresholds and send alerts"""
        if not self.third_box_on:
            return
        
        # Convert alert thresholds if needed
        max_temp = self.max_temp.get()
        min_temp = self.min_temp.get()
        
        if self.temp_unit.get() == "F":
            max_temp = self.fahrenheit_to_celsius(max_temp)
            min_temp = self.fahrenheit_to_celsius(min_temp)
        
        # Check sensor 1
        if self.sensor1_connected and (self.current_temp1 > max_temp or self.current_temp1 < min_temp):
            self.send_temperature_alert(1, self.current_temp1, "High" if self.current_temp1 > max_temp else "Low")
        
        # Check sensor 2
        if self.sensor2_connected and (self.current_temp2 > max_temp or self.current_temp2 < min_temp):
            self.send_temperature_alert(2, self.current_temp2, "High" if self.current_temp2 > max_temp else "Low")
    
    def send_temperature_alert(self, sensor_num, temperature, alert_type):
        """Send temperature alert via email/SMS"""
        # Prevent spam by implementing a cooldown (not shown for brevity)
        message = f"ALERT: Sensor {sensor_num} temperature is {alert_type}: {temperature:.1f}°C"
        
        # Send email if configured
        if self.alert_email.get() and self.email_username:
            threading.Thread(target=self.send_email_alert, args=(message,), daemon=True).start()
        
        # Send SMS if configured (would need SMS service integration)
        if self.alert_phone.get():
            # This would integrate with an SMS service like Twilio
            print(f"SMS Alert: {message}")
    
    def send_email_alert(self, message):
        """Send email alert"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_username
            msg['To'] = self.alert_email.get()
            msg['Subject'] = "Temperature Alert - Smart Thermometer"
            
            msg.attach(MIMEText(message, 'plain'))
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email_username, self.email_password)
            text = msg.as_string()
            server.sendmail(self.email_username, self.alert_email.get(), text)
            server.quit()
            
            print(f"Email alert sent: {message}")
        except Exception as e:
            print(f"Failed to send email alert: {e}")

def main():
    root = tk.Tk()
    app = ThermometerGUI(root)
    
    # Handle window closing
    def on_closing():
        app.running = False
        root.quit()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
