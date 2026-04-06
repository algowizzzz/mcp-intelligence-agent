# Prompts Reference

All prompts used throughout the MCP Intelligence Agent system.

---

## 1. Agent System Prompt

**Location:** `agent/prompt.py`
**Used by:** `agent/agent.py` — passed as `system_prompt` to the LangGraph ReAct agent (Claude Sonnet 4)
**Scope:** Every conversation turn; governs how the agent reasons, calls tools, and formats responses.

```
You are a sophisticated financial risk intelligence agent.

REASONING STYLE:
- Think step by step before deciding which tools to call
- For full risk picture queries: call exposure, trades, limits, and web_search in parallel
- For QoQ trend queries: call get_historical_exposure 4 times in parallel
  with dates 2025-03-31, 2025-06-30, 2025-09-30, 2025-12-31
- Always synthesize all tool results into a coherent structured response
- If a tool fails, note the gap and proceed with available data

SOURCE ATTRIBUTION:
After every specific figure, date, or fact from a tool result, append immediately:
  [src:tool_name]

Examples:
  Net exposure $26.2M [src:get_counterparty_exposure]
  Q3 MTM $33.8M [src:get_historical_exposure]
  Credit rating AA- [src:get_counterparty_exposure]

Do NOT annotate general commentary or your own analysis.

FINANCIAL PRECISION:
- Distinguish MTM (mark-to-market) from notional at all times
- Always state currency and date for exposure figures
- Flag limit breaches explicitly with utilization percentage
- Report VaR at the stated confidence level
```

---

## 2. SAJHA MCP Server Prompts

**Location:** `sajhamcpserver/config/prompts/*.json`
**Used by:** `sajhamcpserver/sajha/core/prompts_registry.py` — loaded at startup, auto-refreshed every 10 min
**Scope:** Served via MCP `prompts/list` and `prompts/get` protocol methods. Variables use `{variable_name}` substitution.

---

### 2.1 Code Review

**File:** `code_review.json`
**Category:** development | **Tags:** code, review, quality, security

**Arguments:** `code` *(required)*, `language` *(required)*

**Template:**
```
Review the following {language} code:

```{language}
{code}
```

Provide a comprehensive code review covering:

1. **Code Quality Assessment**
   - Code structure and organization
   - Naming conventions and readability
   - Code complexity and maintainability

2. **Security Analysis**
   - Potential security vulnerabilities
   - Input validation issues
   - Authentication/authorization concerns

3. **Performance Optimization**
   - Performance bottlenecks
   - Resource usage optimization
   - Scalability considerations

4. **Best Practices**
   - Language-specific best practices
   - Design pattern recommendations
   - Testing recommendations

5. **Specific Improvements**
   - Concrete code improvement suggestions
   - Refactoring opportunities

Format the response with clear sections and prioritize issues by severity.
```

---

### 2.2 Bug Diagnosis

**File:** `bug_diagnosis.json`
**Category:** development | **Tags:** bug, debugging, troubleshooting, fix

**Arguments:** `bug_description` *(required)*, `error_message` *(required)*, `code` *(required)*, `language` *(required)*, `version` *(optional, default: latest)*, `platform` *(optional, default: cross-platform)*

**Template:**
```
Diagnose the following bug:

**Bug Description:**
{bug_description}

**Error Message:**
```
{error_message}
```

**Code Context:**
```{language}
{code}
```

**Environment:**
- Language/Framework: {language}
- Version: {version}
- Platform: {platform}

Please provide:

1. **Root Cause Analysis**
   - Identify the root cause
   - Explain why the bug occurs
   - Related error patterns

2. **Impact Assessment**
   - Severity of the bug
   - Affected functionality
   - Potential side effects

3. **Solution**
   - Step-by-step fix
   - Code corrections
   - Best practices to prevent recurrence

4. **Testing Recommendations**
   - Test cases to verify the fix
   - Edge cases to consider
   - Regression testing suggestions

5. **Prevention**
   - Code review recommendations
   - Design improvements
   - Automated testing suggestions

Provide clear, actionable solutions with code examples where applicable.
```

---

### 2.3 Documentation Generator

**File:** `documentation_generator.json`
**Category:** development | **Tags:** documentation, technical-writing, api

**Arguments:** `content` *(required)*, `doc_type` *(required)*, `audience` *(optional, default: developers)*, `format` *(optional, default: markdown)*, `detail_level` *(optional, default: comprehensive)*

**Template:**
```
Generate {doc_type} documentation for the following:

{content}

**Documentation Requirements:**
- Target Audience: {audience}
- Format: {format}
- Detail Level: {detail_level}

Please provide:

1. **Overview**
   - Brief summary
   - Purpose and scope
   - Key features

2. **Detailed Documentation**
   - Component descriptions
   - Usage examples
   - Parameters and return values

3. **Best Practices**
   - Common use cases
   - Tips and tricks
   - Common pitfalls to avoid

4. **Additional Resources**
   - Related documentation
   - Further reading

Use clear, concise language with practical examples.
```

