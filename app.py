#!/usr/bin/env python3

import streamlit as st
import time
import threading
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import requests
import os
import sqlite3
import hashlib
import json
from datetime import datetime
import subprocess
import sys

# ChromeDriver fix function (Kept for compatibility)
def install_chromedriver():
    try:
        subprocess.run([
            sys.executable, "-m", "pip", "install", 
            "webdriver-manager==4.0.1", "--no-cache-dir"
        ], capture_output=True, check=True)
        
        from webdriver_manager.chrome import ChromeDriverManager
        driver_path = ChromeDriverManager().install()
        return driver_path
    except Exception as e:
        print(f"ChromeDriver install failed: {e}")
        return None

# Database setup (No changes needed)
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_configs (
            user_id INTEGER PRIMARY KEY,
            chat_id TEXT,
            name_prefix TEXT,
            delay INTEGER DEFAULT 10,
            cookies TEXT,
            messages TEXT,
            automation_running BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS admin_e2ee_threads (
            user_id INTEGER,
            thread_id TEXT,
            chat_type TEXT,
            cookies_hash TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, cookies_hash)
        )
    ''')
    
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(username, password):
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        c.execute('SELECT id FROM users WHERE username = ?', (username,))
        if c.fetchone():
            return False, "Username already exists"
        
        password_hash = hash_password(password)
        c.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', 
                 (username, password_hash))
        user_id = c.lastrowid
        
        c.execute('''
            INSERT INTO user_configs 
            (user_id, chat_id, name_prefix, delay, cookies, messages) 
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, '', '[LORD DEVIL]', 10, '', 'Hello!\nHow are you?'))
        
        conn.commit()
        conn.close()
        return True, "User created successfully"
    except Exception as e:
        return False, f"Error creating user: {str(e)}"

def verify_user(username, password):
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        password_hash = hash_password(password)
        c.execute('SELECT id FROM users WHERE username = ? AND password_hash = ?', 
                 (username, password_hash))
        result = c.fetchone()
        conn.close()
        
        return result[0] if result else None
    except:
        return None

def get_user_config(user_id):
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        c.execute('''
            SELECT chat_id, name_prefix, delay, cookies, messages 
            FROM user_configs WHERE user_id = ?
        ''', (user_id,))
        result = c.fetchone()
        conn.close()
        
        if result:
            return {
                'chat_id': result[0] or '',
                'name_prefix': result[1] or '',
                'delay': result[2] or 10,
                'cookies': result[3] or '',
                'messages': result[4] or 'Hello!'
            }
        return None
    except:
        return None

