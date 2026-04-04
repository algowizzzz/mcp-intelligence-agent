# OSFI Guideline B-13: Technology and Cyber Risk Management

**Issuing Authority:** Office of the Superintendent of Financial Institutions Canada (OSFI)
**Effective Date:** January 1, 2024
**Applies To:** All federally regulated financial institutions (FRFIs), including banks, trust and loan companies, cooperative retail associations, insurance companies, and pension plans subject to OSFI oversight
**Legislative Authority:** Office of the Superintendent of Financial Institutions Act, R.S.C. 1985, c. 18 (3rd Supp.)
**Related Guidelines:** OSFI Guideline E-21 (Operational Risk and Resilience), OSFI Guideline B-10 (Third-Party Risk Management), OSFI Corporate Governance Guideline

---

## 1. Purpose and Scope

### 1.1 Purpose

This Guideline sets out OSFI's supervisory expectations for the management of technology and cyber risk at federally regulated financial institutions (FRFIs). It establishes a principles-based framework that reflects the nature, size, complexity, and risk profile of FRFIs while articulating minimum standards for governance, risk management, controls, and resilience in the areas of technology and cybersecurity.

Technology risk is the risk of adverse outcomes — financial loss, reputational damage, regulatory sanction, or operational disruption — resulting from the failure, inadequacy, or misuse of information systems, technology infrastructure, and related processes. Cyber risk is a subset of technology risk arising from deliberate, malicious, unauthorized, or accidental actions that exploit vulnerabilities in an institution's digital environment, potentially threatening the confidentiality, integrity, or availability of systems and data.

The scale and sophistication of cyber threats targeting financial institutions have escalated materially in recent years, including ransomware attacks, supply chain compromises, social engineering campaigns targeting employees, and nation-state sponsored intrusions. This Guideline reflects OSFI's assessment that robust and proactive technology and cyber risk management is a fundamental prerequisite for operational resilience and public confidence in Canada's financial system.

### 1.2 Scope of Application

This Guideline applies to all FRFIs as defined under applicable legislation, including:
- Federally regulated deposit-taking institutions under the Bank Act, Trust and Loan Companies Act, and Cooperative Credit Associations Act
- Federally regulated insurance companies and insurance holding companies under the Insurance Companies Act
- Federally regulated pension plans under the Pension Benefits Standards Act

OSFI applies proportionate expectations based on the nature, size, complexity, and risk profile of each FRFI. Smaller institutions with limited technology footprints may satisfy certain expectations through simplified processes, but the fundamental principles in this Guideline apply to all FRFIs. Foreign bank branches are subject to expectations aligned with their operational scope and domestic risk exposure.

---

## 2. Governance

### 2.1 Board of Directors Responsibilities

The Board of Directors bears ultimate responsibility for the oversight of technology and cyber risk as components of the institution's overall risk management framework. Board-level responsibilities include:

1. **Approving the technology and cyber risk appetite:** The Board must approve a written technology and cyber risk appetite statement that defines the institution's tolerance for technology failures, cybersecurity incidents, and technology-driven operational disruptions. The risk appetite must include quantitative metrics (e.g., maximum acceptable downtime for critical systems, maximum acceptable data loss in a recovery scenario) and qualitative thresholds.

2. **Oversight of the technology and cyber risk management framework:** The Board, through its Risk Committee (or equivalent), must receive regular reporting on the institution's technology and cyber risk posture, including material vulnerabilities, significant incidents, the status of the patch management program, emerging threat intelligence, and progress against the institution's technology strategic plan.

3. **Ensuring adequate resources:** The Board must satisfy itself that management has allocated sufficient financial, human, and technological resources to meet the institution's technology and cyber risk management obligations under this Guideline and applicable regulatory requirements.

4. **Horizon scanning and emerging risk oversight:** The Board must ensure that management has processes to identify and assess emerging technology risks, including threats arising from artificial intelligence, quantum computing, cloud adoption, and geopolitical cyber threats targeting financial services.

### 2.2 Senior Management Responsibilities

Senior management is accountable for the design, implementation, and ongoing operation of the technology and cyber risk management framework. Responsibilities include:

1. Developing, implementing, and maintaining technology and cyber risk management policies, procedures, and standards consistent with the Board-approved risk appetite;
2. Establishing clear ownership and accountability for technology and cyber risk across the three lines of defence;
3. Ensuring a qualified and experienced Chief Information Security Officer (CISO) or equivalent role is established with sufficient authority, resources, and independence to execute the security mandate;
4. Providing regular (at minimum quarterly) technology and cyber risk reporting to the Board, including key risk indicators (KRIs), material incident summaries, and results from vulnerability assessments and penetration tests;
5. Reviewing and approving the institution's technology strategic plan, ensuring it adequately addresses cyber resilience, legacy system risks, and cloud adoption governance.

