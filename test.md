# Scoring Systems Design Diagrams

## Table of Contents
1. [Relevancy Scorer Design](#relevancy-scorer-design)
2. [Confidence Scorer Design](#confidence-scorer-design)
3. [Integration Flow Diagrams](#integration-flow-diagrams)
4. [Scoring Algorithm Flowcharts](#scoring-algorithm-flowcharts)

## Relevancy Scorer Design

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              Relevancy Scorer                                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  Input: Search Results + Query                                                  │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐            │
│  │  Web Search     │    │  Vector Search  │    │   User Query    │            │
│  │   Results       │    │    Results      │    │                 │            │
│  │                 │    │                 │    │ "R740 won't     │            │
│  │ [{title: "...", │    │ [{title: "...", │    │  boot amber     │            │
│  │   content:"...",│    │   content:"...",│    │  LED"}          │            │
│  │   url: "..."}] │    │   snippet:"..."}]│    │                 │            │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘            │
│           │                       │                       │                    │
│           └───────────────────────┼───────────────────────┘                    │
│                                   │                                            │
│  ┌─────────────────────────────────▼─────────────────────────────────┐         │
│  │                     Scoring Engine                                 │         │
│  │                                                                    │         │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐   │         │
│  │  │ Query Term      │  │ Dell/PowerEdge  │  │ Technical       │   │         │
│  │  │ Overlap         │  │ Relevance       │  │ Relevance       │   │         │
│  │  │                 │  │                 │  │                 │   │         │
│  │  │ Weight: 30%     │  │ Weight: 25%     │  │ Weight: 20%     │   │         │
│  │  │                 │  │                 │  │                 │   │         │
│  │  │ • Jaccard       │  │ • PowerEdge     │  │ • Tech Keywords │   │         │
│  │  │   Similarity    │  │   Models        │  │ • Symptoms      │   │         │
│  │  │ • Term          │  │ • Dell Keywords │  │ • Error Codes   │   │         │
│  │  │   Intersection  │  │ • Official      │  │ • Procedures    │   │         │
│  │  │                 │  │   Sources       │  │                 │   │         │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘   │         │
│  │                                                                    │         │
│  │  ┌─────────────────┐  ┌─────────────────┐                        │         │
│  │  │ Source          │  │ Content         │                        │         │
│  │  │ Authority       │  │ Quality         │                        │         │
│  │  │                 │  │                 │                        │         │
│  │  │ Weight: 15%     │  │ Weight: 10%     │                        │         │
│  │  │                 │  │                 │                        │         │
│  │  │ • Official Dell │  │ • Length        │                        │         │
│  │  │ • Documentation │  │ • Structure     │                        │         │
│  │  │ • Community     │  │ • Completeness  │                        │         │
│  │  │ • Vector DB     │  │ • Technical     │                        │         │
│  │  │                 │  │   Detail        │                        │         │
│  │  └─────────────────┘  └─────────────────┘                        │         │
│  └─────────────────────────────────────────────────────────────────┘         │
│                                   │                                            │
│  ┌─────────────────────────────────▼─────────────────────────────────┐         │
│  │                    Score Calculation                               │         │
│  │                                                                    │         │
│  │    Final Score = Σ(Factor Score × Weight)                         │         │
│  │                                                                    │         │
│  │    Score = (Term_Overlap × 0.30) +                                │         │
│  │            (Dell_Relevance × 0.25) +                              │         │
│  │            (Tech_Relevance × 0.20) +                              │         │
│  │            (Source_Authority × 0.15) +                            │         │
│  │            (Content_Quality × 0.10)                               │         │
│  │                                                                    │         │
│  │    Range: 0.0 to 1.0                                              │         │
│  └─────────────────────────────────────────────────────────────────┘         │
│                                   │                                            │
│  Output: Ranked Results with Scores                                           │
│  ┌─────────────────────────────────▼─────────────────────────────────┐         │
│  │ [{title: "PowerEdge R740 Boot Issues",                            │         │
│  │   content: "...",                                                 │         │
│  │   url: "support.dell.com/...",                                    │         │
│  │   relevance_score: 0.85},                                         │         │
│  │  {title: "Server Boot Troubleshooting",                           │         │
│  │   content: "...",                                                 │         │
│  │   url: "community.dell.com/...",                                  │         │
│  │   relevance_score: 0.72}, ...]                                    │         │
│  └─────────────────────────────────────────────────────────────────┘         │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Factor Scoring Breakdown

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         Factor Scoring Mechanisms                               │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│ 1. Query Term Overlap (Weight: 0.30)                                           │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  Input Query: "R740 server won't boot amber LED"                               │
│  ┌─────────────────┐         ┌─────────────────┐                              │
│  │ Query Terms     │         │ Content Terms   │                              │
│  │                 │         │                 │                              │
│  │ • r740          │         │ • poweredge     │                              │
│  │ • server        │         │ • r740          │                              │
│  │ • won't         │         │ • server        │                              │
│  │ • boot          │         │ • boot          │                              │
│  │ • amber         │         │ • failure       │                              │
│  │ • led           │         │ • amber         │                              │
│  └─────────────────┘         │ • led           │                              │
│           │                  │ • diagnostic    │                              │
│           │                  └─────────────────┘                              │
│           │                           │                                        │
│           └─────────┬─────────────────┘                                        │
│                     │                                                          │
│  ┌─────────────────▼─────────────────┐                                         │
│  │     Jaccard Similarity            │                                         │
│  │                                   │                                         │
│  │ Intersection = {r740, server,     │                                         │
│  │                boot, amber, led}  │                                         │
│  │ Count = 5                         │                                         │
│  │                                   │                                         │
│  │ Union = {r740, server, won't,     │                                         │
│  │         boot, amber, led,         │                                         │
│  │         poweredge, failure,       │                                         │
│  │         diagnostic}               │                                         │
│  │ Count = 9                         │                                         │
│  │                                   │                                         │
│  │ Score = 5/6 = 0.83                │                                         │
│  └─────────────────────────────────────┘                                         │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│ 2. Dell/PowerEdge Relevance (Weight: 0.25)                                     │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐            │
│  │ PowerEdge Model │    │ Dell Keywords   │    │ Official Source │            │
│  │ Detection       │    │ Detection       │    │ Bonus           │            │
│  │                 │    │                 │    │                 │            │
│  │ Models:         │    │ Keywords:       │    │ Sources:        │            │
│  │ • R740 ✓ (+0.3) │    │ • dell ✓ (+0.1) │    │ • dell.com ✓    │            │
│  │ • R730          │    │ • poweredge ✓   │    │   (+0.3)        │            │
│  │ • R720          │    │   (+0.1)        │    │ • support.dell  │            │
│  │ • T340          │    │ • idrac ✓ (+0.1)│    │   .com ✓ (+0.3) │            │
│  │ • ...           │    │ • openmanage    │    │                 │            │
│  └─────────────────┘    │ • perc          │    └─────────────────┘            │
│                         │ • lifecycle     │                                   │
│                         └─────────────────┘                                   │
│                                   │                                            │
│  ┌─────────────────────────────────▼─────────────────────────────────┐         │
│  │ Score Calculation:                                                 │         │
│  │                                                                    │         │
│  │ PowerEdge Model Found: 0.3                                        │         │
│  │ Dell Keywords (3 × 0.1): 0.3 (capped at 0.4)                     │         │
│  │ Official Source Bonus: 0.3                                        │         │
│  │                                                                    │         │
│  │ Total: 0.3 + 0.3 + 0.3 = 0.9 (capped at 1.0)                     │         │
│  └─────────────────────────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│ 3. Technical Relevance (Weight: 0.20)                                          │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐            │
│  │ Technical       │    │ Symptom         │    │ Error Codes &   │            │
│  │ Keywords        │    │ Keywords        │    │ Procedures      │            │
│  │                 │    │                 │    │                 │            │
│  │ Found:          │    │ Found:          │    │ Patterns:       │            │
│  │ • bios          │    │ • error ✓       │    │ • Error codes   │            │
│  │ • uefi          │    │ • failure ✓     │    │   [A-Z]{1,3}    │            │
│  │ • firmware ✓    │    │ • boot ✓        │    │   \d{3,4} ✓     │            │
│  │ • diagnostic ✓  │    │ • led ✓         │    │ • Procedural    │            │
│  │ • memory        │    │ • amber ✓       │    │   words ✓       │            │
│  │ • cpu           │    │ • hang          │    │   (step, guide) │            │
│  └─────────────────┘    │ • crash         │    └─────────────────┘            │
│                         └─────────────────┘                                   │
│                                   │                                            │
│  ┌─────────────────────────────────▼─────────────────────────────────┐         │
│  │ Score Calculation:                                                 │         │
│  │                                                                    │         │
│  │ Technical Keywords (2 × 0.05): 0.10 (max 0.4)                     │         │
│  │ Symptom Keywords (5 × 0.1): 0.50 → 0.30 (capped)                  │         │
│  │ Error Code Pattern Found: 0.20                                     │         │
│  │ Procedural Content: 0.10                                           │         │
│  │                                                                    │         │
│  │ Total: 0.10 + 0.30 + 0.20 + 0.10 = 0.70                           │         │
│  └─────────────────────────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│ 4. Source Authority Hierarchy (Weight: 0.15)                                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│                           Authority Pyramid                                     │
│                                                                                 │
│                      ┌─────────────────────┐                                   │
│                      │ support.dell.com    │ Score: 1.0                        │
│                      │ (Official Support)  │                                   │
│                      └─────────────────────┘                                   │
│                               │                                                 │
│                    ┌─────────────────────┐                                     │
│                    │      dell.com       │ Score: 0.9                          │
│                    │  (Official Site)    │                                     │
│                    └─────────────────────┘                                     │
│                               │                                                 │
│              ┌─────────────────────┬─────────────────────┐                     │
│              │   Vector Search     │  Technical Docs     │ Score: 0.8/0.7      │
│              │  (Internal Docs)    │  (docs.*, manual.*) │                     │
│              └─────────────────────┴─────────────────────┘                     │
│                               │                                                 │
│                    ┌─────────────────────┐                                     │
│                    │ Community Forums    │ Score: 0.5                          │
│                    │ (reddit, stackoverflow) │                                 │
│                    └─────────────────────┘                                     │
│                               │                                                 │
│                    ┌─────────────────────┐                                     │
│                    │ Other Web Sources   │ Score: 0.3                          │
│                    │                     │                                     │
│                    └─────────────────────┘                                     │
│                                                                                 │
│  URL Analysis:                                                                  │
│  "https://support.dell.com/poweredge-r740-boot-issues" → Score: 1.0            │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│ 5. Content Quality Assessment (Weight: 0.10)                                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐            │
│  │ Length          │    │ Structure       │    │ Technical       │            │
│  │ Analysis        │    │ Indicators      │    │ Detail Level    │            │
│  │                 │    │                 │    │                 │            │
│  │ Word Count: 156 │    │ Found:          │    │ Indicators:     │            │
│  │ > 100 words ✓   │    │ • "1." ✓        │    │ • Colons: 8     │            │
│  │ Score: +0.4     │    │ • "Step" ✓      │    │   > 2 ✓ (+0.2)  │            │
│  │                 │    │ • "First" ✓     │    │ • Sentences: 12 │            │
│  │                 │    │ Score: +0.3     │    │   > 3 ✓ (+0.1)  │            │
│  │                 │    │                 │    │                 │            │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘            │
│                                   │                                            │
│  ┌─────────────────────────────────▼─────────────────────────────────┐         │
│  │ Total Quality Score:                                               │         │
│  │                                                                    │         │
│  │ Length Score: 0.4                                                  │         │
│  │ Structure Score: 0.3                                               │         │
│  │ Technical Detail Score: 0.3                                        │         │
│  │                                                                    │         │
│  │ Total: 0.4 + 0.3 + 0.3 = 1.0 (capped at 1.0)                     │         │
│  └─────────────────────────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Final Score Calculation Example

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         Final Relevancy Score Calculation                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  Example: "Dell PowerEdge R740 Boot Issues" result                             │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │ Factor Scores:                                          │ Weight │ Weighted │ │
│  ├─────────────────────────────────────────────────────────┼────────┼─────────┤ │
│  │ 1. Query Term Overlap: 0.83                            │  0.30  │  0.249  │ │
│  │    (5 matching terms out of 6 query terms)             │        │         │ │
│  ├─────────────────────────────────────────────────────────┼────────┼─────────┤ │
│  │ 2. Dell/PowerEdge Relevance: 0.90                      │  0.25  │  0.225  │ │
│  │    (Model: 0.3 + Keywords: 0.3 + Official: 0.3)       │        │         │ │
│  ├─────────────────────────────────────────────────────────┼────────┼─────────┤ │
│  │ 3. Technical Relevance: 0.70                           │  0.20  │  0.140  │ │
│  │    (Tech: 0.1 + Symptoms: 0.3 + Codes: 0.2 + Proc: 0.1)│       │         │ │
│  ├─────────────────────────────────────────────────────────┼────────┼─────────┤ │
│  │ 4. Source Authority: 1.00                              │  0.15  │  0.150  │ │
│  │    (support.dell.com source)                           │        │         │ │
│  ├─────────────────────────────────────────────────────────┼────────┼─────────┤ │
│  │ 5. Content Quality: 1.00                               │  0.10  │  0.100  │ │
│  │    (Length: 0.4 + Structure: 0.3 + Detail: 0.3)       │        │         │ │
│  ├─────────────────────────────────────────────────────────┼────────┼─────────┤ │
│  │                                            TOTAL SCORE │  1.00  │  0.864  │ │
│  └─────────────────────────────────────────────────────────┴────────┴─────────┘ │
│                                                                                 │
│  Final Relevancy Score: 0.864 (86.4% relevant)                                 │
│  Ranking: HIGH RELEVANCE                                                       │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Confidence Scorer Design

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                               Confidence Scorer                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  Input: Generated Plan + Context                                               │
│  ┌─────────────────┐         ┌─────────────────────────────────────────────────┐ │
│  │ Generated Plan  │         │              Context                            │ │
│  │                 │         │                                                 │ │
│  │ {               │         │ {                                               │ │
│  │   title: "...", │         │   search_results: [...],                       │ │
│  │   steps: [...], │         │   vector_results: [...],                       │ │
│  │   warnings: [], │         │   tool_execution_summary: {...},               │ │
│  │   risk_level:   │         │   information_gaps: [...],                     │ │
│  │   "medium",     │         │   confidence_factors: {...}                    │ │
│  │   ...           │         │ }                                               │ │
│  │ }               │         │                                                 │ │
│  └─────────────────┘         └─────────────────────────────────────────────────┘ │
│           │                                   │                                 │
│           └─────────────────┬─────────────────┘                                 │
│                             │                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │                      Six-Factor Analysis Engine                             │ │
│  │                                                                             │ │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐            │ │
│  │  │ Information     │  │ Plan            │  │ Technical       │            │ │
│  │  │ Quality         │  │ Completeness    │  │ Accuracy        │            │ │
│  │  │                 │  │                 │  │                 │            │ │
│  │  │ Weight: 25%     │  │ Weight: 20%     │  │ Weight: 20%     │            │ │
│  │  │                 │  │                 │  │                 │            │ │
│  │  │ • Source Count  │  │ • Essential     │  │ • PowerEdge     │            │ │
│  │  │ • Diversity     │  │   Elements      │  │   Specificity   │            │ │
│  │  │ • Relevance     │  │ • Step Detail   │  │ • Tech Terms    │            │ │
│  │  │   Quality       │  │ • Structure     │  │ • Procedures    │            │ │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘            │ │
│  │                                                                             │ │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐            │ │
│  │  │ Risk            │  │ Source          │  │ Specificity     │            │ │
│  │  │ Assessment      │  │ Reliability     │  │                 │            │ │
│  │  │                 │  │                 │  │                 │            │ │
│  │  │ Weight: 15%     │  │ Weight: 10%     │  │ Weight: 10%     │            │ │
│  │  │                 │  │                 │  │                 │            │ │
│  │  │ • Risk Levels   │  │ • Official      │  │ • Measurements  │            │ │
│  │  │ • Warnings      │  │   Sources       │  │ • Commands      │            │ │
│  │  │ • Escalation    │  │ • Tool Success  │  │ • Paths         │            │ │
│  │  │   Triggers      │  │   Rate          │  │ • Specifics     │            │ │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘            │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
│                                     │                                           │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │                     Confidence Calculation Engine                           │ │
│  │                                                                             │ │
│  │    Weighted Score = Σ(Factor Score × Weight)                               │ │
│  │                                                                             │ │
│  │    Confidence = (Info_Quality × 0.25) +                                    │ │
│  │                 (Completeness × 0.20) +                                    │ │
│  │                 (Tech_Accuracy × 0.20) +                                   │ │
│  │                 (Risk_Assessment × 0.15) +                                 │ │
│  │                 (Source_Reliability × 0.10) +                              │ │
│  │                 (Specificity × 0.10)                                       │ │
│  │                                                                             │ │
│  │    Range: 0.0 to 1.0                                                       │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
│                                     │                                           │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │                     Confidence Level Mapping                               │ │
│  │                                                                             │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │ │
│  │  │    HIGH     │  │   MEDIUM    │  │     LOW     │  │  VERY_LOW   │       │ │
│  │  │             │  │             │  │             │  │             │       │ │
│  │  │ Score ≥ 0.8 │  │ 0.6 ≤ Score │  │ 0.4 ≤ Score │  │ Score < 0.4 │       │ │
│  │  │             │  │     < 0.8   │  │     < 0.6   │  │             │       │ │
│  │  │ • Strong    │  │ • Reasonable│  │ • Significant│  │ • Insufficient│      │ │
│  │  │   foundation│  │   approach  │  │   gaps      │  │   quality   │       │ │
│  │  │ • Reliable  │  │ • May need  │  │ • Expert    │  │ • Escalation│       │ │
│  │  │   execution │  │   validation│  │   review    │  │   required  │       │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘       │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
│                                     │                                           │
│  Output: Detailed Confidence Assessment                                        │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │ {                                                                           │ │
│  │   overall_score: 0.74,                                                     │ │
│  │   confidence_level: "medium",                                              │ │
│  │   factor_scores: {                                                         │ │
│  │     information_quality: 0.68,                                             │ │
│  │     plan_completeness: 0.85,                                               │ │
│  │     technical_accuracy: 0.72,                                              │ │
│  │     risk_assessment: 0.90,                                                 │ │
│  │     source_reliability: 0.60,                                              │ │
│  │     specificity: 0.45                                                      │ │
│  │   },                                                                       │ │
│  │   limiting_factors: ["specificity: 0.45", "source_reliability: 0.60"],    │ │
│  │   improvement_suggestions: [...],                                          │ │
│  │   score_explanation: "Plan is reasonable but needs more specifics..."      │ │
│  │ }                                                                           │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Factor Analysis Breakdown

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         Confidence Factor Analysis                              │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│ 1. Information Quality Assessment (Weight: 0.25)                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐            │
│  │ Source Count    │    │ Source          │    │ Relevance       │            │
│  │ Analysis        │    │ Diversity       │    │ Quality         │            │
│  │                 │    │                 │    │                 │            │
│  │ Search: 7       │    │ Web: ✓          │    │ Avg Relevance:  │            │
│  │ Vector: 3       │    │ Vector: ✓       │    │ 0.73            │            │
│  │ Total: 10       │    │ Both: +0.3      │    │ Score: 0.73×0.3 │            │
│  │ ≥5: +0.4        │    │                 │    │      = 0.22     │            │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘            │
│                                   │                                            │
│  ┌─────────────────────────────────▼─────────────────────────────────┐         │
│  │ Information Quality Score:                                         │         │
│  │                                                                    │         │
│  │ Source Count (≥5): 0.40                                            │         │
│  │ Source Diversity (both): 0.30                                      │         │
│  │ Relevance Quality: 0.22                                            │         │
│  │                                                                    │         │
│  │ Total: 0.40 + 0.30 + 0.22 = 0.92 → 0.92 (within 1.0 limit)       │         │
│  └─────────────────────────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│ 2. Plan Completeness Assessment (Weight: 0.20)                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐            │
│  │ Essential       │    │ Optional        │    │ Step Analysis   │            │
│  │ Elements        │    │ Elements        │    │                 │            │
│  │                 │    │                 │    │                 │            │
│  │ Present:        │    │ Present:        │    │ Total Steps: 6  │            │
│  │ ✓ title         │    │ ✓ prerequisites │    │ ≥5: +0.2        │            │
│  │ ✓ steps         │    │ ✓ warnings      │    │                 │            │
│  │ ✓ estimated_time│    │ ✓ escalation    │    │ Detailed Steps: │            │
│  │ Score: 3×0.15   │    │ Score: 3×0.1    │    │ 5/6 = 0.83      │            │
│  │      = 0.45     │    │      = 0.30     │    │ Score: 0.83×0.15│            │
│  └─────────────────┘    └─────────────────┘    │      = 0.12     │            │
│                                                └─────────────────┘            │
│                                   │                                            │
│  ┌─────────────────────────────────▼─────────────────────────────────┐         │
│  │ Plan Completeness Score:                                           │         │
│  │                                                                    │         │
│  │ Essential Elements: 0.45                                           │         │
│  │ Optional Elements: 0.30                                            │         │
│  │ Step Count Bonus: 0.20                                             │         │
│  │ Step Detail Quality: 0.12                                          │         │
│  │                                                                    │         │
│  │ Total: 0.45 + 0.30 + 0.20 + 0.12 = 1.07 → 1.00 (capped)          │         │
│  └─────────────────────────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│ 3. Technical Accuracy Assessment (Weight: 0.20)                                │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐            │
│  │ PowerEdge       │    │ Technical       │    │ Procedural      │            │
│  │ Specificity     │    │ Terminology     │    │ Language        │            │
│  │                 │    │                 │    │                 │            │
│  │ Found:          │    │ Found:          │    │ Found:          │            │
│  │ • poweredge ✓   │    │ • bios ✓        │    │ • step ✓        │            │
│  │ • idrac ✓       │    │ • memory ✓      │    │ • check ✓       │            │
│  │ • perc          │    │ • diagnostic ✓  │    │ • verify ✓      │            │
│  │ Score: 2×0.1    │    │ • firmware      │    │ • configure ✓   │            │
│  │      = 0.20     │    │ Score: 3×0.05   │    │ Score: 4×0.04   │            │
│  │ (max 0.3)       │    │      = 0.15     │    │      = 0.16     │            │
│  └─────────────────┘    │ (max 0.25)      │    │ (max 0.20)      │            │
│                         └─────────────────┘    └─────────────────┘            │
│                                   │                                            │
│  ┌─────────────────┐    ┌─────────▼─────────┐                                 │
│  │ Error Codes &   │    │ Model Specificity │                                 │
│  │ Patterns        │    │                   │                                 │
│  │                 │    │ Found:            │                                 │
│  │ Found:          │    │ • "r740" pattern  │                                 │
│  │ • Error pattern │    │ Score: +0.10      │                                 │
│  │   [E1234] ✓     │    │                   │                                 │
│  │ Score: +0.15    │    │                   │                                 │
│  └─────────────────┘    └───────────────────┘                                 │
│                                   │                                            │
│  ┌─────────────────────────────────▼─────────────────────────────────┐         │
│  │ Technical Accuracy Score:                                          │         │
│  │                                                                    │         │
│  │ PowerEdge Specificity: 0.20                                        │         │
│  │ Technical Terms: 0.15                                              │         │
│  │ Procedural Language: 0.16                                          │         │
│  │ Error Codes: 0.15                                                  │         │
│  │ Model Specificity: 0.10                                            │         │
│  │                                                                    │         │
│  │ Total: 0.20 + 0.15 + 0.16 + 0.15 + 0.10 = 0.76                    │         │
│  └─────────────────────────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│ 4. Risk Assessment Quality (Weight: 0.15)                                      │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐            │
│  │ Overall Risk    │    │ Step-Level      │    │ Safety          │            │
│  │ Level           │    │ Risk Coverage   │    │ Warnings        │            │
│  │                 │    │                 │    │                 │            │
│  │ Specified:      │    │ Steps with Risk:│    │ Warnings: 3     │            │
│  │ ✓ "medium"      │    │ 5 out of 6      │    │ Score: 3×0.1    │            │
│  │ Score: +0.20    │    │ Coverage: 83%   │    │      = 0.30     │            │
│  │                 │    │ Score: 0.83×0.3 │    │ (max 0.25)      │            │
│  │                 │    │      = 0.25     │    │      → 0.25     │            │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘            │
│                                   │                                            │
│  ┌─────────────────┐    ┌─────────▼─────────┐                                 │
│  │ Escalation      │    │ Safety Language   │                                 │
│  │ Triggers        │    │                   │                                 │
│  │                 │    │ Found:            │                                 │
│  │ Defined:        │    │ • "backup" ✓      │                                 │
│  │ ✓ 2 triggers    │    │ • "ensure" ✓      │                                 │
│  │ Score: +0.15    │    │ • "verify" ✓      │                                 │
│  │                 │    │ Score: 3×0.02     │                                 │
│  │                 │    │      = 0.06       │                                 │
│  └─────────────────┘    │ (max 0.10)        │                                 │
│                         └───────────────────┘                                 │
│                                   │                                            │
│  ┌─────────────────────────────────▼─────────────────────────────────┐         │
│  │ Risk Assessment Score:                                             │         │
│  │                                                                    │         │
│  │ Overall Risk Level: 0.20                                           │         │
│  │ Step Risk Coverage: 0.25                                           │         │
│  │ Safety Warnings: 0.25                                              │         │
│  │ Escalation Triggers: 0.15                                          │         │
│  │ Safety Language: 0.06                                              │         │
│  │                                                                    │         │
│  │ Total: 0.20 + 0.25 + 0.25 + 0.15 + 0.06 = 0.91                    │         │
│  └─────────────────────────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Confidence Decision Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          Confidence-Based Decision Flow                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│                              Input: Plan + Context                              │
│                                       │                                         │
│                     ┌─────────────────▼─────────────────┐                      │
│                     │    Calculate Factor Scores        │                      │
│                     │                                   │                      │
│                     │  • Information Quality: 0.92      │                      │
│                     │  • Plan Completeness: 1.00        │                      │
│                     │  • Technical Accuracy: 0.76       │                      │
│                     │  • Risk Assessment: 0.91          │                      │
│                     │  • Source Reliability: 0.65       │                      │
│                     │  • Specificity: 0.48              │                      │
│                     └─────────────────┬─────────────────┘                      │
│                                       │                                         │
│                     ┌─────────────────▼─────────────────┐                      │
│                     │     Weighted Score Calculation    │                      │
│                     │                                   │                      │
│                     │ Score = (0.92×0.25) + (1.00×0.20) │                      │
│                     │       + (0.76×0.20) + (0.91×0.15) │                      │
│                     │       + (0.65×0.10) + (0.48×0.10) │                      │
│                     │                                   │                      │
│                     │ Score = 0.23 + 0.20 + 0.152       │                      │
│                     │       + 0.137 + 0.065 + 0.048     │                      │
│                     │                                   │                      │
│                     │ Final Score = 0.832               │                      │
│                     └─────────────────┬─────────────────┘                      │
│                                       │                                         │
│                     ┌─────────────────▼─────────────────┐                      │
│                     │    Confidence Level Mapping       │                      │
│                     │                                   │                      │
│                     │ Score: 0.832                      │                      │
│                     │ Range: [0.8, 1.0) → HIGH          │                      │
│                     └─────────────────┬─────────────────┘                      │
│                                       │                                         │
│         ┌─────────────────────────────▼─────────────────────────────┐           │
│         │                 Decision Matrix                           │           │
│         │                                                           │           │
│         │ Confidence Level: HIGH (0.832)                            │           │
│         │ Risk Factors: Medium (from plan analysis)                 │           │
│         │ Limiting Factors: ["specificity: 0.48"]                   │           │
│         │                                                           │           │
│         │ ┌─────────────┐    ┌─────────────┐    ┌─────────────┐   │           │
│         │ │   HIGH      │    │   MEDIUM    │    │     LOW     │   │           │
│         │ │ ≥ 0.8       │    │ 0.6 - 0.8   │    │ 0.4 - 0.6   │   │           │
│         │ │             │    │             │    │             │   │           │
│         │ │ → EXECUTE   │    │ → ADVISORY  │    │ → REQUIRED  │   │           │
│         │ │   ✓         │    │             │    │             │   │           │
│         │ └─────────────┘    └─────────────┘    └─────────────┘   │           │
│         │                                                           │           │
│         │ Decision: EXECUTE with Advisory Notes                     │           │
│         │ Reason: High confidence but note specificity limitation   │           │
│         └───────────────────────────────────────────────────────────┘           │
│                                       │                                         │
│                     ┌─────────────────▼─────────────────┐                      │
│                     │     Generate Recommendations      │                      │
│                     │                                   │                      │
│                     │ Primary: Execute plan as provided │                      │
│                     │                                   │                      │
│                     │ Advisory Notes:                   │                      │
│                     │ • Add more specific commands      │                      │
│                     │ • Include exact file paths        │                      │
│                     │ • Provide model-specific details  │                      │
│                     │                                   │                      │
│                     │ Monitoring:                       │                      │
│                     │ • Track execution success         │                      │
│                     │ • Collect user feedback           │                      │
│                     │ • Update scoring models           │                      │
│                     └───────────────────────────────────┘                      │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Integration Flow Diagrams

### Complete Scoring Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           Complete Scoring Pipeline                             │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│ User Query: "PowerEdge R740 won't boot, amber LED showing"                     │
│                                       │                                         │
│            ┌─────────────────────────▼─────────────────────────┐               │
│            │              Tool Orchestration                   │               │
│            │                                                   │               │
│            │  ┌─────────────────┐    ┌─────────────────┐      │               │
│            │  │  Web Search     │    │ Vector Search   │      │               │
│            │  │     Tool        │    │     Tool        │      │               │
│            │  │                 │    │                 │      │               │
│            │  │ Returns 8       │    │ Returns 3       │      │               │
│            │  │ results         │    │ results         │      │               │
│            │  └─────────────────┘    └─────────────────┘      │               │
│            └─────────────────────────┬─────────────────────────┘               │
│                                      │                                         │
│            ┌─────────────────────────▼─────────────────────────┐               │
│            │            Relevancy Scoring                      │               │
│            │                                                   │               │
│            │  For each result:                                 │               │
│            │  1. Query Term Overlap (30%)                      │               │
│            │  2. Dell/PowerEdge Relevance (25%)                │               │
│            │  3. Technical Relevance (20%)                     │               │
│            │  4. Source Authority (15%)                        │               │
│            │  5. Content Quality (10%)                         │               │
│            │                                                   │               │
│            │  Output: Ranked results with scores               │               │
│            │  [0.92, 0.87, 0.76, 0.65, 0.58, ...]            │               │
│            └─────────────────────────┬─────────────────────────┘               │
│                                      │                                         │
│            ┌─────────────────────────▼─────────────────────────┐               │
│            │           Information Fusion                      │               │
│            │                                                   │               │
│            │  • Combine top-ranked results                     │               │
│            │  • Remove duplicates                              │               │
│            │  • Create context summary                         │               │
│            │  • Generate metadata                              │               │
│            └─────────────────────────┬─────────────────────────┘               │
│                                      │                                         │
│            ┌─────────────────────────▼─────────────────────────┐               │
│            │            Plan Generation                        │               │
│            │                                                   │               │
│            │  • LLM processes fused information                │               │
│            │  • Generates structured plan                      │               │
│            │  • Includes steps, warnings, prerequisites        │               │
│            └─────────────────────────┬─────────────────────────┘               │
│                                      │                                         │
│            ┌─────────────────────────▼─────────────────────────┐               │
│            │           Confidence Scoring                      │               │
│            │                                                   │               │
│            │  1. Information Quality (25%)                     │               │
│            │     - Source count: 11 → 0.40                     │               │
│            │     - Diversity: web+vector → 0.30                │               │
│            │     - Avg relevance: 0.76 → 0.23                  │               │
│            │     - Subtotal: 0.93                              │               │
│            │                                                   │               │
│            │  2. Plan Completeness (20%)                       │               │
│            │     - Essential elements: 3/3 → 0.45              │               │
│            │     - Optional elements: 3 → 0.30                 │               │
│            │     - Step count: 6 → 0.20                        │               │
│            │     - Step detail: 83% → 0.12                     │               │
│            │     - Subtotal: 1.00 (capped)                     │               │
│            │                                                   │               │
│            │  3. Technical Accuracy (20%)                      │               │
│            │     - PowerEdge terms: 2 → 0.20                   │               │
│            │     - Tech terms: 3 → 0.15                        │               │
│            │     - Procedural: 4 → 0.16                        │               │
│            │     - Error codes: ✓ → 0.15                       │               │
│            │     - Model specific: ✓ → 0.10                    │               │
│            │     - Subtotal: 0.76                              │               │
│            │                                                   │               │
│            │  4. Risk Assessment (15%)                         │               │
│            │     - Risk level: ✓ → 0.20                        │               │
│            │     - Step coverage: 83% → 0.25                   │               │
│            │     - Warnings: 3 → 0.25                          │               │
│            │     - Escalation: ✓ → 0.15                        │               │
│            │     - Safety lang: 3 → 0.06                       │               │
│            │     - Subtotal: 0.91                              │               │
│            │                                                   │               │
│            │  5. Source Reliability (10%)                      │               │
│            │     - Official sources: 30% → 0.12                │               │
│            │     - Vector docs: ✓ → 0.30                       │               │
│            │     - Tool success: 90% → 0.27                    │               │
│            │     - Subtotal: 0.69                              │               │
│            │                                                   │               │
│            │  6. Specificity (10%)                             │               │
│            │     - Measurements: ✓ → 0.20                      │               │
│            │     - Commands: ✓ → 0.15                          │               │
│            │     - Network: ✗ → 0.00                           │               │
│            │     - Components: 2 → 0.10                        │               │
│            │     - Generic penalty: -0.12                      │               │
│            │     - Subtotal: 0.33                              │               │
│            │                                                   │               │
│            │  Final Score Calculation:                         │               │
│            │  (0.93×0.25) + (1.00×0.20) + (0.76×0.20) +       │               │
│            │  (0.91×0.15) + (0.69×0.10) + (0.33×0.10)         │               │
│            │  = 0.233 + 0.200 + 0.152 + 0.137 + 0.069 + 0.033 │               │
│            │  = 0.824                                          │               │
│            │                                                   │               │
│            │  Confidence Level: HIGH (≥ 0.8)                   │               │
│            └─────────────────────────┬─────────────────────────┘               │
│                                      │                                         │
│            ┌─────────────────────────▼─────────────────────────┐               │
│            │            Routing Decision                       │               │
│            │                                                   │               │
│            │  Confidence: HIGH (0.824)                         │               │
│            │  Risk Level: MEDIUM                               │               │
│            │  Limiting Factors: Specificity (0.33)             │               │
│            │                                                   │               │
│            │  Decision: EXECUTE                                │               │
│            │  Recommendation: Proceed with advisory notes      │               │
│            │  Advisory: Improve command specificity            │               │
│            └───────────────────────────────────────────────────┘               │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Scoring Algorithm Flowcharts

### Relevancy Scoring Flowchart

```
                              START
                                │
                    ┌───────────▼───────────┐
                    │   Input: Result +     │
                    │   Query               │
                    └───────────┬───────────┘
                                │
                    ┌───────────▼───────────┐
                    │ Extract text content  │
                    │ from result           │
                    └───────────┬───────────┘
                                │
         ┌─────────────────────▼─────────────────────┐
         │          Calculate Factor Scores          │
         └─────────────────────┬─────────────────────┘
                                │
    ┌────────────────────────────┼────────────────────────────┐
    │                           │                            │
    ▼                           ▼                            ▼
┌─────────┐               ┌─────────┐                 ┌─────────┐
│ Term    │               │ Dell/   │                 │Technical│
│Overlap  │               │PowerEdge│                 │Relevance│
│         │               │Relevance│                 │         │
│Weight:  │               │         │                 │Weight:  │
│ 0.30    │               │Weight:  │                 │ 0.20    │
│         │               │ 0.25    │                 │         │
└────┬────┘               └────┬────┘                 └────┬────┘
     │                         │                           │
     │    ┌─────────┐          │      ┌─────────┐          │
     │    │Source   │          │      │Content  │          │
     │    │Authority│          │      │Quality  │          │
     │    │         │          │      │         │          │
     │    │Weight:  │          │      │Weight:  │          │
     │    │ 0.15    │          │      │ 0.10    │          │
     │    └────┬────┘          │      └────┬────┘          │
     │         │               │           │               │
     └─────────┼───────────────┼───────────┼───────────────┘
               │               │           │
               └───────────────┼───────────┘
                               │
                    ┌─────────▼─────────┐
                    │ Weighted Sum      │
                    │                   │
                    │ Score = Σ(Factor  │
                    │ Score × Weight)   │
                    └─────────┬─────────┘
                              │
                    ┌─────────▼─────────┐
                    │ Normalize to      │
                    │ [0.0, 1.0] range  │
                    └─────────┬─────────┘
                              │
                    ┌─────────▼─────────┐
                    │ Return relevance  │
                    │ score             │
                    └─────────┬─────────┘
                              │
                             END

Flow Details:

1. Term Overlap Calculation:
   ┌─────────────────────┐
   │ Extract query terms │ → {"r740", "boot", "amber", "led"}
   └─────────────────────┘
                │
   ┌─────────────────────┐
   │Extract content terms│ → {"poweredge", "r740", "boot", "led", "diagnostic"}
   └─────────────────────┘
                │
   ┌─────────────────────┐
   │ Calculate Jaccard   │ → |intersection| / |query_terms|
   │ Similarity          │   = 3 / 4 = 0.75
   └─────────────────────┘

2. Dell/PowerEdge Relevance:
   ┌─────────────────────┐
   │ Check PowerEdge     │ → "r740" found → +0.3
   │ models              │
   └─────────────────────┘
                │
   ┌─────────────────────┐
   │ Check Dell keywords │ → "poweredge" found → +0.1
   │                     │   "dell" found → +0.1
   └─────────────────────┘
                │
   ┌─────────────────────┐
   │ Check official      │ → "support.dell.com" → +0.3
   │ source              │
   └─────────────────────┘

3. Technical Relevance:
   ┌─────────────────────┐
   │ Count technical     │ → "diagnostic", "firmware" → 2×0.05 = 0.1
   │ keywords            │
   └─────────────────────┘
                │
   ┌─────────────────────┐
   │ Count symptom       │ → "boot", "led", "amber" → 3×0.1 = 0.3
   │ keywords            │
   └─────────────────────┘
                │
   ┌─────────────────────┐
   │ Check error codes   │ → Pattern found → +0.2
   │ and procedures      │   Procedures found → +0.1
   └─────────────────────┘

4. Source Authority:
   ┌─────────────────────┐
   │ Evaluate URL domain │ → "support.dell.com" → 1.0
   │ and source type     │   "dell.com" → 0.9
   └─────────────────────┘   "docs.*" → 0.7
                             "community" → 0.5
                             "other" → 0.3

5. Content Quality:
   ┌─────────────────────┐
   │ Analyze length      │ → >100 words → +0.4
   │                     │   50-100 words → +0.2
   └─────────────────────┘   <20 words → -0.2
                │
   ┌─────────────────────┐
   │ Check structure     │ → Numbered steps → +0.3
   │                     │   "Step", "First" → +0.3
   └─────────────────────┘
                │
   ┌─────────────────────┐
   │ Assess technical    │ → Multiple colons → +0.2
   │ detail              │   Complete sentences → +0.1
   └─────────────────────┘
```

### Confidence Scoring Flowchart

```
                              START
                                │
                    ┌───────────▼───────────┐
                    │   Input: Plan +       │
                    │   Context             │
                    └───────────┬───────────┘
                                │
                    ┌───────────▼───────────┐
                    │ Initialize scoring    │
                    │ weights and thresholds│
                    └───────────┬───────────┘
                                │
         ┌─────────────────────▼─────────────────────┐
         │        Calculate Six Factor Scores        │
         └─────────────────────┬─────────────────────┘
                                │
    ┌───────────┬──────────────┼──────────────┬──────────────┬─────────┐
    │           │              │              │              │         │
    ▼           ▼              ▼              ▼              ▼         ▼
┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
│Info     │ │Plan     │ │Tech     │ │Risk     │ │Source   │ │Specific-│
│Quality  │ │Complete │ │Accuracy │ │Assess   │ │Reliable │ │ity      │
│(25%)    │ │(20%)    │ │(20%)    │ │(15%)    │ │(10%)    │ │(10%)    │
└────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘
     │           │           │           │           │           │
     └───────────┼───────────┼───────────┼───────────┼───────────┘
                 │           │           │           │
                 └───────────┼───────────┼───────────┘
                             │           │
                             └───────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │ Calculate Weighted Sum      │
                    │                             │
                    │ Score = Σ(Factor_i × W_i)   │
                    │ where W_i are weights       │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │ Determine Confidence Level  │
                    │                             │
                    │ HIGH:    Score ≥ 0.8        │
                    │ MEDIUM:  0.6 ≤ Score < 0.8  │
                    │ LOW:     0.4 ≤ Score < 0.6  │
                    │ VERY_LOW: Score < 0.4       │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │ Identify Limiting Factors   │
                    │ (Factors with score < 0.5)  │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │ Generate Improvement        │
                    │ Suggestions                 │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │ Create Assessment Report    │
                    └──────────────┬──────────────┘
                                   │
                                  END

Detailed Factor Calculations:

1. Information Quality (Weight: 0.25):
   ┌─────────────────────┐
   │ Count Sources       │ → Total = Web + Vector
   └─────────────────────┘
                │
   ┌─────────────────────┐
   │ Assess Diversity    │ → Both web and vector = +0.3
   └─────────────────────┘   One type only = +0.2
                │
   ┌─────────────────────┐
   │ Calculate Avg       │ → Weighted by relevance scores
   │ Relevance           │
   └─────────────────────┘

2. Plan Completeness (Weight: 0.20):
   ┌─────────────────────┐
   │ Check Essential     │ → title, steps, time
   │ Elements            │   Each present = +0.15
   └─────────────────────┘
                │
   ┌─────────────────────┐
   │ Check Optional      │ → prerequisites, warnings,
   │ Elements            │   escalation_triggers
   └─────────────────────┘   Each present = +0.1
                │
   ┌─────────────────────┐
   │ Analyze Steps       │ → Count and detail level
   └─────────────────────┘

3. Technical Accuracy (Weight: 0.20):
   ┌─────────────────────┐
   │ PowerEdge Terms     │ → "poweredge", "idrac", etc.
   └─────────────────────┘   Each = +0.1 (max 0.3)
                │
   ┌─────────────────────┐
   │ Technical Terms     │ → "bios", "memory", etc.
   └─────────────────────┘   Each = +0.05 (max 0.25)
                │
   ┌─────────────────────┐
   │ Procedural Terms    │ → "step", "check", etc.
   └─────────────────────┘   Each = +0.04 (max 0.2)
                │
   ┌─────────────────────┐
   │ Error Codes &       │ → Pattern matching
   │ Model Specifics     │   +0.15 and +0.1
   └─────────────────────┘

4. Risk Assessment (Weight: 0.15):
   ┌─────────────────────┐
   │ Overall Risk Level  │ → Present = +0.2
   └─────────────────────┘
                │
   ┌─────────────────────┐
   │ Step Risk Coverage  │ → % of steps with risk
   └─────────────────────┘   × 0.3
                │
   ┌─────────────────────┐
   │ Safety Elements     │ → Warnings, escalation,
   └─────────────────────┘   safety language

5. Source Reliability (Weight: 0.10):
   ┌─────────────────────┐
   │ Official Sources    │ → % Dell sources × 0.4
   └─────────────────────┘
                │
   ┌─────────────────────┐
   │ Vector Docs         │ → Present = +0.3
   └─────────────────────┘
                │
   ┌─────────────────────┐
   │ Tool Success Rate   │ → Success rate × 0.3
   └─────────────────────┘

6. Specificity (Weight: 0.10):
   ┌─────────────────────┐
   │ Specific Values     │ → Numbers, units = +0.2
   └─────────────────────┘
                │
   ┌─────────────────────┐
   │ Commands & Paths    │ → File paths, commands = +0.15
   └─────────────────────┘
                │
   ┌─────────────────────┐
   │ Component Details   │ → "slot", "bay" etc. = +0.05 each
   └─────────────────────┘
                │
   ┌─────────────────────┐
   │ Generic Penalty     │ → Reduce for generic terms
   └─────────────────────┘
```

This comprehensive set of design diagrams provides detailed visual representations of how both the Relevancy Scorer and Confidence Scorer work, including their architectures, algorithms, factor calculations, and integration flows. The diagrams show the multi-factor weighted approaches used by both scorers and how they contribute to the overall intelligence of the Dell PowerEdge Support Planner Agent.
