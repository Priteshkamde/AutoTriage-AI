# AutoTriage-AI
AI-powered bug triage and smart assignment engine

Currently in Build stage

Plan 1 : Code Ownership Analysis
Tracks who's been working on what files/modules
Identifies domain experts by activity patterns
Considers file complexity and change frequency

Plan 2 : Smart Assignment Logic
Primary owner (most commits) gets priority 1
Falls back to secondary owners or domain experts
Considers current workload and availability
Escalates to team leads when unclear

TLDR :
Bug Report → Extract Context → Find File Owners → (experimental Score Expertise) → Check Availability → Assign + Notify

┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   GitHub Repo   │────│  Change Detector │────│  AI Orchestrator│
│   (Webhooks)    │    │   (Event Bus)    │    │   (LangChain)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                 │                        │
                       ┌─────────▼─────────┐             │
                       │  Code Analyzer    │             │
                       │  (AST Parser)     │             │
                       └─────────┬─────────┘             │
                                 │                        │
                       ┌─────────▼─────────┐    ┌────────▼────────┐
                       │ Documentation     │    │  AI Doc Writer  │
                       │ Knowledge Base    │────│  (Claude/GPT)   │
                       │ (Vector Store)    │    └─────────────────┘
                       └───────────────────┘             │
                                                ┌────────▼────────┐
                                                │  Doc Repository │
                                                │  (GitHub)│
                                                └─────────────────┘

                                              
