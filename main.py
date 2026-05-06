import os
import random
import string
import time
import requests
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- কাস্টম ডোমেইন কনফিগারেশন ---
# আপনি এখানে আপনার ৫-৬টি ডোমেইন লিস্ট করে রাখতে পারেন। 
# বর্তমানে প্রথমটি (index 0) ডিফল্ট হিসেবে কাজ করবে।
CUSTOM_DOMAINS = [
    "pay.teamsbapp.com",
    "gateway.teamsbapp.com",
    "api.teamsbapp.com"
]
# ------------------------------

DB_URL = os.getenv("DB_URL", "https://voter-tools-bot-default-rtdb.asia-southeast1.firebasedatabase.app").rstrip("/")
DB_SECRET = os.getenv("DB_SECRET", "i6GYcCX7hPOC8oTiHvzyvZEQHPag4Lt1ZxlizSxe")

class PaymentRequest(BaseModel):
    webhook: str
    name: str
    key: str
    amount: str
    user_id: str
    domain: str

def get_base_url(request: Request) -> str:
    scheme = request.headers.get("x-forwarded-proto", "http")
    host = request.headers.get("host", "localhost")
    return f"{scheme}://{host}"

def update_fb_status(pid: str, updates: dict):
    fb_url = f"{DB_URL}/payments/{pid}.json?auth={DB_SECRET}"
    try:
        requests.patch(fb_url, json=updates, timeout=10)
    except:
        pass

def send_webhook(url: str, payload: dict) -> bool:
    try:
        resp = requests.post(url, json=payload, timeout=10)
        return resp.status_code == 200
    except:
        return False


