"""
Offer Service - Offer Generation with Versioning

Generates professional offers with work packages, pricing, and event sourcing.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from datetime import datetime, timedelta, date
from decimal import Decimal
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel

from ...models.offer import (
    Offer,
    OfferStatus,
    WorkPackage,
    EstimatedHours,
    Deliverable,
    Money,
)
from ...models.project import Project
from ...infrastructure.events.bus import EventBus
from ...infrastructure.repositories.offer_repository import OfferRepository
from .work_packages import WorkPackageGenerator
from .pdf_generator import PDFGenerator


app = FastAPI(title="Offer Service", version="1.0.0")


# Request/Response models
class CreateOfferRequest(BaseModel):
    project_id: str
    conversation_id: str
    customer_id: str


class OfferResponse(BaseModel):
    offer_id: str
    offer_number: str
    version: int
    status: str
    total_value: Dict[str, Any]
    valid_until: str
    work_packages: List[Dict[str, Any]]
    approval_required: bool


class OfferService:
    """Service for offer generation and management."""

    OFFER_VALIDITY_DAYS = 30
    APPROVAL_THRESHOLD = Decimal("100000.00")  # EUR 100k
    DEFAULT_HOURLY_RATE = Decimal("120.00")  # EUR 120/hour

    def __init__(
        self,
        offer_repository: OfferRepository,
        event_bus: EventBus,
        work_package_generator: WorkPackageGenerator,
        pdf_generator: PDFGenerator
    ):
        self.offer_repo = offer_repository
        self.event_bus = event_bus
        self.wp_generator = work_package_generator
        self.pdf_generator = pdf_generator

    async def create_offer(
        self,
        project_id: UUID,
        conversation_id: UUID,
        customer_id: UUID
    ) -> Offer:
        """
        Create new offer from project requirements.

        Args:
            project_id: Project identifier
            conversation_id: Source conversation
            customer_id: Customer identifier

        Returns:
            Created offer entity
        """
        # Generate offer number
        offer_number = await self._generate_offer_number()

        # Generate work packages based on project
        work_packages = await self.wp_generator.generate_work_packages(project_id)

        # Calculate total value
        total_value = self._calculate_total_value(work_packages)

        # Determine if approval needed
        approval_required = total_value.amount > self.APPROVAL_THRESHOLD

        # Create offer entity
        offer = Offer(
            id=uuid4(),
            offer_number=offer_number,
            version=1,
            customer_id=customer_id,
            project_id=project_id,
            conversation_id=conversation_id,
            created_at=datetime.utcnow(),
            valid_until=date.today() + timedelta(days=self.OFFER_VALIDITY_DAYS),
            status=OfferStatus.PENDING_APPROVAL if approval_required else OfferStatus.DRAFT,
            total_value=total_value,
            work_packages=work_packages,
            terms_and_conditions=self._get_standard_terms(),
            approval_required=approval_required,
            approval_workflow_id=None,
            events=[]
        )

        # Persist offer
        await self.offer_repo.save(offer)

        # Publish event
        await self.event_bus.publish({
            "event_type": "OfferCreated",
            "aggregate_id": str(offer.id),
            "aggregate_type": "Offer",
            "payload": {
                "offer_number": offer_number,
                "total_value": str(total_value.amount),
                "approval_required": approval_required,
                "project_id": str(project_id)
            }
        })

        # Trigger approval workflow if needed
        if approval_required:
            await self._initiate_approval_workflow(offer)

        return offer

    async def get_offer(self, offer_id: UUID) -> Optional[Offer]:
        """Retrieve offer by ID."""
        return await self.offer_repo.get_by_id(offer_id)

    async def update_offer(
        self,
        offer_id: UUID,
        modifications: Dict[str, Any]
    ) -> Offer:
        """
        Update offer and increment version.

        Args:
            offer_id: Offer identifier
            modifications: Fields to modify

        Returns:
            Updated offer with incremented version
        """
        offer = await self.offer_repo.get_by_id(offer_id)
        if not offer:
            raise ValueError(f"Offer {offer_id} not found")

        # Create new version
        offer.version += 1

        # Apply modifications
        for field, value in modifications.items():
            if hasattr(offer, field):
                setattr(offer, field, value)

        # Recalculate total if work packages changed
        if "work_packages" in modifications:
            offer.total_value = self._calculate_total_value(offer.work_packages)

        # Save updated offer
        await self.offer_repo.save(offer)

        # Publish event
        await self.event_bus.publish({
            "event_type": "OfferModified",
            "aggregate_id": str(offer_id),
            "aggregate_type": "Offer",
            "payload": {
                "new_version": offer.version,
                "modifications": list(modifications.keys())
            }
        })

        return offer

    async def approve_offer(self, offer_id: UUID, approver_id: UUID) -> Offer:
        """Approve offer (for high-value offers)."""
        offer = await self.offer_repo.get_by_id(offer_id)
        if not offer:
            raise ValueError(f"Offer {offer_id} not found")

        offer.status = OfferStatus.APPROVED

        await self.offer_repo.save(offer)

        await self.event_bus.publish({
            "event_type": "OfferApproved",
            "aggregate_id": str(offer_id),
            "aggregate_type": "Offer",
            "payload": {
                "approver_id": str(approver_id),
                "approved_at": datetime.utcnow().isoformat()
            }
        })

        return offer

    async def send_offer(self, offer_id: UUID) -> Offer:
        """Mark offer as sent to customer."""
        offer = await self.offer_repo.get_by_id(offer_id)
        if not offer:
            raise ValueError(f"Offer {offer_id} not found")

        offer.status = OfferStatus.SENT

        await self.offer_repo.save(offer)

        await self.event_bus.publish({
            "event_type": "OfferSent",
            "aggregate_id": str(offer_id),
            "aggregate_type": "Offer",
            "payload": {
                "sent_at": datetime.utcnow().isoformat()
            }
        })

        return offer

    async def generate_pdf(
        self,
        offer_id: UUID,
        language: str = "de"
    ) -> bytes:
        """Generate PDF document for offer."""
        offer = await self.offer_repo.get_by_id(offer_id)
        if not offer:
            raise ValueError(f"Offer {offer_id} not found")

        pdf_bytes = await self.pdf_generator.generate_offer_pdf(offer, language)

        return pdf_bytes

    def _calculate_total_value(self, work_packages: List[WorkPackage]) -> Money:
        """Calculate total offer value from work packages."""
        total = Decimal("0.00")

        for wp in work_packages:
            total += wp.total_cost.amount

        return Money(amount=total, currency="EUR")

    async def _generate_offer_number(self) -> str:
        """Generate unique offer number in format YY-NNNN."""
        year = datetime.utcnow().year % 100
        sequence = await self.offer_repo.get_next_sequence_number()

        return f"{year:02d}-{sequence:04d}"

    def _get_standard_terms(self) -> str:
        """Get standard terms and conditions."""
        return """
