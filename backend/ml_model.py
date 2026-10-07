# ml_model.py - Complete Machine Learning Module
import schedule
import time
import threading
from datetime import datetime, timedelta
import numpy as np
from collections import defaultdict
import pickle
import os

class HabitLearner:
    def __init__(self, db):
        self.db = db
        self.running = False
        self.auto_control_enabled = True
        self.scheduler_thread = None
        
        # ML model storage
        self.habit_patterns = {}
        self.prediction_model = None
        self.model_file = 'habit_model.pkl'
        
        # Load existing model if available
        self.load_model()
    
    def start_scheduler(self):
        """Start ML automation scheduler"""
        if self.running:
            return
        
        self.running = True
        
        # Clear existing schedule
        schedule.clear()
        
        # Schedule tasks
        schedule.every(1).hours.do(self.analyze_and_predict)
        schedule.every(5).minutes.do(self.check_and_execute)
        schedule.every().day.at("00:00").do(self.retrain_model)
        
        print("🤖 ML Scheduler Started")
        
        def scheduler_loop():
            while self.running:
                schedule.run_pending()
                time.sleep(60)
        
        self.scheduler_thread = threading.Thread(target=scheduler_loop, daemon=True)
        self.scheduler_thread.start()
    
    def analyze_and_predict(self):
        """Analyze habits and make predictions"""
        print("\n📊 Running ML analysis...")
        
        # Get all habits from database
        habits = self.db.get_habits_for_ml()
        
        if not habits:
            print("📊 No habits found yet")
            return
        
        # Group by device and time
        predictions = self.generate_predictions(habits)
        
        # Save predictions
        for pred in predictions:
            self.db.save_prediction(
                pred['device'],
                pred['action'],
                pred['confidence'],
                pred['scheduled_time']
            )
        
        print(f"📊 Generated {len(predictions)} predictions")
        return predictions
    
    def generate_predictions(self, habits):
        """Generate predictions from habit data"""
        predictions = []
        current_time = datetime.now()
        
        # Group habits by device and hour
        device_patterns = defaultdict(lambda: defaultdict(list))
        
        for habit in habits:
            device = habit['device_name']
            action = habit['action']
            hour = habit['hour_of_day']
            frequency = habit['total_frequency']
            
            device_patterns[device][hour].append({
                'action': action,
                'frequency': frequency
            })
        
        # Generate predictions for next 24 hours
        for hour in range(24):
            future_time = current_time + timedelta(hours=hour)
            future_hour = future_time.hour
            future_day = future_time.weekday()
            
            for device, hour_patterns in device_patterns.items():
                if future_hour in hour_patterns:
                    actions = hour_patterns[future_hour]
                    
                    # Find most frequent action for this hour
                    total_actions = sum(a['frequency'] for a in actions)
                    
                    for action_data in actions:
                        confidence = action_data['frequency'] / total_actions
                        
                        # Different thresholds for different devices
                        if device == 'door':
                            # Door requires 98% confidence
                            if confidence > 0.98:
                                predictions.append({
                                    'device': device,
                                    'action': action_data['action'],
                                    'confidence': confidence,
                                    'scheduled_time': f"{future_hour:02d}:00"
                                })
                        elif device == 'fan':
                            # Fan requires 75% confidence
                            if confidence > 0.75:
                                predictions.append({
                                    'device': device,
                                    'action': action_data['action'],
                                    'confidence': confidence,
                                    'scheduled_time': f"{future_hour:02d}:00"
                                })
                        else:
                            # Light requires 70% confidence
                            if confidence > 0.7:
                                predictions.append({
                                    'device': device,
                                    'action': action_data['action'],
                                    'confidence': confidence,
                                    'scheduled_time': f"{future_hour:02d}:00"
                                })
        
        return predictions
    
    def check_and_execute(self):
        """Check if any predictions should be executed now"""
        if not self.auto_control_enabled:
            return
        
        current_time = datetime.now()
        current_hour = current_time.hour
        current_minute = current_time.minute
        
        print(f"\n🤖 Checking automation at {current_time.strftime('%H:%M')}")
        
        # Get all habits for current time
        habits = self.db.get_habits_for_ml()
        
        # Group by device for current hour
        current_habits = defaultdict(list)
        
        for habit in habits:
            if habit['hour_of_day'] == current_hour:
                device = habit['device_name']
                current_habits[device].append(habit)
        
        # Execute predictions with high confidence
        for device, device_habits in current_habits.items():
            if not device_habits:
                continue
            
            # Find most frequent action
            total = sum(h['total_frequency'] for h in device_habits)
            best_action = max(device_habits, key=lambda x: x['total_frequency'])
            confidence = best_action['total_frequency'] / total
            
            # Different thresholds for different devices
            if device == 'door':
                # Door requires 98% confidence
                if confidence > 0.98:
                    print(f"🤖 Auto-executing: {device} -> {best_action['action']}")
                    
                    # Get current status
                    current = self.db.get_device_status(device)
                    
                    if current and current[0]['status'] != best_action['action'].upper():
                        # Execute the action
                        action = best_action['action'].upper()
                        if device == 'door':
                            action = 'UNLOCKED' if best_action['action'] == 'unlock' else 'LOCKED'
                        
                        self.db.update_device_status(device, action, source='auto')
            elif device == 'fan':
                # Fan requires 85% confidence
                if confidence > 0.85:
                    print(f"🤖 Auto-executing: {device} -> {best_action['action']}")
                    
                    # Get current status
                    current = self.db.get_device_status(device)
                    
                    if current and current[0]['status'] != best_action['action'].upper():
                        # Execute the action
                        action = best_action['action'].upper()
                        if device == 'door':
                            action = 'UNLOCKED' if best_action['action'] == 'unlock' else 'LOCKED'
                        
                        self.db.update_device_status(device, action, source='auto')
            else:
                # Light requires 80% confidence
                if confidence > 0.8:
                    print(f"🤖 Auto-executing: {device} -> {best_action['action']}")
                    
                    # Get current status
                    current = self.db.get_device_status(device)
                    
                    if current and current[0]['status'] != best_action['action'].upper():
                        # Execute the action
                        action = best_action['action'].upper()
                        if device == 'door':
                            action = 'UNLOCKED' if best_action['action'] == 'unlock' else 'LOCKED'
                        
                        self.db.update_device_status(device, action, source='auto')
    
    def learn_from_command(self, device, action):
        """Learn from user command"""
        # Record in database
        self.db.record_habit(device, action)
        
        # Update in-memory patterns
        print(f"📚 ML Learned: {device} -> {action}")
    
    def retrain_model(self):
        """Retrain ML model with latest data"""
        print("🔄 Retraining ML model...")
        
        habits = self.db.get_habits_for_ml()
        
        if len(habits) < 10:  # Need minimum data
            print("📊 Insufficient data for training")
            return
        
        # Create feature vectors
        X = []  # Features
        y = []  # Labels
        
        for habit in habits:
            # Features: hour, day, device (encoded), frequency
            features = [
                habit['hour_of_day'],
                habit['day_of_week'],
                self.encode_device(habit['device_name']),
                habit['total_frequency']
            ]
            X.append(features)
            y.append(self.encode_action(habit['action']))
        
        # Save model (simplified - in production use scikit-learn)
        model_data = {
            'X': X,
            'y': y,
            'patterns': habits
        }
        
        with open(self.model_file, 'wb') as f:
            pickle.dump(model_data, f)
        
        print(f"✅ Model retrained with {len(habits)} data points")
    
    def encode_device(self, device):
        """Encode device name to number"""
        devices = {'light': 0, 'fan': 1, 'door': 2}
        return devices.get(device, 0)
    
    def encode_action(self, action):
        """Encode action to number"""
        actions = {'on': 0, 'off': 1, 'lock': 2, 'unlock': 3, 'speed': 4}
        return actions.get(action, 0)
    
    def load_model(self):
        """Load existing model"""
        if os.path.exists(self.model_file):
            try:
                with open(self.model_file, 'rb') as f:
                    self.habit_patterns = pickle.load(f)
                print("✅ ML Model loaded successfully")
            except:
                print("⚠️ Could not load existing model")
    
    def get_insights(self):
        """Get user habit insights"""
        habits = self.db.get_habits_for_ml()
        
        insights = []
        
        # Most used devices
        device_counts = defaultdict(int)
        for h in habits:
            device_counts[h['device_name']] += h['total_frequency']
        
        for device, count in device_counts.items():
            insights.append(f"📊 {device.title()}: used {count} times")
        
        # Peak usage hours
        hour_counts = defaultdict(int)
        for h in habits:
            hour_counts[h['hour_of_day']] += h['total_frequency']
        
        if hour_counts:
            peak_hour = max(hour_counts.items(), key=lambda x: x[1])
            insights.append(f"⏰ Peak usage: {peak_hour[0]:02d}:00 ({peak_hour[1]} actions)")
        
        return insights