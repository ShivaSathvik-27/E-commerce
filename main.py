from random import randint
from flask import Flask, Response, render_template, request, redirect, url_for,jsonify,session
from flask_mail import Mail, Message
from sklearn.preprocessing import LabelEncoder
from joblib import load
import pandas as pd
import pyrebase
import requests
import firebase_admin
from firebase_admin import auth, credentials

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yb345677829'  # Add a secret key for session management
ZEROBOUNCE_API_ENDPOINT = 'https://api.zerobounce.net/v2/validate'
ZEROBOUNCE_API_KEY = '8416b4f53b7b4a44929e31310bdab74a'
# Configure Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_TLS'] = False  # Use SSL, not TLS
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = 'hemanthd2429@gmail.com'  
app.config['MAIL_PASSWORD'] = 'zmoalxdykkkxzwas'  
app.config['MAIL_DEFAULT_SENDER'] = 'noreply@example.com'

#check git push

mail = Mail(app)

# Add your own Firebase configuration
config = {
 "apiKey": "AIzaSyBi3lUri8UKhtDgjzPfI9QUQxZPO_sva78",
  "authDomain": "major-9e2f4.firebaseapp.com",
  "databaseURL": "https://major-9e2f4-default-rtdb.firebaseio.com",
  "projectId": "major-9e2f4",
  "storageBucket": "major-9e2f4.appspot.com",
  "messagingSenderId": "512642884212",
  "appId": "1:512642884212:web:074a518577291379052721"
}


otp = randint(100000, 999999)  # Generate a 6-digit OTP
cred = credentials.Certificate("C:\\Users\\damer\\Desktop\\ma\\python-firebase-flask-login-master\\major-9e2f4-firebase-adminsdk-1j8c9-93031c0855.json")
firebase_admin.initialize_app(cred)
firebase = pyrebase.initialize_app(config)
auth = firebase.auth()
db = firebase.database()

person = {"is_logged_in": False, "name": "", "email": "", "uid": ""}

@app.route("/")
def login():
    return render_template("login.html")

@app.route("/signup")
def signup():
    return render_template("signup.html")
@app.route("/email")
def email():
    return render_template("email1.html")
@app.route("/success")
def success():
    return render_template("success.html")
@app.route("/login_page")
def login_page():
    return render_template("login.html")
@app.route("/logout")
def logout():
    # Clear the session data
    
    # Redirect the user to the login page
    return render_template("login.html")

@app.route("/welcome")
def welcome():
    if person["is_logged_in"]:
        return render_template("welcome.html", email=person["email"], name=person["name"])
    else:
        return redirect(url_for('login'))

@app.route("/result", methods=["POST", "GET"])
def result():
    if request.method == "POST":
        result = request.form
        email = result["email"]
        password = result["pass"]
        try:
            user = auth.sign_in_with_email_and_password(email, password)
            global person
            person["is_logged_in"] = True
            person["email"] = user["email"]
            person["uid"] = user["localId"]
            user_data = db.child("users").child(person["uid"]).get().val()
            session['name'] = user_data.get('name', '') if user_data else ''
            return redirect(url_for('welcome'))
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 400:
                try:
                    error_message = e.response.json()["error"]["message"]
                    if error_message == "INVALID_LOGIN_CREDENTIALS":
                        return render_template("login.html", error="Invalid email or password.")
                    else:
                        return render_template("login.html", error="An  error occurred.")
                except Exception as e:
                    return render_template("login.html", error="An unexpected error occurred.")
            else:
                return render_template("login.html", error="An unexpected error occurred.")
    else:
        if person["is_logged_in"]:
            return redirect(url_for('welcome'))
        else:
            return redirect(url_for('login'))
def validate_email(email):
    # Make a GET request to ZeroBounce API
    params = {'api_key': ZEROBOUNCE_API_KEY, 'email': email}
    response = requests.get(ZEROBOUNCE_API_ENDPOINT, params=params)
    return response.json()

@app.route("/register", methods=["POST", "GET"])
def register():
    if request.method == "POST":
        result = request.form
        email = result["email"]
        password = result["pass"]
        name = result["name"]
        response = validate_email(email)
        if response['status'] != 'valid':
            return "Invalid email address. Please enter a valid email."
        try:
            user = auth.create_user_with_email_and_password(email, password)
            if user is None:
                return "Failed to create user"
            user_id = user['localId']
            data = {"email": email, "name": name}
            db.child("users").child(user_id).set(data)
            msg = Message(subject='Anomaly detection registration', sender='noreply@example.com', recipients=[email])
            msg.body = f"hi {name},\nYour otp for completion of registration is: {otp}"
            mail.send(msg)
            return redirect(url_for('email'))
        except Exception as e:
            return f"An unexpected error occurred during registration: {e}"
    else:
        if person["is_logged_in"]:
            return redirect(url_for('welcome'))
        else:
            return render_template('login.html')  # Assuming you have a register.html template

@app.route('/validate', methods=["POST"])
def validate():
    user_otp = request.form['otp']
    if otp == int(user_otp):
        return redirect(url_for('success'))
    return "<h3> Please Try again</h3>"



@app.route('/predict', methods=['POST'])
def predict():
    if request.method == 'POST':
        uploaded_file = request.files['file']
        if uploaded_file.filename != '':
            test = pd.read_csv(uploaded_file)
            le = LabelEncoder()
            test['ID'] = pd.Series(le.fit_transform(test['ID']))
            X_test = test.values[:, 0:6]
            classifier = load('sso_model.joblib')
            y_pred = classifier.predict(X_test)
            predictions = []
            anomaly_detected = False
            
            for i in range(len(test)):
                if y_pred[i] == 0:
                    predictions.append({"input": test.iloc[i].to_dict(), "prediction": 'No Anomaly Detected'})
                elif y_pred[i] == 1:
                    predictions.append({"input": test.iloc[i].to_dict(), "prediction": 'Anomaly Detected'})
                    anomaly_detected = True
            
            if anomaly_detected:
                send_anomaly_notification(person['email'],session['name']);

            return render_template('result.html', predictions=predictions)
    return redirect(url_for('welcome'))

def send_anomaly_notification(email,name):
    msg = Message(subject='Anomaly Detected',
                  sender=app.config['MAIL_DEFAULT_SENDER'],
                  recipients=[email])
    msg.body = "Hey "+name+",\nAnomaly has been detected in your data. Please take care of yourself."
    mail.send(msg)

@app.route("/reset_password", methods=["GET", "POST"])
def reset_password():
    if request.method == "GET":
        return render_template("reset_password.html")
    elif request.method == "POST":
        email = request.form.get("email")
        if not email:
            return jsonify({"error": "Email is required."}), 400

        try:
            reset_request = {
            "requestType": "PASSWORD_RESET",
            "email": email
            }
            response = requests.post(
            f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={config['apiKey']}",
            json=reset_request
                )
            if response.ok:
                return redirect(url_for('reset_success', message="Password reset email sent successfully."))
            else:
                return jsonify({"error": "Failed to send password reset email."}), response.status_code
        except Exception as e:
            return jsonify({"error": str(e)}), 500

@app.route("/reset_success")
def reset_success():
    message = request.args.get('message')
    return render_template("reset_success.html", message=message)
if __name__ == "__main__":
    app.run(debug=True)  # Run in debug mode for development
