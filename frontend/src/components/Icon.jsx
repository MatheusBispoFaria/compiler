const paths = {
  grid: 'M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z',
  file: 'M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z M14 2v6h6 M8 13h8 M8 17h5',
  archive: 'M3 3h18v5H3z M5 8v13h14V8 M10 12h4',
  chat: 'M21 11a8 8 0 0 1-8 8H6l-4 3V11a9 9 0 0 1 19 0Z M7 10h10 M7 14h6',
  chevron: 'm10 6 6 6-6 6',
  plus: 'M12 5v14 M5 12h14',
  spark: 'm12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5Z',
  arrow: 'M5 12h14 m-6-6 6 6-6 6',
  send: 'm22 2-7 20-4-9-9-4 20-7Z M22 2 11 13',
  upload: 'M12 16V3 m-5 5 5-5 5 5 M4 15v5a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-5',
  save: 'M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h12l4 4v12a2 2 0 0 1-2 2Z M7 3v6h10V3 M7 21v-8h10v8',
  shield: 'M12 2 3 6v6c0 5 9 10 9 10s9-5 9-10V6z M12 8v5 M12 16h.01',
  heart: 'M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8L12 21l8.8-8.6a5.5 5.5 0 0 0 0-7.8Z',
  trend: 'm3 17 6-6 4 4 8-10 M15 5h6v6',
  layers: 'm12 3 10 5-10 5L2 8z M2 12l10 5 10-5 M2 16l10 5 10-5',
  compare: 'M7 3v18 M17 3v18 M3 7h8 M13 17h8 M14 7h6 M4 17h6',
  clock: 'M12 8v5l3 2 M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0',
  flag: 'M4 22V3 M4 3c5-4 11 4 16 0v11c-5 4-11-4-16 0',
  search: 'M21 21l-5-5 M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0',
  check: 'm5 12 4 4L19 6',
  close: 'm6 6 12 12 M6 18 18 6',
};

export default function Icon({ name, size = 20, ...props }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}><path d={paths[name] || paths.spark} /></svg>;
}
