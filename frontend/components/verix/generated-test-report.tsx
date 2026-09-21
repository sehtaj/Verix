import type { GeneratedTestReport } from "@/types/api";

const labels = {
  normal: "Normal",
  boundary: "Boundary",
  invalid_input: "Invalid input",
  error_handling: "Error handling",
  black_box: "Black box",
  gray_box: "Gray box",
};

export function GeneratedTestReportPanel({ report }: { report: GeneratedTestReport }) {
  return (
    <section className="mt-5 border border-dashed border-outline-variant bg-surface-low p-4">
      <header className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="font-heading text-sm font-bold uppercase">Expected Behavior Evidence</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            Gemini cited these bounded excerpts when deciding what behavior to test. Execution results remain authoritative.
          </p>
        </div>
        <span className="border border-dashed border-outline-variant px-2 py-1 font-heading text-[10px] text-muted-foreground">
          {report.model}
        </span>
      </header>

      <div className="mt-4 space-y-2">
        {report.cases.map((testCase) => (
          <article key={testCase.test_name} className="border border-dashed border-outline-variant bg-surface p-3">
            <div className="flex flex-wrap items-center gap-2">
              <code className="path-text text-xs text-primary">{testCase.test_name}</code>
              <span className="border border-outline-variant px-2 py-0.5 text-[10px] uppercase">
                {labels[testCase.category]}
              </span>
              <span className="border border-outline-variant px-2 py-0.5 text-[10px] uppercase">
                {labels[testCase.strategy]}
              </span>
            </div>
            <p className="mt-2 text-xs text-muted-foreground">{testCase.expected_behavior}</p>
          </article>
        ))}
      </div>

      <h3 className="mt-4 font-heading text-xs font-bold uppercase">Behavior sources</h3>
      <ul className="mt-2 space-y-3">
        {report.sources.map((source, index) => (
          <li key={`${source.kind}:${source.path}:${index}`} className="border border-dashed border-outline-variant bg-surface p-3 text-xs">
            <div className="flex flex-wrap items-center gap-2">
              <span className="path-text text-primary">{source.path}</span>
              <span className="uppercase text-muted-foreground">{source.kind.replaceAll("_", " ")}</span>
            </div>
            <q className="mt-2 block break-words text-muted-foreground">{source.excerpt}</q>
          </li>
        ))}
      </ul>

      <section className="mt-4 border border-dashed border-outline-variant p-3">
        <h3 className="font-heading text-xs font-bold uppercase">AI assumptions</h3>
        {report.assumptions.length > 0 ? (
          <ul className="mt-2 list-disc space-y-1 pl-4 text-xs text-muted-foreground">
            {report.assumptions.map((item) => <li key={item}>{item}</li>)}
          </ul>
        ) : (
          <p className="mt-2 text-xs text-muted-foreground">No additional assumptions reported.</p>
        )}
      </section>
    </section>
  );
}
