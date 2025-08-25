from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from flask_mail import Mail, Message
import pandas as pd
import joblib
import traceback
import numpy as np
import io
from datetime import datetime

# --- Initialize Flask App and CORS ---
app = Flask(__name__)
CORS(app)  # Enable Cross-Origin Resource Sharing for frontend communication

# --- Brevo SMTP Config for Email Alerts ---
# This configuration is for the /emergency route
app.config['MAIL_SERVER'] = 'smtp-relay.brevo.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = '957aef001@smtp-brevo.com'  # Your Brevo Login
app.config['MAIL_PASSWORD'] = 'alVwOhdpJxfvMGzS'      # Your Brevo SMTP Key
app.config['MAIL_DEFAULT_SENDER'] = '957aef001@smtp-brevo.com'

# --- Initialize Flask-Mail ---
mail = Mail(app)

# --- Load Machine Learning Model and Scaler ---
try:
    # Ensure these files are in the same directory as app.py
    rf_model = joblib.load("seizure_model.pkl")
    scaler = joblib.load("scaler.pkl")
    print("✅ Model and Scaler loaded successfully.")
except FileNotFoundError as e:
    print(f"❌ Critical Error: Could not find model or scaler file. Make sure 'seizure_model.pkl' and 'scaler.pkl' are present. Details: {e}")
    exit(1) # Exit if essential files are missing
except Exception as e:
    print(f"❌ Error loading model or scaler: {e}")
    exit(1)

# --- Helper function for sending emails (if you have email_alert.py) ---
def send_email_alert(user, maps_link, doctor_email):
    """Function to send an email alert."""
    try:
        msg = Message(
            subject=f"🚨 EMERGENCY ALERT: Seizure Detected for {user}",
            recipients=[doctor_email],
            body=f"""
            This is an automated emergency alert.
            A potential seizure has been detected for user: {user}.

            Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            
            Last known location:
            {maps_link}

            Please take immediate action.
            """,
            html=f"""
            <h3>🚨 Emergency Alert: Seizure Detected</h3>
            <p>This is an automated emergency alert for user: <strong>{user}</strong>.</p>
            <p>A potential seizure event was detected at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.</p>
            <p><strong>Last Known Location:</strong></p>
            <p><a href="{maps_link}" style="font-size: 16px; padding: 10px 20px; background-color: #d9534f; color: white; text-decoration: none; border-radius: 5px;">View on Google Maps</a></p>
            <p>Please take immediate action.</p>
            """
        )
        mail.send(msg)
        print(f"✅ Email alert sent successfully to {doctor_email}")
    except Exception as e:
        print(f"❌ Failed to send email alert: {e}")
        # In a real app, you might have fallback notifications here.


# --- Flask Routes ---

@app.route('/')
def index():
    """Serves the main file upload page."""
    # This assumes you have an index.html in a 'templates' folder
    return render_template('index.html')

@app.route('/results.html')
def results():
    """Serves the results page."""
    # This assumes you have a results.html in a 'templates' folder
    return render_template('results.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    """
    Handles file upload, runs prediction, and returns data for the results page.
    """
    print("\n📂 File upload request received.")
    if 'file' not in request.files:
        print("❌ Error: No file part in request.")
        return jsonify({"error": "No file part in the request"}), 400
    
    file = request.files['file']
    if file.filename == '':
        print("❌ Error: No file selected.")
        return jsonify({"error": "No file selected for upload"}), 400

    try:
        # Read the CSV file into a pandas DataFrame
        data = pd.read_csv(file)
        print(f"📄 CSV file '{file.filename}' read successfully. Shape: {data.shape}")

        # --- VALIDATION ---
        # 1. Check if the number of columns matches what the model expects
        expected_features = scaler.n_features_in_
        if data.shape[1] != expected_features:
            error_msg = f"Invalid CSV format. Expected {expected_features} columns, but got {data.shape[1]}."
            print(f"❌ {error_msg}")
            return jsonify({"error": error_msg}), 400
            
        # 2. Check if the required columns for display exist
        display_columns = ['heart_rate', 'temperature', 'spo2', 'vibration_intensity']
        # We assume the original CSV has these headers for the results page
        # A more robust solution would be to map column indices if headers are absent
        if not all(col in data.columns for col in display_columns):
             # Create a list of missing columns for a helpful error message
            missing_cols = [col for col in display_columns if col not in data.columns]
            error_msg = f"CSV is missing required columns for display: {', '.join(missing_cols)}. Please ensure the CSV has these headers."
            print(f"❌ {error_msg}")
            return jsonify({'error': error_msg}), 400

        # --- PREDICTION ---
        # Scale the data using the loaded scaler
        X_scaled = scaler.transform(data)
        
        # Predict using the loaded Random Forest model
        y_pred = rf_model.predict(X_scaled)
        
        # Consolidate results: if any row predicts a seizure, the overall result is "Seizure"
        # This is a safe approach for medical alerts.
        final_prediction = "Seizure Detected" if 1 in y_pred else "Safe"
        print(f"🧠 Prediction complete. Overall result: {final_prediction}")
        
        # --- DATA PREPARATION FOR FRONTEND ---
        # Select only the necessary columns for the results page table
        data_for_frontend = data[display_columns].to_json(orient='records')

        # --- SUCCESS RESPONSE ---
        # Send both the prediction and the table data back to the frontend
        return jsonify({
            'prediction': final_prediction,
            'csv_data': data_for_frontend
        })

    except Exception as e:
        # Catch any other errors during processing
        print(f"\n❌ An unexpected error occurred: {traceback.format_exc()}")
        return jsonify({"error": f"An internal error occurred: {str(e)}"}), 500


@app.route('/emergency', methods=['POST'])
def emergency_alert():
    """
    Receives emergency data (like location) and triggers an email alert.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid request format"}), 400

    user = data.get("user", "Unknown User")
    lat = data.get("lat")
    lon = data.get("lon")
    doctor_email = data.get("doctor_email")

    if not all([lat, lon, doctor_email]):
        return jsonify({"error": "Missing required data: lat, lon, or doctor_email"}), 400

    maps_link = f"https://www.google.com/maps?q={lat},{lon}"
    print(f"\n🚨 Emergency Alert Triggered for user '{user}' to doctor '{doctor_email}'")
    
    # Call the function to dispatch the email
    send_email_alert(user, maps_link, doctor_email)

    return jsonify({
        "status": "Emergency alert sent",
        "maps_link": maps_link
    })


if __name__ == '__main__':
    # Runs the Flask server
    # host='0.0.0.0' makes it accessible on your local network
    app.run(host='0.0.0.0', port=5000, debug=True)