def update_user_config(user_id, chat_id, name_prefix, delay, cookies, messages):
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        c.execute('''
            INSERT OR REPLACE INTO user_configs 
            (user_id, chat_id, name_prefix, delay, cookies, messages, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (user_id, chat_id, name_prefix, delay, cookies, messages))
        
        conn.commit()
        conn.close()
        return True
    except:
        return False

def get_automation_running(user_id):
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        c.execute('SELECT automation_running FROM user_configs WHERE user_id = ?', (user_id,))
        result = c.fetchone()
        conn.close()
        
        return result[0] if result else False
    except:
        return False

def set_automation_running(user_id, running):
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        c.execute('UPDATE user_configs SET automation_running = ? WHERE user_id = ?', 
                 (running, user_id))
        conn.commit()
        conn.close()
        return True
    except:
        return False

def get_username(user_id):
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        c.execute('SELECT username FROM users WHERE id = ?', (user_id,))
        result = c.fetchone()
        conn.close()
        
        return result[0] if result else "Unknown"
    except:
        return "Unknown"

# Initialize database
init_db()

# Streamlit App Configuration
st.set_page_config(
    page_title="LORD DEVIL E2EE FACEBOOK CONVO",
    page_icon="🔒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# UI Styles (Kept as is)
custom_css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
    
    * {
        font-family: 'Poppins', sans-serif;
    }
    
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
    }
    
    .main-header h1 {
        color: white;
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
    }
    
    .main-header p {
        color: rgba(255,255,255,0.9);
        font-size: 1.1rem;
        margin-top: 0.5rem;
    }
    
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
    }
    
    .login-box {
        background: white;
        padding: 3rem;
        border-radius: 20px;
        box-shadow: 0 20px 60px rgba(0,0,0,0.1);
        max-width: 500px;
        margin: 2rem auto;
    }
    
    .success-box {
        background: linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 1rem 0;
    }
    
    .error-box {
        background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 1rem 0;
    }
    
    .footer {
        text-align: center;
        padding: 2rem;
        color: #667eea;
        font-weight: 600;
        margin-top: 3rem;
    }
    
    .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stNumberInput>div>div>input {
        border-radius: 10px;
        border: 2px solid #e0e0e0;
        padding: 0.75rem;
        transition: all 0.3s ease;
    }
    
    .stTextInput>div>div>input:focus, .stTextArea>div>div>textarea:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2);
    }
    
    .info-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        margin: 1rem 0;
    }
    
    .log-container {
        background: #1e1e1e;
        color: #00ff00;
        padding: 1rem;
        border-radius: 10px;
        font-family: 'Courier New', monospace;
        max-height: 400px;
        overflow-y: auto;
    }
    
    .status-running { color: green; font-weight: bold; font-size: 18px; }
    .status-stopped { color: red; font-weight: bold; font-size: 18px; }
</style>
"""

st.markdown(custom_css, unsafe_allow_html=True)

# Session State & Automation State (No changes needed here)
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'username' not in st.session_state:
    st.session_state.username = None
if 'automation_running' not in st.session_state:
    st.session_state.automation_running = False
if 'logs' not in st.session_state:
    st.session_state.logs = []
if 'message_count' not in st.session_state:
    st.session_state.message_count = 0

class AutomationState:
    def __init__(self):
        self.running = False
        self.message_count = 0
        self.logs = []
        self.message_rotation_index = 0

if 'automation_state' not in st.session_state:
    st.session_state.automation_state = AutomationState()

if 'auto_start_checked' not in st.session_state:
    st.session_state.auto_start_checked = False

def log_message(msg, automation_state=None):
    timestamp = time.strftime("%H:%M:%S")
    formatted_msg = f"[{timestamp}] {msg}"
    
    if automation_state:
        automation_state.logs.append(formatted_msg)
    else:
        if 'logs' in st.session_state:
            st.session_state.logs.append(formatted_msg)

# setup_browser function (No changes needed)
def setup_browser(automation_state=None):
    log_message('Setting up Chrome browser...', automation_state)
    
    chrome_options = Options()
    
    # Essential options for headless mode
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--remote-debugging-port=9222')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    # Anti-detection measures
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Streamlit Cloud compatible paths
    CHROME_PATH = r"/usr/bin/chromium"
    CHROMEDRIVER_PATH = r"/usr/bin/chromedriver"
    
    # SYSTEM PATH DETECTION
    if os.path.exists(CHROMEDRIVER_PATH):
        log_message(f'Found ChromeDriver at: {CHROMEDRIVER_PATH}', automation_state)
    if os.path.exists(CHROME_PATH):
        log_message(f'Found Chrome at: {CHROME_PATH}', automation_state)
    
    driver = None
    
    try:
        # Approach 1: Direct system chromedriver (Streamlit Cloud)
        if os.path.exists(CHROMEDRIVER_PATH):
            service = Service(CHROMEDRIVER_PATH)
            if os.path.exists(CHROME_PATH):
                chrome_options.binary_location = CHROME_PATH
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            log_message('Chrome started with system chromedriver!', automation_state)
            return driver
    except Exception as e:
        log_message(f'System chromedriver failed: {e}', automation_state)
    
    try:
        # Approach 2: webdriver-manager with chromium
        from webdriver_manager.chrome import ChromeDriverManager
        from webdriver_manager.core.os_manager import ChromeType
        
        service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        log_message('Chrome started with webdriver-manager (Chromium)!', automation_state)
        return driver
    except Exception as e:
        log_message(f'Webdriver-manager Chromium failed: {e}', automation_state)
    
    try:
        # Approach 3: webdriver-manager standard chrome
        from webdriver_manager.chrome import ChromeDriverManager
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        log_message('Chrome started with webdriver-manager (Chrome)!', automation_state)
        return driver
    except Exception as e:
        log_message(f'Webdriver-manager Chrome failed: {e}', automation_state)
    
    try:
        # Approach 4: Direct Chrome without service
        driver = webdriver.Chrome(options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        log_message('Chrome started with auto-detect!', automation_state)
        return driver
    except Exception as e:
        log_message(f'Auto-detect failed: {e}', automation_state)
    
    # Final fallback
    log_message('All ChromeDriver methods failed!', automation_state)
    raise Exception("ChromeDriver setup failed - Please check Streamlit Cloud logs")

# find_message_input function (OPTIMIZED SELECTORS APPLIED HERE)
def find_message_input(driver, process_id, automation_state=None):
    log_message(f'{process_id}: Finding message input...', automation_state)
    
    time.sleep(5)
    
    # Scroll up and down to ensure the element is loaded into the viewport
    try:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(2)
    except Exception:
        pass
    
    message_input_selectors = [
        # ✅ TOP PRIORITY (CONFIRMED E2EE SELECTORS - Your Feedback)
        'div[role="textbox"][contenteditable="true"][data-lexical-editor="true"]', # 1. E2EE BEST
        'div[data-lexical-editor="true"]',                                       # 2. E2EE FALLBACK
        'div[contenteditable="true"][role="textbox"]',                           # 3. UNIVERSAL FALLBACK
        'div[aria-label="Message"][contenteditable="true"]',                     # 4. KEYWORD FALLBACK
    ]
    
    log_message(f'{process_id}: Trying {len(message_input_selectors)} Confirmed Selectors...', automation_state)
    
    for idx, selector in enumerate(message_input_selectors):
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            log_message(f'{process_id}: Selector {idx+1}/{len(message_input_selectors)} found {len(elements)} elements', automation_state)
            
            for element in elements:
                try:
                    # Check if the element is actually editable (contenteditable or textarea/input)
                    is_editable = driver.execute_script("""
                        return arguments[0].contentEditable === 'true' || 
                               arguments[0].tagName === 'TEXTAREA' || 
                               arguments[0].tagName === 'INPUT';
                    """, element)
                    
                    if is_editable:
                        # Log HTML for debugging selector issue
                        element_html = driver.execute_script("return arguments[0].outerHTML;", element)
                        log_message(f'{process_id}: Potential HTML (Start): {element_html[:150]}...', automation_state)
                        
                        if element.is_displayed() and element.is_enabled():
                            log_message(f'{process_id}: Found **Editable & Visible** element with selector #{idx+1}', automation_state)
                            
                            time.sleep(2)
                            
                            try:
                                element.click()
                                time.sleep(1)
                            except:
                                driver.execute_script("arguments[0].click();", element)
                                time.sleep(1)
                            
                            # Small confirmation check (mostly for logging)
                            element_text = driver.execute_script("""
                                return arguments[0].placeholder || 
                                       arguments[0].getAttribute('aria-label') || 
                                       arguments[0].getAttribute('aria-placeholder') || 
                                       arguments[0].getAttribute('data-placeholder') || '';
                            """, element).lower()
                            
                            keywords = ['message', 'write', 'type', 'send', 'chat', 'msg', 'reply', 'text']
                            if any(keyword in element_text for keyword in keywords) or idx < 4: # Prioritize the confirmed list
                                log_message(f'{process_id}: Confirmed message input!', automation_state)
                                return element
                except Exception as e:
                    # Ignore errors for non-editable or hidden elements
                    continue
                    
        except Exception as e:
            # Ignore errors for selector failure
            continue
    
    log_message(f'{process_id}: No message input found after all selectors', automation_state)
    return None

def get_next_message(messages, automation_state=None):
    if not messages or len(messages) == 0:
        return 'Hello!'
    
    if automation_state:
        message = messages[automation_state.message_rotation_index % len(messages)]
        automation_state.message_rotation_index += 1
    else:
        message = messages[0]
    
    return message

# send_messages function (ROBUST SENDING LOGIC APPLIED HERE)
def send_messages(config, automation_state, user_id, process_id='AUTO-1'):
    driver = None
    try:
        log_message(f'{process_id}: Starting automation...', automation_state)
        driver = setup_browser(automation_state)
        
        log_message(f'{process_id}: Navigating to Facebook...', automation_state)
        driver.get('https://www.facebook.com/')
        time.sleep(6)
        
        if config['cookies'] and config['cookies'].strip():
            log_message(f'{process_id}: Adding cookies...', automation_state)
            cookie_array = config['cookies'].split(';')
            for cookie in cookie_array:
                cookie_trimmed = cookie.strip()
                if cookie_trimmed:
                    first_equal_index = cookie_trimmed.find('=')
                    if first_equal_index > 0:
                        name = cookie_trimmed[:first_equal_index].strip()
                        value = cookie_trimmed[first_equal_index + 1:].strip()
                        try:
                            driver.add_cookie({
                                'name': name,
                                'value': value,
                                'domain': '.facebook.com',
                                'path': '/'
                            })
                        except Exception:
                            pass
        
        if config['chat_id']:
            chat_id = config['chat_id'].strip()
            log_message(f'{process_id}: Opening conversation {chat_id}...', automation_state)
            
            driver.get(f'https://www.facebook.com/messages/e2ee/t/{chat_id}')
            log_message(f'{process_id}: Trying URL: https://www.facebook.com/messages/e2ee/t/{chat_id}', automation_state)
        else:
            log_message(f'{process_id}: Opening messages...', automation_state)
            driver.get('https://www.facebook.com/messages')
        
        log_message(f'{process_id}: Waiting 60+ seconds for page load...', automation_state)
        time.sleep(65)
        
        message_input = find_message_input(driver, process_id, automation_state)
        
        if not message_input:
            log_message(f'{process_id}: Message input not found!', automation_state)
            automation_state.running = False
            return 0
        
        log_message(f'{process_id}: Ready to send messages!', automation_state)
        
        delay = int(config['delay'])
        messages_sent = 0
        messages_list = [msg.strip() for msg in config['messages'].split('\n') if msg.strip()]
        
        if not messages_list:
            messages_list = ['Hello!']
        
        while automation_state.running and messages_sent < 100:
            base_message = get_next_message(messages_list, automation_state)
            
            if config['name_prefix']:
                message_to_send = f"{config['name_prefix']} {base_message}"
            else:
                message_to_send = base_message
            
            try:
                # Type message using JavaScript for stability
                driver.execute_script("""
                    const element = arguments[0];
                    const message = arguments[1];
                    
                    element.focus();
                    element.click();
                    
                    if (element.tagName === 'DIV' && element.contentEditable === 'true') {
                        element.innerHTML = '';
                        element.innerText = message;
                    } else if (element.tagName === 'TEXTAREA' || element.tagName === 'INPUT') {
                        element.value = '';
                        element.value = message;
                    } else {
                        element.textContent = '';
                        element.textContent = message;
                    }
                    
                    element.dispatchEvent(new Event('input', { bubbles: true, cancelable: true }));
                    element.dispatchEvent(new Event('change', { bubbles: true, cancelable: true }));
                    element.dispatchEvent(new Event('keydown', { bubbles: true, cancelable: true }));
                """, message_input, message_to_send)
                
                time.sleep(2)
                
                sent = False
                
                # 💥 FIX 2: Primary attempt - Send using ENTER key (Most reliable for contenteditable divs)
                try:
                    message_input.send_keys(Keys.ENTER)
                    log_message(f'{process_id}: Sent via Enter key (Primary)', automation_state)
                    sent = True
                except Exception as e:
                    pass 
                
                time.sleep(1) # Small delay
                
                # 💥 FIX 3: Fallback to Send Button Click
                if not sent:
                    send_buttons = driver.find_elements(By.CSS_SELECTOR, 
                        '[aria-label*="Send" i], [data-testid="send-button"], button[type="submit"]')
                    for btn in send_buttons:
                        if btn.is_displayed() and btn.is_enabled():
                            driver.execute_script("arguments[0].click();", btn)
                            sent = True
                            log_message(f'{process_id}: Send button clicked (Secondary)', automation_state)
                            break
                
                time.sleep(1) 
                
                # 💥 FIX 4: JavaScript ENTER event (Final fallback)
                if not sent:
                    driver.execute_script("""
                        const element = arguments[0];
                        element.dispatchEvent(new KeyboardEvent('keydown', {
                            key: 'Enter',
                            code: 'Enter', 
                            keyCode: 13,
                            which: 13,
                            bubbles: true
                        }));
                    """, message_input)
                    log_message(f'{process_id}: Sent via JavaScript event (Fallback)', automation_state)
                    sent = True
                
                # Log final result and proceed
                if sent:
                    time.sleep(2) # Give FB time to process
                    messages_sent += 1
                    automation_state.message_count = messages_sent
                    log_message(f'{process_id}: Message {messages_sent} sent: "{message_to_send}"', automation_state)
                    time.sleep(delay)
                else:
                    log_message(f'{process_id}: Failed to send message in all attempts!', automation_state)
                    break # Break the while loop if sending failed
                
            except Exception as e:
                log_message(f'{process_id}: Error sending message: {str(e)}', automation_state)
                break
        
        log_message(f'{process_id}: Automation stopped! Total messages sent: {messages_sent}', automation_state)
        automation_state.running = False
        return messages_sent
        
    except Exception as e:
        log_message(f'{process_id}: Fatal error: {str(e)}', automation_state)
        automation_state.running = False
        return 0
    finally:
        if driver:
            try:
                driver.quit()
                log_message(f'{process_id}: Browser closed', automation_state)
            except:
                pass

# THREADING APPROACH WITH RERUN AT END OF THREAD (No changes needed)
def run_automation_with_notification(user_config, username, automation_state, user_id):
    send_messages(user_config, automation_state, user_id)
    set_automation_running(user_id, False)
    st.rerun() 

def start_automation(user_config, user_id):
    automation_state = st.session_state.automation_state
    
    if automation_state.running:
        return
    
    automation_state.running = True
    automation_state.message_count = 0
    automation_state.logs = [] # Logs cleared on start
    automation_state.message_rotation_index = 0
    
    set_automation_running(user_id, True)
    
    username = get_username(user_id)
    thread = threading.Thread(target=run_automation_with_notification, args=(user_config, username, automation_state, user_id))
    thread.daemon = True
    thread.start()
    
    st.rerun() # Turant UI update kar do to show 'Running'

def stop_automation(user_id):
    st.session_state.automation_state.running = False
    set_automation_running(user_id, False)
    st.rerun() # Turant UI update kar do to show 'Stopped'

# MAIN UI FUNCTION (Session State Crash Fix Applied Here)
def main():
    st.markdown('<div class="main-header"><h1>LORD DEVIL E2EE FACEBOOK CONVO</h1><p>Created by LORD DEVIL</p></div>', unsafe_allow_html=True)

    if not st.session_state.logged_in:
        tab1, tab2 = st.tabs(["Login", "Sign Up"])
        
        with tab1:
            st.markdown("### Welcome Back!")
            username = st.text_input("Username", key="login_username", placeholder="Enter your username")
            password = st.text_input("Password", key="login_password", type="password", placeholder="Enter your password")
            
            if st.button("Login", key="login_btn", use_container_width=True):
                if username and password:
                    user_id = verify_user(username, password)
                    if user_id:
                        st.session_state.logged_in = True
                        st.session_state.user_id = user_id
                        st.session_state.username = username
                        
                        should_auto_start = get_automation_running(user_id)
                        if should_auto_start:
                            user_config = get_user_config(user_id)
                            if user_config and user_config['chat_id']:
                                start_automation(user_config, user_id)
                        
                        st.success(f"Welcome back, {username}!")
                        st.rerun()
                    else:
                        st.error("Invalid username or password!")
                else:
                    st.warning("Please enter both username and password")
        
        with tab2:
            st.markdown("### Create New Account")
            new_username = st.text_input("Choose Username", key="signup_username", placeholder="Choose a unique username")
            new_password = st.text_input("Choose Password", key="signup_password", type="password", placeholder="Create a strong password")
            confirm_password = st.text_input("Confirm Password", key="confirm_password", type="password", placeholder="Re-enter your password")
            
            if st.button("Create Account", key="signup_btn", use_container_width=True):
                if new_username and new_password and confirm_password:
                    if new_password == confirm_password:
                        success, message = create_user(new_username, new_password)
                        if success:
                            st.success(f"{message} Please login now!")
                        else:
                            st.error(f"{message}")
                    else:
                        st.error("Passwords do not match!")
                else:
                    st.warning("Please fill all fields")

    else:
        if not st.session_state.auto_start_checked and st.session_state.user_id:
            st.session_state.auto_start_checked = True
            should_auto_start = get_automation_running(st.session_state.user_id)
            if should_auto_start and not st.session_state.automation_state.running:
                user_config = get_user_config(st.session_state.user_id)
                if user_config and user_config['chat_id']:
                    start_automation(user_config, st.session_state.user_id)
        
        st.sidebar.markdown(f"### {st.session_state.username}")
        st.sidebar.markdown(f"**User ID:** {st.session_state.user_id}")
        
        if st.sidebar.button("Logout", use_container_width=True):
            if st.session_state.automation_state.running:
                stop_automation(st.session_state.user_id)
            
            st.session_state.logged_in = False
            st.session_state.user_id = None
            st.session_state.username = None
            st.session_state.automation_running = False
            st.session_state.auto_start_checked = False
            st.rerun()
        
        user_config = get_user_config(st.session_state.user_id)
        
        if user_config:
            tab1, tab2 = st.tabs(["Configuration", "Automation"])
            
            with tab1:
                st.markdown("### Your Configuration")
                
                chat_id = st.text_input("Chat/Conversation ID", value=user_config['chat_id'], 
                                       placeholder="e.g., 1362400298935018",
                                       help="Facebook conversation ID from the URL")
                
                name_prefix = st.text_input("Name Prefix", value=user_config['name_prefix'],
                                           placeholder="e.g., [LORD DEVIL]",
                                           help="Prefix to add before each message")
                
                delay = st.number_input("Delay (seconds)", min_value=1, max_value=300, 
                                       value=user_config['delay'],
                                       help="Wait time between messages")
                
                messages = st.text_area("Messages (one per line)", 
                                      value=user_config['messages'],
                                      placeholder="Hello!\nHow are you?\nThis is automated",
                                      height=100,
                                      help="Each line will be sent as a separate message")
                
                cookies = st.text_area("Facebook Cookies (optional)", 
                                      value=user_config['cookies'] if user_config['cookies'] else "",
                                      placeholder="Paste your Facebook cookies here",
                                      height=100,
                                      help="Your cookies are encrypted and stored securely")
                
                if st.button("Save Configuration", use_container_width=True):
                    final_cookies = cookies if cookies.strip() else user_config['cookies']
                    success = update_user_config(
                        st.session_state.user_id,
                        chat_id,
                        name_prefix,
                        delay,
                        final_cookies,
                        messages
                    )
                    if success:
                        st.success("Configuration saved successfully!")
                        st.rerun()
                    else:
                        st.error("Error saving configuration!")
            
            with tab2:
                st.markdown("### Automation Control")
                
                # 💥 FIX 1: Replit Session State Safety Check Applied Here
                if not hasattr(st.session_state, 'automation_state') or \
                   not hasattr(st.session_state.automation_state, 'message_count'):
                    # Temporary safe re-initialization if Streamlit fails to load it properly
                    st.session_state.automation_state = AutomationState()
                    
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Messages Sent", st.session_state.automation_state.message_count)
                
                with col2:
                    status = "Running" if st.session_state.automation_state.running else "Stopped"
                    st.metric("Status", status)
                
                with col3:
                    st.metric("Total Logs", len(st.session_state.automation_state.logs))
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("Start Automation", disabled=st.session_state.automation_state.running, use_container_width=True):
                        current_config = get_user_config(st.session_state.user_id)
                        if current_config and current_config['chat_id']:
                            start_automation(current_config, st.session_state.user_id)
                        else:
                            st.error("Please configure Chat ID first!")
                
                with col2:
                    if st.button("Stop Automation", disabled=not st.session_state.automation_state.running, use_container_width=True):
                        stop_automation(st.session_state.user_id)
                
                st.markdown("### Live Logs")
                
                if st.session_state.automation_state.logs:
                    logs_html = '<div class="log-container">'
                    # Display the last 20 logs
                    for log in st.session_state.automation_state.logs[-20:]: 
                        logs_html += f'<div>{log}</div>'
                    logs_html += '</div>'
                    st.markdown(logs_html, unsafe_allow_html=True)
                else:
                    st.info("No logs yet. Start automation to see logs here.")

    st.markdown('<div class="footer">Made with by LORD DEVIL | 2025 All Rights Reserved</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
