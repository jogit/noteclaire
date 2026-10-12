import { computed, ref } from 'vue'
import { api } from '../api/client'
import type { Student } from '../api/types'
import { getStudentId, setStudentId } from '../lib/currentStudent'

/** Élèves de la famille ; l'élève courant est choisi par navigateur. */
const students = ref<Student[]>([])

async function refresh(): Promise<void> {
  students.value = await api.students()
}

/** L'élève choisi, ou le premier si le choix a disparu (le serveur fait de même). */
const current = computed(
  () => students.value.find((s) => s.id === getStudentId()) ?? students.value[0],
)

/** Change d'élève et recharge l'application : tout l'affichage dépend de l'élève. */
function switchTo(id: number): void {
  setStudentId(id)
  window.location.assign('/')
}

export function useStudents() {
  return { students, current, refresh, switchTo }
}
