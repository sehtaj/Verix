"use client";

import { type FormEvent, useEffect, useRef, useState } from "react";

import {
  fetchRepositoryContext,
  generateRepositoryTests,
  investigateRepository,
  previewRepositoryGenerationContext,
  proposeRepositoryFix,
  runRepositoryTests,
  verifyRepositoryFix,
  ApiError,
  type ApiField,
} from "@/lib/api";
import {
  getActionRecoveryScreen,
  getExecutionStatus,
  getReadyScreen,
  getVerificationRecoveryScreen,
} from "@/lib/repository-results";
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

type RepositoryFormField = Exclude<ApiField, "target_path">;

function formFieldForError(error: unknown): RepositoryFormField | null {
  if (!(error instanceof ApiError) || error.field === "target_path") return null;
  return error.field;
}

export function useRepositoryWorkflow() {
  const requestEpoch = useRef(0);
  const previewRequestEpoch = useRef(0);
  const activeRequest = useRef(false);
  const activePreviewRequest = useRef(false);
  const activeRequestOrigin = useRef<WorkflowScreen | null>(null);
  const previewReturnFocus = useRef<HTMLElement | null>(null);
  const [screen, setScreen] = useState<WorkflowScreen>("new_verification");
  const [repositoryUrl, setRepositoryUrl] = useState("");
  const [repositoryReference, setRepositoryReference] = useState("");
  const [repositorySubdirectory, setRepositorySubdirectory] = useState("");
  const [repositoryContext, setRepositoryContext] = useState<RepositoryContext | null>(null);
  const [selectedTargetPath, setSelectedTargetPath] = useState("");

  const [repositoryError, setRepositoryError] = useState<string | null>(null);
  const [repositoryErrorField, setRepositoryErrorField] =
    useState<RepositoryFormField | null>(null);
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

  useEffect(() => {
    const hasUnreviewedProposal = repositoryFixProposalRun !== null && repositoryFixVerificationRun === null;
    const hasDraftTargeting =
      screen === "new_verification" &&
      Boolean(
        repositoryUrl.trim() ||
          repositoryReference.trim() ||
          repositorySubdirectory.trim(),
      );
    if (!isRepositoryBusy && !hasUnreviewedProposal && !hasDraftTargeting) return;

    function warnBeforeUnload(event: BeforeUnloadEvent) {
      event.preventDefault();
      event.returnValue = "";
    }

    window.addEventListener("beforeunload", warnBeforeUnload);
    return () => window.removeEventListener("beforeunload", warnBeforeUnload);
  }, [
    isRepositoryBusy,
    repositoryFixProposalRun,
    repositoryFixVerificationRun,
    repositoryReference,
    repositorySubdirectory,
    repositoryUrl,
    screen,
  ]);

  function requestBecameStale(epoch: number): boolean {
    return requestEpoch.current !== epoch;
  }

  function clearActionErrors() {
    setRepositoryError(null);
    setRepositoryErrorField(null);
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

  function hasPendingProposal(): boolean {
    return repositoryFixProposalRun !== null && repositoryFixVerificationRun === null;
  }

  function confirmProposalReplacement(message: string): boolean {
    return !hasPendingProposal() || window.confirm(message);
  }

  function resetWorkflow(force = false): boolean {
    const hasUnreviewedProposal = hasPendingProposal();
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
      setRepositoryErrorField("url");
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
      setScreen(getReadyScreen(context));
    } catch (error) {
      if (requestBecameStale(epoch)) return;
      setRepositoryError(
        error instanceof Error
          ? error.message
          : "Unable to fetch repository details. Please try again.",
      );
      setRepositoryErrorField(formFieldForError(error));
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
    if (!confirmProposalReplacement("Select a different target and replace the unreviewed source proposal?")) return;

    activeRequest.current = true;
    const previousScreen = screen;
    activeRequestOrigin.current = previousScreen;
    setRepositoryError(null);
    setRepositoryErrorField(null);
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
      setScreen(getReadyScreen(context));
    } catch (error) {
      if (requestBecameStale(epoch)) return;
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

    previewReturnFocus.current = document.activeElement instanceof HTMLElement
      ? document.activeElement
      : null;
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
    if (!selectedTargetPath) {
      setRepositoryTestError("Select a verified Python source target before running this verification.");
      return;
    }
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
      setScreen(getActionRecoveryScreen(previousScreen, repositoryContext, ["showing_test_result"]));
    } finally {
      if (!requestBecameStale(epoch)) {
        activeRequest.current = false;
        activeRequestOrigin.current = null;
      }
    }
  }

  async function handleRepositoryGeneration() {
    if (repositoryContext === null || activeRequest.current) return;
    if (!selectedTargetPath) {
      setRepositoryGenerationError("Select a verified Python source target before generating focused tests.");
      return;
    }
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
      setScreen(getActionRecoveryScreen(previousScreen, repositoryContext, [
        "showing_test_result",
        "showing_generation_result",
      ]));
    } finally {
      if (!requestBecameStale(epoch)) {
        activeRequest.current = false;
        activeRequestOrigin.current = null;
      }
    }
  }

  async function handleRepositoryInvestigation() {
    if (repositoryContext === null || activeRequest.current) return;
    if (!selectedTargetPath) {
      setRepositoryInvestigationError("Select a verified Python source target before investigating evidence.");
      return;
    }
    if (!confirmProposalReplacement("Run a new investigation and replace the unreviewed source proposal?")) return;
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
      setRepositoryFixProposalRun(null);
      setRepositoryFixVerificationRun(null);
      setRepositoryInvestigationRun(result);
      setScreen("showing_investigation");
    } catch (error) {
      if (requestBecameStale(epoch)) return;
      setRepositoryInvestigationError(
        error instanceof Error ? error.message : "Unable to investigate the repository.",
      );
      setScreen(getActionRecoveryScreen(previousScreen, repositoryContext, [
        "showing_test_result",
        "showing_generation_result",
        "showing_investigation",
      ]));
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
    const previousScreen = screen;
    activeRequestOrigin.current = previousScreen;
    clearActionErrors();
    setScreen("verifying_fix");
    const epoch = requestEpoch.current;

    try {
      const result = await verifyRepositoryFix(
        repositoryContext.metadata.url,
        repositoryFixProposalRun,
      );
      if (requestBecameStale(epoch)) return;
      setRepositoryFixVerificationRun(result);
      setScreen("showing_verification_result");
    } catch (error) {
      if (requestBecameStale(epoch)) return;
      setRepositoryFixVerificationError(
        error instanceof Error ? error.message : "Unable to verify the approved patch.",
      );
      setScreen(getVerificationRecoveryScreen(previousScreen));
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

  function handleEditRepositoryTargeting() {
    requestEpoch.current += 1;
    previewRequestEpoch.current += 1;
    activeRequest.current = false;
    activePreviewRequest.current = false;
    activeRequestOrigin.current = null;
    setScreen("new_verification");
    setRepositoryContext(null);
    setSelectedTargetPath("");
    setIsRepositoryContextPreviewLoading(false);
    clearEvidence();
  }

  return {
    screen,
    activeRequestOrigin: activeRequestOrigin.current,
    repositoryUrl,
    repositoryReference,
    repositorySubdirectory,
    repositoryContext,
    selectedTargetPath,
    repositoryError,
    repositoryErrorField,
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
    handleEditRepositoryTargeting,
    setRepositoryUrl: (value: string) => {
      setRepositoryUrl(value);
      if (repositoryErrorField === "url") {
        setRepositoryError(null);
        setRepositoryErrorField(null);
      }
    },
    setRepositoryReference: (value: string) => {
      setRepositoryReference(value);
      if (repositoryErrorField === "reference") {
        setRepositoryError(null);
        setRepositoryErrorField(null);
      }
    },
    setRepositorySubdirectory: (value: string) => {
      setRepositorySubdirectory(value);
      if (repositoryErrorField === "subdirectory") {
        setRepositoryError(null);
        setRepositoryErrorField(null);
      }
    },
    closeRepositoryContextPreview: () => {
      previewRequestEpoch.current += 1;
      activePreviewRequest.current = false;
      setIsRepositoryContextPreviewLoading(false);
      setRepositoryContextPreview(null);
      setRepositoryContextPreviewError(null);
      const returnTarget = previewReturnFocus.current;
      previewReturnFocus.current = null;
      window.requestAnimationFrame(() => returnTarget?.focus());
    },
    resetWorkflow,
  };
}
