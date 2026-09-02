"use client";

import { useEffect, useRef } from "react";

import { AppShell } from "@/components/verix/app-shell";
import { Button } from "@/components/ui/button";
import { ContextPreviewDialog } from "@/components/verix/context-preview-dialog";
import { FixReviewPanel } from "@/components/verix/fix-review-panel";
import { GenerationResultPanel } from "@/components/verix/generation-result-panel";
import { InvestigationPanel } from "@/components/verix/investigation-panel";
import { NewVerificationForm } from "@/components/verix/new-verification-form";
import { ReadyWorkspace } from "@/components/verix/ready-workspace";
import { TestResultPanel } from "@/components/verix/test-result-panel";
import { VerificationResultPanel } from "@/components/verix/verification-result-panel";
import {
  WorkflowActivityBanner,
  WorkflowLoadingPanel,
} from "@/components/verix/workflow-loading-panel";
import { useRepositoryWorkflow } from "@/hooks/use-repository-workflow";
import { getExecutionStatus } from "@/lib/repository-results";
import type { WorkflowScreen } from "@/types/workflow";

const loadingScreens = new Set<WorkflowScreen>([
  "loading_context",
  "running_existing_tests",
  "generating_tests",
  "investigating",
  "proposing_fix",
  "verifying_fix",
]);

const screenAnnouncements: Record<WorkflowScreen, string> = {
  new_verification: "New verification form ready.",
  loading_context: "Repository context request started.",
  ready_existing_tests: "Repository context loaded. Existing tests are ready to run.",
  ready_generate_tests: "Repository context loaded. Focused tests are ready to generate.",
  running_existing_tests: "Existing test run started.",
  showing_test_result: "Existing test evidence is ready for review.",
  generating_tests: "Focused test generation started.",
  showing_generation_result: "Generated tests and execution evidence are ready for review.",
  investigating: "Evidence investigation started.",
  showing_investigation: "Investigation evidence is ready for review.",
  proposing_fix: "Source proposal request started.",
  reviewing_fix: "Source proposal is ready for explicit review.",
  verifying_fix: "Disposable patch verification started.",
  showing_verification_result: "Disposable verification evidence is ready for review.",
};

const focusOnArrivalScreens = new Set<WorkflowScreen>([
  "loading_context",
  "ready_existing_tests",
  "ready_generate_tests",
  "running_existing_tests",
  "showing_test_result",
  "generating_tests",
  "showing_generation_result",
  "investigating",
  "showing_investigation",
  "proposing_fix",
  "reviewing_fix",
  "verifying_fix",
  "showing_verification_result",
]);

