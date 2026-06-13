# Friction diagnosis prompt

Given a user's real-world problem, return structured friction hypotheses.

For each hypothesis include:

- friction_type
- score from 0 to 1
- direct evidence from the user's description
- what the user lacks
- what would remove the friction
- uncertainty

Allowed friction types: knowledge, diagnosis, skill, channel, execution, verification.
