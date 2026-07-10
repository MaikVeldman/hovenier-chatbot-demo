"""
Eenmalige setup: maakt de eerste admin-gebruiker aan in de database.

Gebruik:
    python setup_admin.py <email> <wachtwoord>

Voorbeeld:
    python setup_admin.py info@veldmanhoveniers.nl MijnWachtwoord123

Daarna log je in via /beheer/login met dit e-mailadres en wachtwoord.
"""
import sys
import os
from dotenv import load_dotenv

load_dotenv()

def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    email    = sys.argv[1].strip()
    password = sys.argv[2]

    if len(password) < 8:
        print("Fout: wachtwoord moet minimaal 8 tekens zijn.")
        sys.exit(1)

    # Zorg dat alle tabellen bestaan
    from infrastructure.db.database import engine, Base
    from infrastructure.db import db_models  # noqa: F401
    Base.metadata.create_all(bind=engine)

    from infrastructure.config.bedrijf import BEDRIJFSNAAM, REGIO, CONTACT_EMAIL, CONTACT_TELEFOON
    from infrastructure.db.repositories.tenant_repository import TenantRepository
    from infrastructure.db.repositories.user_repository import UserRepository

    TENANT_SLUG = os.getenv("TENANT_SLUG", "veldmanhoveniers")

    # Tenant aanmaken of ophalen
    tenant_id = TenantRepository().get_or_create_id(
        slug=TENANT_SLUG,
        bedrijfsnaam=BEDRIJFSNAAM,
        regio=REGIO,
        contact_email=CONTACT_EMAIL,
        contact_telefoon=CONTACT_TELEFOON,
    )
    print(f"Tenant '{TENANT_SLUG}' (id={tenant_id}) klaar.")

    # Admin aanmaken als die nog niet bestaat
    user_repo = UserRepository()
    existing = user_repo.find_by_email(email)
    if existing:
        print(f"Gebruiker '{email}' bestaat al (id={existing.id}).")
        print("Wil je het wachtwoord bijwerken? Gebruik: python setup_admin.py <email> <nieuw-wachtwoord> --update")
        if "--update" in sys.argv:
            user_repo.update_password(existing.id, password)
            print("Wachtwoord bijgewerkt.")
    else:
        uid = user_repo.create(tenant_id, email, password, is_superadmin=True)
        print(f"Admin aangemaakt: {email} (user_id={uid})")

    print("\nKlaar. Log in via /beheer/login met bovenstaand e-mailadres en wachtwoord.")

if __name__ == "__main__":
    main()
