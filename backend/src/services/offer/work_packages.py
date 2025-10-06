"""
Work Package Generator

Generates work packages based on project requirements and estimation models.
"""

from typing import List
from uuid import UUID, uuid4
from decimal import Decimal

from ...models.offer import WorkPackage, EstimatedHours, Deliverable, Money
from ...models.project import Project, ProjectCategory
from ...infrastructure.repositories.project_repository import ProjectRepository
from ..estimation.main import EstimationService


class WorkPackageGenerator:
    """Generates structured work packages for projects."""

    DEFAULT_HOURLY_RATE = Decimal("120.00")  # EUR 120/hour

    # Standard work package templates by project category
    WP_TEMPLATES = {
        ProjectCategory.SOFTWARE_DEVELOPMENT: [
            {
                "name": "Requirements Analysis & Planning",
                "description": "Detailed requirements gathering, technical planning, and architecture design",
                "percentage": 0.15
            },
            {
                "name": "Backend Development",
                "description": "Server-side implementation, API development, and database setup",
                "percentage": 0.30
            },
            {
                "name": "Frontend Development",
                "description": "User interface implementation and client-side logic",
                "percentage": 0.25
            },
            {
                "name": "Testing & Quality Assurance",
                "description": "Unit testing, integration testing, and quality assurance",
                "percentage": 0.15
            },
            {
                "name": "Deployment & Documentation",
                "description": "Production deployment, documentation, and knowledge transfer",
                "percentage": 0.15
            },
        ],
        ProjectCategory.IT_CONSULTING: [
            {
                "name": "Current State Assessment",
                "description": "Analysis of existing systems and processes",
                "percentage": 0.25
            },
            {
                "name": "Strategy Development",
                "description": "IT strategy and roadmap development",
                "percentage": 0.35
            },
            {
                "name": "Implementation Support",
                "description": "Implementation guidance and support",
                "percentage": 0.25
            },
            {
                "name": "Training & Documentation",
                "description": "Staff training and documentation delivery",
                "percentage": 0.15
            },
        ],
    }

    def __init__(self):
        self.project_repo = ProjectRepository()
        self.estimation_service = EstimationService()

    async def generate_work_packages(
        self,
        project_id: UUID
    ) -> List[WorkPackage]:
        """
        Generate work packages for a project.

        Args:
            project_id: Project identifier

        Returns:
            List of work packages with estimates
        """
        # Load project
        project = await self.project_repo.get_by_id(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        # Get total hour estimate
        total_hours = await self.estimation_service.estimate_hours(project)

        # Select template based on project category
        templates = self.WP_TEMPLATES.get(
            project.category,
            self.WP_TEMPLATES[ProjectCategory.SOFTWARE_DEVELOPMENT]
        )

        # Generate work packages
        work_packages = []
        for i, template in enumerate(templates):
            wp = await self._create_work_package(
                template=template,
                total_hours=total_hours,
                project=project,
                order=i + 1
            )
            work_packages.append(wp)

        # Add dependencies
        work_packages = self._add_dependencies(work_packages)

        return work_packages

    async def _create_work_package(
        self,
        template: dict,
        total_hours: Decimal,
        project: Project,
        order: int
    ) -> WorkPackage:
        """Create individual work package from template."""
        # Calculate hours for this package
        package_hours = total_hours * Decimal(str(template["percentage"]))

        # Create estimated hours with PERT distribution
        estimated_hours = EstimatedHours(
            optimistic=package_hours * Decimal("0.8"),
            likely=package_hours,
            pessimistic=package_hours * Decimal("1.3"),
            confidence=0.75
        )

        # Calculate cost
        total_cost = Money(
            amount=estimated_hours.expected * self.DEFAULT_HOURLY_RATE,
            currency="EUR"
        )

        # Generate deliverables
        deliverables = self._generate_deliverables(template["name"], project)

        wp = WorkPackage(
            id=uuid4(),
            offer_id=uuid4(),  # Will be set when offer is created
            name=template["name"],
            description=template["description"],
            deliverables=deliverables,
            estimated_hours=estimated_hours,
            hourly_rate=Money(amount=self.DEFAULT_HOURLY_RATE, currency="EUR"),
            total_cost=total_cost,
            dependencies=[],
            order=order
        )

        return wp

    def _generate_deliverables(
        self,
        package_name: str,
        project: Project
    ) -> List[Deliverable]:
        """Generate deliverables for work package."""
        # Standard deliverable templates
        deliverable_map = {
            "Requirements Analysis & Planning": [
                Deliverable(
                    name="Requirements Specification Document",
                    description="Comprehensive requirements documentation",
                    acceptance_criteria=[
                        "All functional requirements documented",
                        "Non-functional requirements specified",
                        "Stakeholder approval obtained"
                    ]
                ),
                Deliverable(
                    name="Technical Architecture Design",
                    description="System architecture and design documents",
                    acceptance_criteria=[
                        "Architecture diagrams completed",
                        "Technology stack defined",
                        "Security architecture documented"
                    ]
                ),
            ],
            "Backend Development": [
                Deliverable(
                    name="RESTful API Implementation",
                    description="Backend API with all endpoints",
                    acceptance_criteria=[
                        "All API endpoints implemented",
                        "OpenAPI documentation generated",
                        "API tests passing"
                    ]
                ),
                Deliverable(
                    name="Database Schema",
                    description="Database design and implementation",
                    acceptance_criteria=[
                        "Database schema implemented",
                        "Migrations created",
                        "Data integrity ensured"
                    ]
                ),
            ],
            "Frontend Development": [
                Deliverable(
                    name="User Interface",
                    description="Complete frontend application",
                    acceptance_criteria=[
                        "All screens implemented",
                        "Responsive design verified",
                        "Accessibility standards met"
                    ]
                ),
            ],
            "Testing & Quality Assurance": [
                Deliverable(
                    name="Test Suite",
                    description="Comprehensive automated tests",
                    acceptance_criteria=[
                        "Unit test coverage >80%",
                        "Integration tests passing",
                        "E2E tests for critical paths"
                    ]
                ),
                Deliverable(
                    name="QA Report",
                    description="Quality assurance and testing report",
                    acceptance_criteria=[
                        "All critical bugs resolved",
                        "Performance metrics met",
                        "Security scan completed"
                    ]
                ),
            ],
            "Deployment & Documentation": [
                Deliverable(
                    name="Production Deployment",
                    description="Application deployed to production",
                    acceptance_criteria=[
                        "Application running in production",
                        "Monitoring configured",
                        "Backup systems operational"
                    ]
                ),
                Deliverable(
                    name="Technical Documentation",
                    description="Complete system documentation",
                    acceptance_criteria=[
                        "API documentation complete",
                        "Deployment guide created",
                        "Maintenance procedures documented"
                    ]
                ),
            ],
        }

        # Return matching deliverables or generic ones
        return deliverable_map.get(package_name, [
            Deliverable(
                name=f"{package_name} Completion",
                description=f"All tasks for {package_name} completed",
                acceptance_criteria=[
                    "All planned work completed",
                    "Quality standards met",
                    "Stakeholder acceptance obtained"
                ]
            )
        ])

    def _add_dependencies(
        self,
        work_packages: List[WorkPackage]
    ) -> List[WorkPackage]:
        """Add dependency relationships between work packages."""
        # Simple linear dependency: each package depends on previous one
        for i in range(1, len(work_packages)):
            work_packages[i].dependencies = [work_packages[i - 1].id]

        return work_packages

    async def customize_work_package(
        self,
        work_package: WorkPackage,
        customizations: dict
    ) -> WorkPackage:
        """
        Customize work package based on specific requirements.

        Args:
            work_package: Base work package
            customizations: Customization parameters

        Returns:
            Customized work package
        """
        if "hours_adjustment" in customizations:
            multiplier = Decimal(str(customizations["hours_adjustment"]))
            work_package.estimated_hours.optimistic *= multiplier
            work_package.estimated_hours.likely *= multiplier
            work_package.estimated_hours.pessimistic *= multiplier

            # Recalculate cost
            work_package.total_cost = Money(
                amount=work_package.estimated_hours.expected * work_package.hourly_rate.amount,
                currency="EUR"
            )

        if "deliverables" in customizations:
            additional_deliverables = [
                Deliverable(**d) for d in customizations["deliverables"]
            ]
            work_package.deliverables.extend(additional_deliverables)

        if "description" in customizations:
            work_package.description = customizations["description"]

        return work_package
