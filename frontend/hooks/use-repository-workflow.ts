"use client";

import { FormEvent, useState } from "react";

import {
  fetchRepositoryContext,
  generateRepositoryTests,
  investigateRepository,
  previewRepositoryGenerationContext,
  proposeRepositoryFix,
  runRepositoryTests,
} from "../lib/api";
import type {
  RepositoryGenerationRun,
  RepositoryGenerationContextPreview,
  RepositoryInvestigationRun,
  RepositoryContext,
  RepositoryFixProposalRun,
  RepositoryMetadata,
  RepositoryTestPlan,
  RepositoryTestRun,
  RepositoryTree,
} from "../types/api";

function isPublicGitHubRepositoryUrl(value: string): boolean {
  try {
    const url = new URL(value);
    const pathSegments = url.pathname.split("/").filter(Boolean);

    return (
      url.protocol === "https:" &&
      url.hostname === "github.com" &&
      !url.port &&
      pathSegments.length === 2 &&
      !url.search &&
      !url.hash
    );
  } catch {
    return false;
  }
}

export function useRepositoryWorkflow() {
  const [repositoryUrl, setRepositoryUrl] = useState("");
  const [repositoryReference, setRepositoryReference] = useState("");
  const [repositorySubdirectory, setRepositorySubdirectory] = useState("");
  const [repositoryContext, setRepositoryContext] = useState<RepositoryContext | null>(null);
  const [repository, setRepository] = useState<RepositoryMetadata | null>(null);
  const [repositoryTree, setRepositoryTree] = useState<RepositoryTree | null>(null);
  const [repositoryTestPlan, setRepositoryTestPlan] = useState<RepositoryTestPlan | null>(null);
  const [isRepositoryLoading, setIsRepositoryLoading] = useState(false);
  const [repositoryError, setRepositoryError] = useState<string | null>(null);
  const [selectedTargetPath, setSelectedTargetPath] = useState("");
  const [repositoryContextPreview, setRepositoryContextPreview] =
    useState<RepositoryGenerationContextPreview | null>(null);
  const [isRepositoryContextPreviewLoading, setIsRepositoryContextPreviewLoading] =
    useState(false);
  const [repositoryContextPreviewError, setRepositoryContextPreviewError] =
    useState<string | null>(null);
  const [repositoryTestRun, setRepositoryTestRun] = useState<RepositoryTestRun | null>(null);
  const [isRepositoryTestRunning, setIsRepositoryTestRunning] = useState(false);
  const [repositoryTestError, setRepositoryTestError] = useState<string | null>(null);
  const [repositoryGenerationRun, setRepositoryGenerationRun] =
    useState<RepositoryGenerationRun | null>(null);
  const [isRepositoryGenerationRunning, setIsRepositoryGenerationRunning] = useState(false);
  const [repositoryGenerationError, setRepositoryGenerationError] = useState<string | null>(null);
  const [repositoryInvestigationRun, setRepositoryInvestigationRun] =
    useState<RepositoryInvestigationRun | null>(null);
  const [isRepositoryInvestigationRunning, setIsRepositoryInvestigationRunning] =
    useState(false);
  const [repositoryInvestigationError, setRepositoryInvestigationError] =
    useState<string | null>(null);
  const [repositoryFixProposalRun, setRepositoryFixProposalRun] =
    useState<RepositoryFixProposalRun | null>(null);
  const [isRepositoryFixProposalRunning, setIsRepositoryFixProposalRunning] =
    useState(false);
  const [repositoryFixProposalError, setRepositoryFixProposalError] =
    useState<string | null>(null);

  async function handleRepositorySubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!isPublicGitHubRepositoryUrl(repositoryUrl)) {
      setRepositoryError(
        "Enter a public GitHub repository URL, such as https://github.com/owner/repository.",
      );
      setRepository(null);
      setRepositoryContext(null);
      setRepositoryTree(null);
      setRepositoryTestPlan(null);
      setSelectedTargetPath("");
      setRepositoryContextPreview(null);
      setRepositoryContextPreviewError(null);
      setRepositoryTestRun(null);
      setRepositoryTestError(null);
      setRepositoryGenerationRun(null);
      setRepositoryGenerationError(null);
      setRepositoryInvestigationRun(null);
      setRepositoryInvestigationError(null);
      setRepositoryFixProposalRun(null);
      setRepositoryFixProposalError(null);
      return;
    }

    setIsRepositoryLoading(true);
    setRepositoryError(null);
    setRepository(null);
    setRepositoryContext(null);
    setRepositoryTree(null);
    setRepositoryTestPlan(null);
    setSelectedTargetPath("");
    setRepositoryContextPreview(null);
    setRepositoryContextPreviewError(null);
    setRepositoryTestRun(null);
    setRepositoryTestError(null);
    setRepositoryGenerationRun(null);
    setRepositoryGenerationError(null);
    setRepositoryInvestigationRun(null);
    setRepositoryInvestigationError(null);
    setRepositoryFixProposalRun(null);
    setRepositoryFixProposalError(null);

    try {
      const context = await fetchRepositoryContext(repositoryUrl, {
        reference: repositoryReference.trim() || undefined,
        subdirectory: repositorySubdirectory.trim() || undefined,
      });

      setRepositoryContext(context);
      setRepository(context.metadata);
      setRepositoryTree(context.tree);
      setRepositoryTestPlan(context.test_plan);
      setSelectedTargetPath(context.generation_selection.target_path ?? "");
    } catch (error) {
      setRepositoryError(
        error instanceof Error
          ? error.message
          : "Unable to fetch repository details. Please try again.",
      );
    } finally {
      setIsRepositoryLoading(false);
    }
  }

  function handleRepositoryTargetChange(targetPath: string) {
    setSelectedTargetPath(targetPath);
    setRepositoryContextPreview(null);
    setRepositoryContextPreviewError(null);
    setRepositoryGenerationRun(null);
    setRepositoryGenerationError(null);
    setRepositoryInvestigationRun(null);
    setRepositoryInvestigationError(null);
    setRepositoryFixProposalRun(null);
    setRepositoryFixProposalError(null);
  }

  async function handleRepositoryContextPreview() {
    if (repository === null || repositoryContext === null) {
      setRepositoryContextPreviewError(
        "Fetch a public Python repository before previewing its Gemini context.",
      );
      return;
    }
    if (!selectedTargetPath) {
      setRepositoryContextPreviewError("Select a Python source file to preview.");
      return;
    }

    setIsRepositoryContextPreviewLoading(true);
    setRepositoryContextPreviewError(null);
    setRepositoryContextPreview(null);

    try {
      const preview = await previewRepositoryGenerationContext(repository.url, {
        reference: repositoryContext.revision,
        subdirectory: repositoryContext.subdirectory ?? undefined,
        targetPath: selectedTargetPath,
      });

      setRepositoryContextPreview(preview);
    } catch (error) {
      setRepositoryContextPreviewError(
        error instanceof Error
          ? error.message
          : "Unable to preview the Gemini context. Please try again.",
      );
    } finally {
      setIsRepositoryContextPreviewLoading(false);
    }
  }

  async function handleRepositoryTestRun() {
    if (repository === null || repositoryContext === null) {
      setRepositoryTestError("Fetch a public Python repository before running its tests.");
      return;
    }

    setIsRepositoryTestRunning(true);
    setRepositoryTestError(null);
    setRepositoryTestRun(null);
    setRepositoryGenerationError(null);
    setRepositoryGenerationRun(null);
    setRepositoryInvestigationError(null);
    setRepositoryInvestigationRun(null);
    setRepositoryFixProposalError(null);
    setRepositoryFixProposalRun(null);

    try {
      const result = await runRepositoryTests(repository.url, {
        reference: repositoryContext.revision,
        subdirectory: repositoryContext.subdirectory ?? undefined,
      });

      setRepositoryTestRun(result);
    } catch (error) {
      setRepositoryTestError(
        error instanceof Error
          ? error.message
          : "Unable to run repository tests. Please try again.",
      );
    } finally {
      setIsRepositoryTestRunning(false);
    }
  }

  async function handleRepositoryGeneration() {
    if (repository === null || repositoryContext === null) {
      setRepositoryGenerationError(
        "Fetch a public Python repository before generating its tests.",
      );
      return;
    }
    if (!selectedTargetPath) {
      setRepositoryGenerationError("Select a Python source file before generating tests.");
      return;
    }

    setIsRepositoryGenerationRunning(true);
    setRepositoryGenerationError(null);
    setRepositoryGenerationRun(null);
    setRepositoryTestError(null);
    setRepositoryTestRun(null);
    setRepositoryInvestigationError(null);
    setRepositoryInvestigationRun(null);
    setRepositoryFixProposalError(null);
    setRepositoryFixProposalRun(null);

    try {
      const result = await generateRepositoryTests(repository.url, {
        reference: repositoryContext.revision,
        subdirectory: repositoryContext.subdirectory ?? undefined,
        targetPath: selectedTargetPath,
      });

      setRepositoryGenerationRun(result);
    } catch (error) {
      setRepositoryGenerationError(
        error instanceof Error
          ? error.message
          : "Unable to generate repository tests. Please try again.",
      );
    } finally {
      setIsRepositoryGenerationRunning(false);
    }
  }

  async function handleRepositoryInvestigation() {
    if (repository === null || repositoryContext === null) {
      setRepositoryInvestigationError(
        "Fetch a public Python repository before investigating it.",
      );
      return;
    }
    if (!selectedTargetPath) {
      setRepositoryInvestigationError(
        "Select a Python source file before investigating the repository.",
      );
      return;
    }

    setIsRepositoryInvestigationRunning(true);
    setRepositoryInvestigationError(null);
    setRepositoryInvestigationRun(null);
    setRepositoryTestError(null);
    setRepositoryTestRun(null);
    setRepositoryGenerationError(null);
    setRepositoryGenerationRun(null);
    setRepositoryFixProposalError(null);
    setRepositoryFixProposalRun(null);

    try {
      const result = await investigateRepository(repository.url, {
        reference: repositoryContext.revision,
        subdirectory: repositoryContext.subdirectory ?? undefined,
        targetPath: selectedTargetPath,
      });

      setRepositoryInvestigationRun(result);
      setRepositoryTestPlan(result.test_plan);
    } catch (error) {
      setRepositoryInvestigationError(
        error instanceof Error
          ? error.message
          : "Unable to investigate the repository. Please try again.",
      );
    } finally {
      setIsRepositoryInvestigationRunning(false);
    }
  }

  async function handleRepositoryFixProposal() {
    if (repository === null || repositoryContext === null) {
      setRepositoryFixProposalError(
        "Fetch a public Python repository before proposing a fix.",
      );
      return;
    }
    if (!selectedTargetPath) {
      setRepositoryFixProposalError(
        "Select a Python source file before proposing a fix.",
      );
      return;
    }

    setIsRepositoryFixProposalRunning(true);
    setRepositoryFixProposalError(null);
    setRepositoryFixProposalRun(null);
    setRepositoryTestError(null);
    setRepositoryTestRun(null);
    setRepositoryGenerationError(null);
    setRepositoryGenerationRun(null);
    setRepositoryInvestigationError(null);
    setRepositoryInvestigationRun(null);

    try {
      const result = await proposeRepositoryFix(repository.url, {
        reference: repositoryContext.revision,
        subdirectory: repositoryContext.subdirectory ?? undefined,
        targetPath: selectedTargetPath,
      });

      setRepositoryFixProposalRun(result);
      setRepositoryTestPlan(result.test_plan);
    } catch (error) {
      setRepositoryFixProposalError(
        error instanceof Error
          ? error.message
          : "Unable to propose a repository fix. Please try again.",
      );
    } finally {
      setIsRepositoryFixProposalRunning(false);
    }
  }

  return {
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
  };
}
