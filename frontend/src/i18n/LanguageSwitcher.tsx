import { useTranslation } from 'react-i18next';

const languages = [
  { code: 'en', label: 'EN', flag: '🇬🇧' },
  { code: 'fr', label: 'FR', flag: '🇫🇷' },
];

export default function LanguageSwitcher() {
  const { i18n } = useTranslation();

  return (
    <div className="flex items-center gap-0.5 p-0.5 bg-slate-100 rounded-lg dark:bg-slate-800/80 border border-slate-200/60 dark:border-slate-700/60">
      {languages.map((lang) => {
        const isActive = i18n.language.startsWith(lang.code);
        return (
          <button
            key={lang.code}
            onClick={() => i18n.changeLanguage(lang.code)}
            className={`px-2 py-1 rounded-md text-xs font-semibold transition-all cursor-pointer ${
              isActive
                ? 'bg-blue-600 text-white shadow-xs'
                : 'text-slate-500 hover:text-slate-800 hover:bg-slate-200/50 dark:text-slate-400 dark:hover:text-slate-200 dark:hover:bg-slate-700/50'
            }`}
          >
            {lang.label}
          </button>
        );
      })}
    </div>
  );
}
