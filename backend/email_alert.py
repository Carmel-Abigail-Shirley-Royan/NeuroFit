# import smtplib
# from email.mime.text import MIMEText
# def send_email_alert(user, maps_link, doctor_email):
#     sender = "957aef001@smtp-brevo.com"
#     receiver = doctor_email
#     subject = f"🚨 Seizure Alert for {user}"
#     body = f"{user} has had a seizure.\n\nLive location: {maps_link}"

#     msg = MIMEText(body)
#     msg['Subject'] = subject
#     msg['From'] = sender
#     msg['To'] = receiver

#     try:
#         with smtplib.SMTP('smtp-relay.brevo.com', 587) as server:
#             server.starttls()
#             server.login("957aef001@smtp-brevo.com", "alVwOhdpJxfvMGzS")  # <-- Must be App Password
#             server.sendmail(sender, receiver, msg.as_string())
#         print(f"✅ Email sent to {receiver}")
#     except Exception as e:
#         print(f"❌ Email failed: {e}")



import resend
from dotenv import load_dotenv
import os
load_dotenv()

# Set API key directly (for quick testing)
resend.api_key = os.getenv("RESEND_API_KEY")

def send_email_alert(user, maps_link, doctor_email):
    try:
        r = resend.Emails.send({
            "from": "onboarding@resend.dev",   # default verified sender
            "to": doctor_email,
            "subject": f"🚨 Seizure Alert for {user}",
            "html": f"""
                <h2>🚨 Emergency Alert</h2>
                <p><strong>{user}</strong> may be experiencing a seizure.</p>
                <p>📍 <a href="{maps_link}">View Live Location on Google Maps</a></p>
                <p>NeuroGuard<br/>Seizure Detection System</p>
            """
        })
        print(f"✅ Email sent to {doctor_email}, id: {r['id']}")
    except Exception as e:
        print(f"❌ Resend email failed: {e}")
