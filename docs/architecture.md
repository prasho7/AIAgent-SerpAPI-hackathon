# Architecture

This project is intentionally structured as a clean scaffold for the final hackathon solution.

```mermaid
flowchart LR
    U[User] --> UI[Streamlit UI]
    UI --> A[Agent coordinator]
    A --> R[Fallback router]
    A --> RW[Research workflow placeholder]
    RW --> G[Gemini service placeholder]
    RW --> S[SerpApi service placeholder]
    S --> EP[Evidence processor]
    G --> WP[Writer prompt]
    EP --> CV[Citation validator]

    subgraph Future
        G
        S
        RW
    end

    classDef planned fill:#fff2cc,stroke:#d6b656,stroke-width:1px;
    class G,S,RW planned;
```

## Notes

- The current implementation is intentionally small and safe.
- The live Gemini and SerpApi integrations are marked as future work.
- The router is a deterministic fallback and will later be supplemented by Gemini-guided routing.