### 2.3 Three Lines of Defence Model

FRFIs must implement the three-lines-of-defence model in the governance of technology and cyber risk:
- **First Line:** Business units, IT operations, and technology teams own and manage technology and cyber risk day-to-day, implementing controls and operating within the approved risk appetite.
- **Second Line:** The risk management function (including the CISO and enterprise risk management team) provides independent oversight, challenge, and assessment of the first line's risk management activities, develops enterprise-wide frameworks and policies, and reports independently to the Board.
- **Third Line:** Internal audit provides independent, objective assurance to the Board and Audit Committee on the design and operating effectiveness of technology and cyber risk controls, governance processes, and the three-lines structure itself.

---

## 3. Technology Risk Management

### 3.1 Technology Risk Appetite

FRFIs must establish and maintain a formal technology risk appetite framework that:
- Is approved by the Board of Directors and reviewed at least annually
- Defines specific, measurable risk tolerances for technology availability, data integrity, data confidentiality, and recovery capability
- Articulates maximum acceptable Recovery Time Objectives (RTO) and Recovery Point Objectives (RPO) for systems supporting critical business functions
- Includes metrics and indicators that allow management to monitor performance against risk appetite thresholds in near-real time
- Specifies escalation triggers and response actions when risk appetite thresholds are breached

The technology risk appetite must be integrated into the institution's broader enterprise risk appetite framework and must be consistent with the institution's Operational Risk Appetite and its Operational Resilience framework (as set out in OSFI Guideline E-21).

### 3.2 IT Asset Management

A comprehensive and current inventory of all technology assets is foundational to the effective management of technology and cyber risk. FRFIs must maintain a technology asset inventory that:

- Covers all hardware assets (servers, endpoints, network devices, storage, industrial control systems), software assets (applications, operating systems, middleware, databases), data assets (databases, data stores, data flows), and cloud service assets (IaaS, PaaS, SaaS subscriptions);
- Is maintained in a configuration management database (CMDB) or equivalent system that is updated in near-real time as assets are added, modified, or decommissioned;
- Classifies each asset by criticality, data sensitivity, regulatory relevance, and ownership;
- Identifies dependencies between technology assets and critical business processes and services;
- Provides the foundational input to the patch management program, vulnerability management program, and third-party risk management framework.

Institutions must conduct a formal asset inventory reconciliation at least semi-annually to verify accuracy and completeness.

### 3.3 Change Management

All material changes to technology assets — including infrastructure changes, application deployments, configuration changes, vendor upgrades, and cloud environment changes — must be managed through a formal change management process that includes:

1. **Change request and documentation:** All material changes must be formally documented, including the purpose, scope, potential risk impacts, rollback procedures, and testing requirements;
2. **Pre-implementation risk assessment:** A risk assessment must be completed for each material change, with higher-risk changes subject to enhanced review and approval by the Change Advisory Board (CAB) or equivalent governance body;
3. **Non-production testing:** All material changes must be tested in a non-production environment that sufficiently replicates the production environment. Security testing (including vulnerability scanning) must be performed on new or substantially modified applications before production deployment;
4. **Approval and authorization:** Changes must receive appropriate approval based on risk level — routine changes may follow an expedited process; significant or high-risk changes require senior management authorization;
5. **Post-implementation review:** A post-implementation review must be conducted for all significant changes to validate that the change achieved its intended purpose and did not introduce unintended risks or control gaps.

Emergency change procedures may allow expedited processing for urgent changes (including emergency security patches), but must still require documented justification, appropriate authorization, and a post-implementation review.

---

## 4. Cyber Risk Management

### 4.1 Cyber Risk Identification and Assessment

FRFIs must maintain a continuous and systematic process for identifying, assessing, and prioritizing cyber risks. This includes:

1. **Annual comprehensive cyber risk assessment:** A formal, enterprise-wide cyber risk assessment must be completed at least annually and updated when material changes occur in the threat landscape, the institution's technology environment, or its business operations. The assessment must identify critical assets and processes, evaluate threat actors and their capabilities, assess vulnerabilities in the institution's environment, and estimate the likelihood and potential impact of material cyber risk scenarios;

2. **Cyber threat intelligence:** FRFIs must maintain active participation in threat intelligence sharing communities, including the Financial Services Information Sharing and Analysis Center (FS-ISAC), the Canadian Centre for Cyber Security (CCCS), and OSFI's supervisory cyber intelligence briefings. Threat intelligence must be operationalized — translated into actionable defensive measures — within a defined timeframe;

