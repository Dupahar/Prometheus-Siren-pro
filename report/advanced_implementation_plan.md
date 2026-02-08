# 🚀 Implementation Plan: The Mythical Upgrades

**Goal:** Implement the three "Mythical" tier upgrades: **Herd Immunity** (Federated Learning), **Kernel Defense** (eBPF), and **Formal Verification**.
**Excluded:** Edge-Native Intelligence (SLMs) as per user request.

## User Review Required
> [!WARNING]
> **OS Requirement for eBPF**
> The **Kernel-Level Defense** (eBPF/XDP) strictly requires a **Linux Kernel**. You are currently on **Windows**.
> *   **Plan:** We will write the code (using the `aya` framework), but you must run it in **WSL2** or a Linux VM to verify it. It **will not** compilation/run natively on Windows.

> [!NOTE]
> **Dependencies**
> *   **Flower:** Requires `pip install flwr`.
> *   **Kani:** Requires `cargo install --locked kani-verifier` (Heavy install).
> *   **CrossHair:** Requires `pip install crosshair-tool`.

---

## 1. Herd Immunity (Federated Learning)
**Goal:** Train a global model on distributed attack data without sharing raw logs.

### Proposed Changes
#### [NEW] [flower_server.py](file:///c:/Users/mahaj/Downloads/Jirachi/src/federated/server.py)
- **Role:** The Central Aggregator.
- **Library:** `flwr`
- **Logic:**
    - Initialize `flwr.server.start_server`.
    - Strategy: `FedAvg` (Federated Averaging).
    - Rounds: 3 rounds for demo.

#### [NEW] [flower_client.py](file:///c:/Users/mahaj/Downloads/Jirachi/src/federated/client.py)
- **Role:** The "Diplomat" (Sidecar Agent).
- **Logic:**
    - Load local `XGBoost` model.
    - Implement `flwr.client.NumPyClient`.
    - `fit()`: Train functionality on local `training_data.csv`.
    - `evaluate()`: Test against local validation set.

#### [MODIFY] [log_parser.py](file:///c:/Users/mahaj/Downloads/Jirachi/src/prometheus/log_parser.py)
- Ensure it saves a standardized `training_data.csv` so the Flower client has data to read.

---

## 2. Kernel-Level Defense (eBPF & XDP)
**Goal:** Drop malicious packets at the network driver level (Linux only).

### Proposed Changes
#### [NEW] [ebpf_shield (Crate)](file:///c:/Users/mahaj/Downloads/Jirachi/src/ebpf_shield/Cargo.toml)
- **Framework:** `aya` (Rust eBPF).
- **Type:** Binary (XDP Program).

#### [NEW] [xdp_prog.rs](file:///c:/Users/mahaj/Downloads/Jirachi/src/ebpf_shield/src/main.rs)
- **Map:** `HashMap` storing blocked IPs.
- **Logic:**
    ```rust
    if blocklist.contains(&ip_source) {
        return XDP_DROP;
    }
    return XDP_PASS;
    ```

#### [MODIFY] [jirachi-proxy](file:///c:/Users/mahaj/Downloads/Jirachi/src/jirachi-proxy/src/main.rs)
- Add a "User Space Control Plane" to write to the eBPF Map.
- When `Gemini` says "Block IP 1.2.3.4", update the eBPF map instead of just blocking in Axum.

---

## 3. Formal Verification (Mathematical Proofs)
**Goal:** Prove the code cannot crash.

### Proposed Changes
#### [MODIFY] [jirachi-proxy/Cargo.toml](file:///c:/Users/mahaj/Downloads/Jirachi/src/jirachi-proxy/Cargo.toml)
- Add `[dev-dependencies] kani = "..."`

#### [NEW] [verification_harness.rs](file:///c:/Users/mahaj/Downloads/Jirachi/src/jirachi-proxy/tests/kani_harness.rs)
- **Target:** The Request Parser.
- **Proof:**
    ```rust
    #[kani::proof]
    fn verify_parser_safety() {
        let payload: String = kani::any();
        // Prove that parse(payload) NEVER panics
        let _ = parser::parse(&payload);
    }
    ```

#### [NEW] [python_contracts.py](file:///c:/Users/mahaj/Downloads/Jirachi/tests/contracts.py)
- **Tool:** `crosshair`
- **Target:** Patch Generator logic.
- **Contract:**
    ```python
    def apply_patch(code: str, patch: str) -> str:
        """
        post: len(__return__) >= len(code) # Patch should never delete entire file
        post: syntax_valid(__return__)     # Result must be valid Python
        """
    ```

---

## 🚀 Execution Order
1.  **Verification First:** Setup Kani/CrossHair to prove existing code.
2.  **Federated Learning:** Build the Server/Client flow.
3.  **eBPF:** Write the Rust code (even if we can't run it on Windows).