export default function Home() {
  const workflow = useRepositoryWorkflow();
  const previousScreen = useRef<WorkflowScreen>(workflow.screen);

  useEffect(() => {
    if (
      previousScreen.current !== workflow.screen &&
      focusOnArrivalScreens.has(workflow.screen)
    ) {
      window.requestAnimationFrame(() => {
        document.getElementById("main-content")?.focus({ preventScroll: false });
      });
    }
    previousScreen.current = workflow.screen;
  }, [workflow.screen]);

  function renderPreservedEvidence() {
    if (workflow.activeRequestOrigin === "showing_test_result" && workflow.repositoryTestRun) {
      return (
        <TestResultPanel
          result={workflow.repositoryTestRun}
          error={workflow.repositoryTestError ?? workflow.repositoryGenerationError ?? workflow.repositoryInvestigationError}
          isActionBusy
          canUseTarget={Boolean(workflow.selectedTargetPath)}
          onRetry={workflow.handleRepositoryTestRun}
          onGenerate={workflow.handleRepositoryGeneration}
          onInvestigate={workflow.handleRepositoryInvestigation}
          onEditRepository={workflow.handleEditRepositoryTargeting}
        />
      );
    }
    if (workflow.activeRequestOrigin === "showing_generation_result" && workflow.repositoryGenerationRun) {
      return (
        <GenerationResultPanel
          result={workflow.repositoryGenerationRun}
          error={workflow.repositoryGenerationError ?? workflow.repositoryInvestigationError}
          isActionBusy
          onRegenerate={workflow.handleRepositoryGeneration}
          onInvestigate={workflow.handleRepositoryInvestigation}
        />
      );
    }
    if (workflow.activeRequestOrigin === "showing_investigation" && workflow.repositoryInvestigationRun) {
      return (
        <InvestigationPanel
          result={workflow.repositoryInvestigationRun}
          error={workflow.repositoryInvestigationError ?? workflow.repositoryFixProposalError}
          isActionBusy
          onRetry={workflow.handleRepositoryInvestigation}
          onProposeFix={workflow.handleRepositoryFixProposal}
          onEditRepository={workflow.handleEditRepositoryTargeting}
        />
      );
    }
    if (workflow.activeRequestOrigin === "reviewing_fix" && workflow.repositoryFixProposalRun) {
      return (
        <FixReviewPanel
          result={workflow.repositoryFixProposalRun}
          error={workflow.repositoryFixVerificationError}
          isActionBusy
          onBack={workflow.handleBackToInvestigation}
          onApproveAndVerify={workflow.handleRepositoryFixVerification}
        />
      );
    }
    if (workflow.activeRequestOrigin === "showing_verification_result" && workflow.repositoryFixVerificationRun) {
      return (
        <VerificationResultPanel
          result={workflow.repositoryFixVerificationRun}
          error={workflow.repositoryFixVerificationError}
          isActionBusy
          onRetry={workflow.handleRepositoryFixVerification}
        />
      );
    }
    if (workflow.repositoryFixVerificationRun) {
      return (
        <VerificationResultPanel
          result={workflow.repositoryFixVerificationRun}
          error={workflow.repositoryFixVerificationError}
          isActionBusy
          onRetry={workflow.handleRepositoryFixVerification}
        />
      );
    }
    if (workflow.repositoryFixProposalRun) {
      return (
        <FixReviewPanel
          result={workflow.repositoryFixProposalRun}
          error={workflow.repositoryFixVerificationError}
          isActionBusy
          onBack={workflow.handleBackToInvestigation}
          onApproveAndVerify={workflow.handleRepositoryFixVerification}
        />
      );
    }
    if (workflow.repositoryInvestigationRun) {
      return (
        <InvestigationPanel
          result={workflow.repositoryInvestigationRun}
          error={workflow.repositoryInvestigationError ?? workflow.repositoryFixProposalError}
          isActionBusy
          onRetry={workflow.handleRepositoryInvestigation}
          onProposeFix={workflow.handleRepositoryFixProposal}
          onEditRepository={workflow.handleEditRepositoryTargeting}
        />
      );
    }
    if (workflow.repositoryGenerationRun) {
      return (
        <GenerationResultPanel
          result={workflow.repositoryGenerationRun}
          error={workflow.repositoryGenerationError ?? workflow.repositoryInvestigationError}
          isActionBusy
          onRegenerate={workflow.handleRepositoryGeneration}
          onInvestigate={workflow.handleRepositoryInvestigation}
        />
      );
    }
    if (workflow.repositoryTestRun) {
      return (
        <TestResultPanel
          result={workflow.repositoryTestRun}
          error={workflow.repositoryTestError ?? workflow.repositoryGenerationError ?? workflow.repositoryInvestigationError}
          isActionBusy
          canUseTarget={Boolean(workflow.selectedTargetPath)}
          onRetry={workflow.handleRepositoryTestRun}
          onGenerate={workflow.handleRepositoryGeneration}
          onInvestigate={workflow.handleRepositoryInvestigation}
          onEditRepository={workflow.handleEditRepositoryTargeting}
        />
      );
    }
    return null;
  }

  let content;
  if (workflow.screen === "new_verification") {
    content = (
      <NewVerificationForm
        repositoryUrl={workflow.repositoryUrl}
        repositoryReference={workflow.repositoryReference}
        repositorySubdirectory={workflow.repositorySubdirectory}
        isLoading={workflow.isRepositoryLoading}
        error={workflow.repositoryError}
        errorField={workflow.repositoryErrorField}
        onRepositoryUrlChange={workflow.setRepositoryUrl}
        onRepositoryReferenceChange={workflow.setRepositoryReference}
        onRepositorySubdirectoryChange={workflow.setRepositorySubdirectory}
        onSubmit={workflow.handleRepositorySubmit}
      />
    );
  } else if (loadingScreens.has(workflow.screen)) {
    const preservedEvidence = renderPreservedEvidence();
    content = preservedEvidence ? (
      <>
        <WorkflowActivityBanner screen={workflow.screen} />
        {preservedEvidence}
      </>
    ) : (
      <WorkflowLoadingPanel screen={workflow.screen} />
    );
  } else if (
    workflow.repositoryContext &&
    (workflow.screen === "ready_existing_tests" || workflow.screen === "ready_generate_tests")
  ) {
    content = (
      <ReadyWorkspace
        context={workflow.repositoryContext}
        selectedTargetPath={workflow.selectedTargetPath}
        mode={workflow.screen === "ready_existing_tests" ? "existing" : "generate"}
        error={workflow.repositoryTestError ?? workflow.repositoryGenerationError ?? workflow.repositoryError}
        onRunExisting={workflow.handleRepositoryTestRun}
        onGenerate={workflow.handleRepositoryGeneration}
        onPreview={workflow.handleRepositoryContextPreview}
        onSelectTarget={workflow.handleRepositoryTargetChange}
        priorTestRun={workflow.repositoryTestRun}
        onEditRepository={workflow.handleEditRepositoryTargeting}
      />
    );
  } else if (workflow.screen === "showing_test_result" && workflow.repositoryTestRun) {
    content = (
      <TestResultPanel
        result={workflow.repositoryTestRun}
        error={workflow.repositoryTestError ?? workflow.repositoryGenerationError ?? workflow.repositoryInvestigationError}
        canUseTarget={Boolean(workflow.selectedTargetPath)}
        onRetry={workflow.handleRepositoryTestRun}
        onGenerate={workflow.handleRepositoryGeneration}
        onInvestigate={workflow.handleRepositoryInvestigation}
        onEditRepository={workflow.handleEditRepositoryTargeting}
      />
    );
  } else if (
    workflow.screen === "showing_generation_result" &&
    workflow.repositoryGenerationRun
  ) {
    content = (
      <GenerationResultPanel
        result={workflow.repositoryGenerationRun}
        error={workflow.repositoryGenerationError ?? workflow.repositoryInvestigationError}
        onRegenerate={workflow.handleRepositoryGeneration}
        onInvestigate={workflow.handleRepositoryInvestigation}
      />
    );
  } else if (
    workflow.screen === "showing_investigation" &&
    workflow.repositoryInvestigationRun
  ) {
    content = (
      <InvestigationPanel
        result={workflow.repositoryInvestigationRun}
        error={workflow.repositoryInvestigationError ?? workflow.repositoryFixProposalError}
        onRetry={workflow.handleRepositoryInvestigation}
        onProposeFix={workflow.handleRepositoryFixProposal}
        onEditRepository={workflow.handleEditRepositoryTargeting}
      />
    );
  } else if (workflow.screen === "reviewing_fix" && workflow.repositoryFixProposalRun) {
    content = (
      <FixReviewPanel
        result={workflow.repositoryFixProposalRun}
        error={workflow.repositoryFixVerificationError}
        onBack={workflow.handleBackToInvestigation}
        onApproveAndVerify={workflow.handleRepositoryFixVerification}
      />
    );
  } else if (
    workflow.screen === "showing_verification_result" &&
    workflow.repositoryFixVerificationRun
  ) {
    content = (
      <VerificationResultPanel
        result={workflow.repositoryFixVerificationRun}
        error={workflow.repositoryFixVerificationError}
        onRetry={workflow.handleRepositoryFixVerification}
      />
    );
  } else {
    content = (
      <section className="mx-auto max-w-3xl border border-destructive bg-destructive/5 p-6" role="alert">
        <h1 className="font-heading text-2xl font-bold text-destructive">Workflow State Could Not Be Displayed</h1>
        <p className="mt-3 text-muted-foreground">
          The browser is missing evidence required for this screen. Start a new verification to recover safely.
        </p>
        <Button className="mt-5" onClick={() => workflow.resetWorkflow(true)}>
          Return to New Verification
        </Button>
      </section>
    );
  }

  const latestGeneratedEvidence =
    workflow.repositoryFixProposalRun ??
    workflow.repositoryInvestigationRun ??
    workflow.repositoryGenerationRun;

  return (
    <AppShell
      screen={workflow.screen}
      stepEvidence={{
        existingStatus: latestGeneratedEvidence
          ? getExecutionStatus(latestGeneratedEvidence.existing_execution)
          : workflow.repositoryTestRun
            ? getExecutionStatus(workflow.repositoryTestRun.execution)
            : undefined,
        generatedStatus: latestGeneratedEvidence
          ? getExecutionStatus(latestGeneratedEvidence.generated_execution)
          : undefined,
        verificationStatus: workflow.repositoryFixVerificationRun
          ? getExecutionStatus(workflow.repositoryFixVerificationRun.execution)
          : undefined,
        verificationSafetyConfirmed: workflow.repositoryFixVerificationRun
          ? workflow.repositoryFixVerificationRun.applied_in_disposable_workspace &&
            !workflow.repositoryFixVerificationRun.github_changed
          : undefined,
      }}
      context={workflow.repositoryContext}
      selectedTargetPath={workflow.selectedTargetPath}
      isBusy={workflow.isRepositoryBusy}
      isPreviewLoading={workflow.isRepositoryContextPreviewLoading}
      previewError={workflow.repositoryContextPreviewError}
      onNewVerification={() => workflow.resetWorkflow()}
      onSelectTarget={workflow.handleRepositoryTargetChange}
      onPreviewContext={workflow.handleRepositoryContextPreview}
    >
      <p className="sr-only" role="status" aria-live="polite" aria-atomic="true">
        {screenAnnouncements[workflow.screen]}
      </p>
      {workflow.repositoryError &&
        workflow.screen !== "new_verification" &&
        workflow.screen !== "ready_existing_tests" &&
        workflow.screen !== "ready_generate_tests" && (
          <p className="mx-auto mb-5 max-w-5xl border border-destructive bg-destructive/10 p-3 text-sm text-destructive" role="alert">
            {workflow.repositoryError}
          </p>
        )}
      {content}
      <ContextPreviewDialog
        preview={workflow.repositoryContextPreview}
        isLoading={workflow.isRepositoryContextPreviewLoading}
        error={workflow.repositoryContextPreviewError}
        onClose={workflow.closeRepositoryContextPreview}
      />
    </AppShell>
  );
}
