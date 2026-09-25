import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

import en       from './en.json'
import ta       from './ta.json'
import tanglish from './tanglish.json'
import fr       from './fr.json'
import de       from './de.json'
import hi       from './hi.json'
import id       from './id.json'
import it       from './it.json'
import ja       from './ja.json'
import ko       from './ko.json'
import pt       from './pt.json'
import es       from './es.json'

export const LANGUAGES = [
  { code: 'en',       label: 'English',              flag: '🇺🇸' },
  { code: 'ta',       label: 'தமிழ் (Tamil)',         flag: '🇮🇳' },
  { code: 'tanglish', label: 'Tanglish',              flag: '🤝' },
  { code: 'fr',       label: 'Français',              flag: '🇫🇷' },
  { code: 'de',       label: 'Deutsch',               flag: '🇩🇪' },
  { code: 'hi',       label: 'हिन्दी',                flag: '🇮🇳' },
  { code: 'id',       label: 'Indonesia',             flag: '🇮🇩' },
  { code: 'it',       label: 'Italiano',              flag: '🇮🇹' },
  { code: 'ja',       label: '日本語',                 flag: '🇯🇵' },
  { code: 'ko',       label: '한국어',                 flag: '🇰🇷' },
  { code: 'pt',       label: 'Português',             flag: '🇧🇷' },
  { code: 'es',       label: 'Español',               flag: '🇪🇸' },
]

i18n
  .use(initReactI18next)
  .init({
    resources: {
      en:       { translation: en },
      ta:       { translation: ta },
      tanglish: { translation: tanglish },
      fr:       { translation: fr },
      de:       { translation: de },
      hi:       { translation: hi },
      id:       { translation: id },
      it:       { translation: it },
      ja:       { translation: ja },
      ko:       { translation: ko },
      pt:       { translation: pt },
      es:       { translation: es },
    },
    lng: localStorage.getItem('actus-lang') || 'en',
    fallbackLng: 'en',
    interpolation: { escapeValue: false },
  })

export default i18n
