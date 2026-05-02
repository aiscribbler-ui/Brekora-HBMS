import pyotp


class TOTPService:
    @staticmethod
    def generate_secret() -> str:
        return pyotp.random_base32()

    @staticmethod
    def get_provisioning_uri(email: str, secret: str) -> str:
        return pyotp.totp.TOTP(secret).provisioning_uri(email, issuer_name="Brekora BMS")

    @staticmethod
    def verify_token(secret: str, token: str) -> bool:
        totp = pyotp.totp.TOTP(secret)
        return totp.verify(token, valid_window=1)