Allgemeine Geschäftsbedingungen:

1. Zahlungsbedingungen: 30 Tage netto
2. Gültigkeit des Angebots: 30 Tage ab Ausstellungsdatum
3. Alle Preise verstehen sich zuzüglich der gesetzlichen Mehrwertsteuer
4. Lieferung und Leistung erfolgen nach den vereinbarten Terminen
5. Es gelten unsere allgemeinen Geschäftsbedingungen
"""

    async def _initiate_approval_workflow(self, offer: Offer):
        """Initiate approval workflow for high-value offers."""
        await self.event_bus.publish({
            "event_type": "ApprovalWorkflowInitiated",
            "aggregate_id": str(offer.id),
            "aggregate_type": "Offer",
            "payload": {
                "offer_id": str(offer.id),
                "total_value": str(offer.total_value.amount),
                "requires_approval": True
            }
        })


# Dependency injection
async def get_offer_service() -> OfferService:
    """Get offer service instance."""
    # TODO: Wire up actual dependencies
    from ...infrastructure.repositories.offer_repository import OfferRepository
    from ...infrastructure.events.bus import EventBus
    from .work_packages import WorkPackageGenerator
    from .pdf_generator import PDFGenerator

    return OfferService(
        offer_repository=OfferRepository(),
        event_bus=EventBus(),
        work_package_generator=WorkPackageGenerator(),
        pdf_generator=PDFGenerator()
    )


# API Endpoints
@app.post("/offers", response_model=OfferResponse)
async def create_offer(
    request: CreateOfferRequest,
    service: OfferService = Depends(get_offer_service)
):
    """Create new offer."""
    offer = await service.create_offer(
        project_id=UUID(request.project_id),
        conversation_id=UUID(request.conversation_id),
        customer_id=UUID(request.customer_id)
    )

    return OfferResponse(
        offer_id=str(offer.id),
        offer_number=offer.offer_number,
        version=offer.version,
        status=offer.status.value,
        total_value={
            "amount": str(offer.total_value.amount),
            "currency": offer.total_value.currency
        },
        valid_until=offer.valid_until.isoformat(),
        work_packages=[
            {
                "name": wp.name,
                "description": wp.description,
                "total_cost": str(wp.total_cost.amount)
            }
            for wp in offer.work_packages
        ],
        approval_required=offer.approval_required
    )


@app.get("/offers/{offer_id}", response_model=OfferResponse)
async def get_offer(
    offer_id: str,
    service: OfferService = Depends(get_offer_service)
):
    """Get offer by ID."""
    offer = await service.get_offer(UUID(offer_id))
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")

    return OfferResponse(
        offer_id=str(offer.id),
        offer_number=offer.offer_number,
        version=offer.version,
        status=offer.status.value,
        total_value={
            "amount": str(offer.total_value.amount),
            "currency": offer.total_value.currency
        },
        valid_until=offer.valid_until.isoformat(),
        work_packages=[
            {
                "name": wp.name,
                "description": wp.description,
                "total_cost": str(wp.total_cost.amount)
            }
            for wp in offer.work_packages
        ],
        approval_required=offer.approval_required
    )


@app.post("/offers/{offer_id}/download")
async def download_offer(
    offer_id: str,
    language: str = "de",
    service: OfferService = Depends(get_offer_service)
):
    """Generate and download offer PDF."""
    pdf_bytes = await service.generate_pdf(UUID(offer_id), language)

    from fastapi.responses import Response

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=offer-{offer_id}.pdf"
        }
    )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "offer"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