def render_message(
    message: str, 
    refresh: int = 0, 
    loader: bool = False, 
    name: str = "", 
    amount: str = "", 
    theme: str = "info",
    pid: str = "",
    txn_id: str = "",
    payment_method: str = "",
    created_at: int = 0
) -> HTMLResponse:        
    refresh_tag = f'<meta http-equiv="refresh" content="{refresh}">' if refresh > 0 else ""        
            
    # Premium Theme configuration        
    if theme == "success":        
        color_primary = "#059669" # Emerald 600
        color_bg = "#ecfdf5"      # Emerald 50
        color_border = "#a7f3d0"  # Emerald 200
        icon_svg = '''<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>'''
        status_label = "Completed Successfully"
    elif theme == "error":        
        color_primary = "#dc2626" # Red 600
        color_bg = "#fef2f2"      # Red 50
        color_border = "#fecaca"  # Red 200
        icon_svg = '''<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>'''        
        status_label = "Transaction Failed"
    elif theme == "warning":        
        color_primary = "#d97706" # Amber 600
        color_bg = "#fffbeb"      # Amber 50
        color_border = "#fde68a"  # Amber 200
        icon_svg = '''<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>'''        
        status_label = "Attention Required"
    else:        
        color_primary = "#2563eb" # Blue 600
        color_bg = "#eff6ff"      # Blue 50
        color_border = "#bfdbfe"  # Blue 200
        icon_svg = '''<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="5" width="20" height="14" rx="2"></rect><line x1="2" y1="10" x2="22" y2="10"></line></svg>'''        
        status_label = "Processing Payment"

    # Compile the details section conditionally
    details_html = ""
    if name or amount or pid or txn_id:
        rows = []
        if amount:
            rows.append(f'''
            <div class="receipt-row highlight-row">
                <span class="receipt-label">Amount Due</span>
                <span class="receipt-value amount-value">{amount}</span>
            </div>
            ''')
        if name:
            rows.append(f'''
            <div class="receipt-row">
                <span class="receipt-label">Customer Name</span>
                <span class="receipt-value">{name}</span>
            </div>
            ''')
        if pid:
            rows.append(f'''
            <div class="receipt-row">
                <span class="receipt-label">Payment ID</span>
                <span class="receipt-value mono">{pid}</span>
            </div>
            ''')
        if txn_id:
            rows.append(f'''
            <div class="receipt-row">
                <span class="receipt-label">Transaction Ref</span>
                <span class="receipt-value mono">{txn_id}</span>
            </div>
            ''')
        if payment_method:
            rows.append(f'''
            <div class="receipt-row">
                <span class="receipt-label">Payment Method</span>
                <span class="receipt-value capitalize">{payment_method}</span>
            </div>
            ''')
            
        date_script = ""
        date_row = ""
        if created_at > 0:
            date_row = '''
            <div class="receipt-row">
                <span class="receipt-label">Date & Time</span>
                <span class="receipt-value" id="tx-date">Loading...</span>
            </div>
            '''
            date_script = f'''
            <script>
                document.addEventListener("DOMContentLoaded", () => {{
                    const d = new Date({created_at} * 1000);
                    document.getElementById('tx-date').innerText = d.toLocaleString(undefined, {{
                        year: 'numeric', month: 'short', day: 'numeric', 
                        hour: '2-digit', minute: '2-digit'
                    }});
                }});
            </script>
            '''
            rows.append(date_row)

        details_html = f"""
        <div class="receipt-card">
            <div class="receipt-header">Transaction Details</div>
            <div class="receipt-body">
                {''.join(rows)}
            </div>
        </div>
        {date_script}
        """

    # Premium loader component
    loader_html = ""        
    if loader:        
        loader_html = f"""        
        <div class="processing-container">
            <div class="modern-spinner"></div>
            <div class="processing-steps">
                <div class="step active">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
                    <span>Session Initialized</span>
                </div>
                <div class="step active pulse">
                    <div class="step-dot" style="background: {color_primary}"></div>
                    <span>Securing Connection</span>
                </div>
                <div class="step pending">
                    <div class="step-dot"></div>
                    <span>Awaiting Gateway</span>
                </div>
            </div>
        </div>
        """        
        
    html = f"""        
    <!DOCTYPE html>        
    <html lang="en">        
    <head>        
        <meta charset="UTF-8">        
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">        
        <title>SBPay | Secure Payment Checkout</title>        
        {refresh_tag}
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
        <style>        
            :root {{
                --bg-color: #f3f4f6;
                --card-bg: #ffffff;
                --text-main: #111827;
                --text-muted: #6b7280;
                --border-light: #e5e7eb;
                --theme-primary: {color_primary};
                --theme-bg: {color_bg};
                --theme-border: {color_border};
            }}

            * {{        
                box-sizing: border-box;        
                -webkit-tap-highlight-color: transparent;
                margin: 0;
                padding: 0;
            }}        
            
            body {{        
                font-family: 'Inter', system-ui, -apple-system, sans-serif;        
                background-color: var(--bg-color);
                background-image: radial-gradient(circle at 50% 0%, #ffffff 0%, transparent 70%);
                min-height: 100vh;        
                display: flex;        
                flex-direction: column;        
                align-items: center;
                color: var(--text-main);        
            }}        
                    
            /* Header */        
            header {{        
                width: 100%;
                padding: 2rem 1.5rem;
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 0.5rem;
            }}        
            .brand-container {{
                display: flex;
                align-items: center;
                gap: 0.75rem;
            }}
            .brand-logo {{        
                width: 42px;        
                height: 42px;        
                border-radius: 50%;
                object-fit: cover;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            }}        
            .brand-name {{
                font-size: 1.5rem;
                font-weight: 700;
                letter-spacing: -0.02em;
                color: var(--text-main);
            }}
            .secure-badge-top {{
                display: inline-flex;
                align-items: center;
                gap: 0.25rem;
                background: #f3f4f6;
                border: 1px solid var(--border-light);
                padding: 4px 10px;
                border-radius: 100px;
                font-size: 0.75rem;
                font-weight: 600;
                color: var(--text-muted);
                text-transform: uppercase;
                letter-spacing: 0.05em;
            }}
        
            /* Main Content Container */        
            main {{        
                flex-grow: 1;        
                width: 100%;
                max-width: 480px;
                padding: 0 1.25rem 2rem 1.25rem;
                display: flex;
                flex-direction: column;
                justify-content: center;
            }}        
            
            .checkout-card {{        
                background: var(--card-bg);        
                border-radius: 24px;        
                box-shadow: 0 20px 40px -15px rgba(0, 0, 0, 0.05), 0 0 0 1px rgba(0,0,0,0.03);
                overflow: hidden;
                animation: fadeUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards;
                opacity: 0;
                transform: translateY(15px);
            }}        

            @keyframes fadeUp {{        
                to {{ opacity: 1; transform: translateY(0); }}        
            }}        

            /* Status Banner section inside card */
            .status-banner {{
                padding: 2.5rem 2rem 1.5rem 2rem;
                display: flex;
                flex-direction: column;
                align-items: center;
                text-align: center;
                border-bottom: 1px solid var(--border-light);
                background: linear-gradient(180deg, var(--theme-bg) 0%, rgba(255,255,255,0) 100%);
            }}
        
            .icon-wrapper {{        
                width: 64px;        
                height: 64px;        
                background-color: var(--card-bg);        
                color: var(--theme-primary);        
                border-radius: 50%;        
                display: flex;        
                align-items: center;        
                justify-content: center;        
                margin-bottom: 1.25rem;
                box-shadow: 0 8px 16px -4px var(--theme-border), 0 0 0 1px var(--theme-border);
            }}        
            .icon-wrapper svg {{        
                width: 32px;        
                height: 32px;        
            }}        
            
            .status-label {{
                font-size: 0.875rem;
                font-weight: 600;
                color: var(--theme-primary);
                text-transform: uppercase;
                letter-spacing: 0.05em;
                margin-bottom: 0.5rem;
            }}

            h1 {{        
                font-size: 1.25rem;        
                font-weight: 600;        
                color: var(--text-main);        
                line-height: 1.4;        
                margin: 0;
            }}        
        
            /* Details Receipt Area */
            .card-body {{
                padding: 1.5rem 2rem;
                background: #ffffff;
            }}

            .receipt-card {{        
                background: #fafafa;
                border: 1px dashed var(--border-light);
                border-radius: 12px;        
                margin-bottom: 1.5rem;        
                overflow: hidden;
            }}        
            .receipt-header {{
                padding: 0.75rem 1.25rem;
                background: #f3f4f6;
                font-size: 0.75rem;
                font-weight: 600;
                color: var(--text-muted);
                text-transform: uppercase;
                letter-spacing: 0.05em;
                border-bottom: 1px dashed var(--border-light);
            }}
            .receipt-body {{
                padding: 0.5rem 1.25rem;
            }}
            .receipt-row {{        
                display: flex;        
                justify-content: space-between;        
                align-items: center;        
                padding: 0.75rem 0;        
            }}        
            .receipt-row:not(:last-child) {{        
                border-bottom: 1px solid var(--border-light);        
            }}        
            .highlight-row {{
                border-bottom: 2px solid var(--border-light) !important;
                margin-bottom: 0.25rem;
                padding-bottom: 1rem;
            }}
            .receipt-label {{        
                color: var(--text-muted);        
                font-size: 0.875rem;        
                font-weight: 500;        
            }}        
            .receipt-value {{        
                font-weight: 600;        
                color: var(--text-main);        
                font-size: 0.875rem;        
                text-align: right;
            }}        
            .amount-value {{        
                font-size: 1.25rem;        
                color: var(--text-main);        
            }}        
            .mono {{
                font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
                font-size: 0.8rem;
                color: #4b5563;
                background: #f3f4f6;
                padding: 2px 6px;
                border-radius: 4px;
            }}
            .capitalize {{ text-transform: capitalize; }}
        
            /* Loader / Processing Area */        
            .processing-container {{        
                display: flex;
                flex-direction: column;
                align-items: center;
                background: #fafafa;
                border-radius: 12px;
                padding: 1.5rem;
                border: 1px solid var(--border-light);
            }}        
            
            .modern-spinner {{
                width: 36px;
                height: 36px;
                border: 3px solid var(--theme-border);
                border-top-color: var(--theme-primary);
                border-radius: 50%;
                animation: spin 0.8s linear infinite;
                margin-bottom: 1.5rem;
            }}

            .processing-steps {{
                width: 100%;
                display: flex;
                flex-direction: column;
                gap: 0.75rem;
            }}

            .step {{
                display: flex;
                align-items: center;
                gap: 0.75rem;
                font-size: 0.875rem;
                font-weight: 500;
            }}
            .step.active {{ color: var(--text-main); }}
            .step.pending {{ color: var(--text-muted); opacity: 0.7; }}
            
            .step svg {{
                width: 16px; height: 16px; color: var(--theme-primary);
            }}
            .step-dot {{
                width: 16px; height: 16px; 
                border-radius: 50%;
                background: var(--border-light);
                position: relative;
            }}
            .step.pulse .step-dot::after {{
                content: ''; position: absolute; top: 0; left: 0; right: 0; bottom: 0;
                border-radius: 50%; background: inherit;
                animation: ping 1.5s cubic-bezier(0, 0, 0.2, 1) infinite;
                opacity: 0.5;
            }}

            @keyframes spin {{ to {{ transform: rotate(360deg); }} }}        
            @keyframes ping {{ 75%, 100% {{ transform: scale(2); opacity: 0; }} }}
        
            /* Footer */        
            footer {{        
                width: 100%;
                padding: 2rem 1rem;        
                text-align: center;        
            }}        
            .trust-strip {{
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 0.5rem;
            }}
            .trust-logos {{
                display: flex;
                gap: 1rem;
                color: #9ca3af;
                margin-bottom: 0.5rem;
            }}
            .trust-logos svg {{ width: 24px; height: 24px; }}

            .footer-text {{        
                font-size: 0.75rem;        
                color: #9ca3af;        
                font-weight: 500;        
                display: flex;
                align-items: center;
                gap: 4px;
            }}        
        
            @media (max-width: 480px) {{        
                header {{ padding: 1.5rem 1rem; }}        
                .checkout-card {{ border-radius: 20px; }}
                .status-banner {{ padding: 2rem 1.5rem 1.25rem 1.5rem; }}
                .card-body {{ padding: 1.25rem 1.5rem; }}
                .receipt-card {{ border-radius: 10px; }}
                h1 {{ font-size: 1.125rem; }}        
            }}        
        </style>        
    </head>        
    <body>        
        
        <header>        
            <div class="brand-container">
                <img src="https://sbsakib.eu.cc/api/logo.jpeg" alt="Gateway Logo" class="brand-logo">        
                <span class="brand-name">Gateway</span>
            </div>
            <div class="secure-badge-top">
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
                Secure Checkout
            </div>
        </header>        
        
        <main>        
            <div class="checkout-card">        
                <div class="status-banner">
                    <div class="icon-wrapper">        
                        {icon_svg}        
                    </div>        
                    <div class="status-label">{status_label}</div>
                    <h1>{message}</h1>        
                </div>
                
                <div class="card-body">
                    {details_html}        
                    {loader_html}        
                </div>
            </div>        
        </main>        
        
        <footer>        
            <div class="trust-strip">
                <div class="trust-logos">
                    <svg viewBox="0 0 24 24" fill="currentColor"><path d="M20 4H4c-1.11 0-1.99.89-1.99 2L2 18c0 1.11.89 2 2 2h16c1.11 0 2-.89 2-2V6c0-1.11-.89-2-2-2zm0 14H4v-6h16v6zm0-10H4V6h16v2z"/></svg>
                    <svg viewBox="0 0 24 24" fill="currentColor"><path d="M11.8 10.9c-2.27-.59-3-1.2-3-2.15 0-1.09 1.01-1.85 2.7-1.85 1.78 0 2.44.85 2.5 2.1h2.21c-.07-1.72-1.12-3.3-3.21-3.81V3h-3v2.16c-1.94.42-3.5 1.68-3.5 3.61 0 2.31 1.91 3.46 4.7 4.13 2.5.6 3 1.48 3 2.41 0 .69-.49 1.79-2.7 1.79-2.06 0-2.87-.92-2.98-2.1h-2.2c.12 2.19 1.76 3.42 3.68 3.83V21h3v-2.15c1.95-.37 3.5-1.5 3.5-3.55 0-2.84-2.43-3.81-4.7-4.4z"/></svg>
                </div>
                <div class="footer-text">        
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>
                    End-to-End Encrypted • Powered by SBPay
                </div>        
            </div>
        </footer>        
        
    </body>        
    </html>        
    """        
    return HTMLResponse(html) 



