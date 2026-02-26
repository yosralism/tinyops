tinyops

An on-prem, Python-first Network Management System for large ISPs. Tinyops NMS focuses on reliable data collection from thousands of routers via SSH, Telnet, and SNMP, parsing outputs into structured data, and providing extensible workflows for inventory, notifications, and future AI-driven insights.


Key Goals

Reliable multi-protocol collectors with bastion/jump support.
Scheduled and ad-hoc job orchestration with isolated execution.
Parser pipeline producing structured facts and raw artifacts.
Secure user sessions, RBAC, and integrations (Telegram, email, Webex, SNMP traps).
Observability, CI/CD, documentation, and future topology/RAG capabilities.

Getting Started

Clone the repo and create a virtual environment.
Install base dependencies (to be added in requirements/ or pyproject.toml).
Review /docs for architecture details and /infra for deployment assets.