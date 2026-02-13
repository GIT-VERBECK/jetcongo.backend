from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr, BaseModel
from typing import Dict, Any
from app.core.config import settings
import os

class EmailManager:
    def __init__(self):
        self.conf = ConnectionConfig(
            MAIL_USERNAME=settings.MAIL_USER,
            MAIL_PASSWORD=settings.MAIL_PASSWORD,
            MAIL_FROM=settings.MAIL_FROM_EMAIL,
            MAIL_PORT=settings.MAIL_PORT,
            MAIL_SERVER=settings.MAIL_HOST,
            MAIL_STARTTLS=True if settings.MAIL_ENCRYPTION.lower() == 'tls' else False,
            MAIL_SSL_TLS=True if settings.MAIL_ENCRYPTION.lower() == 'ssl' else False,
            USE_CREDENTIALS=True,
            VALIDATE_CERTS=True
        )

    async def send_receipt(self, email: EmailStr, data: Dict[str, Any]):
        """
        Envoie un reçu de paiement avec le template HTML.
        """
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #333; line-height: 1.6; margin: 0; padding: 0; background-color: #f4f7f9; }}
                .container {{ max-width: 600px; margin: 20px auto; background: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.1); border-top: 5px solid #137fec; }}
                .header {{ padding: 30px; background: #fff; display: flex; align-items: center; justify-content: space-between; }}
                .logo-text {{ font-size: 24px; font-weight: bold; color: #137fec; }}
                .receipt-title {{ text-align: right; }}
                .receipt-title h1 {{ margin: 0; font-size: 20px; color: #333; text-transform: uppercase; }}
                .receipt-title p {{ margin: 5px 0 0; font-size: 12px; color: #777; }}
                
                .info-section {{ padding: 20px 30px; display: grid; grid-template-columns: 1fr 1fr; gap: 20px; border-bottom: 1px solid #eee; }}
                .info-box {{ background: #f9f9f9; padding: 15px; border-radius: 6px; }}
                .info-box h3 {{ margin: 0 0 10px; font-size: 12px; color: #777; text-transform: uppercase; }}
                .info-box p {{ margin: 3px 0; font-size: 13px; font-weight: 500; }}

                .table-container {{ padding: 30px; }}
                table {{ width: 100%; border-collapse: collapse; }}
                th {{ text-align: left; padding: 12px; background: #137fec; color: #fff; font-size: 12px; text-transform: uppercase; }}
                td {{ padding: 12px; border-bottom: 1px solid #eee; font-size: 14px; }}
                .total-row {{ background: #f9f9f9; font-weight: bold; }}
                
                .footer {{ padding: 20px; text-align: center; font-size: 11px; color: #999; border-top: 1px solid #eee; }}
                .badge {{ background: #e6fcf5; color: #0ca678; padding: 4px 10px; border-radius: 20px; font-size: 11px; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo-text">JetCongo</div>
                    <div class="receipt-title">
                        <h1>Reçu de Paiement</h1>
                        <p>Réf: {data.get('ref', 'N/A')}</p>
                        <p>Date: {data.get('date_paiement', 'N/A')}</p>
                    </div>
                </div>

                <div class="info-section">
                    <div class="info-box">
                        <h3>Émetteur</h3>
                        <p><strong>JetCongo</strong></p>
                        <p>Q. Himbi, Av. Lac-Kivu, 121</p>
                        <p>Nord-Kivu, Goma</p>
                        <p>Tél: +243 81 000 0000</p>
                    </div>
                    <div class="info-box">
                        <h3>Client & Voyage</h3>
                        <p><strong>{data.get('client_name', 'Client')}</strong></p>
                        <p>{data.get('trajet', 'N/A')}</p>
                        <p>Places: {data.get('seats', 1)}</p>
                        <p>Départ: {data.get('depart_time', 'N/A')}</p>
                    </div>
                </div>

                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Description</th>
                                <th>Montant</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>Billet de transport ({data.get('trajet')})</td>
                                <td>$ {data.get('subtotal', '0.00')}</td>
                            </tr>
                            <tr>
                                <td>Frais de service & Taxes</td>
                                <td>$ {data.get('taxes', '0.00')}</td>
                            </tr>
                            <tr class="total-row">
                                <td>Total Payé</td>
                                <td>$ {data.get('total', '0.00')}</td>
                            </tr>
                        </tbody>
                    </table>
                    <div style="margin-top: 20px; text-align: right;">
                        <span class="badge">PAYÉ LE {data.get('date_paiement')}</span>
                    </div>
                </div>

                <div class="footer">
                    <p>Merci d'avoir choisi JetCongo pour vos déplacements.</p>
                    <p>© 2026 JetCongo. Tous droits réservés.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        message = MessageSchema(
            subject="Votre Reçu de Paiement JetCongo",
            recipients=[email],
            body=html,
            subtype=MessageType.html
        )

        fm = FastMail(self.conf)
        await fm.send_message(message)

email_manager = EmailManager()
