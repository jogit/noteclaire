/** Vrai une fois l'assistant de premier lancement terminé (ou inutile) dans cette session. */
let checked = false

export const isSetupChecked = (): boolean => checked
export const markSetupDone = (): void => {
  checked = true
}
