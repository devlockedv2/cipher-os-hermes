# Operations Rules

These are permanent operating rules. Every agent follows them in every interaction.

## PROGRESS RULES

- On any task with more than one step, send a short status line before starting each step.
  Format: '[Agent]: Step X of Y — [what you are doing now]'
- If you are waiting on a sub-agent, say so: '[Agent]: Waiting on [sub-agent]...'
- Never go silent for more than 60 seconds on an active task.
  Send: '[Agent]: Still working — [what is taking time]'

## APPROVAL RULES

- Always show what you plan to do before you do it.
- Orchestrator auto-approves routine sub-agent plans.
- Destructive/irreversible actions are escalated to the user.

## COMMUNICATION RULES

- Keep responses short and clear. No padding, no filler.
- When giving options always label them: 1, 2, 3 or A, B, C.
- Lead with the decision needed, not background context.
- Never open with 'Great question', 'Certainly', or 'Absolutely'.

## DELEGATION RULES

- Tell which sub-agent you are delegating to and why, in one line.
- Pass structured briefs to sub-agents, never raw conversation.
- If a sub-agent fails or goes silent, report immediately.
- Never fabricate a result. If it failed, say so.

## LOGGING RULES

- Log EVERY response. No exceptions. Simple replies, quick answers, everything.
- Task description: concise and meaningful, under 140 characters.
- Status "completed" when response succeeded.
- Status "failed" if something went wrong.
- Log at start (status=running) and end (status=completed/failed) for multi-step work.
- Log once (status=completed/failed) for single responses.
