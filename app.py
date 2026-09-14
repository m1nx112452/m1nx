import os
import psutil
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from pyrogram import Client

app = Flask(__name__)
app.secret_key = "super_secret_admin_key"

# এডমিন ইউজারনেম ও পাসওয়ার্ড
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "password123"

# মেমোরি স্টোরেজ (প্রয়োজন অনুযায়ী ডাটাবেজ যুক্ত করতে পারেন)
bot_list = []
active_sessions = {}

def get_ram_usage():
    process = psutil.Process(os.getpid())
    return round(process.memory_info().rss / (1024 * 1024), 2)  # MB তে রিটার্ন করবে

@app.route('/')
def home():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] == ADMIN_USERNAME and request.form['password'] == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        return render_template('login.html', error="Invalid Credentials")
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    ram_mb = get_ram_usage()
    return render_template('dashboard.html', bots=bot_list, ram_usage=ram_mb)

# ১. ওটিপি রিকোয়েস্ট পাঠানো
@app.route('/api/send_otp', methods=['POST'])
def send_otp():
    phone = request.form.get('phone_number')
    api_id = request.form.get('api_id')
    api_hash = request.form.get('api_hash')
    
    try:
        client = Client(f"session_{phone}", api_id=api_id, api_hash=api_hash)
        client.connect()
        sent_code = client.send_code(phone)
        active_sessions[phone] = {
            'client': client,
            'phone_code_hash': sent_code.phone_code_hash
        }
        return jsonify({"status": "success", "message": "OTP Sent Successfully"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

# ২. ওটিপি ভেরিফাই ও ইউজারবট কানেক্ট
@app.route('/api/verify_otp', methods=['POST'])
def verify_otp():
    phone = request.form.get('phone_number')
    otp = request.form.get('otp')
    
    session_data = active_sessions.get(phone)
    if not session_data:
        return jsonify({"status": "error", "message": "Session not found"})
        
    client = session_data['client']
    phone_code_hash = session_data['phone_code_hash']
    
    try:
        client.sign_in(phone, phone_code_hash, otp)
        string_session = client.export_session_string()
        client.disconnect()
        return jsonify({"status": "success", "session_string": string_session})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

# ৩. বটের ইউজারনেম অ্যাড/ডিলিট
@app.route('/api/add_bot', methods=['POST'])
def add_bot():
    username = request.form.get('bot_username')
    if username and username not in bot_list:
        bot_list.append(username)
    return redirect(url_for('dashboard'))

@app.route('/api/delete_bot/<username>')
def delete_bot(username):
    if username in bot_list:
        bot_list.remove(username)
    return redirect(url_for('dashboard'))

# ৪. বাইপাস এপিআই এন্ডপয়েন্ট
@app.route('/api/bypass')
def bypass_api():
    url = request.args.get('url')
    if not url:
        return jsonify({"error": "No URL provided"}), 400
    
    bypassed_url = f"https://bypassed-link.com?result={url}"
    return jsonify({"original_url": url, "bypassed_url": bypassed_url, "status": "Success"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
