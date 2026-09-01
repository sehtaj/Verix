"use client";

import { type FormEvent, useRef, useState } from "react";

import {
  fetchRepositoryContext,
  generateRepositoryTests,
  investigateRepository,
  previewRepositoryGenerationContext,
  proposeRepositoryFix,
  runRepositoryTests,
  verifyRepositoryFix,
} from "@/lib/api";
import { getExecutionStatus } from "@/lib/repository-results";
import type {
  RepositoryContext,
  RepositoryFixProposalRun,
  RepositoryFixVerificationRun,
  RepositoryGenerationContextPreview,
  RepositoryGenerationRun,
  RepositoryInvestigationRun,
  RepositoryTestRun,
} from "@/types/api";
import type { WorkflowScreen } from "@/types/workflow";

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

function readyScreen(context: RepositoryContext): WorkflowScreen {
  return context.test_plan.test_paths.length > 0
    ? "ready_existing_tests"
    : "ready_generate_tests";
}

export function useRepositoryWorkflow() {
  const requestEpoch = useRef(0);
  const previewRequestEpoch = useRef(0);
  const activeRequest = useRef(false);
  const activePreviewRequest = useRef(false);
  const activeRequestOrigin = useRef<WorkflowScreen | null>(null);
  const [screen, setScreen] = useState<WorkflowScreen>("new_verification");
  const [repositoryUrl, setRepositoryUrl] = useState("");
  const [repositoryReference, setRepositoryReference] = useState("");
  const [repositorySubdirectory, setRepositorySubdirectory] = useState("");
  const [repositoryContext, setRepositoryContext] = useState<RepositoryContext | null>(null);
  const [selectedTargetPath, setSelectedTargetPath] = useState("");

  const [repositoryError, setRepositoryError] = useState<string | null>(null);
  const [repositoryContextPreview, setRepositoryContextPreview] =
    useState<RepositoryGenerationContextPreview | null>(null);
  const [isRepositoryContextPreviewLoading, setIsRepositoryContextPreviewLoading] =
    useState(false);
  const [repositoryContextPreviewError, setRepositoryContextPreviewError] =
    useState<string | null>(null);
  const [repositoryTestRun, setRepositoryTestRun] = useState<RepositoryTestRun | null>(null);
  const [repositoryTestError, setRepositoryTestError] = useState<string | null>(null);
  const [repositoryGenerationRun, setRepositoryGenerationRun] =
    useState<RepositoryGenerationRun | null>(null);
  const [repositoryGenerationError, setRepositoryGenerationError] = useState<string | null>(null);
  const [repositoryInvestigationRun, setRepositoryInvestigationRun] =
    useState<RepositoryInvestigationRun | null>(null);
  const [repositoryInvestigationError, setRepositoryInvestigationError] =
    useState<string | null>(null);
  const [repositoryFixProposalRun, setRepositoryFixProposalRun] =
    useState<RepositoryFixProposalRun | null>(null);
  const [repositoryFixProposalError, setRepositoryFixProposalError] =
    useState<string | null>(null);
  const [repositoryFixVerificationRun, setRepositoryFixVerificationRun] =
    useState<RepositoryFixVerificationRun | null>(null);
  const [repositoryFixVerificationError, setRepositoryFixVerificationError] =
    useState<string | null>(null);

  const isRepositoryLoading = screen === "loading_context";
  const isRepositoryBusy = [
    "loading_context",
    "running_existing_tests",
    "generating_tests",
    "investigating",
    "proposing_fix",
    "verifying_fix",
  ].includes(screen) || isRepositoryContextPreviewLoading;

  function requestBecameStale(epoch: number): boolean {
    return requestEpoch.current !== epoch;
  }

  function clearActionErrors() {
    setRepositoryError(null);
    setRepositoryContextPreviewError(null);
    setRepositoryTestError(null);
    setRepositoryGenerationError(null);
    setRepositoryInvestigationError(null);
    setRepositoryFixProposalError(null);
    setRepositoryFixVerificationError(null);
  }

  function clearEvidence() {
    setRepositoryContextPreview(null);
    setRepositoryTestRun(null);
    setRepositoryGenerationRun(null);
    setRepositoryInvestigationRun(null);
    setRepositoryFixProposalRun(null);
    setRepositoryFixVerificationRun(null);
    clearActionErrors();
  }

  function resetWorkflow(force = false): boolean {
    const hasUnreviewedProposal = repositoryFixProposalRun !== null && repositoryFixVerificationRun === null;
    if (
      !force &&
      (activeRequest.current || activePreviewRequest.current || isRepositoryBusy || hasUnreviewedProposal) &&
      !window.confirm("Start a new verification and clear the current browser-held results?")
    ) {
      return false;
    }

    setScreen("new_verification");
    setRepositoryUrl("");
    setRepositoryReference("");
    setRepositorySubdirectory("");
    setRepositoryContext(null);
    setSelectedTargetPath("");
    requestEpoch.current += 1;
    previewRequestEpoch.current += 1;
    activeRequest.current = false;
    activePreviewRequest.current = false;
    activeRequestOrigin.current = null;
    setIsRepositoryContextPreviewLoading(false);
    clearEvidence();
    return true;
  }

  async function handleRepositorySubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedUrl = repositoryUrl.trim();

    if (!isPublicGitHubRepositoryUrl(trimmedUrl)) {
      setRepositoryError(
        "Enter a public GitHub repository URL, such as https://github.com/owner/repository.",
      );
      return;
    }
    if (activeRequest.current) return;

    activeRequest.current = true;
    activeRequestOrigin.current = screen;
    clearEvidence();
    setScreen("loading_context");
    const epoch = requestEpoch.current;

    try {
      const context = await fetchRepositoryContext(trimmedUrl, {
        reference: repositoryReference.trim() || undefined,
        subdirectory: repositorySubdirectory.trim() || undefined,
      });
      if (requestBecameStale(epoch)) return;

      setRepositoryUrl(context.metadata.url);
      setRepositoryContext(context);
      setSelectedTargetPath(context.generation_selection.target_path ?? "");
      setScreen(readyScreen(context));
    } catch (error) {
      if (requestBecameStale(epoch)) return;
      setRepositoryError(
        error instanceof Error
          ? error.message
          : "Unable to fetch repository details. Please try again.",
      );
      setScreen("new_verification");
    } finally {
      if (!requestBecameStale(epoch)) {
        activeRequest.current = false;
        activeRequestOrigin.current = null;
      }
    }
  }

  async function handleRepositoryTargetChange(targetPath: string) {
    if (repositoryContext === null || targetPath === selectedTargetPath || activeRequest.current) return;

    activeRequest.current = true;
    const previousTarget = selectedTargetPath;
    const previousScreen = screen;
    activeRequestOrigin.current = previousScreen;
    setSelectedTargetPath(targetPath);
    setRepositoryError(null);
    setScreen("loading_context");
    const epoch = requestEpoch.current;

    try {
      const context = await fetchRepositoryContext(repositoryContext.metadata.url, {
        reference: repositoryContext.revision,
        subdirectory: repositoryContext.subdirectory ?? undefined,
        targetPath,
      });
      if (requestBecameStale(epoch)) return;
      clearEvidence();
      setRepositoryContext(context);
      setSelectedTargetPath(context.generation_selection.target_path ?? targetPath);
      setScreen(readyScreen(context));
    } catch (error) {
      if (requestBecameStale(epoch)) return;
      setSelectedTargetPath(previousTarget);
      setRepositoryError(
        error instanceof Error ? error.message : "Unable to select that source target.",
      );
      setScreen(previousScreen);
    } finally {
      if (!requestBecameStale(epoch)) {
        activeRequest.current = false;
        activeRequestOrigin.current = null;
      }
    }
  }

  async function handleRepositoryContextPreview() {
    if (repositoryContext === null || !selectedTargetPath) {
      setRepositoryContextPreviewError(
        "Select a verified Python source file before previewing its context.",
      );
      return;
    }
    if (activePreviewRequest.current) return;

    activePreviewRequest.current = true;
    setRepositoryContextPreviewError(null);
    setRepositoryContextPreview(null);
    setIsRepositoryContextPreviewLoading(true);
    const epoch = previewRequestEpoch.current;

    try {
      const preview = await previewRepositoryGenerationContext(
        repositoryContext.metadata.url,
        {
          reference: repositoryContext.revision,
          subdirectory: repositoryContext.subdirectory ?? undefined,
          targetPath: selectedTargetPath,
        },
      );
      if (previewRequestEpoch.current !== epoch) return;
      setRepositoryContextPreview(preview);
    } catch (error) {
      if (previewRequestEpoch.current !== epoch) return;
      setRepositoryContextPreviewError(
        error instanceof Error ? error.message : "Unable to preview the selected context.",
      );
    } finally {
      if (previewRequestEpoch.current === epoch) {
        activePreviewRequest.current = false;
        setIsRepositoryContextPreviewLoading(false);
      }
    }
  }

  async function handleRepositoryTestRun() {
    if (repositoryContext === null || activeRequest.current) return;
    activeRequest.current = true;
    const previousScreen = screen;
    activeRequestOrigin.current = previousScreen;
    clearActionErrors();
    setScreen("running_existing_tests");
    const epoch = requestEpoch.current;

    try {
      const result = await runRepositoryTests(repositoryContext.metadata.url, {
        reference: repositoryContext.revision,
        subdirectory: repositoryContext.subdirectory ?? undefined,
      });
      if (requestBecameStale(epoch)) return;
      setRepositoryTestRun(result);
      setScreen(
        getExecutionStatus(result.execution) === "no_tests"
          ? "ready_generate_tests"
          : "showing_test_result",
      );
    } catch (error) {
      if (requestBecameStale(epoch)) return;
      setRepositoryTestError(
        error instanceof Error ? error.message : "Unable to run repository tests.",
      );
      setScreen(previousScreen === "showing_test_result" ? previousScreen : readyScreen(repositoryContext));
    } finally {
      if (!requestBecameStale(epoch)) {
        activeRequest.current = false;
        activeRequestOrigin.current = null;
      }
    }
  }

  async function handleRepositoryGeneration() {
    if (repositoryContext === null || !selectedTargetPath || activeRequest.current) return;
    activeRequest.current = true;
    const previousScreen = screen;
    activeRequestOrigin.current = previousScreen;
    clearActionErrors();
    setScreen("generating_tests");
    const epoch = requestEpoch.current;

    try {
      const result = await generateRepositoryTests(repositoryContext.metadata.url, {
        reference: repositoryContext.revision,
        subdirectory: repositoryContext.subdirectory ?? undefined,
        targetPath: selectedTargetPath,
      });
      if (requestBecameStale(epoch)) return;
      setRepositoryGenerationRun(result);
      setScreen("showing_generation_result");
    } catch (error) {
      if (requestBecameStale(epoch)) return;
      setRepositoryGenerationError(
        error instanceof Error ? error.message : "Unable to generate focused tests.",
      );
      setScreen(
        previousScreen === "showing_test_result" || previousScreen === "showing_generation_result"
          ? previousScreen
          : readyScreen(repositoryContext),
      );
    } finally {
      if (!requestBecameStale(epoch)) {
        activeRequest.current = false;
        activeRequestOrigin.current = null;
      }
    }
  }

  async function handleRepositoryInvestigation() {
    if (repositoryContext === null || !selectedTargetPath || activeRequest.current) return;
    activeRequest.current = true;
    const previousScreen = screen;
    activeRequestOrigin.current = previousScreen;
    clearActionErrors();
    setScreen("investigating");
    const epoch = requestEpoch.current;

    try {
      const result = await investigateRepository(repositoryContext.metadata.url, {
        reference: repositoryContext.revision,
        subdirectory: repositoryContext.subdirectory ?? undefined,
        targetPath: selectedTargetPath,
      });
      if (requestBecameStale(epoch)) return;
      setRepositoryInvestigationRun(result);
      setScreen("showing_investigation");
    } catch (error) {
      if (requestBecameStale(epoch)) return;
      setRepositoryInvestigationError(
        error instanceof Error ? error.message : "Unable to investigate the repository.",
      );
      setScreen(
        previousScreen === "showing_test_result" ||
          previousScreen === "showing_generation_result" ||
          previousScreen === "showing_investigation"
          ? previousScreen
          : readyScreen(repositoryContext),
      );
    } finally {
      if (!requestBecameStale(epoch)) {
        activeRequest.current = false;
        activeRequestOrigin.current = null;
      }
    }
  }

  async function handleRepositoryFixProposal() {
    if (repositoryContext === null || !selectedTargetPath || activeRequest.current) return;
    activeRequest.current = true;
    activeRequestOrigin.current = screen;
    clearActionErrors();
    setScreen("proposing_fix");
    const epoch = requestEpoch.current;

    try {
      const result = await proposeRepositoryFix(repositoryContext.metadata.url, {
        reference: repositoryContext.revision,
        subdirectory: repositoryContext.subdirectory ?? undefined,
        targetPath: selectedTargetPath,
      });
      if (requestBecameStale(epoch)) return;
      setRepositoryFixProposalRun(result);
      setRepositoryFixVerificationRun(null);
      setRepositoryInvestigationRun(result);
      setScreen("reviewing_fix");
    } catch (error) {
      if (requestBecameStale(epoch)) return;
      setRepositoryFixProposalError(
        error instanceof Error ? error.message : "Unable to propose a source fix.",
      );
      setScreen("showing_investigation");
    } finally {
      if (!requestBecameStale(epoch)) {
        activeRequest.current = false;
        activeRequestOrigin.current = null;
      }
    }
  }

  async function handleRepositoryFixVerification() {
    if (repositoryContext === null || repositoryFixProposalRun === null || activeRequest.current) return;
    activeRequest.current = true;
    activeRequestOrigin.current = screen;
    clearActionErrors();
    setScreen("verifying_fix");
    const epoch = requestEpoch.current;

    try {
      const result = await verifyRepositoryFix(
        repositoryContext.metadata.url,
        repositoryFixProposalRun.proposal,
      );
      if (requestBecameStale(epoch)) return;
      setRepositoryFixVerificationRun(result);
      setScreen("showing_verification_result");
    } catch (error) {
      if (requestBecameStale(epoch)) return;
      setRepositoryFixVerificationError(
        error instanceof Error ? error.message : "Unable to verify the approved patch.",
      );
      setScreen("reviewing_fix");
    } finally {
      if (!requestBecameStale(epoch)) {
        activeRequest.current = false;
        activeRequestOrigin.current = null;
      }
    }
  }

  function handleBackToInvestigation() {
    if (repositoryInvestigationRun !== null) setScreen("showing_investigation");
  }

  return {
    screen,
    activeRequestOrigin: activeRequestOrigin.current,
    repositoryUrl,
    setRepositoryUrl,
    repositoryReference,
    setRepositoryReference,
    repositorySubdirectory,
    setRepositorySubdirectory,
    repositoryContext,
    selectedTargetPath,
    repositoryError,
    repositoryContextPreview,
    repositoryContextPreviewError,
    repositoryTestRun,
    repositoryTestError,
    repositoryGenerationRun,
    repositoryGenerationError,
    repositoryInvestigationRun,
    repositoryInvestigationError,
    repositoryFixProposalRun,
    repositoryFixProposalError,
    repositoryFixVerificationRun,
    repositoryFixVerificationError,
    isRepositoryLoading,
    isRepositoryContextPreviewLoading,
    isRepositoryBusy,
    handleRepositorySubmit,
    handleRepositoryTargetChange,
    handleRepositoryContextPreview,
    handleRepositoryTestRun,
    handleRepositoryGeneration,
    handleRepositoryInvestigation,
    handleRepositoryFixProposal,
    handleRepositoryFixVerification,
    handleBackToInvestigation,
    closeRepositoryContextPreview: () => {
      previewRequestEpoch.current += 1;
      activePreviewRequest.current = false;
      setIsRepositoryContextPreviewLoading(false);
      setRepositoryContextPreview(null);
      setRepositoryContextPreviewError(null);
    },
    resetWorkflow,
  };
}
