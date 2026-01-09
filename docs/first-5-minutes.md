# First 5 minutes

0. If anything fails to run, start with `n3 doctor` for setup checks.
1. Scaffold Agent Lab and open Studio
   - `n3 new agent-lab demo`
   - `cd demo`
   - `n3 app.ai studio`
2. Run an agent
   - Open the **Agents** tab.
   - Pick a mode (single or parallel) and run the agent.
3. See the Timeline
   - Open **Timeline** to read trace-backed stages (Memory → Tools → Output → Merge).
4. Inspect memory and handoffs
   - Open **Memory Packs** to see the active pack.
   - Open **Handoff** to preview any packet contents and selection reasons.
5. Explore
   - Open **State** to see stored values.
   - Open **Traces** after a run to inspect tool calls and AI inputs/outputs.