3. **Crown jewels analysis:** Institutions must identify and maintain a register of their most critical and sensitive assets — including systems supporting critical business functions, core banking infrastructure, payment systems, and repositories of sensitive customer data — and apply enhanced protections proportionate to the risk;

4. **Attack surface management:** FRFIs must continuously monitor their external attack surface, including internet-exposed assets, cloud environments, and third-party digital integrations, to identify unauthorized or unmanaged exposure.

### 4.2 Cyber Controls

FRFIs must implement a layered set of technical and procedural cyber controls, including access management, identity governance, data protection, network security, endpoint security, and — as a central element of the control framework — a robust patch management program.

#### 4.2.1 Access Management and Identity Governance

- Multi-factor authentication (MFA) must be enforced for all privileged access, all remote access, and all access to critical systems and data repositories;
- The principle of least privilege must be applied to all user, system, and service accounts — access rights must be limited to the minimum necessary for the user's role;
- Privileged Access Management (PAM) controls must be implemented for all administrative and privileged accounts, including just-in-time access provisioning and session recording for high-privilege accounts;
- Formal access reviews must be conducted at least quarterly for privileged accounts and at least annually for all other accounts;
- Access rights must be promptly revoked upon employee departure or role change, with automated deprovisioning controls implemented for critical systems.

#### 4.2.2 Patch Management

Institutions must maintain a formal **patch management** program that covers all technology assets within the institution's inventory — including on-premises servers, endpoints, network infrastructure, cloud instances, and third-party software components. The **patch management** program is one of the most critical cyber controls and is a primary means of reducing the exploitable attack surface.

The **patch management** program must include the following elements:

- **Patch identification:** A formal process for monitoring security bulletins, vendor advisories, and threat intelligence sources (including the National Vulnerability Database (NVD), CCCS advisories, and vendor-specific security channels) to identify applicable patches in a timely manner;
- **Patch assessment and prioritization:** Each identified patch must be assessed for applicability to the institution's asset inventory and assigned a remediation priority based on the CVSS (Common Vulnerability Scoring System) base score, evidence of active exploitation, and asset criticality. Prioritization tiers and mandatory deployment timelines are as follows:

  | Patch Category | Definition | Mandatory Deployment Timeline |
  |---|---|---|
  | Emergency | Critical vulnerability with confirmed active exploitation (zero-day or in-the-wild exploitation) | **Within 72 hours** of patch release |
  | Critical | CVSS base score ≥ 9.0, or vendor-rated Critical | **Within 30 days** of patch release |
  | High | CVSS base score 7.0–8.9 | Within 60 days of patch release |
  | Medium | CVSS base score 4.0–6.9 | Within 90 days of patch release |
  | Low | CVSS base score < 4.0 | Within 180 days of patch release |

  Institutions must maintain a target of **95% or greater patch compliance** within the mandatory timelines for Critical and Emergency patches across all in-scope assets. Compliance rates below this threshold must be escalated to Senior Management with a formal remediation plan.

- **Emergency patch deployment:** Institutions must maintain a documented emergency patch management process that enables the deployment of emergency patches — those addressing actively exploited vulnerabilities — **within 72 hours** of patch release. The emergency process must include expedited testing procedures, pre-authorized approval pathways for critical systems, and a rollback plan in the event of deployment failures;
- **Exception management:** Where patches cannot be applied within mandatory timelines (e.g., due to compatibility issues, system criticality, or vendor support constraints), a formal risk acceptance process must be followed, including documentation of the compensating controls in place, time-bound remediation commitments, and escalation to Senior Management. Open exceptions must be reviewed monthly;
- **Patch compliance reporting:** Management must receive at least monthly reporting on patch management compliance rates, aged vulnerabilities, open exceptions, and remediation trends. The CISO must report patch management status to the Board Risk Committee at least quarterly.

#### 4.2.3 Network Security

- Network segmentation must be implemented to isolate critical systems and limit lateral movement in the event of a compromise. Production environments must be segmented from development, test, and administrative networks;
- Perimeter security controls — including next-generation firewalls, intrusion detection and prevention systems (IDS/IPS), and web application firewalls (WAF) — must be deployed and actively monitored;
- All sensitive data in transit must be encrypted using current cryptographic standards (minimum TLS 1.2; TLS 1.3 preferred for new implementations);
- Firewall rule sets and network access control lists must be reviewed at least semi-annually, and unauthorized or unnecessary rules must be removed promptly;
- DNS filtering and email security controls (including SPF, DKIM, DMARC) must be implemented to reduce phishing and malware delivery risks.

