import { getStudentId } from '../lib/currentStudent'
import { ApiError } from './errors'
import type {
  AcceptResult,
  AuthStatus,
  Backup,
  Chapter,
  ChatGPTModel,
  ChatGPTStatus,
  Course,
  CourseVersion,
  ExplainMode,
  Explanation,
  Level,
  DownloadReport,
  Adaptation,
  AIProviderChoice,
  SetupStatus,
  CourseVersionContent,
  Notes,
  NoteVersion,
  NoteVersionContent,
  PhotoReading,
  StoredPhoto,
  NoteSource,
  Quiz,
  ReferenceDocument,
  RevisionSheet,
  SearchResult,
  Student,
  Subject,
  Suggestion,
  SyncReport,
  TrashItem,
  Usage,
  UsageDetails,
} from './types'

type Method = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'

let onAuthRequired: () => void = () => {}

export function setAuthRequiredHandler(handler: () => void): void {
  onAuthRequired = handler
}

function requestHeaders(body: unknown): Record<string, string> {
  const headers: Record<string, string> = {}
  if (body !== undefined && !(body instanceof FormData))
    headers['Content-Type'] = 'application/json'
  const studentId = getStudentId()
  if (studentId !== undefined) headers['X-Student-Id'] = String(studentId)
  return headers
}

function requestBody(body: unknown): BodyInit | undefined {
  if (body === undefined) return undefined
  return body instanceof FormData ? body : JSON.stringify(body)
}

async function apiError(response: Response): Promise<ApiError> {
  const payload = await response.json().catch(() => null)
  const code: string = payload?.error?.code ?? `http_${response.status}`
  if (code === 'auth_required') onAuthRequired()
  return new ApiError(code, response.status, payload?.error?.message, payload?.error?.details)
}

