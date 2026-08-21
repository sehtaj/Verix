"""Coordinate one investigation and one unapplied repository fix proposal."""

from models.fix_proposal import RepositoryFixProposalRun
from services.llm_service import GeminiLLMService
from services.repository_fix_context import select_repository_fix_context
from services.repository_fix_validation import validate_repository_fix_proposal
from workflows.repository_investigation import RepositoryInvestigationWorkflow


class RepositoryFixProposalWorkflow:
    """Generate one review-only proposal from one completed investigation."""

    def __init__(
        self,
        investigation_workflow: RepositoryInvestigationWorkflow,
        llm_service: GeminiLLMService,
    ) -> None:
        self.investigation_workflow = investigation_workflow
        self.llm_service = llm_service

    def run(
        self,
        repository_url: str,
        reference: str | None = None,
        subdirectory: str | None = None,
        target_path: str | None = None,
    ) -> RepositoryFixProposalRun:
        """Investigate once and generate one proposal without applying it."""
        investigation = self.investigation_workflow.run(
            repository_url,
            reference,
            subdirectory,
            target_path,
        )
        generation_context = investigation.generation_context
        if generation_context is None:
            raise RuntimeError("Repository investigation did not preserve fix context.")

        fix_context = select_repository_fix_context(
            generation_context,
            investigation,
        )
        proposal = self.llm_service.generate_repository_fix_proposal(fix_context)
        try:
            validate_repository_fix_proposal(
                proposal,
                fix_context.source_file.content,
            )
        except ValueError:
            raise RuntimeError(
                "Generated repository fix proposal failed validation."
            ) from None

        return RepositoryFixProposalRun(
            investigation=investigation,
            proposal=proposal,
        )