### 4.3 Vulnerability Management

FRFIs must implement a continuous vulnerability management program that:

- Performs automated vulnerability scanning of all technology assets in scope at least **monthly**, with critical systems scanned more frequently (at least weekly);
- Prioritizes remediation based on the combination of CVSS score, evidence of active exploitation, asset criticality, and network accessibility;
- Tracks all identified vulnerabilities through a centralized vulnerability management platform, with assigned owners, target remediation dates, and status tracking;
- Reports on aged vulnerabilities (those past their mandatory remediation timeline) to Senior Management at least quarterly, with a formal escalation process for vulnerabilities on critical systems that remain unpatched beyond mandatory timelines;
- Includes cloud environments, container workloads, and third-party software components (including open-source dependencies) in the scope of vulnerability scanning.

The vulnerability management program must be operationally integrated with the patch management program to ensure that identified vulnerabilities trigger timely patch assessment and remediation.

### 4.4 Penetration Testing

FRFIs must conduct **annual penetration tests** of their critical systems, applications, and network infrastructure by qualified, independent internal or external resources. The penetration testing program must:

- Cover external attack surfaces (internet-facing systems and applications), internal network environments, and — for D-SIBs and larger institutions — conduct red team exercises simulating sophisticated threat actor techniques;
- Use qualified assessors with recognized industry certifications (OSCP, CREST, or equivalent) and, for external assessors, demonstrate independence from the institution's security operations team;
- Be scoped based on the institution's current threat model and the results of the annual cyber risk assessment;
- Produce a formal written report documenting all findings, their severity, and recommended remediation actions;
- Track all penetration test findings through the vulnerability management program to remediation, with Senior Management oversight of critical findings.

D-SIBs must also conduct periodic threat-led penetration tests (TLPT), modeled on the TIBER-EU or equivalent framework, at least every three years.

---

## 5. Incident Response

### 5.1 Incident Response Framework

FRFIs must maintain a documented, tested cyber and technology incident response plan (IRP) that covers the full lifecycle of incident management:

1. **Detection and triage:** Automated detection capabilities (SIEM, EDR, IDS/IPS, user behaviour analytics) must be in place to identify indicators of compromise. Alert triage procedures must be defined, with escalation paths based on severity;
2. **Containment:** Procedures for containing an incident to limit further damage, including network isolation, account suspension, and disabling of compromised systems, must be pre-defined and executable within defined timeframes;
3. **Eradication and remediation:** Processes for removing malware, closing vulnerabilities, resetting compromised credentials, and applying applicable emergency patches;
4. **Recovery:** Procedures for restoring systems from clean backups, validating system integrity before returning to production, and confirming that threats have been fully eliminated;
5. **Post-incident review:** A formal post-incident review (PIR) or lessons-learned process must be conducted for all material incidents, with findings tracked to remediation and reported to the Board.

### 5.2 OSFI Reporting Requirements

FRFIs must notify OSFI promptly when they become aware of a material technology or cyber incident. For the purposes of this Guideline, a material incident includes any incident that:
- Results in significant disruption to critical business functions or services to customers
- Involves unauthorized access to, or exfiltration of, sensitive customer or business data
- Has potential systemic implications or may affect other FRFIs
- Attracts or is likely to attract significant media attention or reputational harm

Reporting timelines are as follows:
- **Initial notification:** Within **72 hours** of the FRFI becoming aware that a material incident has occurred or is underway. The initial notification need not contain a complete root cause analysis but must describe the nature and apparent scope of the incident, systems affected, and immediate containment actions taken;
- **Interim updates:** At regular intervals (as agreed with OSFI or as directed by OSFI) while the incident remains active or investigation is ongoing;
- **Final incident report:** Within **30 days** of the incident being resolved, providing a full root cause analysis, impact assessment, timeline, and description of remedial actions taken and planned.

### 5.3 Incident Severity Classification

| Severity Level | Definition | Internal Response Time |
|---|---|---|
| Critical | Significant impact to critical operations, confirmed data breach of material scope, or systemic threat | Incident Response Team convened within **1 hour** |
| High | Significant operational disruption, confirmed intrusion or unauthorized access, contained data exposure | Incident Response Team convened within **4 hours** |
| Medium | Limited operational impact, suspected intrusion or anomalous access, investigation required | Response team engaged within **24 hours** |
| Low | Minor technical incident, no confirmed customer impact or data exposure | Managed within standard IT operations within **5 business days** |

All Critical and High incidents must be escalated to the CISO and Senior Management regardless of time of day or day of week.

