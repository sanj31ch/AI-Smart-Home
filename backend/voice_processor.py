# voice_processor.py - Complete Voice Processing Module
import re
import difflib

class VoiceProcessor:
    def __init__(self):
        # Complete command patterns for all languages
        self.commands = {
            'english': {
                'light': {
                    'keywords': ['light', 'lights', 'bulb', 'lamp'],
                    'on': ['on', 'turn on', 'switch on', 'enable'],
                    'off': ['off', 'turn off', 'switch off', 'disable']
                },
                'fan': {
                    'keywords': ['fan', 'fans', 'blower', 'cooler'],
                    'on': ['on', 'turn on', 'switch on', 'start'],
                    'off': ['off', 'turn off', 'switch off', 'stop'],
                    'speed': ['speed', 'set speed', 'change speed', 'fan speed']
                },
                'door': {
                    'keywords': ['door', 'gate', 'lock', 'entrance'],
                    'lock': ['lock', 'close', 'secure', 'bolt'],
                    'unlock': ['unlock', 'open', 'release']
                }
            },
            'hindi': {
                'light': {
                    'keywords': ['लाइट', 'बल्ब', 'रोशनी', 'दीपक'],
                    'on': ['चालू', 'ऑन', 'जला', 'जलाओ'],
                    'off': ['बंद', 'ऑफ', 'बुझा', 'बुझाओ']
                },
                'fan': {
                    'keywords': ['पंखा', 'फैन', 'पवनक', 'हवा'],
                    'on': ['चालू', 'ऑन', 'घुमाओ'],
                    'off': ['बंद', 'ऑफ', 'बंद करो'],
                    'speed': ['स्पीड', 'गति', 'रफ्तार']
                },
                'door': {
                    'keywords': ['दरवाजा', 'गेट', 'ताला', 'किवाड़'],
                    'lock': ['बंद', 'लॉक', 'ताला लगाओ'],
                    'unlock': ['खोल', 'अनलॉक', 'ताला खोलो']
                }
            },
            'marathi': {
                'light': {
                    'keywords': ['दिवा', 'लाइट', 'बल्ब', 'प्रकाश'],
                    'on': ['चालू', 'ऑन', 'लाव', 'लावा'],
                    'off': ['बंद', 'ऑफ', 'विझव', 'विझवा']
                },
                'fan': {
                    'keywords': ['पंखा', 'फॅन', 'पवनक'],
                    'on': ['चालू', 'ऑन', 'सुरू'],
                    'off': ['बंद', 'ऑफ', 'बंद कर'],
                    'speed': ['स्पीड', 'गती', 'वेग']
                },
                'door': {
                    'keywords': ['दरवाजा', 'गेट', 'कुलूप', 'दार'],
                    'lock': ['बंद', 'लॉक', 'कुलूप लाव'],
                    'unlock': ['उघड', 'अनलॉक', 'कुलूप उघड']
                }
            }
        }
    
    def process_command(self, text, language='english'):
        """Process voice command and return device, action, confidence"""
        text = text.lower().strip()
        
        # Default to English if language not supported
        if language not in self.commands:
            language = 'english'
        
        # Try exact matching first
        result = self.exact_match(text, language)
        if result[0]:
            return result
        
        # Try fuzzy matching
        result = self.fuzzy_match(text, language)
        if result[0]:
            return result
        
        # Try keyword matching
        result = self.keyword_match(text, language)
        if result[0]:
            return result
        
        return None, None, 0.0
    
    def exact_match(self, text, language):
        """Try exact pattern matching"""
        patterns = {
            'english': {
                'light on': ('light', 'on'),
                'light off': ('light', 'off'),
                'fan on': ('fan', 'on'),
                'fan off': ('fan', 'off'),
                'fan speed': ('fan', 'speed'),
                'lock door': ('door', 'lock'),
                'unlock door': ('door', 'unlock'),
                'door lock': ('door', 'lock'),
                'door unlock': ('door', 'unlock')
            },
            'hindi': {
                'लाइट चालू': ('light', 'on'),
                'लाइट बंद': ('light', 'off'),
                'पंखा चालू': ('fan', 'on'),
                'पंखा बंद': ('fan', 'off'),
                'दरवाजा बंद': ('door', 'lock'),
                'दरवाजा खोल': ('door', 'unlock')
            },
            'marathi': {
                'दिवा चालू': ('light', 'on'),
                'दिवा बंद': ('light', 'off'),
                'पंखा चालू': ('fan', 'on'),
                'पंखा बंद': ('fan', 'off'),
                'दरवाजा बंद': ('door', 'lock'),
                'दरवाजा उघड': ('door', 'unlock')
            }
        }
        
        if language in patterns:
            for pattern, (device, action) in patterns[language].items():
                if pattern in text:
                    return device, action, 1.0
        
        return None, None, 0.0
    
    def fuzzy_match(self, text, language):
        """Use fuzzy string matching"""
        lang_commands = self.commands[language]
        
        # Split text into words
        words = text.split()
        
        # Check each word for device keywords
        detected_device = None
        detected_action = None
        
        # Find device
        for device, device_data in lang_commands.items():
            for keyword in device_data['keywords']:
                if keyword in text:
                    detected_device = device
                    break
            if detected_device:
                break
        
        if not detected_device:
            return None, None, 0.0
        
        # Find action based on device
        if detected_device == 'fan':
            # Check for speed commands
            if 'speed' in text or any(word in text for word in lang_commands['fan']['speed']):
                return 'fan', 'speed', 0.8
        
        # Check for on/off/lock/unlock
        if detected_device == 'light' or detected_device == 'fan':
            for action in ['on', 'off']:
                for keyword in lang_commands[detected_device][action]:
                    if keyword in text:
                        return detected_device, action, 0.9
        
        elif detected_device == 'door':
            for action in ['lock', 'unlock']:
                for keyword in lang_commands['door'][action]:
                    if keyword in text:
                        return 'door', action, 0.9
        
        return None, None, 0.0
    
    def keyword_match(self, text, language):
        """Simple keyword matching"""
        text_lower = text.lower()
        
        # Device keywords
        if any(word in text_lower for word in ['light', 'लाइट', 'दिवा']):
            if any(word in text_lower for word in ['on', 'चालू', 'ऑन']):
                return 'light', 'on', 0.7
            elif any(word in text_lower for word in ['off', 'बंद', 'ऑफ']):
                return 'light', 'off', 0.7
        
        elif any(word in text_lower for word in ['fan', 'पंखा', 'फैन', 'फॅन']):
            if any(word in text_lower for word in ['on', 'चालू', 'ऑन']):
                return 'fan', 'on', 0.7
            elif any(word in text_lower for word in ['off', 'बंद', 'ऑफ']):
                return 'fan', 'off', 0.7
            elif any(word in text_lower for word in ['speed', 'स्पीड', 'गति', 'गती']):
                return 'fan', 'speed', 0.7
        
        elif any(word in text_lower for word in ['door', 'दरवाजा', 'गेट']):
            if any(word in text_lower for word in ['lock', 'बंद', 'लॉक']):
                return 'door', 'lock', 0.7
            elif any(word in text_lower for word in ['unlock', 'खोल', 'उघड']):
                return 'door', 'unlock', 0.7
        
        return None, None, 0.0
    
    def extract_speed_value(self, text):
        """Extract speed value from command (0-100)"""
        numbers = re.findall(r'\d+', text)
        if numbers:
            speed = int(numbers[0])
            return min(max(speed, 0), 100)
        return 50  # Default speed
    
    def get_supported_commands(self, language='english'):
        """Get example commands for UI"""
        examples = {
            'english': [
                "Light on", "Light off",
                "Fan on", "Fan off", "Fan speed 50",
                "Lock door", "Unlock door"
            ],
            'hindi': [
                "लाइट चालू", "लाइट बंद",
                "पंखा चालू", "पंखा बंद", "पंखा स्पीड 50",
                "दरवाजा बंद", "दरवाजा खोल"
            ],
            'marathi': [
                "दिवा चालू", "दिवा बंद",
                "पंखा चालू", "पंखा बंद", "पंखा स्पीड 50",
                "दरवाजा बंद", "दरवाजा उघड"
            ]
        }
        return examples.get(language, examples['english'])