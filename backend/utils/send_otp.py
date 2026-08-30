
import aiosmtplib
from pydantic import EmailStr
from pydantic import BaseModel
import os
from dotenv import load_dotenv
import aiosmtplib
from email.message import EmailMessage
load_dotenv()

SMTP_PASSWORD=os.getenv('SMTP_PASSWORD')
SMTP_EMAIL=os.getenv('SMTP_EMAIL')
SMTP_HOST=os.getenv('SMTP_HOST')
SMTP_PORT=int(os.getenv('SMTP_PORT'))

class SendOTP(BaseModel):
    email:EmailStr
    otp:int


async def send_mail(payload:SendOTP):
    msg=EmailMessage()
    msg['To']=payload['email']
    msg['From']=SMTP_EMAIL
    msg['Subject']="OTP Verification for RetailIQ"
    
    msg.set_content(f"This is your otp {payload['otp']}")
    try:
        await aiosmtplib.send(msg,username=SMTP_EMAIL,password=SMTP_PASSWORD,hostname=SMTP_HOST,port=SMTP_PORT)
        return True
    except Exception as e:
        print(e)
        return False