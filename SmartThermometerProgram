"""
SmartThermometerProgram.py
Combined Flask server and Tkinter GUI for Smart Thermometer project. 
This script runs a Flask server to receive temperature data from an ESP32 device,
and provides a Tkinter GUI to display real-time temperature readings, control sensor states,
and plot historical data. It also sends SMS alerts via Twilio when temperature thresholds are crossed. 

Group 11: Braden Miller, Kent Zdan, Scott Pearson, Xavier Uhrmacher
Due: 10/03/2025
"""
from flask import Flask, request, jsonify
from datetime import datetime
import threading
import queue
import time
import math
import collections
import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import json
import os
from twilio.rest import Client

# -----------------------------
# Global variables and constants
# -----------------------------
#Graphing constants
GRAPH_TIME_SPAN = 300 
UPDATE_INTERVAL_MS = 1000 
TEMP_C_MAX = 50
TEMP_C_MIN = 10
TEMP_F_MIN = 50
TEMP_F_MAX = 122

# Data persistence
PERSISTENCE_FILE = "temp_history.json"
MAX_HISTORY_SEC = 500  # store last 500 seconds

# Data processing
data_queue = queue.Queue() # Thread-safe queue to pass data from Flask -> GUI
THIRD_BOX_TIMEOUT_S = 2.0 # seconds of no data to consider off

# Command state to send to ESP32 (sensor1, sensor2, display_on)
command_state = {
    "sensor1": False,
    "sensor2": False,
    "display_on": True
}

# Track when each command was last changed
last_changed = {
    "sensor1": 0.0,
    "sensor2": 0.0,
    "display_on": 0.0
}

# Twilio API credentials & setup
ACCOUNT_SID = "AC9b8a0e9eae4e3bc14a539ff7bd46b7c9"
AUTH_TOKEN = "3914edbaeb967838c56309427136c630"
FROM_NUMBER = "+18556127806"   # Twilio number
TO_NUMBER = "+18777804236"     # Virtual phone number

client = Client(ACCOUNT_SID, AUTH_TOKEN)

# --- Alert cooldown tracking ---
last_alert_time = {
    "sensor1_high": 0.0,
    "sensor1_low": 0.0,
    "sensor2_high": 0.0,
    "sensor2_low": 0.0,
}
ALERT_COOLDOWN = 30  # seconds


# -----------------------------
# Out-of-Threshold Alert functions
# -----------------------------
# Send high temp alert via Twilio SMS
def send_high_temp_alert(temp_c, temp_f):
    message_body = (
        f"Smart Thermometer Alert: Temperature exceeded 32°C (89.6°F).\n"
        f"Current: {temp_c:.1f}°C / {temp_f:.1f}°F."
    )
    _send(body=message_body)

# Send low temp alert via Twilio SMS
def send_low_temp_alert(temp_c, temp_f):
    message_body = (
        f"Smart Thermometer Alert: Temperature dropped below 21°C (69.8°F).\n"
        f"Current: {temp_c:.1f}°C / {temp_f:.1f}°F."
    )
    _send(body=message_body)

# Internal function to send SMS via Twilio
def _send(body):
    try:
        client.messages.create(
            to=TO_NUMBER,
            from_=FROM_NUMBER,
            body=body
        )
        print(f"Twilio alert sent: {body}")
    except Exception as e:
        print(f"Failed to send Twilio alert: {e}")

# Check thresholds and manage cooldowns
def check_alerts(sensor_name, temp_c):
    """Check thresholds and send SMS alerts respecting cooldowns.
       sensor_name should be 'sensor1' or 'sensor2'.
       temp_c is a float (Celsius) or None.
    """
    if temp_c is None:
        return
    try:
        temp_c_val = float(temp_c)
    except Exception:
        return

    temp_f = (temp_c_val * 9 / 5) + 32
    now = time.time()

    # High threshold
    if temp_c_val > 32.0:
        key = f"{sensor_name}_high"
        if now - last_alert_time.get(key, 0) >= ALERT_COOLDOWN:
            send_high_temp_alert(temp_c_val, temp_f)
            last_alert_time[key] = now

    # Low threshold
    if temp_c_val < 21.0:
        key = f"{sensor_name}_low"
        if now - last_alert_time.get(key, 0) >= ALERT_COOLDOWN:
            send_low_temp_alert(temp_c_val, temp_f)
            last_alert_time[key] = now



