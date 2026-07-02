from flask import Flask
from flask_mail import Mail, Message

app = Flask(__name__)

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'aliabatcha990@gmail.com'
app.config['MAIL_PASSWORD'] = 'mvvxqttzfdgxosoy'

mail = Mail(app)

with app.app_context():
    msg = Message(
        subject='Test Email from Flask',
        sender='aliabatcha990@gmail.com',
        recipients=['aliabatcha990@gmail.com']
    )
    msg.body = 'Hello! This is a test email sent from my Flask app.'
    mail.send(msg)
    print('Email sent!')