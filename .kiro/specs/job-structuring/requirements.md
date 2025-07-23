# Requirements Document

## Introduction

The Job Structuring feature aims to create a robust system for automatically extracting and structuring job information from unstructured job descriptions and memos. This system will use AI (specifically Gemini models) to convert raw job data into a standardized JSON format that can be used for candidate matching, search optimization, and analytics. The structured data will include basic job information, requirements, evaluation points, keywords, search templates, and RAG parameters.

## Requirements

### Requirement 1

**User Story:** As a recruitment manager, I want to automatically extract structured data from job descriptions and memos, so that I can standardize job information for better candidate matching.

#### Acceptance Criteria
1. WHEN a job description and memo are provided THEN the system SHALL extract basic job information including title, company, industry, job type, employment type, and location
2. WHEN processing job requirements THEN the system SHALL categorize them into must-have and nice-to-have with importance ratings
3. WHEN analyzing job content THEN the system SHALL identify key evaluation points with weights and evaluation criteria
4. WHEN structuring is complete THEN the system SHALL output a standardized JSON format with all required fields

### Requirement 2

**User Story:** As a recruitment consultant, I want the system to generate optimized search templates based on job requirements, so that I can find better candidates more efficiently.

#### Acceptance Criteria
1. WHEN job requirements are processed THEN the system SHALL generate at least 5 search templates with different purposes
2. WHEN creating search templates THEN the system SHALL prioritize them based on importance to the job
3. WHEN generating search queries THEN the system SHALL use proper syntax with boolean operators (AND, OR) and grouping
4. WHEN search templates are created THEN the system SHALL include templates for both must-have and nice-to-have requirements

### Requirement 3

**User Story:** As a data analyst, I want the system to extract relevant keywords and categorize them, so that I can perform better analytics on job requirements.

#### Acceptance Criteria
1. WHEN processing job content THEN the system SHALL extract technical keywords related to required skills and technologies
2. WHEN analyzing soft skills THEN the system SHALL identify and categorize relevant soft skill keywords
3. WHEN processing domain knowledge THEN the system SHALL extract industry and domain-specific keywords
4. WHEN analyzing company culture THEN the system SHALL identify keywords related to company values and work environment

### Requirement 4

**User Story:** As an AI engineer, I want the system to generate RAG (Retrieval-Augmented Generation) parameters, so that I can optimize the AI matching process.

#### Acceptance Criteria
1. WHEN structuring job data THEN the system SHALL generate appropriate industry, job type, and skills filters
2. WHEN creating RAG parameters THEN the system SHALL set an appropriate similarity threshold based on job specificity
3. WHEN optimizing for relevance THEN the system SHALL identify fields that should receive boosted relevance in matching
4. WHEN RAG parameters are generated THEN the system SHALL ensure they are compatible with the existing AI matching system

### Requirement 5

**User Story:** As a system administrator, I want the job structuring process to be reliable and error-resistant, so that it can be integrated into automated workflows.

#### Acceptance Criteria
1. WHEN input files are missing or invalid THEN the system SHALL provide clear error messages
2. WHEN API keys are not configured THEN the system SHALL fail gracefully with appropriate instructions
3. WHEN the AI model returns unexpected formats THEN the system SHALL handle the error and attempt to extract valid JSON
4. WHEN processing is complete THEN the system SHALL save the structured data to a specified output location

### Requirement 6

**User Story:** As a developer, I want a flexible and modular job structuring system, so that I can extend it for different job types and formats.

#### Acceptance Criteria
1. WHEN implementing the system THEN it SHALL use a modular design with clear separation of concerns
2. WHEN processing different job formats THEN the system SHALL be adaptable to various input structures
3. WHEN new requirements emerge THEN the system SHALL be extensible without major refactoring
4. WHEN integrating with other systems THEN the system SHALL provide clear interfaces and documentation