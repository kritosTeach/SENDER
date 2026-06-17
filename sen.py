import streamlit as st
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import time
import base64
import hashlib
import secrets
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# ------------------- ENCRYPTION UTILITIES (unchanged) -------------------
try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad, unpad
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

def aes_encrypt(plaintext: str, key: str, iv: str = None) -> str:
    if not CRYPTO_AVAILABLE:
        return "[ERROR] pycryptodome not installed."
    try:
        key_bytes = hashlib.sha256(key.encode('utf-8')).digest()
        if iv:
            iv_bytes = iv.encode('utf-8')[:16].ljust(16, b'\0')
        else:
            iv_bytes = secrets.token_bytes(16)
        cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
        padded = pad(plaintext.encode('utf-8'), AES.block_size)
        ciphertext = cipher.encrypt(padded)
        result = base64.b64encode(iv_bytes + ciphertext).decode('utf-8')
        return result
    except Exception as e:
        return f"Encryption error: {str(e)}"

def aes_decrypt(ciphertext_b64: str, key: str) -> str:
    if not CRYPTO_AVAILABLE:
        return "[ERROR] pycryptodome not installed."
    try:
        key_bytes = hashlib.sha256(key.encode('utf-8')).digest()
        raw = base64.b64decode(ciphertext_b64)
        iv_bytes = raw[:16]
        ciphertext = raw[16:]
        cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
        decrypted = unpad(cipher.decrypt(ciphertext), AES.block_size)
        return decrypted.decode('utf-8')
    except Exception as e:
        return f"Decryption error: {str(e)}"

def base64_encode(text: str) -> str:
    return base64.b64encode(text.encode('utf-8')).decode('utf-8')

def base64_decode(text: str) -> str:
    try:
        return base64.b64decode(text.encode('utf-8')).decode('utf-8')
    except:
        return "Invalid Base64"

def rot13(text: str) -> str:
    return text.translate(str.maketrans(
        'ABCDEFGHIJKLMabcdefghijklmNOPQRSTUVWXYZnopqrstuvwxyz',
        'NOPQRSTUVWXYZnopqrstuvwxyzABCDEFGHIJKLMabcdefghijklm'
    ))

def rot47(text: str) -> str:
    result = []
    for ch in text:
        if '!' <= ch <= '~':
            result.append(chr(33 + ((ord(ch) - 33 + 47) % 94)))
        else:
            result.append(ch)
    return ''.join(result)

def xor_cipher(text: str, key: str) -> str:
    if not key:
        return "Error: Provide a key for XOR"
    key_bytes = key.encode('utf-8')
    result = []
    for i, ch in enumerate(text):
        result.append(chr(ord(ch) ^ key_bytes[i % len(key_bytes)]))
    return ''.join(result)

def reverse_text(text: str) -> str:
    return text[::-1]

def caesar_cipher(text: str, shift: int) -> str:
    result = []
    for ch in text:
        if ch.isalpha():
            base = 65 if ch.isupper() else 97
            result.append(chr((ord(ch) - base + shift) % 26 + base))
        else:
            result.append(ch)
    return ''.join(result)

def vigenere_encrypt(text: str, key: str) -> str:
    if not key:
        return "Error: Provide a key"
    key = key.upper()
    result = []
    key_index = 0
    for ch in text:
        if ch.isalpha():
            base = 65 if ch.isupper() else 97
            shift = ord(key[key_index % len(key)]) - 65
            result.append(chr((ord(ch) - base + shift) % 26 + base))
            key_index += 1
        else:
            result.append(ch)
    return ''.join(result)

def vigenere_decrypt(text: str, key: str) -> str:
    if not key:
        return "Error: Provide a key"
    key = key.upper()
    result = []
    key_index = 0
    for ch in text:
        if ch.isalpha():
            base = 65 if ch.isupper() else 97
            shift = ord(key[key_index % len(key)]) - 65
            result.append(chr((ord(ch) - base - shift) % 26 + base))
            key_index += 1
        else:
            result.append(ch)
    return ''.join(result)

def atbash(text: str) -> str:
    result = []
    for ch in text:
        if ch.isalpha():
            base = 65 if ch.isupper() else 97
            result.append(chr(base + 25 - (ord(ch) - base)))
        else:
            result.append(ch)
    return ''.join(result)

def to_hex(text: str) -> str:
    return text.encode('utf-8').hex()

