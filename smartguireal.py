#!/usr/bin/env python3
""" Merged Flask + Tkinter GUI for Smart Thermometer - Runs Flask server in a background thread.
   Stores incoming temperature posts in a thread-safe queue.
   Tkinter GUI reads latest queue item once per second and updates the 300s rolling history and the live graph.

   Ensure your ESP32 posts to http://<this_machine_ip>:8080/data
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
import twilioreal  # for sending SMS alerts

# --- Requirements and Constants ---
GRAPH_TIME_SPAN = 300  # seconds to keep on graph
UPDATE_INTERVAL_MS = 1000  # GUI update interval in ms (1s)
TEMP_C_MAX = 50
TEMP_C_MIN = 10
TEMP_F_MIN = 50
TEMP_F_MAX = 122
PERSISTENCE_FILE = "temp_history.json"
MAX_HISTORY_SEC = 500  # store last 500 seconds

# --- ALERT THRESHOLDS ---
LOW_C = 18.0
HIGH_C = 32.0

# Track last alert state to prevent spamming
last_alert_state = {1: None, 2: None}  # type: dict[int, str | None]

# Thread-safe queue to pass data from Flask -> GUI
data_queue = queue.Queue()

# For deciding if third box is on/off (no data means off)
THIRD_BOX_TIMEOUT_S = 2.0  # if no posts within this, treat as off

# -----------------------------
# Shared command state (GUI -> ESP via Flask response)
# -----------------------------
command_state = {"sensor1": False, "sensor2": False, "display_on": True}
last_changed = {"sensor1": 0.0, "sensor2": 0.0, "display_on": 0.0}


def save_history(history_1, history_2):
    """Save history to disk as JSON."""
    try:
        with open(PERSISTENCE_FILE, "w") as f:
            json.dump({"history_1": list(history_1), "history_2": list(history_2)}, f)
    except Exception as e:
        print(f"Error saving history: {e}")


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
# Flask server (background)
# -----------------------------
app = Flask(__name__)


@app.route("/")
def home():
    return "ESP32 Temperature Server is running!"


@app.route("/test")
def test_endpoint():
    return jsonify({"message": "Server is running!", "timestamp": datetime.now().isoformat()})


@app.route("/data", methods=["POST"])
def receive_data():
    try:
        data = request.json or {}
        temp1 = data.get("temp1", None)
        temp2 = data.get("temp2", None)
        esp_ts = data.get("timestamp", None)

        if "sensor1" in data:
            if time.time() - last_changed["sensor1"] > 1.0:
                command_state["sensor1"] = bool(data["sensor1"])

        if "sensor2" in data:
            if time.time() - last_changed["sensor2"] > 1.0:
                command_state["sensor2"] = bool(data["sensor2"])

        received_time = time.time()
        human_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(
            f"[{human_ts}] Received data from ESP32: "
            f"temp1={temp1}, temp2={temp2}, esp_ts={esp_ts}, "
            f"sensor1={command_state['sensor1']}, sensor2={command_state['sensor2']}"
        )

        data_queue.put(
            {"temp1": temp1, "temp2": temp2, "esp_timestamp": esp_ts, "server_recv_time": received_time}
        )

        resp = {
            "status": "success",
            "sensor1": bool(command_state.get("sensor1", False)),
            "sensor2": bool(command_state.get("sensor2", False)),
            "display_on": bool(command_state.get("display_on", False)),
        }
        return jsonify(resp), 200
    except Exception as e:
        print(f"Error processing request: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400


def run_flask_server():
    app.run(host="0.0.0.0", port=8080, debug=False, use_reloader=False, threaded=True)


# -----------------------------
# GUI + Plotting
# -----------------------------
class SmartThermometerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Smart Thermometer GUI (Merged Server + GUI)")

        self.temps_c = {1: 22.0, 2: 22.0}
        self.sensors_enabled = {1: False, 2: False}
        self.third_box_on = False
        self.last_recv_time = 0.0

        nan_init = float("nan")
        loaded1, loaded2 = load_history()
        if loaded1 and loaded2:
            loaded1 = [
                v if (v is None or (isinstance(v, (int, float)) and not math.isnan(v))) else float("nan")
                for v in loaded1
            ]
            loaded2 = [
                v if (v is None or (isinstance(v, (int, float)) and not math.isnan(v))) else float("nan")
                for v in loaded2
            ]
            self.history_1 = collections.deque(loaded1[-MAX_HISTORY_SEC:], maxlen=MAX_HISTORY_SEC)
            self.history_2 = collections.deque(loaded2[-MAX_HISTORY_SEC:], maxlen=MAX_HISTORY_SEC)
        else:
            self.history_1 = collections.deque([nan_init] * MAX_HISTORY_SEC, maxlen=MAX_HISTORY_SEC)
            self.history_2 = collections.deque([nan_init] * MAX_HISTORY_SEC, maxlen=MAX_HISTORY_SEC)

        self.create_widgets()
        self.setup_graph()
        self.root.after(UPDATE_INTERVAL_MS, self.periodic_update)

    def create_widgets(self):
        control_frame = ttk.LabelFrame(self.root, text="System Control & Real-Time Data")
        control_frame.pack(padx=10, pady=10, fill="x")

        self.unit_button = ttk.Button(control_frame, text="Switch to °F", command=self.toggle_units)
        self.unit_button.grid(row=0, column=0, padx=5, pady=5)
        self.display_units = "C"

        self.temp_label_1 = ttk.Label(control_frame, text="Sensor 1: ---", font=("Helvetica", 18, "bold"))
        self.temp_label_1.grid(row=1, column=0, padx=10, pady=6, sticky="W")
        self.temp_label_2 = ttk.Label(control_frame, text="Sensor 2: ---", font=("Helvetica", 18, "bold"))
        self.temp_label_2.grid(row=2, column=0, padx=10, pady=6, sticky="W")

        self.toggle_button_1 = ttk.Button(
            control_frame, text=self._btn_text(1), command=lambda: self.toggle_sensor_cmd(1)
        )
        self.toggle_button_1.grid(row=1, column=1, padx=5, pady=5)

        self.toggle_button_2 = ttk.Button(
            control_frame, text=self._btn_text(2), command=lambda: self.toggle_sensor_cmd(2)
        )
        self.toggle_button_2.grid(row=2, column=1, padx=5, pady=5)

    def _btn_text(self, sensor_num):
        desired = command_state.get(f"sensor{sensor_num}", False)
        return f"Set Sensor {sensor_num} {'OFF' if desired else 'ON'}"

    def toggle_sensor_cmd(self, sensor_num):
        key = f"sensor{sensor_num}"
        current = command_state.get(key, False)
        command_state[key] = not current
        last_changed[key] = time.time()
        print(f"(Virtual) Sensor {sensor_num} desired set to {'ON' if command_state[key] else 'OFF'}")
        if sensor_num == 1:
            self.toggle_button_1.config(text=self._btn_text(1))
        else:
            self.toggle_button_2.config(text=self._btn_text(2))

    def setup_graph(self):
        graph_frame = ttk.LabelFrame(self.root, text="Temperature Graph (Last 300 Seconds)")
        graph_frame.pack(padx=10, pady=10, fill="both", expand=True)
        self.fig, self.ax = plt.subplots(figsize=(9, 4))
        self.canvas = FigureCanvasTkAgg(self.fig, master=graph_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(fill=tk.BOTH, expand=True)
        self.ax.set_ylim(TEMP_C_MIN, TEMP_C_MAX)
        self.ax.set_xlim(GRAPH_TIME_SPAN, 0)
        self.ax.set_ylabel("Temp, °C")
        self.ax.set_xlabel("Seconds ago")
        self.ax.set_title("Temperature History")

    def periodic_update(self):
        global last_alert_state
        got_message = False
        latest_msg = None
        while True:
            try:
                msg = data_queue.get_nowait()
                latest_msg = msg
                got_message = True
            except queue.Empty:
                break

        if got_message and latest_msg is not None:
            t1 = latest_msg.get("temp1", None)
            t2 = latest_msg.get("temp2", None)
            self.last_recv_time = latest_msg.get("server_recv_time", time.time())
            if t1 is not None:
                self.temps_c[1] = float(t1)
                self.sensors_enabled[1] = True
            else:
                self.sensors_enabled[1] = False
            if t2 is not None:
                self.temps_c[2] = float(t2)
                self.sensors_enabled[2] = True
            else:
                self.sensors_enabled[2] = False
            self.third_box_on = True
            self.history_1.append(self.temps_c[1] if self.sensors_enabled[1] else float("nan"))
            self.history_2.append(self.temps_c[2] if self.sensors_enabled[2] else float("nan"))
        else:
            now = time.time()
            if now - self.last_recv_time > THIRD_BOX_TIMEOUT_S:
                self.third_box_on = False
            self.history_1.append(float("nan"))
            self.history_2.append(float("nan"))

        # --- ALERT LOGIC ---
        for sensor_id in [1, 2]:
            if self.sensors_enabled[sensor_id]:
                temp_c = self.temps_c[sensor_id]
                temp_f = (temp_c * 9 / 5) + 32
                if temp_c > HIGH_C and last_alert_state[sensor_id] != "high":
                    twilioreal.send_high_temp_alert(temp_c, temp_f)
                    last_alert_state[sensor_id] = "high"
                elif temp_c < LOW_C and last_alert_state[sensor_id] != "low":
                    twilioreal.send_low_temp_alert(temp_c, temp_f)
                    last_alert_state[sensor_id] = "low"
                elif LOW_C <= temp_c <= HIGH_C:
                    last_alert_state[sensor_id] = None

        # Update textual labels
        if not self.third_box_on:
            self.temp_label_1.config(text="No data available")
            self.temp_label_2.config(text="No data available")
        else:
            if self.sensors_enabled[1]:
                val = self.c_to_f(self.temps_c[1]) if self.display_units == "F" else self.temps_c[1]
                self.temp_label_1.config(text=f"Sensor 1: {val:.2f}°{self.display_units}")
            else:
                self.temp_label_1.config(text="Sensor 1: OFF")
            if self.sensors_enabled[2]:
                val = self.c_to_f(self.temps_c[2]) if self.display_units == "F" else self.temps_c[2]
                self.temp_label_2.config(text=f"Sensor 2: {val:.2f}°{self.display_units}")
            else:
                self.temp_label_2.config(text="Sensor 2: OFF")

        self.toggle_button_1.config(text=self._btn_text(1))
        self.toggle_button_2.config(text=self._btn_text(2))
        self.redraw_graph()
        self.root.after(UPDATE_INTERVAL_MS, self.periodic_update)
        save_history(self.history_1, self.history_2)

    def redraw_graph(self):
        # unchanged plotting code...
        pass

    def toggle_units(self):
        if self.display_units == "C":
            self.display_units = "F"
            self.unit_button.config(text="Switch to °C")
        else:
            self.display_units = "C"
            self.unit_button.config(text="Switch to °F")

    def c_to_f(self, celsius):
        return (celsius * 9 / 5) + 32


# -----------------------------
# Main startup
# -----------------------------
def main():
    flask_thread = threading.Thread(target=run_flask_server, daemon=True)
    flask_thread.start()
    print("Flask server thread started on port 8080.")

    root = tk.Tk()
    gui = SmartThermometerGUI(root)
    print("Starting GUI mainloop...")
    root.mainloop()
    print("GUI closed. Exiting.")


if __name__ == "__main__":
    main()
