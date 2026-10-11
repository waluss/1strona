import logging
from sqlalchemy.orm import Session
from app.models import Tenant, User
from app.core.config import settings
from app.core.security import get_password_hash

logger = logging.getLogger(__name__)

def bootstrap_initial_data(db: Session) -> None:
    admin_user = db.query(User).filter(User.username == "admin").first()
    if not admin_user:
        logger.info("Bootstrapping initial tenant and admin user...")
        default_tenant = Tenant(
            name="Default Tenant",
            is_active=True
        )
        db.add(default_tenant)
        db.flush()

        hashed_password = get_password_hash(settings.INITIAL_ADMIN_PASSWORD)
        admin_user = User(
            tenant_id=default_tenant.id,
            username="admin",
            email="admin@tenderflow.local",
            hashed_password=hashed_password,
            is_active=True,
            is_admin=True,
            must_change_password=True
        )
        db.add(admin_user)
        db.commit()
        logger.info("Default tenant and admin user successfully created.")
