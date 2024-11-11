import tkinter as tk 
from tkinter import ttk, messagebox
import paho.mqtt.client as mqtt
import sqlite3
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import json
import threading
import time

class HealthMonitoringSystem:
    def _init_(self):
        self.root = tk.Tk()
        self.root.title("Smart Health Monitoring System")
        self.root.geometry("1000x600")
        
        self.current_user = None
        self.mqtt_client = None
        self.setup_mqtt()
        self.setup_database()
        
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        self.selected_graph = tk.StringVar(value="heart")
        self.graph_data = {"heart": [], "temp": [], "calories": []}
        self.fig = None
        self.canvas = None
        
        self.show_login_page()
        
    def setup_mqtt(self):
        mqtt_broker = "broker.hivemq.com"
        mqtt_port = 1883
        
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self.on_mqtt_connect
        self.mqtt_client.on_message = self.on_mqtt_message
        
        try:
            self.mqtt_client.connect(mqtt_broker, mqtt_port, 60)
            self.mqtt_client.subscribe([("health/data", 0)])
            self.mqtt_client.loop_start()
            print("Connected to MQTT broker")
        except Exception as e:
            print(f"Failed to connect to MQTT broker: {e}")
    
    def on_mqtt_connect(self, client, userdata, flags, rc):
        print(f"Connected to MQTT broker with result code: {rc}")
        
    def setup_database(self):
        self.conn = sqlite3.connect('health_monitoring.db')
        self.create_tables()
        
    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE,
                password TEXT,
                name TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS health_data (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                heart_rate FLOAT,
                temperature FLOAT,
                calories FLOAT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        self.conn.commit()

    def show_login_page(self):
        self.clear_frame()
        ttk.Label(self.main_frame, text="Smart Health Monitoring System", 
                  font=('Helvetica', 16)).pack(pady=20)
        
        # Login form
        login_frame = ttk.Frame(self.main_frame)
        login_frame.pack(pady=10)
        
        ttk.Label(login_frame, text="Username:").pack(pady=5)
        username_entry = ttk.Entry(login_frame)
        username_entry.pack(pady=5)
        
        ttk.Label(login_frame, text="Password:").pack(pady=5)
        password_entry = ttk.Entry(login_frame, show="*")
        password_entry.pack(pady=5)
        
        ttk.Button(login_frame, text="Login", 
                   command=lambda: self.login_user(username_entry.get(), password_entry.get())).pack(pady=10)
        
        ttk.Button(self.main_frame, text="Sign Up", 
                   command=self.show_signup_page).pack(pady=10)

    def show_signup_page(self):
        self.clear_frame()
        ttk.Label(self.main_frame, text="Sign Up", font=('Helvetica', 16)).pack(pady=20)
        
        signup_frame = ttk.Frame(self.main_frame)
        signup_frame.pack(pady=10)
        
        ttk.Label(signup_frame, text="Username:").pack(pady=5)
        username_entry = ttk.Entry(signup_frame)
        username_entry.pack(pady=5)
        
        ttk.Label(signup_frame, text="Password:").pack(pady=5)
        password_entry = ttk.Entry(signup_frame, show="*")
        password_entry.pack(pady=5)
        
        ttk.Label(signup_frame, text="Name:").pack(pady=5)
        name_entry = ttk.Entry(signup_frame)
        name_entry.pack(pady=5)
        
        ttk.Button(signup_frame, text="Register", 
                   command=lambda: self.register_user(username_entry.get(), password_entry.get(), name_entry.get())).pack(pady=10)
        
        ttk.Button(self.main_frame, text="Back", 
                   command=self.show_login_page).pack(pady=10)

    def register_user(self, username, password, name):
        if not username or not password or not name:
            messagebox.showerror("Error", "Please fill all fields")
            return
        
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (username, password, name) VALUES (?, ?, ?)",
                (username, password, name)
            )
            self.conn.commit()
            messagebox.showinfo("Success", "Registration successful!")
            self.show_login_page()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Username already exists")

    def on_mqtt_message(self, client, userdata, msg):
        try:
            if msg.topic == "health/data" and self.current_user:
                data = json.loads(msg.payload)
                self.update_health_data(data)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
        except Exception as e:
            print(f"Error processing message: {e}")

    def update_health_data(self, data):
        try:
                self.graph_data["heart"].append(data['heart_rate'])
                self.graph_data["temp"].append(data['temperature'])
                self.graph_data["calories"].append(data['calories'])
        
        # Keep only last 100 readings
                for key in self.graph_data:
                        if len(self.graph_data[key]) > 100:
                                self.graph_data[key] = self.graph_data[key][-100:]

        # Establish a new database connection for this thread
                conn = sqlite3.connect('health_monitoring.db')
                cursor = conn.cursor()
                     
        # Store in database
       
                cursor.execute(""" INSERT INTO health_data (user_id, heart_rate, temperature, calories)
                VALUES (?, ?, ?, ?) """, (self.current_user[0], data['heart_rate'], data['temperature'], data['calories']))
                conn.commit()
   
        
        # Close the connection
                conn.close()
                print("Inserted Data:", data)  # Debug: Print inserted data to console
        except Exception as e:
                print(f"Error inserting health data: {e}")



    def login_user(self, username, password):
        if not username or not password:
            messagebox.showerror("Error", "Please fill all fields")
            return
        
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE username = ? AND password = ?", 
            (username, password)
        )
        user = cursor.fetchone()
        
        if user:
            self.current_user = user
            self.show_dashboard()
        else:
            messagebox.showerror("Error", "Invalid credentials")

    def show_dashboard(self):
        self.clear_frame()
        
        # Header
        ttk.Label(self.main_frame, text=f"Welcome, {self.current_user[3]}", 
                  font=('Helvetica', 16)).pack(pady=10)
        
        # Control Frame
        control_frame = ttk.Frame(self.main_frame)
        control_frame.pack(fill=tk.X, padx=10)
        
        # Radio Buttons
        ttk.Radiobutton(control_frame, text="Heart Rate", 
                        variable=self.selected_graph, value="heart",
                        command=self.update_graph).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(control_frame, text="Temperature", 
                        variable=self.selected_graph, value="temp",
                        command=self.update_graph).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(control_frame, text="Calories", 
                        variable=self.selected_graph, value="calories",
                        command=self.update_graph).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.main_frame, text="View History", command=self.check_history).pack(pady=10)

        # Graph Frame
        graph_frame = ttk.Frame(self.main_frame)
        graph_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.fig = Figure(figsize=(8, 4))
        self.canvas = FigureCanvasTkAgg(self.fig, master=graph_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Start updating graph
        self.update_graph()
        self.schedule_graph_update()
        
        # Logout button
        ttk.Button(self.main_frame, text="Logout", 
                   command=self.show_login_page).pack(pady=10)

    def clear_frame(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()

    def update_graph(self):
        if not self.fig or not self.canvas:
            return
            
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        
        graph_type = self.selected_graph.get()
        data = self.graph_data[graph_type][-20:]  # Show last 20 readings
        
        if data:
            ax.plot(range(len(data)), data)
            
            if graph_type == "heart":
                ax.set_ylabel("Heart Rate (BPM)")
                ax.set_title("Heart Rate Over Time")
            elif graph_type == "temp":
                ax.set_ylabel("Temperature (Â°C)")
                ax.set_title("Body Temperature Over Time")
            else:
                ax.set_ylabel("Calories Burned")
                ax.set_title("Calories Burned Over Time")
                
        self.canvas.draw()

    def schedule_graph_update(self):
        self.update_graph()
        self.root.after(5000, self.schedule_graph_update)
        
    def check_history(self):
        # Check if there's a current user logged in
        if not self.current_user:
            messagebox.showerror("Error", "No user is logged in.")
            return

        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT timestamp, heart_rate, temperature, calories 
            FROM health_data 
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT 100
        """, (self.current_user[0],))
        history_data = cursor.fetchall()
        print("Fetched History Data:", history_data)
        
        if history_data:
                history_message = "Last Received Health Data Records:\n\n"
                for record in history_data:
                        history_message += f"Timestamp: {record[0]}, Heart Rate: {record[1]}, Temperature: {record[2]}, Calories: {record[3]}\n"
                messagebox.showinfo("Health Data History", history_message)
        else:
                messagebox.showinfo("Health Data History", "No history data found.")

    def run(self):
        self.root.mainloop()
    

if _name_ == "_main_":
    app = HealthMonitoringSystem()
    app.run()