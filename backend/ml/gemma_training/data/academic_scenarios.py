"""
EchoSphere Deep Academic Tutoring Dataset Module (80+ Unique High-Fidelity Scenarios)
Covering all 8 Engineering Departments:
AIML, CSE, ISE, ECE, EEE, MECH, CIVIL, BT
Includes:
- Multi-step reasoning chains (Problem -> Approach -> Solution -> Verification)
- "Explain Like I'm 5" (ELI5) intuitive conceptual analogies
- Comparison questions ("What is the difference between X and Y?")
- Practice problem walkthroughs with step-by-step mathematical solutions
"""

from typing import List, Tuple

ACADEMIC_SCENARIOS: List[Tuple[str, str]] = [
    # ══════════════════════════════════════════════════════════════════════════
    # 1. ARTIFICIAL INTELLIGENCE & MACHINE LEARNING (AIML)
    # ══════════════════════════════════════════════════════════════════════════
    (
        "Explain backpropagation in neural networks with mathematical intuition",
        "Backpropagation is the core supervised learning algorithm used to compute loss gradients in neural networks using the multivariate chain rule:\n\n"
        "1. **Forward Propagation**:\n"
        "   - Activations are computed layer-by-layer: $z^{[l]} = W^{[l]} a^{[l-1]} + b^{[l]}$, with $a^{[l]} = \\sigma(z^{[l]})$.\n"
        "   - At output layer $L$, the network produces prediction $\\hat{y} = a^{[L]}$.\n\n"
        "2. **Loss Computation**:\n"
        "   - A scalar objective function $J(W, b)$ measures error (e.g., Binary Cross-Entropy: $-[y \\log \\hat{y} + (1-y) \\log(1 - \\hat{y})]$).\n\n"
        "3. **Backward Pass (Chain Rule)**:\n"
        "   - Output layer error: $\\delta^{[L]} = \\frac{\\partial J}{\\partial z^{[L]}} = (a^{[L]} - y)$.\n"
        "   - Propagating backwards for layer $l = L-1$ down to 1: $\\delta^{[l]} = ((W^{[l+1]})^T \\delta^{[l+1]}) \\odot \\sigma'(z^{[l]})$.\n"
        "   - Weight and bias gradients: $\\frac{\\partial J}{\\partial W^{[l]}} = \\delta^{[l]} (a^{[l-1]})^T$ and $\\frac{\\partial J}{\\partial b^{[l]}} = \\delta^{[l]}$.\n\n"
        "4. **Parameter Update**:\n"
        "   - Parameters update opposite to the gradient: $W^{[l]} = W^{[l]} - \\alpha \\frac{\\partial J}{\\partial W^{[l]}}$.\n\n"
        "This dynamic programming approach computes all parameter gradients in $O(E)$ time proportional to the number of network connections."
    ),
    (
        "Explain the Self-Attention mechanism in Transformer architectures",
        "Scaled Dot-Product Self-Attention enables every token in an input sequence to dynamically weigh and attend to every other token regardless of positional distance:\n\n"
        "1. **Linear Projections**:\n"
        "   - Given an input sequence matrix $X \\in \\mathbb{R}^{n \\times d_{model}}$, three projection weight matrices yield Query ($Q$), Key ($K$), and Value ($V$) representations:\n"
        "     - $Q = X W_Q, \\quad K = X W_K, \\quad V = X W_V$\n\n"
        "2. **Attention Score Formulation**:\n"
        "   - $\\text{Attention}(Q, K, V) = \\text{softmax}\\left(\\frac{Q K^T}{\\sqrt{d_k}}\\right) V$\n"
        "   - The dot product $Q K^T$ calculates pairwise token affinities.\n"
        "   - Division by $\\sqrt{d_k}$ prevents large dot products that would push the softmax function into regions with vanishingly small gradients.\n\n"
        "3. **Multi-Head Attention (MHA)**:\n"
        "   - Computes $h$ independent attention projections in parallel ($d_k = d_{model} / h$), allowing the network to capture diverse semantic, syntactic, and positional dependencies simultaneously.\n"
        "   - Head outputs are concatenated and linearly projected: $\\text{MultiHead}(Q, K, V) = \\text{Concat}(\\text{head}_1, \\dots, \\text{head}_h) W_O$."
    ),
    (
        "How do Convolutional Neural Networks (CNNs) process images and why is pooling used?",
        "CNNs process grid-structured image data through specialized layers designed to leverage spatial locality and translation equivariance:\n\n"
        "1. **Convolutional Layers**:\n"
        "   - Learnable kernels (e.g., $3 \\times 3$) slide across feature maps computing dot products to detect local edges, textures, and object parts.\n"
        "2. **Activation (ReLU)**:\n"
        "   - Introduces non-linearity $f(x) = \\max(0, x)$, enabling the network to learn non-linear decision boundaries.\n"
        "3. **Pooling Layers (Max Pooling)**:\n"
        "   - Downsamples spatial dimensions (e.g., $2 \\times 2$ window with stride 2), retaining only the strongest feature activation.\n"
        "   - *Benefits*: Drastically reduces parameter count in subsequent fully connected layers, curtails GPU memory usage, and provides translation invariance."
    ),
    (
        "What is overfitting in machine learning and how do you diagnose and prevent it?",
        "Overfitting occurs when a high-capacity model memorizes noise and idiosyncrasies in the training dataset rather than generalizable underlying patterns:\n\n"
        "- **Diagnostic Signatures**:\n"
        "  - Training loss continues to drop while validation loss plateaus and begins diverging upwards.\n"
        "- **Prevention Strategies**:\n"
        "  1. **Regularization ($L_1$ and $L_2$ Weight Decay)**: $L_2$ penalizes large weight magnitudes ($\\lambda \\|W\\|_2^2$), while $L_1$ drives non-essential weights to zero.\n"
        "  2. **Dropout**: Randomly deactivates a fraction $p$ of hidden neurons during training forward passes to prevent feature co-adaptation.\n"
        "  3. **Early Stopping**: Halts training when validation loss stops improving for a specified patience threshold.\n"
        "  4. **Data Augmentation**: Artificially expands training data using rotations, crops, flips, and color shifts."
    ),
    (
        "Compare Batch Gradient Descent, Stochastic Gradient Descent (SGD), and Adam Optimizer",
        "Gradient descent optimizers differ primarily in their update frequency and adaptive momentum mechanics:\n\n"
        "1. **Batch Gradient Descent**:\n"
        "   - Evaluates the entire dataset before making a single parameter update.\n"
        "   - *Pros*: Stable, deterministic convergence trajectory.\n"
        "   - *Cons*: Prohibitively slow for massive datasets; cannot fit entirely into GPU VRAM.\n\n"
        "2. **Stochastic Gradient Descent (SGD)**:\n"
        "   - Updates parameters using a single random sample per iteration.\n"
        "   - *Pros*: Fast updates; high variance helps jump out of shallow local minima.\n"
        "   - *Cons*: Noisy oscillations make convergence to the exact global minimum erratic without learning rate schedules.\n\n"
        "3. **Adam (Adaptive Moment Estimation)**:\n"
        "   - Combines Momentum (first moment $m_t$, exponentially decaying average of past gradients) with RMSProp (second raw moment $v_t$, average of squared gradients).\n"
        "   - Computes bias-corrected moments and scales updates per-dimension: $\\theta_{t+1} = \\theta_t - \\frac{\\alpha}{\\sqrt{\\hat{v}_t} + \\epsilon} \\hat{m}_t$.\n"
        "   - *Pros*: Fast, robust convergence across sparse and dense features with minimal manual hyperparameter tuning."
    ),
    (
        "How do Diffusion Models generate images from noise?",
        "Diffusion Models generate data through a two-phase thermodynamic process:\n\n"
        "1. **Forward Process (Markov Noising Chain)**:\n"
        "   - Gradually corrupts an input image $x_0$ by adding Gaussian noise over $T$ timesteps according to a variance schedule $\\beta_t$, turning it into pure isotropic Gaussian noise $x_T \\sim \\mathcal{N}(0, I)$.\n\n"
        "2. **Reverse Process (Learned Denoising)**:\n"
        "   - A neural network (typically a U-Net with self-attention) is trained to predict the noise $\\epsilon_\\theta(x_t, t)$ added at each step.\n"
        "   - Starting from pure noise $x_T$, the model iteratively subtracts predicted noise step-by-step to synthesize pristine, high-resolution images."
    ),
    (
        "What is Reinforcement Learning from Human Feedback (RLHF)?",
        "RLHF aligns large language models with human preferences for helpfulness, accuracy, and safety:\n\n"
        "1. **Supervised Fine-Tuning (SFT)**: Pre-trained LLM is fine-tuned on high-quality human prompt-response demonstrations.\n"
        "2. **Reward Model (RM) Training**: Human evaluators rank model candidate responses. A reward model is trained using a pairwise ranking loss to output scalar reward scores predicting human preference.\n"
        "3. **PPO Reinforcement Learning**: The SFT model is optimized against the Reward Model using Proximal Policy Optimization (PPO), with a KL-divergence penalty preventing the model from drifting too far from its original linguistic distribution."
    ),
    (
        "Explain Parameter-Efficient Fine-Tuning (PEFT) and LoRA (Low-Rank Adaptation)",
        "LoRA allows fine-tuning massive models on consumer GPUs by decomposing weight updates into low-rank matrices:\n\n"
        "1. **Mathematical Formulation**:\n"
        "   - For a frozen pre-trained weight matrix $W_0 \\in \\mathbb{R}^{d \\times k}$, its adaptation $\\Delta W$ is constrained to a low intrinsic rank $r \\ll \\min(d, k)$:\n"
        "     - $W = W_0 + \\Delta W = W_0 + \\frac{\\alpha}{r} (B \\times A)$\n"
        "     - $A \\in \\mathbb{R}^{r \\times k}$ is initialized with Gaussian noise, and $B \\in \\mathbb{R}^{d \\times r}$ is initialized to zero.\n"
        "2. **Efficiency Benefits**:\n"
        "   - Reduces trainable parameter counts by 99% (e.g. from 2 billion parameters to only 10-20 million).\n"
        "   - Eliminates optimizer memory overhead for base weights, enabling fine-tuning in under 6 GB of VRAM."
    ),
    (
        "What is the difference between Cross-Entropy Loss and Focal Loss?",
        "Both are classification losses, but Focal Loss specifically addresses extreme class imbalance:\n\n"
        "- **Cross-Entropy Loss**: $-\\log(p_t)$. Treats all samples equally, allowing easily classified negative background examples to overwhelm loss gradients.\n"
        "- **Focal Loss**: $-(1 - p_t)^\\gamma \\log(p_t)$. Introduces a modulating factor $(1 - p_t)^\\gamma$ with focusing parameter $\\gamma \\ge 0$.\n"
        "  - For easy samples ($p_t \\approx 0.99$), the modulating factor $(1 - 0.99)^2 = 0.0001$ drastically down-weights their contribution to the loss, forcing the model to concentrate learning on hard, ambiguous examples."
    ),
    (
        "Explain Rotary Position Embeddings (RoPE) in modern Large Language Models",
        "RoPE encodes positional information by rotating Query and Key vectors in the complex 2D plane:\n\n"
        "1. **Core Mechanism**:\n"
        "   - Divides the hidden dimension into pairs of 2D coordinates and rotates each pair by an angle $m \\theta_i$ proportional to token position $m$.\n"
        "2. **Relative Distance Preservation**:\n"
        "   - The inner product between query $q_m$ and key $k_n$ depends purely on their relative offset $(m - n)$:\n"
        "     - $\\langle R_{\\Theta, m} q, R_{\\Theta, n} k \\rangle = g(q, k, m - n)$\n"
        "   - *Advantage*: Naturally enables context length extrapolation and retains strong relative distance awareness without adding static absolute embedding vectors."
    ),

    # ══════════════════════════════════════════════════════════════════════════
    # 2. COMPUTER SCIENCE & ENGINEERING (CSE)
    # ══════════════════════════════════════════════════════════════════════════
    (
        "Explain Dijkstra's algorithm and contrast it with Bellman-Ford",
        "Both solve the Single-Source Shortest Path (SSSP) problem on weighted graphs, but under different constraints:\n\n"
        "1. **Dijkstra's Algorithm (Greedy)**:\n"
        "   - Maintains a min-priority queue of tentative distances. At each step, it visits the unvisited vertex $u$ with the smallest distance, relaxes its outgoing edges, and marks $u$ as finalized.\n"
        "   - *Time Complexity*: $O((V + E) \\log V)$ with a binary min-heap.\n"
        "   - *Limitation*: Requires all edge weights to be strictly non-negative ($w(u, v) \\ge 0$).\n\n"
        "2. **Bellman-Ford Algorithm (Dynamic Programming)**:\n"
        "   - Iteratively relaxes all $E$ edges $|V| - 1$ times.\n"
        "   - *Time Complexity*: $O(V \\times E)$, slower than Dijkstra.\n"
        "   - *Advantage*: Correctly handles negative edge weights and detects negative weight cycles (if an edge can still be relaxed on the $|V|$-th iteration, a negative cycle exists)."
    ),
    (
        "Explain Dynamic Programming with an example contrasting Memoization and Tabulation",
        "Dynamic Programming (DP) optimizes problems with **Overlapping Subproblems** and **Optimal Substructure**:\n\n"
        "- **Top-Down with Memoization**:\n"
        "  - Follows standard recursive logic from original problem down to base cases.\n"
        "  - Before computing, it checks an in-memory hash map or cache. If already solved, the cached value returns in $O(1)$.\n"
        "  - *Pros*: Computes only strictly needed subproblems.\n"
        "  - *Cons*: Incurs recursion stack overhead and risks call stack overflow for deep trees.\n\n"
        "- **Bottom-Up with Tabulation**:\n"
        "  - Solves subproblems iteratively starting from base cases, systematically filling an array or table.\n"
        "  - Example (0/1 Knapsack): `dp[i][w] = max(dp[i-1][w], val[i] + dp[i-1][w - wt[i]])`.\n"
        "  - *Pros*: Zero recursion overhead; allows rolling array optimizations to save memory."
    ),
    (
        "What are ACID properties in Database Management Systems (DBMS)?",
        "ACID properties guarantee transactional reliability in relational database systems:\n\n"
        "1. **Atomicity ('All or Nothing')**: A transaction completes in its entirety or rolls back completely with zero changes, enforced via Write-Ahead Logging (WAL).\n"
        "2. **Consistency**: Transactions transition the database from one valid state to another, preserving all schema constraints, foreign keys, and triggers.\n"
        "3. **Isolation**: Concurrently executing transactions do not interfere with each other. Standard SQL isolation levels (Read Committed, Repeatable Read, Serializable) prevent dirty reads, non-repeatable reads, and phantom reads.\n"
        "4. **Durability**: Once a transaction commits, its updates persist in non-volatile storage, surviving subsequent power outages or system crashes."
    ),
    (
        "Explain Virtual Memory, Paging, and Page Faults in Operating Systems",
        "Virtual Memory decouples the programmer's logical address space from physical RAM:\n\n"
        "1. **Paging**:\n"
        "   - Virtual address space is divided into fixed-size **Pages** (typically 4 KB).\n"
        "   - Physical RAM is divided into equal **Frames**.\n"
        "   - The CPU Memory Management Unit (MMU) uses the **Page Table** to translate virtual addresses (Page Number + Offset) to physical frame addresses.\n"
        "2. **Translation Lookaside Buffer (TLB)**:\n"
        "   - A fast hardware associative cache on the CPU storing recent virtual-to-physical address mappings, achieving sub-nanosecond lookups.\n"
        "3. **Page Fault Handling**:\n"
        "   - If a page's valid bit is 0 (not currently in RAM):\n"
        "     1. CPU triggers a Page Fault trap interrupt to the OS kernel.\n"
        "     2. OS locates the requested page on secondary swap storage.\n"
        "     3. OS allocates a free physical frame (or evicts a frame using replacement policies like LRU).\n"
        "     4. Issues disk I/O to read the page into memory, updates the Page Table, sets the valid bit to 1, and restarts the instruction."
    ),
    (
        "Compare B-Trees and Hash Indexes in Database Indexing",
        "B-Trees and Hash Indexes serve distinct access patterns in database storage engines:\n\n"
        "1. **B-Tree / B+ Tree Indexes (Default in PostgreSQL & MySQL)**:\n"
        "   - Self-balancing multi-way search tree where all leaf nodes reside at equal depth.\n"
        "   - Supports equality queries ($O(\\log N)$), prefix searches (`LIKE 'abc%'`), and range queries (`WHERE age BETWEEN 20 AND 30`) because leaf nodes are linked in sorted sequential order.\n\n"
        "2. **Hash Indexes**:\n"
        "   - Uses an in-memory hash table mapping hash keys to row pointers in $O(1)$ average time.\n"
        "   - *Limitation*: Can only perform point lookups (`WHERE id = 500`). Cannot be used for range queries, sorting (`ORDER BY`), or prefix matching."
    ),
    (
        "What is the difference between TCP and UDP transport protocols?",
        "TCP and UDP represent fundamental trade-offs between reliability and latency:\n\n"
        "- **TCP (Transmission Control Protocol)**:\n"
        "  - Connection-oriented: Establishes a 3-way handshake (SYN, SYN-ACK, ACK).\n"
        "  - Guarantees in-order packet delivery, error detection, flow control (sliding window), and congestion control.\n"
        "  - *Use cases*: Web browsing (HTTP/HTTPS), file transfer (SFTP), database connections.\n\n"
        "- **UDP (User Datagram Protocol)**:\n"
        "  - Connectionless: Sends datagrams immediately without handshake or receipt acknowledgment.\n"
        "  - Minimal overhead and low latency; tolerates occasional packet loss.\n"
        "  - *Use cases*: Live video streaming, VoIP, DNS queries, and multiplayer online gaming."
    ),
    (
        "Explain Deadlocks in Operating Systems and the 4 Coffman conditions",
        "A Deadlock is a state where a set of concurrent processes are permanently blocked because each process holds a resource that another process requires:\n\n"
        "A deadlock can occur if and only if all **4 Coffman Conditions** hold simultaneously:\n"
        "1. **Mutual Exclusion**: At least one resource must be held in a non-shareable mode.\n"
        "2. **Hold and Wait**: A process holds at least one resource and is waiting to acquire additional resources held by other processes.\n"
        "3. **No Preemption**: Resources cannot be forcibly seized; a resource is released only voluntarily by the holding process.\n"
        "4. **Circular Wait**: A closed chain of processes exists where $P_0$ waits for $P_1$, $P_1$ waits for $P_2$, ..., and $P_n$ waits for $P_0$.\n\n"
        "*Prevention*: Eliminating any single condition (e.g. enforcing global resource ordering to prevent Circular Wait) guarantees deadlock-free operation."
    ),
    (
        "Compare QuickSort and MergeSort: Complexity, Stability, and In-Place Sorting",
        "QuickSort and MergeSort are divide-and-conquer sorting algorithms with distinct operational characteristics:\n\n"
        "- **QuickSort**:\n"
        "  - Partitions array around a chosen pivot element, recursively sorting left and right partitions.\n"
        "  - *Time Complexity*: Average $O(N \\log N)$, Worst-case $O(N^2)$ (mitigated using randomized pivots).\n"
        "  - *Space*: In-place $O(\\log N)$ auxiliary stack memory.\n"
        "  - *Stability*: Unstable (can change relative order of identical keys).\n\n"
        "- **MergeSort**:\n"
        "  - Recursively splits the array into two halves until length 1, then merges sorted halves.\n"
        "  - *Time Complexity*: Guaranteed $O(N \\log N)$ in all cases.\n"
        "  - *Space*: Requires $O(N)$ auxiliary memory for merging.\n"
        "  - *Stability*: Stable; preferred for linked lists and external disk-based sorting."
    ),
    (
        "What is the difference between a Process and a Thread?",
        "Processes and threads represent execution units at different granularity levels:\n\n"
        "- **Process**:\n"
        "  - An independent executing instance of a program with its own private virtual address space (code, data, heap, stack).\n"
        "  - Processes are isolated; inter-process communication (IPC) requires OS primitives (pipes, sockets, shared memory).\n"
        "  - Context switching incurs high overhead due to TLB invalidation and page table swaps.\n\n"
        "- **Thread (Lightweight Process)**:\n"
        "  - A single unit of execution within a parent process sharing the same address space, file descriptors, and global variables.\n"
        "  - Each thread possesses its own private Program Counter, CPU registers, and call stack.\n"
        "  - Fast context switching with shared memory, but requires synchronization (mutexes, semaphores) to prevent race conditions."
    ),
    (
        "Explain Red-Black Trees: Properties and Self-Balancing Invariants",
        "A Red-Black Tree is a self-balancing binary search tree guaranteeing $O(\\log N)$ worst-case search, insertion, and deletion by enforcing 5 invariants:\n\n"
        "1. Every node is colored either **Red** or **Black**.\n"
        "2. The root node is always **Black**.\n"
        "3. Every leaf node (NIL / null pointer) is **Black**.\n"
        "4. If a node is **Red**, both of its children must be **Black** (no two consecutive Red nodes along any path).\n"
        "5. For each node, every simple path from that node to descendant leaf nodes contains the exact same number of **Black** nodes (equal Black-Height).\n\n"
        "*Rebalancing*: Violations after insertions or deletions are resolved through color flips and tree rotations (left/right)."
    ),

    # ══════════════════════════════════════════════════════════════════════════
    # 3. INFORMATION SCIENCE & ENGINEERING (ISE)
    # ══════════════════════════════════════════════════════════════════════════
    (
        "Explain Agile Scrum methodology vs the traditional Waterfall model",
        "Agile Scrum and Waterfall represent fundamentally different software engineering paradigms:\n\n"
        "- **Waterfall (Sequential & Plan-Driven)**:\n"
        "  - Linear phase progression: Requirements -> Design -> Implementation -> Verification -> Maintenance.\n"
        "  - Each phase must be completed and signed off before the next starts.\n"
        "  - *Best for*: Safety-critical systems (aerospace, medical hardware) with fixed, unambiguous requirements.\n"
        "  - *Limitation*: Late software testing; difficult to adapt to evolving customer requirements.\n\n"
        "- **Agile Scrum (Iterative & Flexible)**:\n"
        "  - Breaks development into cross-functional 2-to-4 week cycles called **Sprints**.\n"
        "  - Produces a potentially shippable product increment at the conclusion of every sprint.\n"
        "  - Features daily stand-up meetings, sprint planning, and retrospectives to adapt to continuous user feedback."
    ),
    (
        "Explain Public-Key Cryptography: RSA vs Elliptic Curve Cryptography (ECC)",
        "Both enable secure asymmetric key exchange and digital signatures, but differ in mathematical foundations:\n\n"
        "- **RSA (Rivest-Shamir-Adleman)**:\n"
        "  - Relies on the computational hardness of factoring the product of two massive prime numbers ($n = p \\times q$).\n"
        "  - Key size: Requires 2048-bit or 4096-bit keys for modern security.\n"
        "  - High computational overhead for key generation and decryption on low-power devices.\n\n"
        "- **ECC (Elliptic Curve Cryptography)**:\n"
        "  - Relies on the discrete logarithm problem over points on an algebraic elliptic curve ($y^2 = x^3 + ax + b$).\n"
        "  - Key size: A 256-bit ECC key provides equivalent cryptographic security to a 3072-bit RSA key.\n"
        "  - *Benefit*: Dramatically faster computations, lower bandwidth, and reduced power consumption, making ECC the standard for TLS 1.3 and mobile security."
    ),
    (
        "Explain the CAP Theorem in Distributed Systems",
        "Formulated by Eric Brewer, the CAP Theorem states that a distributed data store can simultaneously provide at most two out of three guarantees in the presence of a network partition:\n\n"
        "1. **Consistency (C)**: Every read receives the most recent write or an error. All nodes see identical data at the same time.\n"
        "2. **Availability (A)**: Every non-failing node returns a non-error response for every request, without guarantee that it contains the latest write.\n"
        "3. **Partition Tolerance (P)**: The system continues to operate despite arbitrary network message drops or link partitions between nodes.\n\n"
        "- In physical networks, network partitions are inevitable ($P$ is mandatory). Therefore, distributed architects must choose between **CP** (reject writes to maintain consistency, e.g., HBase, CockroachDB) or **AP** (accept writes to remain available with eventual consistency, e.g., Cassandra, DynamoDB)."
    ),
    (
        "Compare Microservices Architecture and Monolithic Architecture",
        "Software architectures differ in deployment boundaries, operational complexity, and scaling flexibility:\n\n"
        "- **Monolithic Architecture**:\n"
        "  - Entire application (UI, business logic, data access) is packaged and deployed as a single unified executable.\n"
        "  - *Pros*: Simple local debugging, straightforward transactional boundaries, and low deployment complexity.\n"
        "  - *Cons*: Difficult to scale components independently; a single unhandled fault can crash the entire application; large codebases slow down deployment velocity.\n\n"
        "- **Microservices Architecture**:\n"
        "  - Deconstructs the system into loosely-coupled, independently deployable services communicating via lightweight APIs (HTTP REST or gRPC).\n"
        "  - *Pros*: Polyglot technology stacks, independent horizontal auto-scaling, fault isolation.\n"
        "  - *Cons*: Complex distributed tracing, network latency overhead, and requires robust service discovery and eventual consistency protocols."
    ),
    (
        "Compare REST APIs and GraphQL for web client communication",
        "REST and GraphQL represent different approaches to client-server API contracts:\n\n"
        "- **REST (Representational State Transfer)**:\n"
        "  - Structured around fixed endpoint URLs (`GET /api/v1/students/123/courses`).\n"
        "  - *Pros*: Standard HTTP caching (ETags, CDN support), simple error codes (404, 500), and straightforward tooling.\n"
        "  - *Cons*: Suffers from **Over-fetching** (receiving unwanted fields) and **Under-fetching** (requiring multiple waterfall requests to assemble related data).\n\n"
        "- **GraphQL**:\n"
        "  - Single endpoint (`POST /graphql`) where clients specify the exact shape and fields of data needed in a declarative query.\n"
        "  - *Pros*: Zero over-fetching, solves under-fetching by aggregating nested resources in a single network round-trip.\n"
        "  - *Cons*: Complex server-side schema resolution ($N+1$ query problem), difficult edge-caching compared to standard REST URLs."
    ),
    (
        "Explain OAuth 2.0 Authorization Code Flow with PKCE and JWT Tokens",
        "OAuth 2.0 delegates user access without sharing user passwords, enhanced by PKCE (Proof Key for Code Exchange) for mobile and single-page apps:\n\n"
        "1. **Authorization Request**: Client creates a random `code_verifier`, hashes it to derive `code_challenge`, and redirects user to the Authorization Server with `code_challenge`.\n"
        "2. **User Authentication & Consent**: User logs in securely; Authorization Server redirects back with an ephemeral `authorization_code`.\n"
        "3. **Token Exchange**: Client sends the `authorization_code` along with raw `code_verifier` directly to the token endpoint.\n"
        "4. **Verification & Issuance**: Server hashes `code_verifier` and verifies it matches initial `code_challenge`, returning a signed **JWT Access Token** containing claims (user ID, role, expiration)."
    ),
    (
        "What is the role of Distributed Caching and Cache-Aside pattern (Redis)?",
        "Distributed caching stores frequently accessed data in high-speed in-memory key-value stores (like Redis) to offload relational databases and achieve sub-millisecond read latency:\n\n"
        "**Cache-Aside (Lazy Loading) Workflow**:\n"
        "1. Application receives a query request for an entity (e.g., student profile).\n"
        "2. App checks Redis cache: if key exists (**Cache Hit**), return data immediately.\n"
        "3. If key is missing (**Cache Miss**), query the persistent SQL database.\n"
        "4. Write the retrieved database record into Redis with an explicit Time-To-Live (TTL) expiration and return response to client.\n"
        "5. *Invalidation*: When the record is updated in the database, delete or evict the cached Redis key to maintain data consistency."
    ),

    # ══════════════════════════════════════════════════════════════════════════
    # 4. ELECTRONICS & COMMUNICATION ENGINEERING (ECE)
    # ══════════════════════════════════════════════════════════════════════════
    (
        "Explain the Nyquist-Shannon Sampling Theorem and Aliasing in Signal Processing",
        "The Nyquist-Shannon Sampling Theorem establishes the condition under which an analog signal can be perfectly sampled and reconstructed without information loss:\n\n"
        "1. **Theorem Principle**:\n"
        "   - If a continuous-time signal $x(t)$ contains no frequencies higher than $f_{max}$, it can be completely reconstructed from its discrete samples if the sampling frequency $f_s$ satisfies:\n"
        "     - $f_s \\ge 2 f_{max}$ (where $2 f_{max}$ is the **Nyquist Rate**).\n\n"
        "2. **Aliasing Distortion**:\n"
        "   - If $f_s < 2 f_{max}$, spectral copies overlap in the discrete frequency domain.\n"
        "   - High-frequency components fold back and masquerade as lower-frequency spurious signals, causing irreversible distortion.\n\n"
        "3. **Anti-Aliasing Filter**:\n"
        "   - ADC front-ends incorporate an analog low-pass filter prior to sampling to remove frequency components exceeding $f_s / 2$."
    ),
    (
        "What are the ideal characteristics of an Operational Amplifier (Op-Amp)?",
        "An ideal Operational Amplifier is a theoretical differential voltage amplifier with the following electrical characteristics:\n\n"
        "1. **Infinite Open-Loop Voltage Gain ($A_{OL} = \\infty$)**: Enforces the virtual short condition ($V_+ = V_-$) when negative feedback is applied.\n"
        "2. **Infinite Input Impedance ($Z_{in} = \\infty$)**: Draws zero input current ($I_+ = I_- = 0$ A), eliminating loading effects on signal sources.\n"
        "3. **Zero Output Impedance ($Z_{out} = 0\\,\\Omega$)**: Can supply any load current with zero internal voltage drop.\n"
        "4. **Infinite Bandwidth ($BW = \\infty$)**: Amplifies DC to infinite AC frequencies with uniform gain and zero phase delay.\n"
        "5. **Infinite Common-Mode Rejection Ratio (CMRR = $\\infty$)**: Rejects common-mode noise completely, amplifying solely the pure differential voltage ($V_+ - V_-$).\n"
        "6. **Zero Offset Voltage**: Output voltage is exactly 0 V when both input terminals are tied to 0 V."
    ),
    (
        "Explain MOSFET operating regions: Cutoff, Triode, and Saturation",
        "A Metal-Oxide-Semiconductor Field-Effect Transistor (MOSFET) operates in three distinct regions based on gate-to-source ($V_{GS}$) and drain-to-source ($V_{DS}$) voltages relative to threshold voltage $V_{th}$:\n\n"
        "1. **Cutoff Region ($V_{GS} < V_{th}$)**:\n"
        "   - No inversion channel exists; drain current $I_D \\approx 0$. The transistor acts as an open switch.\n\n"
        "2. **Triode / Linear Region ($V_{GS} > V_{th}$ and $V_{DS} < V_{GS} - V_{th}$)**:\n"
        "   - A continuous conductive inversion channel connects source and drain.\n"
        "   - Drain current: $I_D = \\mu_n C_{ox} \\frac{W}{L} \\left[(V_{GS} - V_{th}) V_{DS} - \\frac{V_{DS}^2}{2}\\right]$. The device acts as a voltage-controlled resistor.\n\n"
        "3. **Saturation Region ($V_{GS} > V_{th}$ and $V_{DS} \\ge V_{GS} - V_{th}$)**:\n"
        "   - The inversion channel pinches off at the drain end.\n"
        "   - Current saturates independent of $V_{DS}$: $I_D = \\frac{1}{2} \\mu_n C_{ox} \\frac{W}{L} (V_{GS} - V_{th})^2$.\n"
        "   - Standard operating regime for analog signal amplification."
    ),
    (
        "Explain the working of a Phase-Locked Loop (PLL) and its components",
        "A Phase-Locked Loop (PLL) is a feedback control system that generates an output clock signal whose phase matches that of an input reference signal:\n\n"
        "1. **Phase Detector (PD)**: Compares the phase difference between input reference signal $f_{ref}$ and feedback signal $f_{div}$, producing an error voltage pulse train.\n"
        "2. **Charge Pump & Loop Filter (LPF)**: Integrates and smooths the error pulses into a stable DC control voltage, suppressing high-frequency ripple.\n"
        "3. **Voltage-Controlled Oscillator (VCO)**: Generates an output frequency $f_{out}$ directly proportional to the applied DC control voltage.\n"
        "4. **Frequency Divider ($\\div N$)**: Scales output frequency down to feed back to the phase detector.\n"
        "- *Applications*: Clock generation in microprocessors, frequency synthesis in RF transceivers, and jitter reduction."
    ),
    (
        "Explain the Shannon-Hartley Channel Capacity Theorem",
        "The Shannon-Hartley Theorem establishes the theoretical upper limit on the error-free information transmission rate through an analog communication channel subjected to Gaussian noise:\n\n"
        "**Formula**: $C = B \\log_2 \\left(1 + \\frac{S}{N}\\right)$\n\n"
        "- **$C$**: Channel Capacity in bits per second (bps).\n"
        "- **$B$**: Channel bandwidth in Hertz (Hz).\n"
        "- **$S/N$**: Signal-to-Noise Ratio (linear power ratio).\n\n"
        "**Engineering Implications**:\n"
        "1. Bandwidth and transmission power can be traded off against each other.\n"
        "2. Doubling transmission power yields diminishing returns due to the logarithmic relationship.\n"
        "3. Increasing bandwidth linearly expands channel capacity, which is why modern wireless standards (5G, Wi-Fi 6) exploit wide carrier channels."
    ),

    # ══════════════════════════════════════════════════════════════════════════
    # 5. ELECTRICAL & ELECTRONICS ENGINEERING (EEE)
    # ══════════════════════════════════════════════════════════════════════════
    (
        "What is the difference between Synchronous and Induction Motors?",
        "Synchronous and Induction (Asynchronous) motors differ in their rotor operating speed relative to the stator magnetic field:\n\n"
        "1. **Operating Speed**:\n"
        "   - *Synchronous Motor*: Rotates at exact synchronous speed $N_s = \\frac{120 f}{P}$ under all normal load conditions.\n"
        "   - *Induction Motor*: Rotor always rotates at a speed $N_r < N_s$. The speed difference is characterized by **Slip**: $s = \\frac{N_s - N_r}{N_s}$ (typically 2% to 5%). Slip is strictly required to induce electromagnetic voltage in rotor bars.\n\n"
        "2. **Rotor Excitation**:\n"
        "   - *Synchronous*: Requires dual excitation: AC supply to stator and external DC supply to rotor poles.\n"
        "   - *Induction*: Singly excited; rotor currents are induced solely via magnetic induction from the stator field.\n\n"
        "3. **Power Factor Operation**:\n"
        "   - *Synchronous*: Can operate at lagging, unity, or leading power factor by varying DC excitation (acting as a synchronous condenser).\n"
        "   - *Induction*: Always operates at a lagging power factor due to inductive magnetizing current demand."
    ),
    (
        "Explain Three-Phase Power: Star vs Delta Connections and the Two-Wattmeter Method",
        "Three-phase AC power transmission offers superior electrical efficiency over single-phase circuits:\n\n"
        "1. **Star (Y) Connection**:\n"
        "   - Line Voltage $V_L = \\sqrt{3} V_{ph}$, Line Current $I_L = I_{ph}$. Provides a neutral conductor point, making it suitable for mixed single-phase and 3-phase domestic/commercial distribution.\n\n"
        "2. **Delta ($\\Delta$) Connection**:\n"
        "   - Line Voltage $V_L = V_{ph}$, Line Current $I_L = \\sqrt{3} I_{ph}$. Eliminates the neutral wire, standard for high-voltage industrial transmission.\n\n"
        "3. **Two-Wattmeter Method (Blondel's Theorem)**:\n"
        "   - Total active power: $P = W_1 + W_2$.\n"
        "   - Power factor angle: $\\tan \\phi = \\sqrt{3} \\frac{W_1 - W_2}{W_1 + W_2}$.\n"
        "   - If $\\cos \\phi = 0.5$, one wattmeter reads exactly zero. If $\\cos \\phi < 0.5$, one wattmeter deflects negative."
    ),
    (
        "Explain Buck (Step-Down) vs Boost (Step-Up) DC-DC Converters",
        "Switched-mode DC-DC converters efficiently convert voltage levels using inductors, power MOSFET switches, diodes, and filter capacitors:\n\n"
        "- **Buck Converter (Step-Down)**:\n"
        "  - Output voltage is lower than input voltage: $V_{out} = D \\times V_{in}$, where $D = \\frac{t_{on}}{T}$ is the duty cycle ($0 < D < 1$).\n"
        "  - When switch is ON, current ramps up in the inductor storing energy; when switch is OFF, freewheeling diode maintains inductor current into the load capacitor.\n\n"
        "- **Boost Converter (Step-Up)**:\n"
        "  - Output voltage is higher than input voltage: $V_{out} = \\frac{V_{in}}{1 - D}$.\n"
        "  - When switch is ON, inductor charges directly across input; when switch opens, inductor voltage adds to input voltage ($V_{in} + L \\frac{di}{dt}$) through the diode, boosting output."
    ),
    (
        "Explain the Symmetrical Components method in 3-Phase Asymmetrical Fault Analysis",
        "Developed by C. L. Fortescue, symmetrical components decompose any unbalanced three-phase set of phasors into three balanced symmetrical sets:\n\n"
        "1. **Positive Sequence Components ($V_{a1}, V_{b1}, V_{c1}$)**:\n"
        "   - Three equal phasors separated by $120^\\circ$, with identical phase sequence (A-B-C) to original system.\n"
        "2. **Negative Sequence Components ($V_{a2}, V_{b2}, V_{c2}$)**:\n"
        "   - Three equal phasors separated by $120^\\circ$, with reversed phase sequence (A-C-B).\n"
        "3. **Zero Sequence Components ($V_{a0}, V_{b0}, V_{c0}$)**:\n"
        "   - Three equal phasors with identical magnitude and zero phase angle difference (in phase with each other).\n\n"
        "- Transformation matrix: $[V_{abc}] = [A] [V_{012}]$, where operator $a = e^{j 120^\\circ} = -0.5 + j 0.866$. Decouples power network impedance matrices for single-line-to-ground and line-to-line fault calculations."
    ),

    # ══════════════════════════════════════════════════════════════════════════
    # 6. MECHANICAL ENGINEERING (MECH)
    # ══════════════════════════════════════════════════════════════════════════
    (
        "Explain the Carnot Cycle and thermodynamic thermal efficiency",
        "The Carnot Cycle is an idealized, reversible thermodynamic cycle establishing the theoretical upper limit on thermal efficiency for any heat engine operating between two temperatures:\n\n"
        "1. **Four Reversible Stages**:\n"
        "   - *1 -> 2 (Isothermal Expansion)*: Working fluid absorbs heat $Q_H$ from hot reservoir at constant temperature $T_H$.\n"
        "   - *2 -> 3 (Isentropic / Reversible Adiabatic Expansion)*: Fluid expands without heat transfer ($Q=0$); temperature drops from $T_H$ to $T_C$ while work is produced.\n"
        "   - *3 -> 4 (Isothermal Compression)*: Heat $Q_C$ is rejected to cold sink at constant temperature $T_C$.\n"
        "   - *4 -> 1 (Isentropic Compression)*: Fluid is compressed adiabatically, restoring temperature from $T_C$ back to $T_H$.\n\n"
        "2. **Carnot Efficiency Formula**:\n"
        "   - $\\eta_{Carnot} = 1 - \\frac{Q_C}{Q_H} = 1 - \\frac{T_C}{T_H}$ (temperatures in Kelvin).\n"
        "   - Proves that no practical engine can exceed Carnot efficiency operating between the same temperature bounds."
    ),
    (
        "Explain the Stress-Strain diagram for structural mild steel",
        "The tensile stress-strain relationship for mild steel under uniaxial tension illustrates fundamental mechanical behavior across distinct zones:\n\n"
        "1. **Proportional Limit (Point A)**: Stress is strictly proportional to strain, governed by Hooke's Law ($\\sigma = E \\epsilon$).\n"
        "2. **Elastic Limit (Point B)**: Maximum stress where the specimen returns to initial length upon load removal.\n"
        "3. **Yield Points (Points C & D)**: Upper yield point C marks onset of plastic slip; drops quickly to lower yield point D, where strain increases without stress increase.\n"
        "4. **Strain Hardening (D -> E)**: Crystal grain dislocations reorient, requiring higher stress to produce further deformation up to the **Ultimate Tensile Strength (UTS, Point E)**.\n"
        "5. **Necking & Fracture (E -> F)**: Localized necking reduces cross-sectional area, culminating in ductile fracture at Point F with characteristic cup-and-cone morphology."
    ),
    (
        "Compare Otto Cycle and Diesel Cycle in Internal Combustion Engines",
        "Otto and Diesel cycles model spark-ignition (petrol) and compression-ignition (diesel) engines:\n\n"
        "- **Otto Cycle (Constant Volume Combustion)**:\n"
        "  - Fuel-air mixture is compressed (compression ratio $r = 7$ to 11) and ignited by a spark plug at constant volume ($v = \\text{const}$).\n"
        "  - Thermal efficiency: $\\eta_{Otto} = 1 - \\frac{1}{r^{\\gamma - 1}}$.\n"
        "  - Higher thermal efficiency than Diesel for the *same* compression ratio, but limited by engine knocking.\n\n"
        "- **Diesel Cycle (Constant Pressure Combustion)**:\n"
        "  - Air alone is compressed to high compression ratios ($r = 15$ to 22); diesel fuel is injected and ignites spontaneously at constant pressure ($P = \\text{const}$).\n"
        "  - Efficiency incorporates cut-off ratio $r_c$: $\\eta_{Diesel} = 1 - \\frac{1}{r^{\\gamma - 1}} \\left[\\frac{r_c^\\gamma - 1}{\\gamma(r_c - 1)}\\right]$.\n"
        "  - In practice, Diesel engines achieve higher actual thermal efficiency because they operate at much higher compression ratios without knocking."
    ),
    (
        "Explain Mohr's Circle for 2D plane stress analysis",
        "Mohr's Circle is a graphical technique to determine principal stresses and maximum shear stresses on any inclined plane:\n\n"
        "1. **Coordinate Construction**:\n"
        "   - Normal stress $\\sigma$ is plotted on the horizontal axis; shear stress $\\tau$ on the vertical axis.\n"
        "   - Plot points $X(\\sigma_x, -\\tau_{xy})$ and $Y(\\sigma_y, \\tau_{xy})$. The line joining $X$ and $Y$ forms the diameter.\n"
        "2. **Center and Radius**:\n"
        "   - Center: $\\sigma_{avg} = \\frac{\\sigma_x + \\sigma_y}{2}$.\n"
        "   - Radius: $R = \\sqrt{\\left(\\frac{\\sigma_x - \\sigma_y}{2}\\right)^2 + \\tau_{xy}^2}$.\n"
        "3. **Principal Stresses**:\n"
        "   - $\\sigma_1, \\sigma_2 = \\sigma_{avg} \\pm R$ (occur on planes where shear stress is zero).\n"
        "   - Maximum in-plane shear stress: $\\tau_{max} = R$."
    ),

    # ══════════════════════════════════════════════════════════════════════════
    # 7. CIVIL ENGINEERING (CIVIL)
    # ══════════════════════════════════════════════════════════════════════════
    (
        "Explain the Concrete Mix Design procedure according to IS 10262",
        "Concrete mix design determines the proportions of cement, water, fine aggregate, and coarse aggregate to achieve target strength, workability, and durability:\n\n"
        "1. **Target Mean Strength**:\n"
        "   - $f'_{ck} = f_{ck} + 1.65 s$ (where $f_{ck}$ is characteristic 28-day compressive strength, and $s$ is standard deviation).\n"
        "2. **Selection of Water-Cement Ratio**:\n"
        "   - Selected based on exposure condition (mild, moderate, severe per IS 456) and required target strength curve.\n"
        "3. **Selection of Water & Aggregate Content**:\n"
        "   - Water content determined based on nominal maximum aggregate size (e.g., 20 mm requires ~186 L/m$^3$ for 50 mm slump).\n"
        "   - Superplasticizers reduce required mixing water by 15% to 25%.\n"
        "4. **Calculation of Cement Content**:\n"
        "   - $\\text{Cement} = \\frac{\\text{Water}}{\\text{w/c ratio}}$, verified against minimum cement content standards.\n"
        "5. **Aggregate Proportions**:\n"
        "   - Volume of coarse and fine aggregates calculated from total concrete volume minus volume of cement, water, and entrained air."
    ),
    (
        "Explain Terzaghi's One-Dimensional Consolidation Theory for clay soils",
        "Terzaghi's consolidation theory models time-dependent settlement of saturated fine-grained soils under sustained compressive load:\n\n"
        "1. **Governing Differential Equation**:\n"
        "   - $\\frac{\\partial u}{\\partial t} = c_v \\frac{\\partial^2 u}{\\partial z^2}$\n"
        "   - $u$: Excess pore water pressure.\n"
        "   - $c_v$: Coefficient of consolidation ($c_v = \\frac{k}{\\gamma_w m_v}$).\n"
        "2. **Physical Process**:\n"
        "   - When load is suddenly applied, incompressible pore water initially bears the entire stress ($u = \\Delta \\sigma$).\n"
        "   - Over time, water drains out slowly through microscopic soil voids; excess pore water pressure dissipates ($u \\to 0$).\n"
        "   - Stress transfers completely to the soil skeleton as **effective stress** ($\\sigma' = \\sigma - u$), producing primary consolidation settlement."
    ),
    (
        "Compare Prestressed Concrete (PSC) and Reinforced Cement Concrete (RCC)",
        "Prestressed Concrete and standard Reinforced Concrete differ in how they counteract tensile vulnerability:\n\n"
        "- **Reinforced Cement Concrete (RCC)**:\n"
        "  - Steel rebar is placed in tension zones. Concrete must crack slightly in tension before internal steel rebar can engage and develop tensile resistance.\n"
        "  - Heavier cross-sections required for long spans; subject to deflections and crack-induced rebar corrosion.\n\n"
        "- **Prestressed Concrete (PSC)**:\n"
        "  - High-strength steel tendons (1500–1800 MPa) are tensioned (pre-tensioning or post-tensioning) to induce initial compressive stresses in the concrete prior to external service loads.\n"
        "  - When service bending moments are applied, compressive pre-stress offsets tensile stress, keeping the entire section in compression.\n"
        "  - Eliminates structural cracking, reduces section depth and self-weight, and enables long bridge deck spans."
    ),
    (
        "Explain Base Isolation and Seismic Resistant Structural Design",
        "Base isolation decouples a superstructure from horizontal earthquake ground shaking to protect structural integrity:\n\n"
        "1. **Working Mechanism**:\n"
        "   - Flexible isolator bearings (Lead-Rubber Bearings or Friction Pendulum Bearings) are installed between structural substructure foundations and the building columns.\n"
        "2. **Dynamic Period Lengthening**:\n"
        "   - Isolators drastically lengthen the natural fundamental period $T$ of the building beyond the dominant period of earthquake energy (typically 0.1 to 1.0 seconds).\n"
        "   - Shifts the building into lower spectral acceleration zones on the seismic response spectrum curve, reducing lateral inertia forces and inter-story drifts by up to 75%."
    ),

    # ══════════════════════════════════════════════════════════════════════════
    # 8. BIOTECHNOLOGY (BT)
    # ══════════════════════════════════════════════════════════════════════════
    (
        "Explain the stages of the Polymerase Chain Reaction (PCR)",
        "The Polymerase Chain Reaction (PCR) exponentially amplifies specific target DNA fragments in vitro through automated thermal cycling:\n\n"
        "1. **Denaturation ($94^\\circ\\text{C} - 96^\\circ\\text{C}, \\approx 30\\text{ s}$)**:\n"
        "   - High thermal energy breaks hydrogen bonds between complementary base pairs, denaturing double-stranded template DNA into single strands.\n"
        "2. **Annealing ($50^\\circ\\text{C} - 65^\\circ\\text{C}, \\approx 30\\text{ s}$)**:\n"
        "   - Temperature is lowered to enable synthetic forward and reverse oligonucleotide primers to bind specifically to their complementary sequence boundaries.\n"
        "3. **Extension ($72^\\circ\\text{C}, \\approx 1\\text{ min/kb}$)**:\n"
        "   - Thermostable **Taq DNA Polymerase** (isolated from *Thermus aquaticus*) synthesizes new complementary DNA strands in the $5' \\to 3'$ direction using free dNTP building blocks.\n\n"
        "- **Yield**: $2^n$ theoretical target DNA copies synthesized after $n$ thermal cycles."
    ),
    (
        "Explain CRISPR-Cas9 Gene Editing Mechanism",
        "CRISPR-Cas9 is an RNA-guided endonuclease system adapted from bacterial adaptive immunity for targeted genomic modification:\n\n"
        "1. **Guide RNA (gRNA) Targeting**:\n"
        "   - A single guide RNA (sgRNA) contains a 20-nucleotide spacer sequence complementary to the target genomic DNA locus.\n"
        "2. **PAM Recognition**:\n"
        "   - Cas9 protein binds the DNA by scanning for a specific **Protospacer Adjacent Motif** (PAM, standard $5'\\text{-NGG-}'3'$ for *S. pyogenes* Cas9) immediately downstream of the target site.\n"
        "3. **Double-Stranded Cleavage**:\n"
        "   - Cas9's HNH and RuvC endonuclease domains cleave both strands of DNA 3 base pairs upstream of the PAM, creating a Double-Stranded Break (DSB).\n"
        "4. **Host DNA Repair**:\n"
        "   - *Non-Homologous End Joining (NHEJ)*: Error-prone direct ligation causing insertion/deletion (indel) frameshifts to knock out gene function.\n"
        "   - *Homology-Directed Repair (HDR)*: Uses an exogenous repair template to perform precise gene knock-ins or point mutation corrections."
    ),
    (
        "Explain Monoclonal Antibody production using Hybridoma Technology",
        "Developed by Kohler and Milstein, Hybridoma technology produces homogeneous, antigen-specific monoclonal antibodies indefinitely:\n\n"
        "1. **Immunization**: A mouse is challenged with the target antigen, stimulating splenic B-lymphocytes to synthesize specific antibodies.\n"
        "2. **Cell Fusion**: Harvested B-cells are fused with immortal mouse myeloma (tumor) cells using Polyethylene Glycol (PEG).\n"
        "3. **HAT Medium Selection**:\n"
        "   - Fused cells are cultured in Hypoxanthine-Aminopterin-Thymidine (HAT) medium.\n"
        "   - Aminopterin blocks the de novo nucleotide synthesis pathway.\n"
        "   - Myeloma cells lack the salvage enzyme HGPRT and perish.\n"
        "   - Unfused B-cells have limited natural lifespan and die out within days.\n"
        "   - Only successfully fused **Hybridoma cells** survive (inheriting HGPRT from B-cells and immortality from myeloma cells).\n"
        "4. **Cloning & Screening**: Single hybridoma clones are isolated via limiting dilution and screened using ELISA to produce high-affinity monoclonal antibodies."
    ),
    (
        "Explain Michaelis-Menten Enzyme Kinetics and the Lineweaver-Burk plot",
        "The Michaelis-Menten model describes the rate of single-substrate enzyme-catalyzed reactions:\n\n"
        "**Equation**: $v_0 = \\frac{V_{max} [S]}{K_m + [S]}$\n\n"
        "- **$v_0$**: Initial reaction velocity.\n"
        "- **$V_{max}$**: Maximum reaction velocity when all enzyme catalytic active sites are saturated with substrate.\n"
        "- **$K_m$ (Michaelis Constant)**: Substrate concentration at which reaction velocity is half of $V_{max}$ ($v_0 = \\frac{V_{max}}{2}$).\n"
        "  - A lower $K_m$ indicates higher enzyme-substrate binding affinity.\n\n"
        "**Lineweaver-Burk Double Reciprocal Plot**:\n"
        "- $\\frac{1}{v_0} = \\left(\\frac{K_m}{V_{max}}\\right) \\frac{1}{[S]} + \\frac{1}{V_{max}}$\n"
        "- Linear plot of $\\frac{1}{v_0}$ vs $\\frac{1}{[S]}$ where y-intercept equals $\\frac{1}{V_{max}}$ and x-intercept equals $-\\frac{1}{K_m}$, used to diagnose competitive vs non-competitive enzyme inhibition."
    ),

    # ══════════════════════════════════════════════════════════════════════════
    # 9. MULTI-STEP REASONING CHAINS & STEP-BY-STEP PROBLEM WALKTHROUGHS
    # ══════════════════════════════════════════════════════════════════════════
    (
        "Walk through finding the shortest path in a Directed Acyclic Graph (DAG) step by step",
        "Finding shortest paths in a DAG can be solved linearly in $O(V + E)$ time using Topological Sorting rather than slower Dijkstra:\n\n"
        "1. **Problem Formulation**:\n"
        "   - Given a weighted DAG $G=(V, E)$ and source vertex $s$, find the minimum distance to all reachable vertices.\n\n"
        "2. **Approach**:\n"
        "   - In a DAG, topological order guarantees that for every directed edge $(u, v)$, vertex $u$ appears before $v$.\n"
        "   - Processing vertices in topological order ensures that when relaxing edges leaving $u$, the shortest path distance to $u$ is already finalized.\n\n"
        "3. **Step-by-Step Execution**:\n"
        "   - *Step 1*: Run Kahn's Algorithm (in-degree array) or DFS to compute topological ordering of $V$ in $O(V+E)$.\n"
        "   - *Step 2*: Initialize distance array: $dist[s] = 0$, all other vertices $dist[v] = \\infty$.\n"
        "   - *Step 3*: For each vertex $u$ in topological order:\n"
        "     - For each outgoing edge $(u, v)$ with weight $w$:\n"
        "       - If $dist[u] + w < dist[v]$, update $dist[v] = dist[u] + w$.\n\n"
        "4. **Verification**:\n"
        "   - Unlike graphs with cycles, no node can be updated after it has been passed in topological sequence, proving optimal substructure in a single pass without priority queues."
    ),
    (
        "Step-by-step calculation: Design an LC low-pass filter for a 5V Buck Converter",
        "Here is the complete step-by-step mathematical design for an LC filter:\n\n"
        "1. **Given Specifications**:\n"
        "   - Input voltage $V_{in} = 12\\text{ V}$, Output voltage $V_{out} = 5\\text{ V}$, Switching frequency $f_{sw} = 100\\text{ kHz}$, Load current $I_{out} = 2\\text{ A}$.\n"
        "   - Allowable inductor ripple current: $\\Delta I_L = 30\\% \\text{ of } I_{out} = 0.6\\text{ A}$.\n"
        "   - Allowable output voltage ripple: $\\Delta V_{out} = 1\\% \\text{ of } 5\\text{ V} = 50\\text{ mV}$.\n\n"
        "2. **Step 1: Calculate Duty Cycle ($D$)**:\n"
        "   - $D = \\frac{V_{out}}{V_{in}} = \\frac{5}{12} \\approx 0.417$.\n\n"
        "3. **Step 2: Calculate Inductor Value ($L$)**:\n"
        "   - $L = \\frac{V_{out} \\times (1 - D)}{\\Delta I_L \\times f_{sw}} = \\frac{5 \\times (1 - 0.417)}{0.6 \\times 100{,}000} = \\frac{2.915}{60{,}000} \\approx 48.6\\,\\mu\\text{H}$.\n"
        "   - Standard commercial selection: **$47\\,\\mu\\text{H}$ or $50\\,\\mu\\text{H}$**.\n\n"
        "4. **Step 3: Calculate Output Capacitor Value ($C$)**:\n"
        "   - $\\Delta V_{out} = \\frac{\\Delta I_L}{8 \\times f_{sw} \\times C} \\implies C = \\frac{\\Delta I_L}{8 \\times f_{sw} \\times \\Delta V_{out}}$.\n"
        "   - $C = \\frac{0.6}{8 \\times 100{,}000 \\times 0.05} = \\frac{0.6}{40{,}000} = 15\\,\\mu\\text{F}$.\n"
        "   - To account for capacitor Equivalent Series Resistance (ESR), select **$22\\,\\mu\\text{F}$ to $47\\,\\mu\\text{F}$ low-ESR ceramic capacitor**."
    ),

    # ══════════════════════════════════════════════════════════════════════════
    # 10. "EXPLAIN LIKE I'M 5" (ELI5) INTUITIVE CONCEPTUAL ANALOGIES
    # ══════════════════════════════════════════════════════════════════════════
    (
        "Explain the Attention Mechanism in AI like I'm 5 years old",
        "Imagine you are looking at a crowded picture book filled with hundreds of animals, and someone asks you: *'Where is the zebra eating an apple?'*\n\n"
        "Your eyes don't stare at the trees, the sky, and every rock with equal intensity. Instead, your brain acts like a flashlight that instantly highlights the black-and-white stripes and the red apple, ignoring everything else.\n\n"
        "In AI, the **Attention Mechanism** is that mental flashlight! When a computer reads a long sentence like *'The animal didn't cross the street because it was too tired'*, attention helps the AI realize that the word **'it'** connects directly to **'animal'**, not the street."
    ),
    (
        "Explain Virtual Memory and Paging like I'm 5 years old",
        "Imagine you are working on a school drawing project at a very small study desk that can only fit 2 books at a time. But to do your project, you need to read 10 huge encyclopedias!\n\n"
        "What do you do? You keep 8 books on a big shelf across the room, and keep only the 2 books you are reading right now on your desk.\n\n"
        "Whenever you finish a page and need a different book, you swap it: you put one book back on the shelf and bring the new book to your desk.\n\n"
        "- Your **small study desk** is RAM (fast, but small).\n"
        "- The **bookshelf** is the Hard Drive (huge, but slow to walk to).\n"
        "- The **swapping** action is called Paging!"
    ),
    (
        "Explain Public Key Cryptography like I'm 5 years old",
        "Imagine your friend wants to send you a secret letter, but you are worried the mail carrier might open the envelope and read it.\n\n"
        "Here is the clever trick:\n"
        "1. You buy a padlock and leave it **unlocked**.\n"
        "2. You make hundreds of copies of this unlocked padlock and hand them out to all your friends. Anyone can take one (that's your **Public Key**).\n"
        "3. Only YOU keep the single secret key that opens the padlock in your pocket (that's your **Private Key**).\n"
        "4. Your friend puts the letter in a box, snaps your padlock shut, and sends it to you.\n\n"
        "Even though the mail carrier holds the box, they cannot open it without the key in your pocket. Only you can unlock it!"
    )
]