---

### 2.4 Data Analysis

**File:** `data_analysis.json`
**Category:** analytics | **Tags:** data, analysis, statistics, insights

**Arguments:** `data` *(required)*, `dataset_description` *(required)*, `analysis_focus` *(optional, default: comprehensive overview)*

**Template:**
```
Analyze the following dataset and provide insights:

**Dataset Description:**
{dataset_description}

**Data:**
{data}

**Analysis Focus:**
{analysis_focus}

Please provide:

1. **Data Overview**
   - Data structure and types
   - Data quality assessment
   - Missing values and outliers

2. **Statistical Analysis**
   - Descriptive statistics
   - Distribution analysis
   - Correlation analysis

3. **Key Insights**
   - Patterns and trends
   - Anomalies and outliers
   - Significant findings

4. **Visualizations**
   - Recommended chart types
   - Key visualizations to create

5. **Recommendations**
   - Actionable insights
   - Next steps for analysis
   - Data quality improvements

Present findings in a clear, business-friendly format with supporting statistics.
```

---

### 2.5 Content Writing

**File:** `content_writing.json`
**Category:** content | **Tags:** writing, content, marketing, copywriting

**Arguments:** `topic` *(required)*, `content_type` *(required)*, `audience` *(required)*, `tone` *(optional, default: professional)*, `length` *(optional, default: medium 500-800 words)*, `key_points` *(optional)*, `context` *(optional)*

**Template:**
```
Write {content_type} about:

**Topic:** {topic}

**Target Audience:** {audience}

**Tone:** {tone}

**Length:** {length}

**Key Points to Cover:**
{key_points}

**Additional Context:**
{context}

Create engaging, well-structured content that:

1. **Captures Attention**
   - Compelling introduction
   - Clear value proposition
   - Engaging hook

2. **Delivers Value**
   - Well-organized content
   - Clear and concise messaging
   - Actionable information

3. **Engages the Audience**
   - Appropriate tone and style
   - Relevant examples
   - Clear call-to-action

4. **Optimized for Purpose**
   - SEO-friendly (if applicable)
   - Platform-appropriate formatting
   - Scannable structure

Deliver polished, professional content ready for publication.
```

---

### 2.6 Business Plan

**File:** `business_plan.json`
**Category:** business | **Tags:** business, strategy, planning, entrepreneurship

**Arguments:** `business_name` *(required)*, `description` *(required)*, `industry` *(required)*, `target_market` *(required)*, `objectives` *(required)*, `plan_type` *(optional, default: business plan)*

**Template:**
```
Create a {plan_type} for:

**Business/Project Name:** {business_name}

**Industry:** {industry}

**Description:**
{description}

**Target Market:** {target_market}

**Key Objectives:**
{objectives}

Generate a comprehensive {plan_type} including:

1. **Executive Summary**
   - Business overview
   - Mission and vision
   - Key success factors

2. **Market Analysis**
   - Industry overview
   - Target market definition
   - Competitive landscape
   - Market opportunities

3. **Strategy**
   - Business model
   - Go-to-market strategy
   - Competitive advantages
   - Growth strategy

4. **Operations Plan**
   - Key activities
   - Resource requirements
   - Technology and infrastructure

5. **Financial Projections**
   - Revenue model
   - Cost structure
   - Key metrics and KPIs
   - Funding requirements

6. **Risk Analysis**
   - Key risks and challenges
   - Mitigation strategies
   - Contingency plans

7. **Implementation Roadmap**
   - Milestones and timeline
   - Success metrics
   - Next steps

Provide a professional, detailed, and actionable plan.
```

---

## Summary

| Prompt | Location | Used By | Purpose |
|--------|----------|---------|---------|
| Agent System Prompt | `agent/prompt.py` | LangGraph ReAct agent (Claude Sonnet 4) | Controls reasoning, tool selection, source attribution, financial precision |
| Code Review | `sajhamcpserver/config/prompts/code_review.json` | SAJHA MCP `prompts/get` endpoint | Code quality, security, performance review |
| Bug Diagnosis | `sajhamcpserver/config/prompts/bug_diagnosis.json` | SAJHA MCP `prompts/get` endpoint | Root cause analysis and fix recommendations |
| Documentation Generator | `sajhamcpserver/config/prompts/documentation_generator.json` | SAJHA MCP `prompts/get` endpoint | API / code / system docs generation |
| Data Analysis | `sajhamcpserver/config/prompts/data_analysis.json` | SAJHA MCP `prompts/get` endpoint | Dataset insights and statistical analysis |
| Content Writing | `sajhamcpserver/config/prompts/content_writing.json` | SAJHA MCP `prompts/get` endpoint | Blog posts, articles, marketing copy |
| Business Plan | `sajhamcpserver/config/prompts/business_plan.json` | SAJHA MCP `prompts/get` endpoint | Strategic and business planning documents |
