import os
import json
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from dotenv import load_dotenv

# ===========================================================================
# Basic Configuration
# ===========================================================================

script_dir = os.path.dirname(os.path.abspath(__file__))
log_file_path = os.path.join(script_dir, "email_campaign.log")

logging.basicConfig(
    level=logging.INFO,  # Change to DEBUG for more detailed logs
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path, mode='a'),  # Append logs to file
        logging.StreamHandler(),                      # Also log to console
    ]
)

logging.info("All Packers Expeditions Email Campaign Script started.")

# Load environment variables from .env file
load_dotenv()

# ===========================================================================
# Retrieve SMTP details and other environment variables
# ===========================================================================
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = os.getenv("SMTP_PORT")
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")  # For sending log emails to yourself

# Validate SMTP details
missing_smtp_vars = []
for var_name, var_value in [
    ("SMTP_SERVER", SMTP_SERVER),
    ("SMTP_PORT", SMTP_PORT),
    ("EMAIL_ADDRESS", EMAIL_ADDRESS),
    ("EMAIL_PASSWORD", EMAIL_PASSWORD),
    ("ADMIN_EMAIL", ADMIN_EMAIL),
]:
    if not var_value:
        missing_smtp_vars.append(var_name)

if missing_smtp_vars:
    logging.error(f"Missing SMTP environment variables: {
                  ', '.join(missing_smtp_vars)}.")
    exit(1)

# Convert SMTP_PORT to int if possible
try:
    SMTP_PORT = int(SMTP_PORT)
except ValueError:
    logging.error(f"Invalid SMTP_PORT value: {SMTP_PORT}")
    exit(1)

# ===========================================================================
# Load Recipients from a Local JSON File
# ===========================================================================
recipients_file_path = os.path.join(script_dir, "recipients.json")
RECIPIENTS = []
if not os.path.isfile(recipients_file_path):
    logging.error(f"Recipients JSON file not found at: {recipients_file_path}")
else:
    try:
        with open(recipients_file_path, "r", encoding="utf-8") as f:
            RECIPIENTS = json.load(f)
            if not isinstance(RECIPIENTS, list):
                logging.error(
                    "The recipients.json file should contain a JSON array.")
                RECIPIENTS = []
    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse recipients.json file: {e}")

logging.info(f"Loaded recipients: {RECIPIENTS}")

# Initialize counters and lists for tracking
success_count = 0
failure_count = 0
failed_recipients = []

# ===========================================================================
# Function to send promotional email
# ===========================================================================