def process_payment_bg(pid: str, req: PaymentRequest, base_url: str):
    # এখানে রিকোয়েস্টের ডোমেইন ব্যবহারের পরিবর্তে আমরা CUSTOM_DOMAINS এর প্রথম ডোমেইনটি ব্যবহার করছি।
    # আপনি চাইলে লজিক পরিবর্তন করে CUSTOM_DOMAINS[1] বা অন্য ইনডেক্স ব্যবহার করতে পারেন।
    target_domain = CUSTOM_DOMAINS[0].rstrip("/")
    cp_url = f"https://{target_domain}/api/payment/create" 
    
    success_url = f"{base_url}/?id={pid}"
    cancel_url = f"{base_url}/?id={pid}"

    cb_payload = {
        "cus_name": req.name,
        "cus_email": "none@example.com",
        "amount": req.amount,
        "success_url": success_url,
        "cancel_url": cancel_url,
        "metadata": {"user_id": req.user_id}
    }
    
    headers = {
        "API-KEY": req.key,
        "SECRET-KEY": req.key,
        "BRAND-KEY": req.key,
        "Content-Type": "application/json"
    }

    try:
        cp_resp = requests.post(cp_url, json=cb_payload, headers=headers, timeout=15)
        cp_data = cp_resp.json()
        payment_url = cp_data.get("payment_url", "")
        
        if payment_url:
            update_fb_status(pid, {"gateway_payment_url": payment_url, "status": "ready"})
        else:
            update_fb_status(pid, {"status": "failed", "error": "Missing payment_url in gateway response"})
    except Exception as e:
        update_fb_status(pid, {"status": "failed", "error": str(e)})

