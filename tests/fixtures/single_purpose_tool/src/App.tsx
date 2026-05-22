import React, { useState } from "react";

export default function App() {
  const [principal, setPrincipal] = useState("");
  const [rate, setRate] = useState("");
  const [term, setTerm] = useState("");
  const [result, setResult] = useState<number | null>(null);

  function calculate() {
    const p = parseFloat(principal);
    const r = parseFloat(rate) / 100 / 12;
    const n = parseFloat(term) * 12;
    const payment = (p * r * Math.pow(1 + r, n)) / (Math.pow(1 + r, n) - 1);
    setResult(payment);
  }

  return (
    <div>
      <h1>Mortgage Calculator</h1>
      <input placeholder="Principal" value={principal} onChange={e => setPrincipal(e.target.value)} />
      <input placeholder="Annual Rate %" value={rate} onChange={e => setRate(e.target.value)} />
      <input placeholder="Term (years)" value={term} onChange={e => setTerm(e.target.value)} />
      <button onClick={calculate}>Calculate</button>
      {result && <p>Monthly Payment: ${result.toFixed(2)}</p>}
    </div>
  );
}
