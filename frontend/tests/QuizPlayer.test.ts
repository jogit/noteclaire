import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import type { QuizQuestion } from '../src/api/types'
import QuizPlayer from '../src/components/QuizPlayer.vue'

const questions: QuizQuestion[] = [
  {
    type: 'qcm',
    question: 'Comment appelle-t-on a ?',
    choices: ['Le coefficient directeur', "L'ordonnée à l'origine"],
    answer: 'Le coefficient directeur',
    explanation: 'a donne la pente.',
    course_excerpt: 'a est le coefficient directeur.',
  },
  {
    type: 'true_false',
    question: 'Une fonction linéaire a b = 0.',
    choices: ['Vrai', 'Faux'],
    answer: 'Vrai',
    explanation: 'Par définition.',
    course_excerpt: '',
  },
  {
    type: 'short',
    question: 'Forme d’une fonction affine ?',
    choices: [],
    answer: '$f(x) = ax + b$',
    explanation: 'Voir le cours.',
    course_excerpt: '',
  },
]

const button = (wrapper: ReturnType<typeof mount>, text: string) =>
  wrapper.findAll('button').find((b) => b.text().includes(text))!

describe('QuizPlayer', () => {
  it('corrige un QCM sans dépendre de la couleur et montre l’extrait du cours', async () => {
    const wrapper = mount(QuizPlayer, { props: { questions } })
    expect(wrapper.text()).toContain('Question 1 sur 3')

    await button(wrapper, "L'ordonnée").trigger('click')

    expect(wrapper.text()).toContain('✘ Ta réponse')
    expect(wrapper.text()).toContain('✔ Bonne réponse')
    expect(wrapper.text()).toContain('✘ Pas tout à fait.')
    expect(wrapper.text()).toContain('Dans ton cours')
    expect(wrapper.find('.quiz-choice').attributes('disabled')).toBeDefined()
  })

  it('compte le score jusqu’à la fin et permet de recommencer', async () => {
    const wrapper = mount(QuizPlayer, { props: { questions } })

    await button(wrapper, 'Le coefficient directeur').trigger('click')
    await button(wrapper, 'Question suivante').trigger('click')
    await button(wrapper, 'Vrai').trigger('click')
    await button(wrapper, 'Question suivante').trigger('click')

    await wrapper.find('#short-answer').setValue('ax+b')
    await wrapper.find('form').trigger('submit')
    expect(wrapper.find('.katex').exists()).toBe(true)
    await button(wrapper, "J'avais juste").trigger('click')
    await button(wrapper, 'Voir mon score').trigger('click')

    expect(wrapper.text()).toContain('Score : 3 / 3')
    await button(wrapper, 'Recommencer').trigger('click')
    expect(wrapper.text()).toContain('Question 1 sur 3')
  })
})
