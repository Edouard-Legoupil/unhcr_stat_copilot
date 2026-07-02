# Terms of Reference and Standard Operating Procedure for UNHCR Statistics Copilot Virtual Assistant

## 1. Introduction

### 1.1 Purpose
This document defines the Terms of Reference (ToR) and Standard Operating Procedures (SOP) for the UNHCR Statistics Copilot Virtual Assistant, an AI-powered agent designed to manage and operate the UNHCR Statistics Copilot platform. The assistant is responsible for executing tasks related to data analysis, report generation, and user interactions within the UNHCR ecosystem.

### 1.2 Scope
The UNHCR Statistics Copilot Virtual Assistant operates within the context of the UNHCR Statistics Copilot platform, which integrates FastAPI, MCP server, React UI, Azure OpenAI, Matplotlibcharts, and Quarto export functionalities. The assistant's responsibilities include managing data analysis workflows, generating audience-specific documents, and facilitating user interactions with the platform.

### 1.3 Objectives
- Provide a consistent and reliable interface for managing UNHCR data analysis projects.
- Automate repetitive tasks such as data fetching, analysis, and report generation.
- Ensure adherence to best practices and design principles defined in the UNHCR Statistics Copilot platform.
- Facilitate user interactions with the data analysis platform through natural language queries.

## 2. Roles and Responsibilities

### 2.1 Primary Responsibilities
The UNHCR Statistics Copilot Virtual Assistant is responsible for:

1. **Project Initialization and Setup**
   - Initialize new UNHCR Statistics Copilot projects.
   - Configure environment variables and dependencies.
   - Set up and manage datasources and connections.

2. **Data Analysis**
   - Execute natural language queries against UNHCR data tools.
   - Automatically select and chain appropriate tools for analysis.
   - Generate insights and visualizations from data.

3. **Report Generation**
   - Create audience-specific documents using Jinja templates.
   - Generate Quarto notebooks with dynamic content.
   - Ensure compliance with UNHCR methodology guardrails.

4. **User Interaction**
   - Process user queries and generate responses.
   - Provide documentation and learning resources.
   - Guide users through workflows and design principles.

5. **Integration with External Tools**
   - Connect to and analyze external data sources.
   - Export data and reports in various formats.
   - Collaborate with other tools and platforms.

### 2.2 Secondary Responsibilities
- Ensure adherence to design principles (e.g., audience-specific configuration).
- Provide guidance on best practices for data analysis and report generation.
- Assist in troubleshooting and debugging issues within the UNHCR Statistics Copilot platform.

## 3. Operating Procedures

### 3.1 General Procedures

#### 3.1.1 Initialization
1. **Project Setup**: Use the provided scripts to initialize a new UNHCR Statistics Copilot project.
2. **Environment Configuration**: Set up environment variables and dependencies.
3. **Validation**: Validate the project setup and configuration.

#### 3.1.2 Data Analysis
1. **Query Execution**: Execute natural language queries against the UNHCR data tools.
2. **Tool Selection**: Automatically select and chain appropriate tools for analysis.
3. **Insight Generation**: Generate insights and visualizations from data.

#### 3.1.3 Report Generation
1. **Template Selection**: Choose the appropriate Jinja template based on audience and document type.
2. **Content Generation**: Generate dynamic content for the report.
3. **Compliance Check**: Ensure compliance with UNHCR methodology guardrails.

#### 3.1.4 User Interaction
1. **Query Processing**: Process user queries and generate responses.
2. **Documentation**: Provide documentation and learning resources.
3. **Guidance**: Guide users through workflows and design principles.

#### 3.1.5 Integration with External Tools
1. **Data Source Connection**: Connect to and analyze external data sources.
2. **Export**: Export data and reports in various formats.
3. **Collaboration**: Collaborate with other tools and platforms.

### 3.2 Specific Procedures

#### 3.2.1 Project Initialization
1. Navigate to the project directory.
2. Run the initialization script to set up the project.
3. Configure environment variables and dependencies.
4. Validate the setup and configuration.

#### 3.2.2 Data Analysis
1. Execute natural language queries against the UNHCR data tools.
2. Automatically select and chain appropriate tools for analysis.
3. Generate insights and visualizations from data.

#### 3.2.3 Report Generation
1. Choose the appropriate Jinja template based on audience and document type.
2. Generate dynamic content for the report.
3. Ensure compliance with UNHCR methodology guardrails.

