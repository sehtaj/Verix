"use client";

import { FormEvent, useState } from "react";

import {
  fetchRepositoryContext,
  generateRepositoryTests,
  investigateRepository,
  runRepositoryTests,
} from "../lib/api";
import type {
  RepositoryGenerationRun,
  RepositoryInvestigationRun,
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
  const [repository, setRepository] = useState<RepositoryMetadata | null>(null);
  const [repositoryTree, setRepositoryTree] = useState<RepositoryTree | null>(null);
  const [repositoryTestPlan, setRepositoryTestPlan] = useState<RepositoryTestPlan | null>(null);
  const [isRepositoryLoading, setIsRepositoryLoading] = useState(false);
  const [repositoryError, setRepositoryError] = useState<string | null>(null);
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

  async function handleRepositorySubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!isPublicGitHubRepositoryUrl(repositoryUrl)) {
      setRepositoryError(
        "Enter a public GitHub repository URL, such as https://github.com/owner/repository.",
      );
      setRepository(null);
      setRepositoryTree(null);
      setRepositoryTestPlan(null);
      setRepositoryTestRun(null);
      setRepositoryTestError(null);
      setRepositoryGenerationRun(null);
      setRepositoryGenerationError(null);
      setRepositoryInvestigationRun(null);
      setRepositoryInvestigationError(null);
      return;
    }

    setIsRepositoryLoading(true);
    setRepositoryError(null);
    setRepository(null);
    setRepositoryTree(null);
    setRepositoryTestPlan(null);
    setRepositoryTestRun(null);
    setRepositoryTestError(null);
    setRepositoryGenerationRun(null);
    setRepositoryGenerationError(null);
    setRepositoryInvestigationRun(null);
    setRepositoryInvestigationError(null);

    try {
      const context = await fetchRepositoryContext(repositoryUrl);

      setRepository(context.metadata);
      setRepositoryTree(context.tree);
      setRepositoryTestPlan(context.test_plan);
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

  async function handleRepositoryTestRun() {
    if (repository === null) {
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

    try {
      const result = await runRepositoryTests(repository.url);

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
    if (repository === null) {
      setRepositoryGenerationError(
        "Fetch a public Python repository before generating its tests.",
      );
      return;
    }

    setIsRepositoryGenerationRunning(true);
    setRepositoryGenerationError(null);
    setRepositoryGenerationRun(null);
    setRepositoryTestError(null);
    setRepositoryTestRun(null);
    setRepositoryInvestigationError(null);
    setRepositoryInvestigationRun(null);

    try {
      const result = await generateRepositoryTests(repository.url);

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
    if (repository === null) {
      setRepositoryInvestigationError(
        "Fetch a public Python repository before investigating it.",
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

    try {
      const result = await investigateRepository(repository.url);

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

  return {
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
  };
}
