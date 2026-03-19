# Aviation Corp Flask App - Email Configuration

## SMTP Setup for Gmail

This app uses Flask-Mail to send emails via Gmail SMTP.

### Setup Instructions:

1. **Enable 2-Factor Authentication** on your Gmail account:
   - Go to https://myaccount.google.com/security
   - Enable 2-Step Verification

2. **Generate an App Password**:
   - Go to https://support.google.com/accounts/answer/185833
   - Generate an app password for "Mail"
   - Copy the 16-character password

3. **Configure Environment Variables**:
   - Open the `.env` file in the project root
   - Replace `your_gmail_app_password_here` with your actual app password
   - The MAIL_USERNAME is already set to `khaldudxb@gmail.com`

4. **Install Dependencies** (already done):
   - Flask-Mail
   - python-dotenv

### Email Features:

- **Contact Form**: Sends notification emails to khaldudxb@gmail.com when someone submits the contact form
- **Registration**: Sends welcome emails to new users upon account creation
- **Database Storage**: All contact messages are stored in MongoDB `Contact_Messages` collection with additional metadata (IP, user agent, status)

### Security Notes:

- Never commit the `.env` file to version control
- The app password is separate from your main Gmail password
- Emails are sent securely via TLS encryption

### Testing:

Run the app and submit the contact form to test email sending.