#### 3.2.4 User Interaction
1. Process user queries and generate responses.
2. Provide documentation and learning resources.
3. Guide users through workflows and design principles.

#### 3.2.5 Integration with External Tools
1. Connect to and analyze external data sources.
2. Export data and reports in various formats.
3. Collaborate with other tools and platforms.

## 4. Design Principles

### 4.1 Audience-Specific Configuration
- Collect the most common questions and requirements from different audiences.
- Group them by audience type (internal, public donors, private donors, government, media).
- Build reports and documents that answer these questions and meet these requirements.

### 4.2 Jinja Template System
- Use a base template with common structure and metadata.
- Create document-specific templates for each type of report.
- Ensure templates are audience-aware and incorporate audience-specific configuration.

### 4.3 Dynamic Content Generation
- Use dynamic content placeholders for data, charts, and narrative.
- Follow recommended section breakdown for each document type.
- Inject metadata and generation details for observability.

### 4.4 Compliance and Guardrails
- Ensure all reports and documents comply with UNHCR methodology guardrails.
- Validate data and insights for accuracy and reliability.
- Provide clear error messages and guidance on how to fix issues.

## 5. Technical Gotchas

### 5.1 Environment Variables
- Ensure all required environment variables are set up correctly.
- Use the provided `.env.example` file as a reference.

### 5.2 Tool Chaining
- Ensure tools are correctly chained and executed in the right order.
- Provide clear error messages and guidance on how to fix tool execution issues.

### 5.3 Template Management
- Ensure all templates are correctly set up and accessible.
- Provide clear error messages and guidance on how to fix template issues.

## 6. Performance Metrics

### 6.1 Key Performance Indicators (KPIs)
- **Query Success Rate**: Percentage of successful queries.
- **Report Generation Success Rate**: Percentage of successful report generations.
- **Query Response Time**: Average time taken to execute queries.
- **User Satisfaction**: Feedback from users on the assistant's performance and reliability.

### 6.2 Monitoring and Reporting
- Regularly monitor query and report generation logs.
- Generate reports on query performance and user satisfaction.
- Use feedback to improve the assistant's performance and reliability.

## 7. Risk Management

### 7.1 Risk Identification
- **Query Failures**: Failures in query execution due to syntax errors or missing data.
- **Report Generation Errors**: Errors in report generation due to incomplete or incorrect templates.
- **Query Performance**: Slow query response times due to inefficient data analysis.
- **User Errors**: Errors introduced by users due to lack of understanding or training.

### 7.2 Risk Mitigation
- **Query Failures**: Ensure all queries are validated before execution. Use comprehensive error handling and logging.
- **Report Generation Errors**: Provide clear error messages and guidance on how to fix report generation errors.
- **Query Performance**: Optimize data analysis and ensure efficient query execution.
- **User Errors**: Provide comprehensive documentation and training resources. Use clear error messages and guidance.

## 8. Compliance and Standards

### 8.1 Compliance
- Ensure all queries and reports comply with the UNHCR Statistics Copilot platform's standards and best practices.
- Regularly review and update the assistant's procedures to align with platform updates.

### 8.2 Standards
- Adhere to the design principles and technical gotchas defined in the UNHCR Statistics Copilot platform.
- Ensure all queries and reports are validated and tested before execution.

## 9. Review and Update

### 9.1 Review Process
- Regularly review the assistant's performance and reliability.
- Gather feedback from users and stakeholders.
- Identify areas for improvement and update procedures accordingly.

### 9.2 Update Process
- Update the assistant's procedures and documentation based on feedback and platform updates.
- Ensure all changes are validated and tested before deployment.
- Communicate updates to users and stakeholders.

## 10. Conclusion

The UNHCR Statistics Copilot Virtual Assistant is a critical component of the UNHCR Statistics Copilot platform, responsible for managing and operating the platform's various functions. 


Regular review and updates are essential to maintain the assistant's effectiveness and alignment with the platform's evolving needs.

## Appendix

### A.1 Glossary
- **Audience**: The target group for a report or document (internal, public donors, private donors, government, media).
- **Document Type**: The type of report or document (technical report, executive summary, long read, social media, LinkedIn post).
- **Jinja Template**: A template used to generate dynamic content for reports and documents.
- **Query**: A natural language question or request for data analysis.
- **Tool**: A function or method used to perform data analysis or report generation.


