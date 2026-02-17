"""Encrypt PII fields in users table

Revision ID: 20250217_000001
Revises: 20250213_000001
Create Date: 2025-02-17

This migration:
1. Increases column sizes for full_name and company to accommodate encryption overhead
2. Encrypts existing plaintext data in these columns

Note: This migration requires the encryption key to be properly configured.
Ensure FIELD_ENCRYPTION_KEY or JWT_SECRET is set before running.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm import Session


# revision identifiers, used by Alembic.
revision = '20250217_000001'
down_revision = '20250213_000001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Upgrade: Expand column sizes and encrypt existing PII data.
    """
    # First, alter the column sizes to accommodate encrypted data
    # Encrypted data is approximately 1.5-2x the size of plaintext plus overhead
    op.alter_column(
        'users',
        'full_name',
        type_=sa.String(512),
        existing_type=sa.String(255),
        existing_nullable=True
    )

    op.alter_column(
        'users',
        'company',
        type_=sa.String(512),
        existing_type=sa.String(255),
        existing_nullable=True
    )

    # Now encrypt existing data
    # We need to do this in Python to use the encryption service
    bind = op.get_bind()
    session = Session(bind=bind)

    try:
        # Import encryption service here to avoid import issues during migration setup
        from app.services.encryption import encrypt_field

        # Get all users with non-null, non-encrypted PII fields
        result = session.execute(
            sa.text("""
                SELECT id, full_name, company
                FROM users
                WHERE (full_name IS NOT NULL AND full_name NOT LIKE 'enc:%')
                   OR (company IS NOT NULL AND company NOT LIKE 'enc:%')
            """)
        )

        users_to_update = result.fetchall()

        for user in users_to_update:
            user_id = user[0]
            full_name = user[1]
            company = user[2]

            # Encrypt non-encrypted values
            encrypted_full_name = None
            encrypted_company = None

            if full_name and not full_name.startswith('enc:'):
                encrypted_full_name = encrypt_field(full_name)

            if company and not company.startswith('enc:'):
                encrypted_company = encrypt_field(company)

            # Update only the fields that need encryption
            if encrypted_full_name or encrypted_company:
                updates = []
                params = {'user_id': user_id}

                if encrypted_full_name:
                    updates.append("full_name = :full_name")
                    params['full_name'] = encrypted_full_name

                if encrypted_company:
                    updates.append("company = :company")
                    params['company'] = encrypted_company

                if updates:
                    session.execute(
                        sa.text(f"UPDATE users SET {', '.join(updates)} WHERE id = :user_id"),
                        params
                    )

        session.commit()
        print(f"Encrypted PII fields for {len(users_to_update)} users")

    except ImportError:
        print("WARNING: Could not import encryption service. Data not encrypted.")
        print("Run this migration again after the application is properly set up.")
    except Exception as e:
        session.rollback()
        print(f"ERROR during encryption: {e}")
        raise
    finally:
        session.close()


def downgrade() -> None:
    """
    Downgrade: Decrypt data and reduce column sizes.

    WARNING: This will decrypt all PII data. Ensure this is intentional.
    """
    bind = op.get_bind()
    session = Session(bind=bind)

    try:
        # Import decryption service
        from app.services.encryption import decrypt_field

        # Get all users with encrypted PII fields
        result = session.execute(
            sa.text("""
                SELECT id, full_name, company
                FROM users
                WHERE (full_name IS NOT NULL AND full_name LIKE 'enc:%')
                   OR (company IS NOT NULL AND company LIKE 'enc:%')
            """)
        )

        users_to_update = result.fetchall()

        for user in users_to_update:
            user_id = user[0]
            full_name = user[1]
            company = user[2]

            # Decrypt encrypted values
            decrypted_full_name = None
            decrypted_company = None

            if full_name and full_name.startswith('enc:'):
                decrypted_full_name = decrypt_field(full_name)

            if company and company.startswith('enc:'):
                decrypted_company = decrypt_field(company)

            # Update only the fields that need decryption
            if decrypted_full_name or decrypted_company:
                updates = []
                params = {'user_id': user_id}

                if decrypted_full_name:
                    updates.append("full_name = :full_name")
                    params['full_name'] = decrypted_full_name

                if decrypted_company:
                    updates.append("company = :company")
                    params['company'] = decrypted_company

                if updates:
                    session.execute(
                        sa.text(f"UPDATE users SET {', '.join(updates)} WHERE id = :user_id"),
                        params
                    )

        session.commit()
        print(f"Decrypted PII fields for {len(users_to_update)} users")

    except ImportError:
        print("WARNING: Could not import encryption service. Data not decrypted.")
    except Exception as e:
        session.rollback()
        print(f"ERROR during decryption: {e}")
        raise
    finally:
        session.close()

    # Reduce column sizes back to original
    op.alter_column(
        'users',
        'full_name',
        type_=sa.String(255),
        existing_type=sa.String(512),
        existing_nullable=True
    )

    op.alter_column(
        'users',
        'company',
        type_=sa.String(255),
        existing_type=sa.String(512),
        existing_nullable=True
    )