async function request<T>(
  method: Method,
  path: string,
  body?: unknown,
  options: { keepalive?: boolean } = {},
): Promise<T> {
  let response: Response
  try {
    response = await fetch(path, {
      method,
      headers: requestHeaders(body),
      body: requestBody(body),
      credentials: 'same-origin',
      keepalive: options.keepalive,
    })
  } catch {
    throw new ApiError('network_error', 0)
  }
  if (!response.ok) throw await apiError(response)
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

const chapterPath = (id: number) => `/api/chapters/${id}`

/** Une ressource absente (404) devient null. */
async function orNull<T>(promise: Promise<T>): Promise<T | null> {
  try {
    return await promise
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null
    throw error
  }
}

export const api = {
  appVersion: () => request<{ version: string }>('GET', '/api/version'),
  authStatus: () => request<AuthStatus>('GET', '/api/auth/status'),
  login: (password: string) => request<void>('POST', '/api/auth/login', { password }),
  logout: () => request<void>('POST', '/api/auth/logout'),

  subjects: (includeAll = false) =>
    request<Subject[]>('GET', `/api/subjects${includeAll ? '?include_all=true' : ''}`),
  createSubject: (name: string) => request<Subject>('POST', '/api/subjects', { name }),
  updateSubject: (id: number, changes: { name?: string }) =>
    request<Subject>('PATCH', `/api/subjects/${id}`, changes),
  deleteSubject: (id: number) => request<void>('DELETE', `/api/subjects/${id}`),

  setupStatus: () => request<SetupStatus>('GET', '/api/setup/status'),
  saveAI: (config: {
    ai_provider: AIProviderChoice
    openai_api_key?: string
    local_ai_base_url?: string
    local_ai_model?: string
  }) => request<SetupStatus>('PUT', '/api/setup/ai', config),
  testAI: () => request<{ ok: boolean; message: string }>('POST', '/api/setup/ai/test'),

  levels: () => request<Level[]>('GET', '/api/levels'),
  students: () => request<Student[]>('GET', '/api/students'),
  adaptations: () => request<Adaptation[]>('GET', '/api/adaptations'),
  createStudent: (name: string, level: string) =>
    request<Student>('POST', '/api/students', { name, level }),
  updateStudent: (
    id: number,
    changes: {
      name?: string
      level?: string
      adaptation_codes?: string[]
      adaptation_notes?: string
    },
  ) => request<Student>('PATCH', `/api/students/${id}`, changes),
  setStudentSubjects: (id: number, subjectIds: number[]) =>
    request<Student>('PUT', `/api/students/${id}/subjects`, { subject_ids: subjectIds }),
  deleteStudent: (id: number) => request<void>('DELETE', `/api/students/${id}`),

  chatgptStatus: () => request<ChatGPTStatus>('GET', '/api/chatgpt/status'),
  chatgptLogin: () => request<{ authorization_url: string }>('POST', '/api/chatgpt/login'),
  chatgptModels: () => request<ChatGPTModel[]>('GET', '/api/chatgpt/models'),
  chatgptSetModel: (model: string) => request<void>('PUT', '/api/chatgpt/model', { model }),
  chatgptLogout: () => request<{ revoked: boolean }>('POST', '/api/chatgpt/logout'),
  usage: () => request<Usage>('GET', '/api/usage'),
  usageDetails: () => request<UsageDetails>('GET', '/api/usage/details'),
  /** Durée habituelle (secondes) de chaque opération IA. */
  aiDurations: () => request<Record<string, number>>('GET', '/api/usage/durations'),

  chapters: (subjectId?: number) =>
    request<Chapter[]>(
      'GET',
      subjectId === undefined ? '/api/chapters' : `/api/chapters?subject_id=${subjectId}`,
    ),
  chapter: (id: number) => request<Chapter>('GET', chapterPath(id)),
  createChapter: (subjectId: number, title: string) =>
    request<Chapter>('POST', '/api/chapters', { subject_id: subjectId, title }),
  renameChapter: (id: number, title: string) =>
    request<Chapter>('PATCH', chapterPath(id), { title }),
  deleteChapter: (id: number) => request<void>('DELETE', chapterPath(id)),

  notes: (chapterId: number) => request<Notes>('GET', `${chapterPath(chapterId)}/notes`),
  /** checkpoint « photo » : garde aussi une version des notes tout juste importées. */
  saveNotes: (
    chapterId: number,
    rawText: string,
    source: NoteSource,
    options: { keepalive?: boolean; checkpoint?: 'photo' } = {},
  ) =>
    request<Notes>(
      'PUT',
      `${chapterPath(chapterId)}/notes`,
      { raw_text: rawText, source, checkpoint: options.checkpoint },
      { keepalive: options.keepalive },
    ),
  noteVersions: (chapterId: number) =>
    request<NoteVersion[]>('GET', `${chapterPath(chapterId)}/notes/versions`),
  noteVersion: (chapterId: number, versionId: number) =>
    request<NoteVersionContent>('GET', `${chapterPath(chapterId)}/notes/versions/${versionId}`),
  restoreNoteVersion: (chapterId: number, versionId: number) =>
    request<Notes>('POST', `${chapterPath(chapterId)}/notes/versions/${versionId}/restore`),

  trash: () => request<TrashItem[]>('GET', '/api/trash'),
  restoreChapter: (id: number) => request<Chapter>('POST', `/api/trash/${id}/restore`),
  purgeChapter: (id: number) => request<void>('DELETE', `/api/trash/${id}`),

  backups: () => request<Backup[]>('GET', '/api/backups'),
  createBackup: () => request<Backup>('POST', '/api/backups'),
  restoreBackup: (name: string) =>
    request<void>('POST', `/api/backups/${encodeURIComponent(name)}/restore`),
  restoreBackupFile: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return request<void>('POST', '/api/backups/restore', form)
  },
  backupUrl: (name: string) => `/api/backups/${encodeURIComponent(name)}`,

  /** Renvoie null si le chapitre n'a pas encore été mis au propre. */
  course: (chapterId: number) => orNull(request<Course>('GET', `${chapterPath(chapterId)}/course`)),
  updateCourse: (chapterId: number, content: string) =>
    request<Course>('PUT', `${chapterPath(chapterId)}/course`, { content_markdown: content }),
  versions: (chapterId: number) =>
    request<CourseVersion[]>('GET', `${chapterPath(chapterId)}/course/versions`),
  version: (chapterId: number, version: number) =>
    request<CourseVersionContent>('GET', `${chapterPath(chapterId)}/course/versions/${version}`),
  structure: (chapterId: number) => request<Course>('POST', `${chapterPath(chapterId)}/structure`),

  analyze: (chapterId: number) =>
    request<Suggestion[]>('POST', `${chapterPath(chapterId)}/analyze`),
  pendingSuggestions: (chapterId: number) =>
    request<Suggestion[]>('GET', `${chapterPath(chapterId)}/suggestions?status=pending`),
  acceptSuggestion: (id: number, occurrence?: number) =>
    request<AcceptResult>('POST', `/api/suggestions/${id}/accept`, { occurrence }),
  rejectSuggestion: (id: number) => request<Suggestion>('POST', `/api/suggestions/${id}/reject`),

  revisionSheet: (chapterId: number) =>
    orNull(request<RevisionSheet>('GET', `${chapterPath(chapterId)}/revision-sheet`)),
  createRevisionSheet: (chapterId: number) =>
    request<RevisionSheet>('POST', `${chapterPath(chapterId)}/revision-sheet`),
  quiz: (chapterId: number) => orNull(request<Quiz>('GET', `${chapterPath(chapterId)}/quiz`)),
  createQuiz: (chapterId: number) => request<Quiz>('POST', `${chapterPath(chapterId)}/quiz`),
  explain: (chapterId: number, passage: string, mode: ExplainMode) =>
    request<Explanation>('POST', `${chapterPath(chapterId)}/explain`, { passage, mode }),
  exportMarkdownUrl: (chapterId: number) => `${chapterPath(chapterId)}/export.md`,
  quizAnkiUrl: (chapterId: number) => `${chapterPath(chapterId)}/quiz/anki.txt`,
  search: (query: string) =>
    request<SearchResult[]>('GET', `/api/search?q=${encodeURIComponent(query)}`),

  references: (subjectId?: number) =>
    request<ReferenceDocument[]>(
      'GET',
      subjectId === undefined ? '/api/references' : `/api/references?subject_id=${subjectId}`,
    ),
  uploadReference: (
    subjectId: number,
    file: File,
    metadata: { title: string; source: string; url: string },
  ) => {
    const form = new FormData()
    form.append('file', file)
    form.append('subject_id', String(subjectId))
    form.append('title', metadata.title)
    form.append('source', metadata.source)
    form.append('url', metadata.url)
    return request<ReferenceDocument>('POST', '/api/references', form)
  },
  deleteReference: (id: number) => request<void>('DELETE', `/api/references/${id}`),
  downloadProgrammes: () => request<DownloadReport>('POST', '/api/references/download'),
  syncReferences: () => request<SyncReport>('POST', '/api/references/sync'),

  /** Image ajoutée au cours (ex. photo d'un schéma) : renvoie son adresse. */
  uploadImage: (chapterId: number, image: File) => {
    const form = new FormData()
    form.append('image', image)
    return request<{ url: string }>('POST', `${chapterPath(chapterId)}/images`, form)
  },

  /** Redessine proprement (SVG) un schéma du chapitre ; l'original n'est pas modifié. */
  redrawSchema: (
    chapterId: number,
    url: string,
    correction?: { previousUrl: string; remark: string },
  ) =>
    request<{ url: string; corrections: string[] }>(
      'POST',
      `${chapterPath(chapterId)}/schemas/redraw`,
      {
        url,
        previous_url: correction?.previousUrl,
        remark: correction?.remark,
      },
    ),
  /** Même schéma redessiné, avec ou sans aspect manuscrit (sans appel à l'IA). */
  restyleSchema: (chapterId: number, url: string, hand: boolean) =>
    request<{ url: string }>('POST', `${chapterPath(chapterId)}/schemas/restyle`, { url, hand }),
  /** Photo de notes manuscrites → texte. La photo (sans métadonnées) est conservée avec le chapitre. */
  photo: (chapterId: number, image: File) => {
    const form = new FormData()
    form.append('image', image)
    return request<PhotoReading>('POST', `${chapterPath(chapterId)}/photo`, form)
  },

  /** Photos d'origine importées dans ce chapitre, de la plus ancienne à la plus récente. */
  photos: (chapterId: number) => request<StoredPhoto[]>('GET', `${chapterPath(chapterId)}/photos`),
}
