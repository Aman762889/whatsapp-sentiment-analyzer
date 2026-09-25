from flask import Flask, render_template, request, jsonify
import re
import zipfile
import io

app = Flask(__name__)

GOOD_WORDS = {
    "good", "happy", "great", "awesome", "love", "thanks", "nice", 
    "congrats", "best", "helpful", "sweet", "care", "wonderful", 
    "haha", "lol", "😄", "😍", "🎉", "😊", "❤️", "👍",
    "accha", "acha", "sahi", "mast", "badiya", "badhiya", "pyar", 
    "pyaar", "dost", "yara", "yaar", "shukriya", "dhanyawad", "khoobsurat", 
    "sundar", "wah", "zabardast", "zabrdata", "bhai", "op", "kya"
}

BAD_WORDS = {
    "bad", "hate", "angry", "worst", "stupid", "fool", "fake", 
    "boring", "useless", "shut up", "idiot", "cheat", "liar", 
    "ugly", "crap", "😡", "🤬", "👎", "💔", "🖕",
    "bakwas", "bekar", "kutta", "kamina", "pagal", "paagal", "gadha", 
    "chutiya", "ganda", "jhuta", "jhootha", "bewakoof", "ghatiya", 
    "mar", "dhat", "hat", "faktu", "faltu", "laura", "benchod", "madarchod", 
    "fuck", "randi", "lund", "madarchod randi ka bacha"
}

def analyze_message(message):
    msg_lower = message.lower()
    good_score = sum(1 for word in GOOD_WORDS if word in msg_lower)
    bad_score = sum(1 for word in BAD_WORDS if word in msg_lower)
    
    if good_score > bad_score:
        return "positive"
    elif bad_score > good_score:
        return "negative"
    else:
        return "neutral"

def parse_whatsapp_log(file_content):
    lines = file_content.splitlines()
    stats = {}
    
    for line in lines:
        line_clean = line.strip()
        sender, message = None, None
        
        if ":" in line_clean:
            if line_clean.startswith("["):
                parts = line_clean.split("] ", 1)
                if len(parts) > 1 and ":" in parts[1]:
                    sender, message = parts[1].split(":", 1)
            elif " - " in line_clean:
                parts = line_clean.split(" - ", 1)
                if len(parts) > 1 and ":" in parts[1]:
                    sender, message = parts[1].split(":", 1)
                    
        if sender and message:
            sender = sender.strip()
            message = message.strip()
            
            if "Messages and calls are end-to-end encrypted" in message:
                continue
                
            if sender not in stats:
                stats[sender] = {"total": 0, "positive": 0, "negative": 0, "neutral": 0, "media": 0}
                
            # Detect attached media indicators
            is_media = any(tag in message.lower() for tag in [
                "<attached:", "file attached", "omitted", ".jpg", ".png", ".mp4", ".opus", ".webp"
            ])
            
            if is_media:
                stats[sender]["media"] += 1
                stats[sender]["total"] += 1
            else:
                sentiment = analyze_message(message)
                stats[sender]["total"] += 1
                stats[sender][sentiment] += 1
            
    return stats

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
        
    file = request.files['file']
    filename = file.filename.lower()
    
    try:
        content = ""
        # Handle uploaded zip file directly
        if filename.endswith('.zip'):
            zip_bytes = io.BytesIO(file.read())
            with zipfile.ZipFile(zip_bytes, 'r') as z:
                txt_files = [f for f in z.namelist() if f.endswith('.txt')]
                if not txt_files:
                    return jsonify({"error": "No chat .txt file found inside zip"}), 400
                
                raw_bytes = z.read(txt_files[0])
                try:
                    content = raw_bytes.decode('utf-8-sig')
                except UnicodeDecodeError:
                    content = raw_bytes.decode('latin-1', errors='ignore')
        # Handle standalone .txt file
        elif filename.endswith('.txt'):
            raw_bytes = file.read()
            try:
                content = raw_bytes.decode('utf-8-sig')
            except UnicodeDecodeError:
                content = raw_bytes.decode('latin-1', errors='ignore')
        else:
            return jsonify({"error": "Please upload a .txt or .zip file"}), 400
            
        results = parse_whatsapp_log(content)
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": f"Failed to parse file: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)