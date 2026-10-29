import type { TranslationKey } from '@/i18n'
import type { ContactTopic } from '@/services/api/endpoints'

export const CONTACT_TOPICS: ContactTopic[] = ['question', 'feedback', 'other']

export const TOPIC_KEYS: Record<ContactTopic, TranslationKey> = {
  feedback: 'askUs.topic.feedback',
  question: 'askUs.topic.question',
  other: 'askUs.topic.other',
}
