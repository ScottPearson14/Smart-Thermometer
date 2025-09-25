import tkinter as tk
from tkinter import ttk
import random
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import collections
from matplotlib.animation import FuncAnimation
import math

# --- Requirements and Constants ---
# Total time record displayed on the graph is 300 seconds.
GRAPH_TIME_SPAN = 300
# Update the real-time temperature once a second.
UPDATE_INTERVAL_MS = 1000  
# Max and min temperature limits for the graph (references removed).
TEMP_C_MAX = 50
TEMP_C_MIN = 10

class SmartThermometerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Smart Thermometer GUI")
        
        # Initialize data structures
        #TODO: Replace with real data source
        self.temps_c = {1: 22.0, 2: 22.0} # Start at room temp (approx).
        self.sensors_enabled = {1: False, 2: False}
        self.third_box_on = True
        self.display_units = 'C' # 'C' or 'F'
        
        # Use a deque to store the last 300 seconds of data for the graph
        # Initialize history with NaN so the deque element type is numeric
        nan_init = float('nan')
        self.history_1 = collections.deque([nan_init] * GRAPH_TIME_SPAN, maxlen=GRAPH_TIME_SPAN)
        self.history_2 = collections.deque([nan_init] * GRAPH_TIME_SPAN, maxlen=GRAPH_TIME_SPAN)

        # --- GUI Setup ---
        self.create_widgets()
        self.setup_graph()
        self.update_gui()
        
    def create_widgets(self):
        # Frame for controls and real-time display
        control_frame = ttk.LabelFrame(self.root, text="System Control & Real-Time Data")
        control_frame.pack(padx=10, pady=10, fill="x")

        # Third Box Switch Control (Simulated)
        self.third_box_switch_var = tk.BooleanVar(value=True)
        self.third_box_switch = ttk.Checkbutton(control_frame, text="Third Box On/Off", variable=self.third_box_switch_var, command=self.toggle_third_box)
        self.third_box_switch.grid(row=0, column=0, padx=5, pady=5)
        
        # Unit Conversion Button
        self.unit_button = ttk.Button(control_frame, text="Switch to °F", command=self.toggle_units)
        self.unit_button.grid(row=0, column=1, padx=5, pady=5)

        # Real-time temperature display
        self.temp_label_1 = ttk.Label(control_frame, text="Sensor 1: ---", font=('Helvetica', 24, 'bold'))
        self.temp_label_1.grid(row=1, column=0, padx=10, pady=10, sticky="W")
        
        self.temp_label_2 = ttk.Label(control_frame, text="Sensor 2: ---", font=('Helvetica', 24, 'bold'))
        self.temp_label_2.grid(row=2, column=0, padx=10, pady=10, sticky="W")
        
        # Sensor Toggle Buttons (virtual "press") 
        self.toggle_button_1 = ttk.Button(control_frame, text="Toggle Sensor 1", command=lambda: self.toggle_sensor(1))
        self.toggle_button_1.grid(row=1, column=1, padx=5, pady=5)

        self.toggle_button_2 = ttk.Button(control_frame, text="Toggle Sensor 2", command=lambda: self.toggle_sensor(2))
        self.toggle_button_2.grid(row=2, column=1, padx=5, pady=5)

    def setup_graph(self):
        # Graph frame
        graph_frame = ttk.LabelFrame(self.root, text="Temperature Graph (Last 300 Seconds)")
        graph_frame.pack(padx=10, pady=10, fill="both", expand=True)

        # Matplotlib figure and axis
        self.fig, self.ax = plt.subplots(figsize=(8, 4))
        self.canvas = FigureCanvasTkAgg(self.fig, master=graph_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(fill=tk.BOTH, expand=True)
        self.ax.set_ylim(TEMP_C_MIN, TEMP_C_MAX) # Limits are fixed.
        self.ax.set_xlim(GRAPH_TIME_SPAN, 0)
        self.ax.set_ylabel("Temp, °C")
        self.ax.set_xlabel("Seconds ago")
        self.ax.set_title("Temperature History")
        
        # Create line objects for each sensor
        self.line1, = self.ax.plot([], [], 'b-', label='Sensor 1')
        self.line2, = self.ax.plot([], [], 'r-', label='Sensor 2')
        self.ax.legend()
        
        # Set up the animation
        #self.anim = FuncAnimation(self.fig, self.update_graph, interval=1000, blit=False)
        # Set up the animation
        self.anim = FuncAnimation(self.fig, self.update_graph, interval=1000, blit=False, cache_frame_data=False)

    def update_gui(self):
        # Simulate new data for the graph
        self.simulate_new_data()
        
        # Update labels based on the state of the system
        if not self.third_box_on:
            # Third box off -> show no data available
            self.temp_label_1.config(text="No data available")
            self.temp_label_2.config(text="No data available")
        else:
            # Update sensor 1 display
            if self.sensors_enabled[1]:
                temp = self.temps_c[1]
                if self.display_units == 'F':
                    temp = self.c_to_f(temp)
                self.temp_label_1.config(text=f"Sensor 1: {temp:.2f}°{self.display_units}")
            else:
                self.temp_label_1.config(text="Sensor 1: OFF") # Per requirement 4.

            # Update sensor 2 display
            if self.sensors_enabled[2]:
                temp = self.temps_c[2]
                if self.display_units == 'F':
                    temp = self.c_to_f(temp)
                self.temp_label_2.config(text=f"Sensor 2: {temp:.2f}°{self.display_units}")
            else:
                self.temp_label_2.config(text="Sensor 2: OFF")

        # Schedule the next update
        self.root.after(UPDATE_INTERVAL_MS, self.update_gui)
    
    #TODO: Replace with real data source
    def simulate_new_data(self):
        # This part simulates the data coming from the ESP32.
        # In a real system, you would read from serial/network here.
        if self.third_box_on:
            # Simulate slight temperature changes
            self.temps_c[1] += random.uniform(-0.5, 0.5)
            self.temps_c[2] += random.uniform(-0.5, 0.5)
            
            # Add to history, but only if sensor is "on". Use NaN for missing numeric
            # entries so the deque always contains numeric types (float).
            self.history_1.append(self.temps_c[1] if self.sensors_enabled[1] else float('nan'))
            self.history_2.append(self.temps_c[2] if self.sensors_enabled[2] else float('nan'))
        else:
            # If the third box is off, add missing data to the history
            self.history_1.append(float('nan'))
            self.history_2.append(float('nan'))

    def update_graph(self, frame):
        # Get the current data from the deques
        y1 = list(self.history_1)
        y2 = list(self.history_2)
        x = list(range(GRAPH_TIME_SPAN, 0, -1)) # Labels from 300 to 1.

        # Convert to Fahrenheit if needed 
        if self.display_units == 'F':
            # Convert numeric values, preserve NaN for missing data
            y1 = [self.c_to_f(temp) if (temp is not None and not math.isnan(temp)) else float('nan') for temp in y1]
            y2 = [self.c_to_f(temp) if (temp is not None and not math.isnan(temp)) else float('nan') for temp in y2]
            self.ax.set_ylabel("Temp, °F")
            self.ax.set_ylim(self.c_to_f(TEMP_C_MIN), self.c_to_f(TEMP_C_MAX))
        else:
            self.ax.set_ylabel("Temp, °C")
            self.ax.set_ylim(TEMP_C_MIN, TEMP_C_MAX)

        # Find continuous segments to plot, handling None values for missing data
        # This makes missing data "obvious" on the graph.
        x1_segments, y1_segments = self.get_segments(x, y1)
        x2_segments, y2_segments = self.get_segments(x, y2)

        # Clear old lines and plot new segments
        self.line1.set_data([], [])
        self.line2.set_data([], [])
        
        # Plot each segment
        for xs, ys in zip(x1_segments, y1_segments):
            self.ax.plot(xs, ys, color='b')
        for xs, ys in zip(x2_segments, y2_segments):
            self.ax.plot(xs, ys, color='r')
            
        return self.line1, self.line2

    def get_segments(self, x_data, y_data):
        segments = []
        current_x = []
        current_y = []
        for i in range(len(y_data)):
            val = y_data[i]
            missing = (val is None) or (isinstance(val, float) and math.isnan(val))
            if not missing:
                current_x.append(x_data[i])
                current_y.append(y_data[i])
            else:
                if current_x:
                    segments.append((current_x, current_y))
                    current_x = []
                    current_y = []
        if current_x:
            segments.append((current_x, current_y))
        return [s[0] for s in segments], [s[1] for s in segments]


    def toggle_units(self):
        # Toggles display units and updates the button text.
        if self.display_units == 'C':
            self.display_units = 'F'
            self.unit_button.config(text="Switch to °C")
        else:
            self.display_units = 'C'
            self.unit_button.config(text="Switch to °F")
            
    def toggle_third_box(self):
        # Toggles the state of the third box (simulated)
        self.third_box_on = self.third_box_switch_var.get()
        if not self.third_box_on:
            print("Third box turned off. Data stream will stop.")
        
    def toggle_sensor(self, sensor_num):
        # Toggles the display state for a sensor, simulating button press.
        self.sensors_enabled[sensor_num] = not self.sensors_enabled[sensor_num]
        print(f"Sensor {sensor_num} toggled: {'ON' if self.sensors_enabled[sensor_num] else 'OFF'}")

    @staticmethod
    def c_to_f(celsius):
        # Convert Celsius to Fahrenheit
        return (celsius * 9/5) + 32

if __name__ == "__main__":
    root = tk.Tk()
    app = SmartThermometerGUI(root)
    root.mainloop()