def from_hex(hex_str: str) -> str:
    try:
        return bytes.fromhex(hex_str).decode('utf-8')
    except:
        return "Invalid hex"

def generate_hash(text: str, algo="sha256") -> str:
    if algo == "md5":
        return hashlib.md5(text.encode()).hexdigest()
    elif algo == "sha1":
        return hashlib.sha1(text.encode()).hexdigest()
    else:
        return hashlib.sha256(text.encode()).hexdigest()

# ------------------- PAGE CONFIG -------------------
st.set_page_config(page_title="PRO MAILER ENCRYPT - BULK MODE", layout="wide")

st.markdown("<h1 style='text-align: center; color: #00ff41;'>KRITOS SENDER V.1</h1>", unsafe_allow_html=True)

# Initialize session state
if "html_content_editor" not in st.session_state:
    st.session_state.html_content_editor = "<html><body><h1>Hello</h1><p>Secure Email</p></body></html>"

# Layout
col1, col2, col3 = st.columns([1, 1, 2])

with col1:
    st.subheader("⚙️ SMTP SERVERS (FAILOVER LIST)")
    smtp_list_data = st.text_area(
        "SMTP List (one per line: server|port|user|pass)",
        height=200,
        placeholder="smtp.gmail.com|465|user1@gmail.com|pass1\nsmtp.office365.com|587|user2@outlook.com|pass2"
    )
    
    smtp_configs = []
    for line in smtp_list_data.strip().split('\n'):
        line = line.strip()
        if line and '|' in line:
            parts = line.split('|')
            if len(parts) == 4:
                try:
                    port = int(parts[1])
                    smtp_configs.append({
                        'host': parts[0],
                        'port': port,
                        'user': parts[2],
                        'pass': parts[3]
                    })
                except:
                    pass
    
    st.info(f"✅ Loaded {len(smtp_configs)} SMTP servers for failover")
    st.divider()
    delay = st.number_input("Delay between batches (seconds)", value=2, min_value=0)
    
with col2:
    st.subheader("👥 RECIPIENTS")
    recipients_data = st.text_area("Emails (one per line)", height=300, placeholder="target@example.com")
    recipients_list = [e.strip() for e in recipients_data.split('\n') if e.strip()]
    st.info(f"Loaded: {len(recipients_list)} emails")

with col3:
    st.subheader("✉️ MESSAGE")
    from_name = st.text_input("FROM NAME", "Support Team")
    subject = st.text_input("SUBJECT", "Update Notification")
    html_content = st.text_area("HTML CONTENT", height=200, key="html_content_editor")
    
    # Encryption toolbox (unchanged)
    with st.expander("🔐 ENCRYPTION TOOLBOX (Manipulate HTML Content)", expanded=False):
        # ... (all encryption buttons remain exactly as in original)
        # To keep code concise, I omit repeating the full block here.
        # In your final code, paste the entire ENCRYPTION TOOLBOX expander from original.
        st.markdown("*Encryption tools are available in the full version.*")
        # (You must copy the full expander from your original code)

# ------------------- BULK MODE SETTINGS (NEW) -------------------
st.sidebar.markdown("## 🚀 BULK MODE SETTINGS")
bulk_mode = st.sidebar.checkbox("Enable BULK MODE (Concurrent Sending)", value=False)
max_workers = st.sidebar.slider("Max threads (concurrent emails)", min_value=1, max_value=20, value=5, disabled=not bulk_mode)
st.sidebar.info("In BULK MODE, emails are sent in parallel. Failover still works per recipient. Use delay between batches to avoid rate limits.")

# ------------------- SEND CAMPAIGN WITH FAILOVER & BULK -------------------
def send_one_email(recipient, smtp_configs, from_name, subject, html_body):
    """Try to send to a single recipient using failover list. Returns (recipient, success, used_smtp_host)."""
    for smtp in smtp_configs:
        try:
            if smtp['port'] == 465:
                server = smtplib.SMTP_SSL(smtp['host'], smtp['port'], timeout=30)
            else:
                server = smtplib.SMTP(smtp['host'], smtp['port'], timeout=30)
                server.starttls()
            server.login(smtp['user'], smtp['pass'])
            msg = MIMEMultipart()
            msg['From'] = f"{from_name} <{smtp['user']}>"
            msg['To'] = recipient
            msg['Subject'] = subject
            msg.attach(MIMEText(html_body, 'html'))
            server.send_message(msg)
            server.quit()
            return (recipient, True, smtp['host'])
        except Exception as e:
            try:
                server.quit()
            except:
                pass
            continue
    return (recipient, False, None)