def send_promotional_email(recipient):
    """
    Sends a promotional email about All Packers Expeditions to a single recipient.
    """
    global success_count, failure_count, failed_recipients
    try:
        # Validate required recipient fields
        required_fields = ["email", "name", "trip_name",
                           "trip_date", "trip_cost", "trip_description"]
        missing_fields = [
            field for field in required_fields if field not in recipient]
        if missing_fields:
            logging.error(f"Missing fields {
                          missing_fields} in recipient data: {recipient}")
            failure_count += 1
            failed_recipients.append({
                "name": recipient.get("name", "Unknown"),
                "email": recipient.get("email", "Unknown"),
                "reason": f"Missing fields: {', '.join(missing_fields)}"
            })
            return

        # Ensure trip_cost is a float
        try:
            trip_cost = float(recipient["trip_cost"])
        except (ValueError, TypeError):
            logging.error(f"Invalid trip_cost for recipient {recipient.get(
                'name', 'Unknown')}: {recipient.get('trip_cost')}")
            failure_count += 1
            failed_recipients.append({
                "name": recipient.get("name", "Unknown"),
                "email": recipient.get("email", "Unknown"),
                "reason": f"Invalid trip_cost: {recipient.get('trip_cost')}"
            })
            return

        subject = f"Join Our {recipient['trip_name']} – Your Adventure Awaits!"
        body = f"""\
        <html>
        <head>
            <style>
                /* Add any custom styling here */
            </style>
        </head>
        <body>
            <p>Hi {recipient['name']},</p>
            <p>
                Are you ready for an unforgettable adventure? We at
                <strong>All Packers Expeditions</strong> are excited to invite you to our upcoming
                <strong>{recipient['trip_name']}</strong> on
                <strong>{recipient['trip_date']}</strong>.
            </p>
            <p>
                <strong>Trip Highlights:</strong><br>
                {recipient['trip_description']}<br>
                <strong>Cost:</strong> ${trip_cost:,.2f}
            </p>
            <p>
                We promise breathtaking views, expert guides, and memories that will last a lifetime.
            </p>
            <p>
                <a href="https://allpackersexpeditions.com/"
                   style="
                       display: inline-block;
                       padding: 12px 20px;
                       font-size: 16px;
                       color: #ffffff;
                       background-color: #006400;
                       text-decoration: none;
                       border-radius: 5px;
                       margin: 10px 0;
                   ">
                    Book Your Adventure Now
                </a>
            </p>
            <p>
                If you have any questions or need more information,
                feel free to reply to this email or visit our website:
                <a href="https://allpackersexpeditions.com/"
                   style="color: #1a0dab; text-decoration: none;">
                   All Packers Expeditions
                </a>.
            </p>
            <p>
                We look forward to exploring with you!<br><br>
                Best regards,<br>
                The All Packers Expeditions Team
            </p>
        </body>
        </html>
        """

        # Create email message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = recipient["email"]

        # Attach the HTML content
        msg.attach(MIMEText(body, "html"))

        # Send email
        try:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
                server.sendmail(
                    EMAIL_ADDRESS, recipient["email"], msg.as_string())

            logging.info(f"Promotional email sent successfully to {
                         recipient['name']} ({recipient['email']}).")
            success_count += 1

        except smtplib.SMTPException as smtp_err:
            logging.error(f"SMTP error when sending email to {
                          recipient.get('email', 'Unknown')}: {smtp_err}")
            failure_count += 1
            failed_recipients.append({
                "name": recipient.get("name", "Unknown"),
                "email": recipient.get("email", "Unknown"),
                "reason": f"SMTP error: {smtp_err}"
            })

    except Exception as e:
        logging.error(f"Unexpected error when sending email to {
                      recipient.get('email', 'Unknown')}: {e}")
        failure_count += 1
        failed_recipients.append({
            "name": recipient.get("name", "Unknown"),
            "email": recipient.get("email", "Unknown"),
            "reason": f"Unexpected error: {e}"
        })

# ===========================================================================
# Function to send the log file to admin
# ===========================================================================


def send_log_email():
    """
    Sends the log file as an attachment to the admin email.
    """
    try:
        subject = "All Packers Expeditions - Email Campaign Logs"
        body = """Hello,

Please find attached the log file for the latest email campaign execution.

Best regards,
All Packers Expeditions Automated System
"""

        msg = MIMEMultipart()
        msg["Subject"] = subject
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = ADMIN_EMAIL

        # Attach the body text
        msg.attach(MIMEText(body, "plain"))

        # Attach the log file, if it exists
        if os.path.isfile(log_file_path):
            with open(log_file_path, "rb") as log_file:
                part = MIMEApplication(
                    log_file.read(), Name=os.path.basename(log_file_path))
            part["Content-Disposition"] = f'attachment; filename="{
                os.path.basename(log_file_path)}"'
            msg.attach(part)
        else:
            logging.error(f"Log file not found at {
                          log_file_path}. Cannot attach to log email.")

        # Send log email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, ADMIN_EMAIL, msg.as_string())

        logging.info("Log email sent successfully to admin.")

    except smtplib.SMTPException as smtp_err:
        logging.error(f"SMTP error when sending log email: {smtp_err}")
    except Exception as e:
        logging.error(f"Unexpected error when sending log email: {e}")

# ===========================================================================
# Function to iterate over all recipients
# ===========================================================================


def send_emails_to_all_recipients():
    """
    Sends promotional emails to all recipients in the RECIPIENTS list.
    """
    if not RECIPIENTS:
        logging.warning("No recipients found to send emails.")
        return

    for recipient in RECIPIENTS:
        send_promotional_email(recipient)


# ===========================================================================
# Main Execution
# ===========================================================================
if __name__ == "__main__":
    send_emails_to_all_recipients()
    send_log_email()
    logging.info(f"Script execution completed. Successful: {
                 success_count}, Failed: {failure_count}")
    if failed_recipients:
        logging.info(f"Failed recipients: {failed_recipients}")
