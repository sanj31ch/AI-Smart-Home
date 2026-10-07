# app.py - Complete Flask Backend with Fixed Door Control
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from datetime import datetime
import threading
import speech_recognition as sr
import tempfile
import json

# Import custom modules
from database import Database
from voice_processor import VoiceProcessor
from ml_model import HabitLearner

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialize modules
print("🚀 Initializing Smart Home Backend...")
db = Database()
db.ensure_tables()
voice_processor = VoiceProcessor()
habit_learner = HabitLearner(db)

# Start ML scheduler
habit_learner.start_scheduler()

# Initialize speech recognizer
recognizer = sr.Recognizer()

@app.route('/')
def home():
    return jsonify({
        "message": "AI Smart Home Backend",
        "status": "running",
        "version": "3.0.0",
        "devices": ["light", "fan", "door"],
        "languages": ["english", "hindi", "marathi"],
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    db_status = db.test_connection()
    
    return jsonify({
        "status": "healthy",
        "database": "connected" if db_status else "disconnected",
        "ml_engine": "running",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/devices', methods=['GET'])
def get_devices():
    """Get all devices status"""
    try:
        devices = db.get_device_status()
        
        # Handle None or empty result
        if devices is None or len(devices) == 0:
            # Return default devices if database is empty - use 'door' not 'door_lock'
            default_devices = [
                {"device_name": "light", "status": "OFF", "last_updated": None},
                {"device_name": "fan", "status": "OFF", "last_updated": None},
                {"device_name": "fan_speed", "status": "0", "last_updated": None},
                {"device_name": "door", "status": "LOCKED", "last_updated": None}
            ]
            return jsonify({
                "success": True,
                "timestamp": datetime.now().isoformat(),
                "devices": default_devices,
                "count": len(default_devices)
            })
        
        # Format response
        formatted_devices = []
        for device in devices:
            formatted_devices.append({
                "device_name": device['device_name'],
                "status": device['status'],
                "last_updated": device['last_updated'].strftime('%Y-%m-%d %H:%M:%S') if device['last_updated'] else None
            })
        
        return jsonify({
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "devices": formatted_devices,
            "count": len(formatted_devices)
        })
    except Exception as e:
        print(f"❌ Error in get_devices: {e}")
        # Return default devices on error
        default_devices = [
            {"device_name": "light", "status": "OFF", "last_updated": None},
            {"device_name": "fan", "status": "OFF", "last_updated": None},
            {"device_name": "fan_speed", "status": "0", "last_updated": None},
            {"device_name": "door", "status": "LOCKED", "last_updated": None}
        ]
        return jsonify({
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "devices": default_devices,
            "count": len(default_devices)
        })

@app.route('/api/device/<device_name>', methods=['GET'])
def get_device(device_name):
    """Get specific device status"""
    try:
        device = db.get_device_status(device_name)
        
        if not device:
            return jsonify({"success": False, "error": "Device not found"}), 404
        
        return jsonify({
            "success": True,
            "device": device[0]['device_name'],
            "status": device[0]['status'],
            "last_updated": device[0]['last_updated'].strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/control', methods=['POST'])
def control_device():
    """Control device manually - FIXED for door"""
    try:
        data = request.json
        
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400
        
        device = data.get('device')
        action = data.get('action')
        
        if not device or not action:
            return jsonify({"success": False, "error": "Missing device or action"}), 400
        
        # Validate device - door is now consistent
        valid_devices = ['light', 'fan', 'door']
        if device not in valid_devices:
            return jsonify({"success": False, "error": f"Invalid device: {device}"}), 400
        
        print(f"🔧 Manual control: {device} -> {action}")
        
        # Format action for database
        if device == 'door':
            if action.lower() in ['lock', 'locked', 'close']:
                db_action = 'LOCKED'
                ml_action = 'lock'
            elif action.lower() in ['unlock', 'unlocked', 'open']:
                db_action = 'UNLOCKED'
                ml_action = 'unlock'
            else:
                return jsonify({"success": False, "error": "Invalid door action"}), 400
        else:
            if action.lower() in ['on', 'off']:
                db_action = action.upper()
                ml_action = action.lower()
            else:
                return jsonify({"success": False, "error": "Invalid device action"}), 400
        
        # Update database
        success = db.update_device_status(device, db_action, source='manual')
        
        if success:
            # Record for ML
            db.record_habit(device, ml_action)
            habit_learner.learn_from_command(device, ml_action)
            
            # Get updated status
            devices = db.get_device_status()
            
            return jsonify({
                "success": True,
                "message": f"{device} set to {db_action}",
                "device": device,
                "action": db_action,
                "timestamp": datetime.now().isoformat(),
                "devices": devices
            })
        else:
            return jsonify({"success": False, "error": "Failed to update device"}), 500
            
    except Exception as e:
        print(f"❌ Control error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/fan-speed', methods=['POST'])
def set_fan_speed():
    """Set fan speed (0-100%)"""
    try:
        data = request.json
        speed = data.get('speed', 50)
        
        # Validate speed
        try:
            speed = int(speed)
            speed = max(0, min(100, speed))
        except:
            return jsonify({"success": False, "error": "Invalid speed value"}), 400
        
        # Update fan speed in database
        db.update_device_status('fan_speed', str(speed), source='manual')
        
        # Record for ML
        db.record_habit('fan', 'speed')
        
        return jsonify({
            "success": True,
            "message": f"Fan speed set to {speed}%",
            "speed": speed,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/voice', methods=['POST'])
def process_voice_command():
    """Process voice command from text - FIXED for door"""
    try:
        data = request.json
        
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400
        
        text = data.get('text', '').strip()
        language = data.get('language', 'english')
        
        if not text:
            return jsonify({"success": False, "error": "No text provided"}), 400
        
        print(f"\n🎤 Voice command: '{text}' ({language})")
        
        # Process the command
        device, action, confidence = voice_processor.process_command(text, language)
        
        # Check if command was recognized
        if not device or not action:
            return jsonify({
                "success": False,
                "message": "Command not recognized",
                "text": text,
                "language": language,
                "suggestions": voice_processor.get_supported_commands(language)
            })
        
        # Store voice command
        db.store_voice_command(text, language, device, action, confidence, True)
        
        # Handle fan speed separately
        if device == 'fan' and action == 'speed':
            speed = voice_processor.extract_speed_value(text)
            db.update_device_status('fan_speed', str(speed), source='voice')
            db.record_habit('fan', 'speed')
            
            return jsonify({
                "success": True,
                "message": f"Fan speed set to {speed}%",
                "device": "fan",
                "action": f"speed_{speed}",
                "speed": speed,
                "confidence": confidence,
                "timestamp": datetime.now().isoformat()
            })
        
        # Regular device control
        if device == 'door':
            db_action = 'LOCKED' if action == 'lock' else 'UNLOCKED'
        else:
            db_action = action.upper()
        
        # Update database
        success = db.update_device_status(device, db_action, source='voice')
        
        if success:
            # Record for ML
            db.record_habit(device, action)
            habit_learner.learn_from_command(device, action)
            
            # Get updated status
            devices = db.get_device_status()
            
            response = {
                "success": True,
                "message": f"Voice command executed",
                "text": text,
                "device": device,
                "action": action,
                "executed_action": db_action,
                "confidence": confidence,
                "language": language,
                "timestamp": datetime.now().isoformat(),
                "devices": devices
            }
            
            # Add language-specific message
            if language == 'hindi':
                response["local_message"] = "आवाज़ कमांड सफल"
            elif language == 'marathi':
                response["local_message"] = "ध्वनी आदेश यशस्वी"
            
            return jsonify(response)
        else:
            return jsonify({
                "success": False,
                "error": "Failed to execute command",
                "text": text
            })
            
    except Exception as e:
        print(f"❌ Voice processing error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/voice-audio', methods=['POST'])
def process_voice_audio():
    """Process voice command from audio file"""
    try:
        if 'audio' not in request.files:
            return jsonify({"success": False, "error": "No audio file"}), 400
        
        audio_file = request.files['audio']
        language = request.form.get('language', 'english')
        
        if audio_file.filename == '':
            return jsonify({"success": False, "error": "Empty file"}), 400
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio:
            audio_file.save(temp_audio.name)
            temp_path = temp_audio.name
        
        try:
            # Convert speech to text
            with sr.AudioFile(temp_path) as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio_data = recognizer.record(source)
                
                # Language mapping for Google Speech Recognition
                lang_map = {
                    'english': 'en-IN',
                    'hindi': 'hi-IN',
                    'marathi': 'mr-IN'
                }
                
                sr_language = lang_map.get(language, 'en-IN')
                
                # Recognize speech
                try:
                    text = recognizer.recognize_google(audio_data, language=sr_language)
                    print(f"🎤 Recognized: '{text}'")
                except sr.UnknownValueError:
                    return jsonify({
                        "success": False,
                        "error": "Could not understand audio",
                        "message": "Please speak clearly"
                    }), 400
                except sr.RequestError:
                    return jsonify({
                        "success": False,
                        "error": "Speech recognition service unavailable"
                    }), 500
                
                # Process the recognized text
                device, action, confidence = voice_processor.process_command(text, language)
                
                if not device or not action:
                    return jsonify({
                        "success": False,
                        "message": "Command not recognized",
                        "recognized_text": text,
                        "suggestions": voice_processor.get_supported_commands(language)
                    })
                
                # Store voice command
                db.store_voice_command(text, language, device, action, confidence, True)
                
                # Handle fan speed
                if device == 'fan' and action == 'speed':
                    speed = voice_processor.extract_speed_value(text)
                    db.update_device_status('fan_speed', str(speed), source='voice')
                    db.record_habit('fan', 'speed')
                    
                    return jsonify({
                        "success": True,
                        "message": f"Fan speed {speed}%",
                        "recognized_text": text,
                        "device": "fan",
                        "action": f"speed_{speed}",
                        "confidence": confidence,
                        "timestamp": datetime.now().isoformat()
                    })
                
                # Regular device control
                if device == 'door':
                    db_action = 'LOCKED' if action == 'lock' else 'UNLOCKED'
                else:
                    db_action = action.upper()
                
                # Update database
                success = db.update_device_status(device, db_action, source='voice')
                
                if success:
                    # Record for ML
                    db.record_habit(device, action)
                    habit_learner.learn_from_command(device, action)
                    
                    devices = db.get_device_status()
                    
                    return jsonify({
                        "success": True,
                        "message": "Voice command executed",
                        "recognized_text": text,
                        "device": device,
                        "action": action,
                        "executed_action": db_action,
                        "confidence": confidence,
                        "language": language,
                        "timestamp": datetime.now().isoformat(),
                        "devices": devices
                    })
                else:
                    return jsonify({
                        "success": False,
                        "error": "Failed to execute",
                        "recognized_text": text
                    })
                    
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
                
    except Exception as e:
        print(f"❌ Audio processing error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/device-feedback', methods=['POST'])
def device_feedback():
    """Receive feedback from ESP32"""
    try:
        data = request.json
        device = data.get('device')
        status = data.get('status')
        esp_id = data.get('esp_id')
        
        print(f"📱 ESP Feedback: {device} = {status}")
        
        # Register ESP32
        if esp_id:
            ip = request.remote_addr
            db.register_esp(esp_id, ip)
        
        return jsonify({"success": True})
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/ml/insights', methods=['GET'])
def get_ml_insights():
    """Get ML insights and predictions"""
    try:
        insights = habit_learner.get_insights()
        
        return jsonify({
            "success": True,
            "insights": insights,
            "auto_control": habit_learner.auto_control_enabled,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/ml/toggle', methods=['POST'])
def toggle_ml():
    """Enable/disable ML automation"""
    try:
        data = request.json
        enabled = data.get('enabled', True)
        
        habit_learner.auto_control_enabled = enabled
        
        return jsonify({
            "success": True,
            "auto_control": enabled,
            "message": f"ML automation {'enabled' if enabled else 'disabled'}"
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/supported-commands', methods=['GET'])
def get_supported_commands():
    """Get supported voice commands"""
    language = request.args.get('language', 'english')
    
    commands = voice_processor.get_supported_commands(language)
    
    return jsonify({
        "success": True,
        "language": language,
        "commands": commands
    })

@app.route('/api/history', methods=['GET'])
def get_history():
    """Get command history"""
    try:
        limit = request.args.get('limit', 20, type=int)
        
        cursor = db.connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT command_text, language, recognized_device, recognized_action, 
                   confidence, executed, timestamp 
            FROM voice_commands 
            ORDER BY timestamp DESC 
            LIMIT %s
        """, (limit,))
        
        history = cursor.fetchall()
        cursor.close()
        
        return jsonify({
            "success": True,
            "history": history,
            "count": len(history)
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({"success": False, "error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"success": False, "error": "Internal server error"}), 500

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🎤 AI SMART HOME BACKEND")
    print("="*60)
    print("✅ Database: MySQL")
    print("✅ Voice: Multi-language")
    print("✅ ML: Habit Learning")
    print("✅ Devices: Light, Fan, Door")
    print("="*60)
    
    # Test database
    if db.test_connection():
        print("✅ Database ready")
    else:
        print("⚠️ Database connection failed")
    
    print("\n🌐 Server starting on: http://0.0.0.0:5000")
    print("="*60 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)