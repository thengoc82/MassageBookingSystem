# Chatbot Implementation Contract

Status: Approved
Version: 1.0
Purpose: Define the mandatory implementation rules and roadmap for the chatbot service.

## Authority

This document is the source of truth for chatbot implementation.

Any implementation decision must follow this contract.

If a proposed change conflicts with this document, stop and request approval before proceeding.

---

# Finalized Chatbot Architecture

We have finalized the chatbot architecture.

Implement the system incrementally, following the architecture exactly.

## Core Requirements

- Do NOT redesign the architecture.
- Do NOT change any existing Flask booking logic.
- Do NOT add reservation holds.
- Existing Flask APIs remain the single source of truth.
- The chatbot communicates with Flask only through HTTP.
- Follow the implementation roadmap phase by phase.
- Finish one phase completely before starting the next.
- Every phase must compile and pass tests before continuing.

---

# Architecture Constraints

## Service Boundary

- Separate chatbot service.
- No direct database access.
- No direct Flask internal imports.
- Communication only through HTTP APIs.

## Responsibilities

Chatbot owns:

- conversation management
- intent understanding
- tool orchestration
- response generation
- session state

Flask owns:

- availability calculation
- booking validation
- therapist assignment
- booking persistence
- business rules

The chatbot must never:

- duplicate Flask business logic
- calculate availability locally
- calculate therapist assignment
- bypass Flask APIs

---

# Implementation Roadmap

## Phase 0

Goal:
Scaffold chatbot project.

Create:


chatbot/
app/
conversation/
tools/
schemas/
gateway/
knowledge/
session/
prompts/
models/
tests/


Implement:

- configuration
- interfaces
- tool registry
- JSON schemas for every tool

Restrictions:

- No LLM integration
- No booking logic

Verification:

- Stop
- Run tests
- Verify structure

---

## Phase 1

Goal:
Read-only chatbot foundation.

Implement tools:

- searchShops
- searchCourses
- searchAvailableSlots
- getTherapists
- lookupBooking
- checkEligibility
- faqSearch

Tool requirements:

- HTTP wrapper only
- typed request
- typed response
- retries
- timeout
- error mapping

Implement:

- Redis session storage
- conversation state
- web chat endpoint
- deterministic booking flow

Restrictions:

- No LLM
- No writes

Verification:

- Stop
- Run tests

---

## Phase 2

Goal:
LLM integration.

Implement:

- intent extraction
- planner
- conversation state updates
- tool calling
- tool validation
- response generation

Restriction:

No write operations before Confirmation Gate exists.

Verification:

- Stop
- Run tests

---

## Phase 3

Goal:
Write operations.

Implement:

- createBooking
- modifyBooking
- cancelBooking

Requirements:

Every write tool must:

- require explicit confirmation
- validate schema
- call Flask
- return typed responses

Handle:

- slot unavailable
- validation errors
- insufficient therapists
- backend failures

Verification:

- Stop
- Run tests

---

## Phase 4

Goal:
Knowledge system.

Implement:

- Markdown loader
- chunking
- embeddings
- vector search
- FAQ tool
- citations

Verification:

- Stop
- Run tests

---

## Phase 5

Goal:
Production polish.

Implement:

- recovery
- start over
- go back
- ambiguous input handling
- logging
- tracing
- rate limiting
- metrics

---

# Coding Standards

Required:

- Never duplicate Flask business rules.
- Never calculate availability locally.
- Never calculate therapist assignment.
- Never bypass Flask APIs.
- Never expose raw HTTP responses.
- Never expose raw exceptions.
- Every public function requires type hints.
- Every tool requires unit tests.
- Keep modules under roughly 300 lines when practical.
- Prefer composition over large classes.
- Keep responsibilities isolated.

---

# Phase Completion Rules

After completing every phase:

1. Run tests.
2. Fix all issues.
3. Explain implementation details.
4. Wait for approval before continuing.

Never:

- skip phases
- generate placeholder code
- change architecture without approval

All code must be production quality.