# -----------------------------
# Data persistence functions (keep last 500 seconds of data)
# -----------------------------
# Save history to disk
def save_history(history_1, history_2):
    """Save history to disk as JSON."""
    try:
        with open(PERSISTENCE_FILE, "w") as f:
            json.dump({
                "history_1": list(history_1),
                "history_2": list(history_2)
            }, f)
    except Exception as e:
        print(f"Error saving history: {e}")

# Load history from disk
def load_history():
    """Load history from disk, return two lists (or None if no file)."""
    if not os.path.exists(PERSISTENCE_FILE):
        return None, None
    try:
        with open(PERSISTENCE_FILE, "r") as f:
            data = json.load(f)
            return data.get("history_1", []), data.get("history_2", [])
    except Exception as e:
        print(f"Error loading history: {e}")
        return None, None


# -----------------------------
# Flask server (send/recieve data from ESP32)
# -----------------------------
app = Flask(__name__)

# Basic health check endpoint
@app.route('/')
def home():
   return "ESP32 Temperature Server is running!"

# Test endpoint to verify server is operational
@app.route('/test')
def test_endpoint():
   return jsonify({"message": "Server is running!", "timestamp": datetime.now().isoformat()})

# Endpoint to receive data from ESP32
@app.route('/data', methods=['POST'])
def receive_data():
    try:
        # Get individual data fields from ESP32 JSON
        data = request.json or {}
        temp1 = data.get("temp1", None)
        temp2 = data.get("temp2", None)
        esp_ts = data.get("timestamp", None)

        # capture raw esp-reported sensor flags (if present) so GUI can differentiate
        esp_sensor1 = data.get("sensor1", None)
        esp_sensor2 = data.get("sensor2", None)

        # Update command_state based on GUI changes only (with cooldown)
        if "sensor1" in data:
            if time.time() - last_changed["sensor1"] > 1.0:  # 1s "cooldown"
                command_state["sensor1"] = bool(data["sensor1"])
        if "sensor2" in data:
            if time.time() - last_changed["sensor2"] > 1.0:
                command_state["sensor2"] = bool(data["sensor2"])

        received_time = time.time()
        human_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{human_ts}] Received data from ESP32: "
              f"temp1={temp1}, temp2={temp2}, esp_ts={esp_ts}, "
              f"esp_sensor1={esp_sensor1}, esp_sensor2={esp_sensor2}, "
              f"sensor1_cmd={command_state['sensor1']}, sensor2_cmd={command_state['sensor2']}")

        # Push data to queue for GUI
        data_queue.put({
            "temp1": temp1,
            "temp2": temp2,
            "esp_timestamp": esp_ts,
            "server_recv_time": received_time,
            "esp_sensor1": esp_sensor1,
            "esp_sensor2": esp_sensor2
        })

        # Respond with current command_state
        resp = {
            "status": "success",
            "sensor1": bool(command_state.get("sensor1", False)),
            "sensor2": bool(command_state.get("sensor2", False)),
            "display_on": bool(command_state.get("display_on", False))
        }
        return jsonify(resp), 200
    
    # General error handling
    except Exception as e:
        print(f"Error processing request: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400

# Run Flask server in a separate thread
def run_flask_server():
   # Important: disable the reloader when using Flask in a thread
   app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False, threaded=True)