---

## 6. Third-Party Technology Risk

### 6.1 Due Diligence Prior to Engagement

Before engaging any third-party technology or cloud service provider that will have access to the institution's systems, data, or networks, FRFIs must conduct risk-based due diligence that assesses:
- The provider's technology and cyber risk management practices (including their own patch management program), security certifications (SOC 2 Type II, ISO 27001, CSA STAR), and history of material cyber incidents;
- Data residency, data sovereignty, and data handling practices, including whether customer data will be stored or processed outside Canada;
- Business continuity and disaster recovery capabilities, including RTO and RPO commitments for services provided to the FRFI;
- Incident notification obligations — the provider must contractually commit to notify the FRFI within **24 hours** (or sooner) of any incident affecting the FRFI's systems or data;
- Audit and inspection rights, including the right to conduct or commission independent security assessments of the provider's environment.

### 6.2 Ongoing Third-Party Monitoring

FRFIs must continuously monitor the technology and cyber risk profile of material third-party providers throughout the relationship:
- Annual reassessment of critical providers, including review of updated SOC 2 reports, ISO certificates, or equivalent;
- Monitoring of provider security bulletins, vulnerability disclosures, and patch management communications for shared infrastructure or software components;
- Annual review of contractual terms to ensure they remain aligned with current OSFI expectations and the institution's risk appetite;
- Tracking and monitoring of provider incidents and regulatory actions.

### 6.3 Concentration Risk and Exit Planning

FRFIs must identify and manage concentration risk arising from over-reliance on a single technology provider or a small group of providers for critical services (e.g., core banking platform, cloud infrastructure). Institutions must maintain documented exit strategies and transition plans for all critical third-party technology services, tested and updated at least every two years.

---

## 7. Business Continuity and Disaster Recovery

### 7.1 BCP and DR Requirements

FRFIs must maintain robust Business Continuity Plans (BCPs) and Disaster Recovery (DR) plans for all critical technology systems and services. These plans must:

- Define Recovery Time Objectives (RTO) and Recovery Point Objectives (RPO) for each critical system and business process, approved by Senior Management and consistent with the technology risk appetite;
- Include documented, tested procedures for recovering critical systems from secure, tested backups;
- Cover scenarios including ransomware attacks (requiring recovery from clean, air-gapped backups), major data centre outages, widespread infrastructure failure, and key-person dependency;
- Be tested at least **annually** through full or partial failover exercises, tabletop simulations, and, for critical systems, live failover testing to the DR environment.

### 7.2 Cloud Resilience

Institutions hosting critical workloads in public cloud environments must:
- Implement multi-region or multi-availability-zone architectures for critical applications to avoid single-point-of-failure dependencies;
- Maintain documented and tested cloud exit strategies, including the ability to migrate critical workloads to an alternative provider or on-premises environment within defined timeframes;
- Ensure that data encryption, access controls, and patch management practices in cloud environments meet the same standards as those applied in on-premises environments.

---

## 8. Regulatory Expectations Summary

The following table summarizes the key expectations and timelines established by this Guideline:

| Domain | Key Expectation | Key Timeframe |
|---|---|---|
| Governance | Board-approved technology and cyber risk appetite | Annual review |
| Asset Management | Comprehensive, current inventory (CMDB or equivalent) | Semi-annual reconciliation |
| Patch Management — Emergency | Emergency patches for actively exploited vulnerabilities | **Within 72 hours** of release |
| Patch Management — Critical | Critical patches (CVSS ≥ 9.0 or vendor-rated Critical) | **Within 30 days** of release |
| Patch Management — High | High severity patches (CVSS 7.0–8.9) | Within 60 days of release |
| Patch Compliance Target | 95% or greater within mandatory timelines for Critical/Emergency | Monthly monitoring |
| Vulnerability Management | Automated scanning of all assets | At least monthly |
| Penetration Testing | Independent testing of critical systems | At least annually |
| Incident Response | OSFI notification for material incidents | **Within 72 hours** |
| Third-Party Due Diligence | Pre-engagement risk assessment | Before onboarding |
| BCP/DR Testing | Failover and recovery exercises | At least annually |

---

*Read in conjunction with OSFI Guideline E-21 (Operational Risk and Resilience), OSFI Guideline B-10 (Third-Party Risk Management), and the OSFI Corporate Governance Guideline.*

*For the official and binding version of this Guideline, refer to the OSFI website at osfi-bsif.gc.ca.*

*Office of the Superintendent of Financial Institutions Canada*
*255 Albert Street, Ottawa, Ontario K1A 0H2*
*www.osfi-bsif.gc.ca*