@app.get("/")
def root(request: Request):
    txn_id = request.query_params.get("transactionId", "")
    pid = request.query_params.get("id", "")
    status_param = request.query_params.get("status", "")

    if txn_id and pid:
        fb_url = f"{DB_URL}/payments/{pid}.json?auth={DB_SECRET}"
        try:
            resp = requests.get(fb_url, timeout=10)
            data = resp.json()
        except:
            return render_message("System securely connecting. Please try again.", theme="error")

        if not data:
            return render_message("Invalid or expired payment session.", theme="error")

        current_status = data.get("status", "")
        created_at = data.get("created_at", 0)
        
        if current_status not in ["creating", "ready"]:
            return render_message("This transaction has already been processed.", theme="warning", name=data.get("name"), amount=data.get("amount"), pid=pid, txn_id=txn_id, created_at=created_at)

        req_status = status_param.lower()

        if req_status in ["failed", "cancel", "cancelled", "error"]:
            send_webhook(data["webhook"], {"ok": False})
            update_fb_status(pid, {"status": "cancelled"})
            return render_message("Payment cancelled. You may close this window and return to Telegram.", theme="error", name=data.get("name"), amount=data.get("amount"), pid=pid, created_at=created_at)

        if req_status in ["completed", "success"]:
            # ভেরিফিকেশনের জন্যও CUSTOM_DOMAINS ব্যবহার করা হচ্ছে
            domain = CUSTOM_DOMAINS[0].rstrip("/")
            key = data["key"]
            verify_url = f"https://{domain}/api/payment/verify"
            headers = {
                "API-KEY": key,
                "SECRET-KEY": key,
                "BRAND-KEY": key,
                "Content-Type": "application/json"
            }
            
            try:
                v_resp = requests.post(verify_url, json={"transaction_id": txn_id}, headers=headers, timeout=15)
                v_data = v_resp.json()
                
                if v_data.get("status") == "COMPLETED":
                    wh_success = send_webhook(data["webhook"], {"ok": True})
                    if wh_success:
                        payment_method = request.query_params.get("paymentMethod", "")
                        update_fb_status(pid, {
                            "status": "completed",
                            "transaction_id": txn_id,
                            "payment_method": payment_method,
                            "payment_amount": request.query_params.get("paymentAmount", ""),
                            "payment_fee": request.query_params.get("paymentFee", "")
                        })
                        return render_message("Payment confirmed successfully. You may now return to Telegram.", theme="success", name=data.get("name"), amount=data.get("amount"), pid=pid, txn_id=txn_id, payment_method=payment_method, created_at=created_at)
                    else:
                        update_fb_status(pid, {"status": "webhook_failed"})
                        return render_message("Webhook delivery failed. Please contact support.", theme="error", pid=pid, txn_id=txn_id, created_at=created_at)
                else:
                    send_webhook(data["webhook"], {"ok": False})
                    update_fb_status(pid, {"status": "verify_failed"})
                    return render_message("Payment verification failed. Please return to Telegram.", theme="error", pid=pid, txn_id=txn_id, created_at=created_at)
            except:
                send_webhook(data["webhook"], {"ok": False})
                update_fb_status(pid, {"status": "verify_failed"})
                return render_message("Gateway timeout during verification.", theme="error", pid=pid, txn_id=txn_id, created_at=created_at)

        return render_message("Unknown payment status received.", theme="error", pid=pid, txn_id=txn_id, created_at=created_at)

    try:
        with open("index.html", "r") as f:
            html_content = f.read()
        return HTMLResponse(html_content)
    except:
        return HTMLResponse("<h1>SBPay Secure Payment Gateway Middleware</h1>")

