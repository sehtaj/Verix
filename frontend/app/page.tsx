"use client";

import { PastedCodeGenerator } from "../components/pasted-code-generator";
import {
  RepositoryGenerationResult,
  RepositoryFixProposalResult,
  RepositoryInvestigationResult,
  RepositoryTestRunResult,
} from "../components/repository-execution-results";
import {
  RepositoryContextPreview,
  RepositorySummary,
  RepositoryTestPlanPanel,
  RepositoryTreeView,
} from "../components/repository-inspection";
import { useRepositoryWorkflow } from "../hooks/use-repository-workflow";

export default function Home() {
  const {
    repositoryUrl,
    setRepositoryUrl,
    repositoryReference,
    setRepositoryReference,
    repositorySubdirectory,
    setRepositorySubdirectory,
    repositoryContext,
    repository,
    repositoryTree,
    repositoryTestPlan,
    isRepositoryLoading,
    repositoryError,
    selectedTargetPath,
    repositoryContextPreview,
    isRepositoryContextPreviewLoading,
    repositoryContextPreviewError,
    repositoryTestRun,
    isRepositoryTestRunning,
    repositoryTestError,
    repositoryGenerationRun,
    isRepositoryGenerationRunning,
    repositoryGenerationError,
    repositoryInvestigationRun,
    isRepositoryInvestigationRunning,
    repositoryInvestigationError,
    repositoryFixProposalRun,
    isRepositoryFixProposalRunning,
    repositoryFixProposalError,
    handleRepositorySubmit,
    handleRepositoryTargetChange,
    handleRepositoryContextPreview,
    handleRepositoryTestRun,
    handleRepositoryGeneration,
    handleRepositoryInvestigation,
    handleRepositoryFixProposal,
  } = useRepositoryWorkflow();

  const isRepositoryBusy =
    isRepositoryLoading ||
    isRepositoryContextPreviewLoading ||
    isRepositoryTestRunning ||
    isRepositoryGenerationRunning ||
    isRepositoryInvestigationRunning ||
    isRepositoryFixProposalRunning;

  return (
    <main>
      <section className="generator">
        <h1>Verix</h1>
        <p>Look up a public GitHub repository or generate tests for pasted Python code.</p>
        <form onSubmit={handleRepositorySubmit}>
          <label htmlFor="repository-url">GitHub repository URL</label>
          <input
            id="repository-url"
            name="repository-url"
            placeholder="https://github.com/owner/repository"
            type="url"
            value={repositoryUrl}
            disabled={isRepositoryBusy}
            onChange={(event) => setRepositoryUrl(event.target.value)}
          />
          <p className="field-hint">Use an HTTPS URL for a public repository.</p>
          <label htmlFor="repository-reference">Branch, tag, or commit (optional)</label>
          <input
            id="repository-reference"
            name="repository-reference"
            placeholder="main, release-1.0, or a commit SHA"
            type="text"
            value={repositoryReference}
            disabled={isRepositoryBusy}
            onChange={(event) => setRepositoryReference(event.target.value)}
          />
          <p className="field-hint">
            Leave empty to use the repository&apos;s default branch.
          </p>
          <label htmlFor="repository-subdirectory">Python project folder (optional)</label>
          <input
            id="repository-subdirectory"
            name="repository-subdirectory"
            placeholder="packages/payments"
            type="text"
            value={repositorySubdirectory}
            disabled={isRepositoryBusy}
            onChange={(event) => setRepositorySubdirectory(event.target.value)}
          />
          <p className="field-hint">
            Use a repository-relative folder path for a nested Python project.
          </p>
          <button disabled={isRepositoryBusy} type="submit">
            {isRepositoryLoading ? "Fetching..." : "Fetch repository"}
          </button>
          {repositoryError && (
            <p className="error" role="alert">
              {repositoryError}
            </p>
          )}
        </form>
        {repository !== null && (
          <RepositorySummary repository={repository} />
        )}
        {repositoryTree !== null && (
          <RepositoryTreeView tree={repositoryTree} />
        )}
        {repositoryContext !== null && repositoryTestPlan !== null && (
          <RepositoryContextPreview
            sourcePaths={repositoryTestPlan.source_paths}
            selectedTargetPath={selectedTargetPath}
            preview={repositoryContextPreview}
            isLoading={isRepositoryContextPreviewLoading}
            isDisabled={
              isRepositoryLoading ||
              isRepositoryTestRunning ||
              isRepositoryGenerationRunning ||
              isRepositoryInvestigationRunning ||
              isRepositoryFixProposalRunning
            }
            error={repositoryContextPreviewError}
            onTargetChange={handleRepositoryTargetChange}
            onPreview={handleRepositoryContextPreview}
          />
        )}
        {repositoryTestPlan !== null && (
          <RepositoryTestPlanPanel
            plan={repositoryTestPlan}
            isRepositoryLoading={isRepositoryLoading}
            isRepositoryTestRunning={isRepositoryTestRunning}
            isRepositoryGenerationRunning={isRepositoryGenerationRunning}
            isRepositoryInvestigationRunning={isRepositoryInvestigationRunning}
            isRepositoryFixProposalRunning={isRepositoryFixProposalRunning}
            repositoryTestError={repositoryTestError}
            repositoryGenerationError={repositoryGenerationError}
            repositoryInvestigationError={repositoryInvestigationError}
            repositoryFixProposalError={repositoryFixProposalError}
            onRunRepositoryTests={handleRepositoryTestRun}
            onGenerateRepositoryTests={handleRepositoryGeneration}
            onInvestigateRepository={handleRepositoryInvestigation}
            onProposeRepositoryFix={handleRepositoryFixProposal}
          />
        )}
        {repositoryTestRun !== null && (
          <RepositoryTestRunResult result={repositoryTestRun} />
        )}
        {repositoryGenerationRun !== null && (
          <RepositoryGenerationResult result={repositoryGenerationRun} />
        )}
        {repositoryInvestigationRun !== null && (
          <RepositoryInvestigationResult result={repositoryInvestigationRun} />
        )}
        {repositoryFixProposalRun !== null && (
          <RepositoryFixProposalResult result={repositoryFixProposalRun} />
        )}
        <PastedCodeGenerator />
      </section>
    </main>
  );
}
