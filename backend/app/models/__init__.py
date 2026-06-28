"""ORM models. Import all here so Alembic autogenerate sees them."""
from app.models.catalog import ServiceCatalog, ServiceEmbedding, ServiceSynonym  # noqa: F401
from app.models.clinic import Clinic  # noqa: F401
from app.models.enums import Currency, MatchStatus, ServiceCategory  # noqa: F401
from app.models.ingest import ParsedOffer, RawDocument  # noqa: F401
from app.models.observability import ParseRun  # noqa: F401
from app.models.price import Price  # noqa: F401
from app.models.subscription import PriceSubscription  # noqa: F401
from app.models.unmatched import UnmatchedQueue  # noqa: F401
from app.models.user import User  # noqa: F401
