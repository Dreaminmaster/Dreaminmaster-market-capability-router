# Product Decisions

## D001: Local-first core

The core engine has no network or model dependency. Reason: the product mechanism must remain testable and installable for local agents.

## D002: Risk is not a weighted preference

Critical risk blocks a candidate even when relevance is high. Reason: a single combined score could allow dangerous services to rank well.

## D003: Interpret dialect, do not generate evasion

The system may understand hidden marketplace language for safety and retrieval, but must not help sellers bypass moderation.

## D004: Minimum necessary outsourcing

Diagnosis and review are preferred before full service. Reason: they are cheaper, more verifiable, and preserve user control.

## D005: Official authority is explicit

Where official institutions make the final decision, market services can assist but cannot replace the official route.

## D006: Uncertainty remains visible

Unknown dialect and incomplete listings return hypotheses and evidence requirements, not confident labels.