# -----------------------------
# GUI graphing using Tkinter and Matplotlib
# -----------------------------
class SmartThermometerGUI:
   # Initialize GUI
   def __init__(self, root):
       self.root = root
       self.root.title("Smart Thermometer GUI (Merged Server + GUI)")

       # Current temps (last known). Use None to indicate no last reading available.
       self.temps_c = {1: None, 2: None}

       # Current sensor enabled states
       self.sensors_enabled = {1: False, 2: False}

       # third_box_on derived from receive activity
       self.third_box_on = False
       self.last_recv_time = 0.0

       # history deques (most recent value appended right)
       nan_init = float('nan')

       # Load persisted history if available
       loaded1, loaded2 = load_history()
       if loaded1 and loaded2:
            # Ensure lists are numeric/NaN and ordered oldest->newest
            loaded1 = [v if (v is None or (isinstance(v, (int, float)) and not math.isnan(v))) else float('nan') for v in loaded1]
            loaded2 = [v if (v is None or (isinstance(v, (int, float)) and not math.isnan(v))) else float('nan') for v in loaded2]
            print(f"Loaded {len(loaded1)} points from persistent history")

            # keep the most recent MAX_HISTORY_SEC entries (oldest->newest)
            self.history_1 = collections.deque(loaded1[-MAX_HISTORY_SEC:], maxlen=MAX_HISTORY_SEC)
            self.history_2 = collections.deque(loaded2[-MAX_HISTORY_SEC:], maxlen=MAX_HISTORY_SEC)

            # If loaded histories are shorter than MAX_HISTORY_SEC, pad the left (oldest) side with NaNs
            if len(self.history_1) < MAX_HISTORY_SEC:
                pad = [float('nan')] * (MAX_HISTORY_SEC - len(self.history_1))
                self.history_1 = collections.deque(pad + list(self.history_1), maxlen=MAX_HISTORY_SEC)
            if len(self.history_2) < MAX_HISTORY_SEC:
                pad = [float('nan')] * (MAX_HISTORY_SEC - len(self.history_2))
                self.history_2 = collections.deque(pad + list(self.history_2), maxlen=MAX_HISTORY_SEC)
       else:
            self.history_1 = collections.deque([nan_init] * MAX_HISTORY_SEC, maxlen=MAX_HISTORY_SEC)
            self.history_2 = collections.deque([nan_init] * MAX_HISTORY_SEC, maxlen=MAX_HISTORY_SEC)

       # GUI widgets
       self.create_widgets()
       self.setup_graph()

       # Start periodic GUI update
       self.root.after(UPDATE_INTERVAL_MS, self.periodic_update)

   #Create control buttons and labels
   def create_widgets(self):
       # System Control Frame
       control_frame = ttk.LabelFrame(self.root, text="System Control & Real-Time Data")
       control_frame.pack(padx=10, pady=10, fill="x")

       # Unit toggle button
       self.unit_button = ttk.Button(control_frame, text="Switch to °F", command=self.toggle_units)
       self.unit_button.grid(row=0, column=0, padx=5, pady=5)
       self.display_units = 'C'  # 'C' or 'F'

       # Temperature labels
       self.temp_label_1 = ttk.Label(control_frame, text="Sensor 1: ---", font=('Helvetica', 18, 'bold'))
       self.temp_label_1.grid(row=1, column=0, padx=10, pady=6, sticky="W")
       self.temp_label_2 = ttk.Label(control_frame, text="Sensor 2: ---", font=('Helvetica', 18, 'bold'))
       self.temp_label_2.grid(row=2, column=0, padx=10, pady=6, sticky="W")

       # Sensor toggle buttons
       self.toggle_button_1 = ttk.Button(control_frame, text=self._btn_text(1),
                                         command=lambda: self.toggle_sensor_cmd(1))
       self.toggle_button_1.grid(row=1, column=1, padx=5, pady=5)

       self.toggle_button_2 = ttk.Button(control_frame, text=self._btn_text(2),
                                         command=lambda: self.toggle_sensor_cmd(2))
       self.toggle_button_2.grid(row=2, column=1, padx=5, pady=5)


   # Function to update current desired state in the button text
   def _btn_text(self, sensor_num):
       desired = command_state.get(f"sensor{sensor_num}", False)
       return f"Set Sensor {sensor_num} {'OFF' if desired else 'ON'}"

   # Toggle sensor command state and update button text
   def toggle_sensor_cmd(self, sensor_num):
        key = f"sensor{sensor_num}"
        current = command_state.get(key, False)
        command_state[key] = not current
        last_changed[key] = time.time()   # NEW: mark GUI change
        print(f"(Virtual) Sensor {sensor_num} desired set to {'ON' if command_state[key] else 'OFF'}")
        if sensor_num == 1:
            self.toggle_button_1.config(text=self._btn_text(1))
        else:
            self.toggle_button_2.config(text=self._btn_text(2))

   # Setup Matplotlib graph in Tkinter
   def setup_graph(self):
       graph_frame = ttk.LabelFrame(self.root, text="Temperature Graph (Last 300 Seconds)")
       graph_frame.pack(padx=10, pady=10, fill="both", expand=True)
       self.fig, self.ax = plt.subplots(figsize=(9, 4))
       self.canvas = FigureCanvasTkAgg(self.fig, master=graph_frame)
       self.canvas_widget = self.canvas.get_tk_widget()
       self.canvas_widget.pack(fill=tk.BOTH, expand=True)

       # Hardcode fixed y-axis ranges to match project requirement
       self.ax.set_ylim(TEMP_C_MIN, TEMP_C_MAX) 
       self.ax.set_xlim(GRAPH_TIME_SPAN, 0)
       self.ax.set_ylabel("Temp, °C")
       self.ax.set_xlabel("Seconds ago")
       self.ax.set_title("Temperature History")
       self.legend = None

   # Periodic update function called every second - Updates temps, labels, and graph
   def periodic_update(self):
       """ 1) Drain the queue for the latest message (if any).
           2) Update sensors_enabled, temps, last_recv_time.
           3) Append either new values (if received) or NaN to the history buffers.
           4) Update labels and redraw graph.
       """
       got_message = False
       latest_msg = None
       # Drain the queue, keep the most recent message
       while True:
           try:
               msg = data_queue.get_nowait()
               latest_msg = msg
               got_message = True
           except queue.Empty:
               break

       if got_message and latest_msg is not None:
           # Use latest message only (since updates are once/sec from ESP32)
           t1 = latest_msg.get("temp1", None)
           t2 = latest_msg.get("temp2", None)
           esp_sensor1 = latest_msg.get("esp_sensor1", None)
           esp_sensor2 = latest_msg.get("esp_sensor2", None)

           self.last_recv_time = latest_msg.get("server_recv_time", time.time())

           # Keep command_state as the source of "desired" sensor on/off.
           desired1 = command_state.get("sensor1", False)
           desired2 = command_state.get("sensor2", False)

           # Update temps_c: set to None explicitly if t is None, else parse float
           if t1 is None:
               self.temps_c[1] = None
           else:
               try:
                   self.temps_c[1] = float(t1)
               except Exception:
                   self.temps_c[1] = None

           if t2 is None:
               self.temps_c[2] = None
           else:
               try:
                   self.temps_c[2] = float(t2)
               except Exception:
                   self.temps_c[2] = None

           # Reflect desired state into local sensors_enabled (used for plotting/labels)
           self.sensors_enabled[1] = bool(desired1)
           self.sensors_enabled[2] = bool(desired2)

           # Mark third box on since we got a message
           self.third_box_on = True

           # Check if temps exceed thresholds and send alerts if needed
           if self.sensors_enabled[1] and (self.temps_c[1] is not None):
               check_alerts("sensor1", self.temps_c[1])

           if self.sensors_enabled[2] and (self.temps_c[2] is not None):
               check_alerts("sensor2", self.temps_c[2])

           # Append to history: if GUI desires sensor ON and reading present add reading, else NaN
           self.history_1.append(self.temps_c[1] if (self.sensors_enabled[1] and self.temps_c[1] is not None) else float('nan'))
           self.history_2.append(self.temps_c[2] if (self.sensors_enabled[2] and self.temps_c[2] is not None) else float('nan'))
       else:
           # No message this second
           now = time.time()
           if now - self.last_recv_time > THIRD_BOX_TIMEOUT_S:
               self.third_box_on = False
           # append missing (NaN) to both histories (graph must continue to scroll)
           self.history_1.append(float('nan'))
           self.history_2.append(float('nan'))

       # Update textual labels based on state
       if not self.third_box_on:
           self.temp_label_1.config(text="No data available")
           self.temp_label_2.config(text="No data available")
       else:
           # Sensor 1: Use command_state/desired to decide OFF vs DISCONNECTED
           if not command_state.get("sensor1", False):
               # GUI desired OFF
               self.temp_label_1.config(text="Sensor 1: OFF")
           else:
               # GUI desires ON — show DISCONNECTED if no temp, otherwise value
               if self.temps_c[1] is None:
                   self.temp_label_1.config(text="Sensor 1: no data available")
               else:
                   temp = self.temps_c[1]
                   if self.display_units == 'F':
                       temp = self.c_to_f(temp)
                   self.temp_label_1.config(text=f"Sensor 1: {temp:.2f}°{self.display_units}")

           # Sensor 2 does same
           if not command_state.get("sensor2", False):
               self.temp_label_2.config(text="Sensor 2: OFF")
           else:
               if self.temps_c[2] is None:
                   self.temp_label_2.config(text="Sensor 2: no data available")
               else:
                   temp = self.temps_c[2]
                   if self.display_units == 'F':
                       temp = self.c_to_f(temp)
                   self.temp_label_2.config(text=f"Sensor 2: {temp:.2f}°{self.display_units}")

       # Update GUI toggle button texts to reflect current desired command_state
       self.toggle_button_1.config(text=self._btn_text(1))
       self.toggle_button_2.config(text=self._btn_text(2))

       # Redraw graph using current histories
       self.redraw_graph()

       # schedule next update
       self.root.after(UPDATE_INTERVAL_MS, self.periodic_update)
       # Persist histories to disk
       save_history(self.history_1, self.history_2)

   # Redraw the Matplotlib graph with updated data & labels
   def redraw_graph(self):
       y1_full = list(self.history_1)
       y2_full = list(self.history_2)

       if len(y1_full) < GRAPH_TIME_SPAN:
           pad = [float('nan')] * (GRAPH_TIME_SPAN - len(y1_full))
           y1 = pad + y1_full
       else:
           y1 = y1_full[-GRAPH_TIME_SPAN:]

       if len(y2_full) < GRAPH_TIME_SPAN:
           pad = [float('nan')] * (GRAPH_TIME_SPAN - len(y2_full))
           y2 = pad + y2_full
       else:
           y2 = y2_full[-GRAPH_TIME_SPAN:]

       x = list(range(GRAPH_TIME_SPAN, 0, -1))

       # Convert to Fahrenheit if user selects F
       if self.display_units == 'F':
           y1 = [self.c_to_f(v) if (v is not None and not math.isnan(v)) else float('nan') for v in y1]
           y2 = [self.c_to_f(v) if (v is not None and not math.isnan(v)) else float('nan') for v in y2]
           self.ax.set_ylabel("Temp, °F")
           self.ax.set_ylim(TEMP_F_MIN, TEMP_F_MAX)
       else:
           self.ax.set_ylabel("Temp, °C")
           self.ax.set_ylim(TEMP_C_MIN, TEMP_C_MAX)

       # Clear and redraw
       self.ax.cla()
       self.ax.set_xlim(GRAPH_TIME_SPAN, 0)
       self.ax.set_xlabel("Seconds ago")
       self.ax.set_title("Temperature History")
        # Lock fixed y-axis ranges depending on units
       if self.display_units == 'F':
            self.ax.set_ylabel("Temp, °F")
            self.ax.set_ylim(TEMP_F_MIN, TEMP_F_MAX)
       else:
            self.ax.set_ylabel("Temp, °C")
            self.ax.set_ylim(TEMP_C_MIN, TEMP_C_MAX)

       # Fixed colors for sensor plot lines
       sensor_colors = {1: "blue", 2: "red"}

       # Function to plot segments of data, breaking at NaNs
       def plot_segments(x_vals, y_vals, label, color):
           seg_x, seg_y = [], []
           first_label = label
           for xi, yi in zip(x_vals, y_vals):
               missing = (yi is None) or (isinstance(yi, float) and math.isnan(yi))
               if not missing:
                   seg_x.append(xi)
                   seg_y.append(yi)
               else:
                   if seg_x:
                       self.ax.plot(seg_x, seg_y, linewidth=1.5, label=first_label, color=color)
                       first_label = ""
                   seg_x, seg_y = [], []
           if seg_x:
               self.ax.plot(seg_x, seg_y, linewidth=1.5, label=first_label, color=color)

       plot_segments(x, y1, "Sensor 1", sensor_colors[1])
       plot_segments(x, y2, "Sensor 2", sensor_colors[2])

       self.ax.legend(loc='upper right')
       self.ax.grid(True)
       self.canvas.draw_idle()

   # Toggle between Celsius and Fahrenheit display
   def toggle_units(self):
       if self.display_units == 'C':
           self.display_units = 'F'
           self.unit_button.config(text="Switch to °C")
       else:
           self.display_units = 'C'
           self.unit_button.config(text="Switch to °F")

   # Convert Celsius to Fahrenheit
   def c_to_f(self, celsius):
       return (celsius * 9 / 5) + 32


# -----------------------------
# Main startup function
# -----------------------------
def main():
   # Start Flask in background
   flask_thread = threading.Thread(target=run_flask_server, daemon=True)
   flask_thread.start()
   print("Flask server thread started on port 8080.")

   # Start Tkinter GUI
   root = tk.Tk()
   gui = SmartThermometerGUI(root)
   print("Starting GUI mainloop...")
   root.mainloop()
   print("GUI closed. Exiting.")

# -----------------------------
# Starup program
# -----------------------------
if __name__ == "__main__":
   main()