@app.post("/api")
def create_payment(req: PaymentRequest, request: Request, bg_tasks: BackgroundTasks):
    pid = "".join(random.choices(string.digits, k=10))
    base_url = get_base_url(request)

    fb_url = f"{DB_URL}/payments/{pid}.json?auth={DB_SECRET}"
    fb_payload = {
        "id": pid,
        "name": req.name,
        "amount": req.amount,
        "user_id": req.user_id,
        "webhook": req.webhook,
        "gateway_domain": CUSTOM_DOMAINS[0].rstrip("/"), # এখানেও কাস্টম ডোমেইন সেভ হচ্ছে
        "key": req.key,
        "gateway_payment_url": "",
        "status": "creating",
        "error": "",
        "created_at": int(time.time())
    }
    
    try:
        requests.put(fb_url, json=fb_payload, timeout=10)
    except:
        pass

    bg_tasks.add_task(process_payment_bg, pid, req, base_url)

    return JSONResponse({
        "ok": True,
        "id": pid,
        "payment_url": f"{base_url}/pay/{pid}",
        "status": "creating"
    })

@app.get("/pay/{pid}")
def pay_redirect(pid: str):
    fb_url = f"{DB_URL}/payments/{pid}.json?auth={DB_SECRET}"
    try:
        resp = requests.get(fb_url, timeout=10)
        data = resp.json()
    except:
        return render_message("System securely connecting. Please try again.", theme="error")

    if not data:
        return render_message("Invalid or expired payment session.", theme="error")

    status = data.get("status")
    name = data.get("name", "")
    amount = data.get("amount", "")
    created_at = data.get("created_at", 0)

    if status == "creating":
        return render_message("Preparing your secure payment session...", refresh=3, loader=True, name=name, amount=amount, theme="info", pid=pid, created_at=created_at)
    elif status == "ready":
        payment_url = data.get("gateway_payment_url")
        if payment_url:
            return RedirectResponse(url=payment_url)
        else:
            return render_message("Payment gateway link is currently unavailable.", theme="error", pid=pid, created_at=created_at)
    elif status == "failed":
        return render_message("Payment session could not be established.", name=name, amount=amount, theme="error", pid=pid, created_at=created_at)
    else:
        return render_message(f"This payment session is no longer active.", name=name, amount=amount, theme="warning", pid=pid, created_at=created_at)
