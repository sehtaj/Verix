export default function Home() {
  return (
    <main>
      <section className="generator">
        <h1>Verix</h1>
        <p>Paste a Python function to generate unit tests.</p>
        <label htmlFor="code">Python code</label>
        <textarea
          id="code"
          name="code"
          placeholder="def add(a, b):\n    return a + b"
          rows={12}
        />
        <button type="button">Generate tests</button>
      </section>
    </main>
  );
}
