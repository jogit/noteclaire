export interface Subject {
  id: number
  name: string
  slug: string
  enabled?: boolean
  usual_for?: string[]
  chapter_count?: number
}

interface ChapterProgress {
  notes_words: number
  course_version: number | null
  notes_changed: boolean
  pending_suggestions: number
  has_revision_sheet: boolean
  has_quiz: boolean
}

export interface Chapter {
  id: number
  subject_id: number
  subject: Subject
  title: string
  description: string
  school_year: string
  created_at: string
  updated_at: string
  progress?: ChapterProgress | null
}

export type NoteSource = 'keyboard' | 'photo' | 'mixed'

export interface Notes {
  chapter_id: number
  raw_text: string
  source: NoteSource
  updated_at: string
}

export type CourseOrigin = 'ai_structure' | 'user_edit' | 'suggestion_applied'

export interface Course {
  chapter_id: number
  content_markdown: string
  version: number
  origin: CourseOrigin
  created_at: string
  notes_changed: boolean
  has_manual_changes: boolean
  /** Titre clair proposé par la mise au propre (premier titre du cours). */
  title: string
}

export interface CourseVersion {
  version: number
  origin: CourseOrigin
  created_at: string
}

export interface CourseVersionContent extends CourseVersion {
  content_markdown: string
}

export type SuggestionType =
  'correction' | 'missing_information' | 'clarification' | 'addition' | 'warning'

export interface Suggestion {
  id: number
  chapter_id: number
  type: SuggestionType
  original_text: string
  suggested_text: string
  reason: string
  confidence: number
  status: 'pending' | 'accepted' | 'rejected' | 'outdated'
  source_reference: string
  created_at: string
  decided_at: string | null
}

export interface AcceptResult {
  suggestion: Suggestion
  course: Course
}

export interface Occurrence {
  index: number
  before: string
  match: string
  after: string
}

export interface Usage {
  month_cost_eur: number
  budget_eur: number
  cost_tracking: boolean
}

export interface AuthStatus {
  auth_required: boolean
  authenticated: boolean
}

export interface ReferenceDocument {
  id: number
  subject_id: number
  title: string
  source: string
  url: string
  school_year: string
  file_path: string
  chunk_count: number
  updated_at: string
}

export interface SyncReport {
  added: number
  updated: number
  removed: number
  unchanged: number
  errors: string[]
}

export interface RevisionSheet {
  chapter_id: number
  content_markdown: string
  course_version: number
  outdated: boolean
  created_at: string
}

export interface QuizQuestion {
  type: 'qcm' | 'short' | 'true_false'
  question: string
  choices: string[]
  answer: string
  explanation: string
  course_excerpt: string
}

export interface Quiz {
  chapter_id: number
  questions: QuizQuestion[]
  course_version: number
  outdated: boolean
  created_at: string
}

export interface SearchResult {
  chapter_id: number
  title: string
  subject: string
  snippet: string
}

export type ExplainMode = 'simpler' | 'example' | 'question'

export interface Explanation {
  text: string
  answer: string
}

export interface ChatGPTStatus {
  ai_provider: string
  connected: boolean
  email: string
  name: string
  model: string
  needs_reauth: boolean
  redirect_uri: string
}

export interface ChatGPTModel {
  slug: string
  display_name: string
}

export interface OperationUsage {
  operation: string
  calls: number
  errors: number
  input_tokens: number
  output_tokens: number
  cost_eur: number
}

interface RecentRun {
  created_at: string
  operation: string
  chapter_title: string
  provider: string
  model: string
  status: 'success' | 'error'
  error_code: string
  input_tokens: number
  output_tokens: number
  duration_ms: number
}

export interface UsageDetails {
  ai_provider: string
  last_7_days: OperationUsage[]
  this_month: OperationUsage[]
  recent: RecentRun[]
  chatgpt_usage_url: string
}

/** Lecture d'une photo : chaque « [?] » du texte correspond à un élément de « uncertain ». */
export interface PhotoReading {
  text: string
  uncertain: { guess: string; options: string[] }[]
  /** La photo d'origine, conservée avec le chapitre. */
  url: string
  /** Schémas découpés automatiquement : `index` = rang du « [schéma : …] » dans le texte. */
  figures: { index: number; url: string }[]
}

export interface StoredPhoto {
  url: string
  created_at: string
}

export type NoteVersionReason = 'auto' | 'photo' | 'structure' | 'before_restore' | 'big_deletion'

export interface NoteVersion {
  id: number
  reason: NoteVersionReason
  source: NoteSource
  created_at: string
  words: number
  preview: string
}

export interface NoteVersionContent extends NoteVersion {
  raw_text: string
}

export interface TrashItem {
  id: number
  title: string
  subject: Subject
  deleted_at: string
  expires_at: string
}

export interface Backup {
  name: string
  size: number
  created_at: string
}

export interface Student {
  id: number
  name: string
  level: string
  adaptation_codes: string[]
  adaptation_notes: string
  subject_ids: number[]
}

export interface Adaptation {
  id: string
  name: string
}

export interface Level {
  id: string
  name: string
}

export type AIProviderChoice = 'openai' | 'chatgpt' | 'local' | 'fake'

export interface SetupStatus {
  needs_setup: boolean
  ai_provider: string
  has_openai_key: boolean
  local_ai_base_url: string
  local_ai_model: string
  chatgpt_connected: boolean
}

export interface DownloadReport {
  downloaded: number
  already: number
  errors: string[]
}
