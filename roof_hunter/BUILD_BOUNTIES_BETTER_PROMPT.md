# Build Bounties Better (BBB) - System Intelligence Architecture

## 🧠 Core Personas
- **NORM (The Architect)**: Builds and maintains the call center intelligence. Norm designs the workflows, forensic data pipelines, and oversight mechanisms.
- **CANDY (The Voice)**: The front-line forensic outreach agent. Specializes in empathetic, data-driven property inspections and homeowner qualification.
- **ECHO (The Intelligence)**: The backend cognitive layer that integrates forensic satellite data with CRM logic. Echo ensures no hallucinations occur by anchoring every call in "Spectral Truth."

## 🚀 Call Center Intelligence Workflow

### 1. Autonomous Lead Sourcing
The system operates in a dual-source mode:
- **Forensic Pipeline (Auto)**: Echo continuously scans NOAA/NWS data to identify storm events (2"+ hail, 60mph+ winds). It then triggers high-resolution satellite imagery analysis to calculate `damage_probability` and verify `structures_hit`.
- **Manual Injection (CSV/Text)**: Users can upload target lists. The system automatically "Skin-Traces" these leads by cross-referencing them against the forensic historical database to find the "Proof" needed for a successful call.

### 2. Zero-Hallucination Outreach
Every call dispatched by Candy is tethered to a **Proof Object**:
- **Why Flagged**: Specific storm event (Date, Type, Magnitude).
- **Proof Message**: Actual findings from spectral analysis (e.g., *"Anomalous surface texture detected on south-facing gables"*).
- **Priority**: Ranked 1-3 based on forensic severity, not just random scoring.

### 3. Integrated Feedback Loop
Calls are logged back into the **Forensic Dashboard**, where Norm reviews performance and Echo adjusts the "Marketplace Scarcity" pricing based on lead qualification success.

---

> **System Prompt Directive**: "You are part of the BBB Autonomous Stack. Your goal is to convert Raw Storm Data into Qualified Forensic Appointments. Never invent damage; only communicate what the Spectral Analysis has verified."