if st.button("START CAMPAIGN (WITH FAILOVER)", use_container_width=True):
    if not smtp_configs:
        st.error("Please provide at least one valid SMTP server!")
    elif not recipients_list:
        st.error("Please provide recipients!")
    else:
        success_count = 0
        fail_count = 0
        results = []
        
        st.markdown("### 📤 Sending Progress")
        progress_bar = st.progress(0)
        status_placeholder = st.empty()
        
        if bulk_mode:
            # ----- BULK MODE: parallel sending -----
            status_placeholder.info(f"🚀 BULK MODE active with {max_workers} threads. Sending to {len(recipients_list)} recipients...")
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks
                future_to_recipient = {
                    executor.submit(send_one_email, rec, smtp_configs, from_name, subject, st.session_state.html_content_editor): rec
                    for rec in recipients_list
                }
                # Process as they complete
                for idx, future in enumerate(as_completed(future_to_recipient)):
                    recipient, success, used_host = future.result()
                    if success:
                        st.success(f"✅ [{idx+1}/{len(recipients_list)}] Sent to {recipient} via {used_host}")
                        success_count += 1
                    else:
                        st.error(f"❌ [{idx+1}/{len(recipients_list)}] All SMTPs failed for {recipient}")
                        fail_count += 1
                    progress_bar.progress((idx + 1) / len(recipients_list))
                    # Optional delay between batches: we delay every N emails to avoid flood
                    if delay > 0 and (idx+1) % max_workers == 0:
                        time.sleep(delay)
        else:
            # ----- SEQUENTIAL MODE (original behavior with failover) -----
            current_smtp_idx = 0
            for idx, target in enumerate(recipients_list):
                sent = False
                for attempt_idx in range(current_smtp_idx, len(smtp_configs)):
                    smtp = smtp_configs[attempt_idx]
                    try:
                        status_placeholder.info(f"📡 Trying SMTP {attempt_idx+1}/{len(smtp_configs)}: {smtp['host']}:{smtp['port']} for {target}")
                        if smtp['port'] == 465:
                            server = smtplib.SMTP_SSL(smtp['host'], smtp['port'], timeout=30)
                        else:
                            server = smtplib.SMTP(smtp['host'], smtp['port'], timeout=30)
                            server.starttls()
                        server.login(smtp['user'], smtp['pass'])
                        msg = MIMEMultipart()
                        msg['From'] = f"{from_name} <{smtp['user']}>"
                        msg['To'] = target
                        msg['Subject'] = subject
                        msg.attach(MIMEText(st.session_state.html_content_editor, 'html'))
                        server.send_message(msg)
                        server.quit()
                        st.success(f"✅ [{idx+1}/{len(recipients_list)}] Sent to {target} using {smtp['host']}")
                        current_smtp_idx = attempt_idx
                        sent = True
                        success_count += 1
                        break
                    except Exception as e:
                        st.warning(f"⚠️ SMTP {smtp['host']} failed for {target}: {str(e)[:100]}")
                        try:
                            server.quit()
                        except:
                            pass
                        continue
                if not sent:
                    st.error(f"❌ [{idx+1}/{len(recipients_list)}] All SMTP servers failed for {target}")
                    fail_count += 1
                progress_bar.progress((idx + 1) / len(recipients_list))
                time.sleep(delay)
        
        # Final summary
        st.markdown("---")
        st.success(f"🎉 Campaign finished! Success: {success_count}, Failed: {fail_count}")

# CSS for futuristic theme
st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #00ff41; }
    input, textarea { background-color: #1a1c23 !important; color: #00ff41 !important; border: 1px solid #00ff41 !important; font-family: monospace; }
    .stButton>button { background-color: #00ff41; color: black; font-weight: bold; transition: 0.2s; }
    .stButton>button:hover { background-color: #00cc33; transform: scale(1.02); }
    .st-expander { border: 1px solid #00ff41; border-radius: 8px; }
    .stAlert { background-color: #1a1c23; color: #00ff41; }
</style>
""", unsafe_allow_html=True)

if not CRYPTO_AVAILABLE:
    st.sidebar.warning("🔧 For AES encryption, install: pip install pycryptodome")
else:
    st.sidebar.success("✅ Full encryption suite ready (AES included)")