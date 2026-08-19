"use client";

import { PastedCodeGenerator } from "../components/pasted-code-generator";
import {
  RepositoryGenerationResult,
  RepositoryInvestigationResult,
  RepositoryTestRunResult,
} from "../components/repository-execution-results";
import {
  RepositorySummary,
  RepositoryTestPlanPanel,
  RepositoryTreeView,
} from "../components/repository-inspection";
import { useRepositoryWorkflow } from "../hooks/use-repository-workflow";

export default function Home() {
  const {
    repositoryUrl,
    setRepositoryUrl,
    repository,
    repositoryTree,
    repositoryTestPlan,
    isRepositoryLoading,
    repositoryError,
    repositoryTestRun,
    isRepositoryTestRunning,
    repositoryTestError,
    repositoryGenerationRun,
    isRepositoryGenerationRunning,
    repositoryGenerationError,
    repositoryInvestigationRun,
    isRepositoryInvestigationRunning,
    repositoryInvestigationError,
    handleRepositorySubmit,
    handleRepositoryTestRun,
    handleRepositoryGeneration,
    handleRepositoryInvestigation,
  } = useRepositoryWorkflow();

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
            disabled={
              isRepositoryLoading ||
              isRepositoryTestRunning ||
              isRepositoryGenerationRunning
              || isRepositoryInvestigationRunning
            }
            onChange={(event) => setRepositoryUrl(event.target.value)}
          />
          <p className="field-hint">Use an HTTPS URL for a public repository.</p>
          <button
            disabled={
              isRepositoryLoading ||
              isRepositoryTestRunning ||
              isRepositoryGenerationRunning
              || isRepositoryInvestigationRunning
            }
            type="submit"
          >
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
        {repositoryTestPlan !== null && (
          <RepositoryTestPlanPanel
            plan={repositoryTestPlan}
            isRepositoryLoading={isRepositoryLoading}
            isRepositoryTestRunning={isRepositoryTestRunning}
            isRepositoryGenerationRunning={isRepositoryGenerationRunning}
            isRepositoryInvestigationRunning={isRepositoryInvestigationRunning}
            repositoryTestError={repositoryTestError}
            repositoryGenerationError={repositoryGenerationError}
            repositoryInvestigationError={repositoryInvestigationError}
            onRunRepositoryTests={handleRepositoryTestRun}
            onGenerateRepositoryTests={handleRepositoryGeneration}
            onInvestigateRepository={handleRepositoryInvestigation}
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
        <PastedCodeGenerator />
      </section>
    </main>
  );
}
