/** TypeScript interfaces mirroring Pydantic models from the backend. */

export interface ContactInfo {
  name: string;
  email: string;
  phone: string;
  location: string;
  linkedin: string;
  github: string;
  portfolio: string;
}

export interface ExperienceEntry {
  company: string;
  role: string;
  start_date: string;
  end_date: string;
  location: string;
  bullets: string[];
  skills_demonstrated: string[];
}

export interface EducationEntry {
  institution: string;
  degree: string;
  field_of_study: string;
  start_date: string;
  end_date: string;
  degree_mark?: string;
  honours?: string;
}

export interface ProjectEntry {
  repo_name: string;
  repo_url: string;
  description: string;
  tech_stack: string[];
  architecture: string;
  stars: number;
}

export interface PublicationEntry {
  title: string;
  venue: string;
  date: string;
  publisher?: string;
  link?: string;
}

export interface WorkshopEntry {
  title: string;
  date: string;
  place: string;
}

export interface AwardEntry {
  title: string;
  organization: string;
  date: string;
}

export interface InternationalExperienceEntry {
  place: string;
  date: string;
  description: string;
}

export interface ParsedResume {
  contact: ContactInfo;
  professional_summary: string;
  experience: ExperienceEntry[];
  skills: string[];
  education: EducationEntry[];
  certifications: string[];
  totals_yoe: number;
  projects: ProjectEntry[];
  publications: PublicationEntry[];
  workshops: WorkshopEntry[];
  awards: AwardEntry[];
  international_experiences: InternationalExperienceEntry[];
}

export interface TailoredExperienceEntry {
  company: string;
  role: string;
  start_date: string;
  end_date: string;
  location: string;
  bullets: string[];
}

export interface TailoredResume {
  contact: ContactInfo;
  professional_summary: string;
  experience: TailoredExperienceEntry[];
  skills: string[];
  education: EducationEntry[];
  certifications: string[];
  projects: ProjectEntry[];
  publications: PublicationEntry[];
  workshops: WorkshopEntry[];
  awards: AwardEntry[];
  international_experiences: InternationalExperienceEntry[];
  job_title: string;
  company: string;
  ats_keyword_coverage: string[];
  missing_keywords: string[];
  tailoring_notes: string;
  confidence_score: number;
}

export interface JobRequirements {
  job_title: string;
  company: string;
  seniority_level: string;
  required_skills: string[];
  preferred_skills: string[];
  key_responsibilities: string[];
  ats_keywords: string[];
  industry: string;
  team_size: string;
  remote_policy: string;
}

export interface ConversationEntry {
  timestamp: string;
  user_input: string;
  intent: string;
  result_summary: string;
}

export interface TaskResponse {
  task_id: string;
}

export interface TaskStatusResponse {
  status: "queued" | "running" | "completed" | "failed" | "not_found";
  result?: unknown;
  error?: { detail: string; error_code: string };
}

export interface EditResumeResponse {
  updated_fields: string[];
  working_resume: ParsedResume;
  conversation_entry: ConversationEntry;
}

export interface SessionSummary {
  session_id: string;
  candidate_name: string;
  skills_count: number;
  experience_count: number;
  job_count: number;
  tailored_count: number;
  last_updated: string;
}

export interface SessionListResponse {
  items: SessionSummary[];
  total: number;
}

export interface ExportItem {
  filename: string;
  size: number;
  job_title: string;
  company: string;
  confidence_score: number;
}
