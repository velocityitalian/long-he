/* Velocity - inline icon set + mascot art */

const ICONS = {
  bolt: '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" fill="currentColor" stroke="none"/>',
  flame: '<path d="M12 2c2.2 4.2-3.8 6.6-3.8 11.2a3.8 3.8 0 0 0 7.6 0c0-1.6-.7-2.9-1.6-4.1 3.6 1.9 6.3 5.2 6.3 8.7a8.5 8.5 0 1 1-17 0C3.5 11.4 9.4 8.4 12 2z" fill="currentColor" stroke="none"/>',
  star: '<polygon points="12 2 15.1 8.3 22 9.3 17 14.1 18.2 21 12 17.8 5.8 21 7 14.1 2 9.3 8.9 8.3 12 2" fill="currentColor" stroke="none"/>',
  heart: '<path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8l1.1 1.1L12 21.2l7.8-7.7 1.1-1.1a5.5 5.5 0 0 0 0-7.8z"/>',
  check: '<polyline points="20 6.5 9 17.5 4 12.5"/>',
  mic: '<rect x="9" y="2" width="6" height="11.5" rx="3"/><path d="M5 10.5a7 7 0 0 0 14 0"/><line x1="12" y1="19" x2="12" y2="22"/>',
  speaker: '<polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M15.4 8.6a5 5 0 0 1 0 6.8"/><path d="M18.4 5.6a9 9 0 0 1 0 12.8"/>',
  arrowDown: '<line x1="12" y1="4" x2="12" y2="19"/><polyline points="6 13 12 19 18 13"/>',
  chevron: '<polyline points="9 18 15 12 9 6"/>',
  plane: '<path d="M22 2 11 13"/><path d="M22 2l-7 20-4-9-9-4 20-7z"/>',
  fork: '<path d="M7 2v8a3 3 0 0 0 6 0V2"/><line x1="10" y1="13" x2="10" y2="22"/><path d="M17 2c-1.4 2-2 4-2 6a3 3 0 0 0 6 0c0-2-.6-4-2-6"/><line x1="18" y1="11" x2="18" y2="22"/>',
  bag: '<path d="M6 2h12l1 4H5l1-4z"/><path d="M5 8h14v12a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V8z"/><path d="M9 12a3 3 0 0 0 6 0"/>',
  hash: '<line x1="4" y1="9" x2="20" y2="9"/><line x1="4" y1="15" x2="20" y2="15"/><line x1="10" y1="3" x2="8" y2="21"/><line x1="16" y1="3" x2="14" y2="21"/>',
  clock: '<circle cx="12" cy="12" r="9.5"/><polyline points="12 6.5 12 12 16 14"/>',
  rocket: '<path d="M12 2s4 1 6 5c1 2 1 5 1 5l-4 1-3 5-3-5-4-1s0-3 1-5c2-4 6-5 6-5z"/><circle cx="12" cy="9" r="2"/>',
  trophy: '<path d="M8 21h8"/><path d="M12 17v4"/><path d="M7 4h10v5a5 5 0 0 1-10 0V4z"/><path d="M7 6H4a3 3 0 0 0 3 5"/><path d="M17 6h3a3 3 0 0 1-3 5"/>',
  book: '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>',
  smile: '<circle cx="12" cy="12" r="9.5"/><path d="M8 14.5s1.5 2 4 2 4-2 4-2"/><line x1="9" y1="9.5" x2="9.01" y2="9.5"/><line x1="15" y1="9.5" x2="15.01" y2="9.5"/>',
  leaf: '<path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.5 19 2c1 2 2 4.2 2 8 0 5.5-4.8 10-10 10z"/><path d="M4 21c2-6 6-10 12-12"/>',
  users: '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.9"/><path d="M16 3.1a4 4 0 0 1 0 7.8"/>',
  sun: '<circle cx="12" cy="12" r="4.5"/><line x1="12" y1="1.5" x2="12" y2="4.5"/><line x1="12" y1="19.5" x2="12" y2="22.5"/><line x1="1.5" y1="12" x2="4.5" y2="12"/><line x1="19.5" y1="12" x2="22.5" y2="12"/><line x1="4.6" y1="4.6" x2="6.7" y2="6.7"/><line x1="17.3" y1="17.3" x2="19.4" y2="19.4"/><line x1="4.6" y1="19.4" x2="6.7" y2="17.3"/><line x1="17.3" y1="6.7" x2="19.4" y2="4.6"/>',
  palette: '<path d="M12 2a10 10 0 0 0 0 20c1.7 0 2.5-1.3 1.7-2.5-.9-1.3.2-2.7 1.7-2.7H18a4 4 0 0 0 4-4C22 6.4 17.5 2 12 2z"/><circle cx="7.5" cy="10.5" r="1.1" fill="currentColor" stroke="none"/><circle cx="12" cy="7" r="1.1" fill="currentColor" stroke="none"/><circle cx="16.5" cy="10.5" r="1.1" fill="currentColor" stroke="none"/>',
  lotus: '<path d="M12 21c-4.4 0-8-3.1-8-7 2 .9 4 .9 5.4 0C8.2 11 9.4 8 12 6c2.6 2 3.8 5 2.6 8 1.4.9 3.4.9 5.4 0 0 3.9-3.6 7-8 7z"/><path d="M12 21c-2.2-3-2.2-7 0-10 2.2 3 2.2 7 0 10z"/>',
  shield: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
  mountain: '<path d="M3 20l6-14 4 8 3-5 5 11H3z"/><path d="M9 20l3-7"/>',
  sparkles: '<path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9L12 3z"/><path d="M19 15l.9 2.1L22 18l-2.1.9L19 21l-.9-2.1L16 18l2.1-.9L19 15z"/>',
  hourglass: '<path d="M6 2h12"/><path d="M6 22h12"/><path d="M7 2v4a5 5 0 0 0 5 5 5 5 0 0 0 5-5V2"/><path d="M7 22v-4a5 5 0 0 1 5-5 5 5 0 0 1 5 5v4"/>',
  hands: '<path d="M12 21s-7-4.4-7-9a4 4 0 0 1 7-2.5A4 4 0 0 1 19 12c0 4.6-7 9-7 9z"/>',
  dumbbell: '<path d="M6 7v10"/><path d="M18 7v10"/><path d="M3 9v6"/><path d="M21 9v6"/><line x1="6" y1="12" x2="18" y2="12"/>',
  scale: '<path d="M12 3v18"/><path d="M5 21h14"/><path d="M5 7h14"/><path d="M5 7l-3 6h6l-3-6z"/><path d="M19 7l-3 6h6l-3-6z"/>',
  sprout: '<path d="M12 22V12"/><path d="M12 12C12 8 9 5 5 5c0 4 3 7 7 7z"/><path d="M12 14c0-3 2.5-5.5 5.5-5.5 0 3-2.5 5.5-5.5 5.5z"/>',
  target: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.2" fill="currentColor" stroke="none"/>',
  calendar: '<rect x="3" y="5" width="18" height="16" rx="3"/><line x1="8" y1="3" x2="8" y2="7"/><line x1="16" y1="3" x2="16" y2="7"/><line x1="3" y1="10" x2="21" y2="10"/>',
  cloud: '<path d="M18 10h-1.3A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"/>',
  briefcase: '<rect x="3" y="7" width="18" height="13" rx="2.5"/><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="3" y1="12" x2="21" y2="12"/>',
  chip: '<rect x="6" y="6" width="12" height="12" rx="2.5"/><path d="M9 1.5V6M15 1.5V6M9 18v4.5M15 18v4.5M1.5 9H6M1.5 15H6M18 9h4.5M18 15h4.5"/>',
  paw: '<circle cx="7" cy="8" r="2.2"/><circle cx="12" cy="6.2" r="2.2"/><circle cx="17" cy="8" r="2.2"/><circle cx="19" cy="13" r="2"/><path d="M12 12c-3 0-5.5 2.2-5.5 4.6 0 1.6 1.3 2.4 2.7 2.4 1 0 1.9-.5 2.8-.5s1.8.5 2.8.5c1.4 0 2.7-.8 2.7-2.4C17.5 14.2 15 12 12 12z"/>',
  compass: '<circle cx="12" cy="12" r="9.5"/><polygon points="16.2 7.8 14.1 14.1 7.8 16.2 9.9 9.9 16.2 7.8"/>',
  shirt: '<path d="M8 2l4 2 4-2 5 4-3 3v11H6V9L3 6l5-4z"/>',
  music: '<path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>',
  ball: '<circle cx="12" cy="12" r="9.5"/><path d="M5 8.5c3 2 11 2 14 0"/><path d="M5 15.5c3-2 11-2 14 0"/><path d="M12 2.5c-3 4-3 15 0 19"/><path d="M12 2.5c3 4 3 15 0 19"/>',
  gift: '<rect x="3" y="8" width="18" height="4" rx="1"/><path d="M5 12v8a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-8"/><line x1="12" y1="8" x2="12" y2="22"/><path d="M12 8c-2 0-5-1-5-3.5S9.5 2.5 12 8z"/><path d="M12 8c2 0 5-1 5-3.5S14.5 2.5 12 8z"/>',
  globe: '<circle cx="12" cy="12" r="9.5"/><line x1="2.5" y1="12" x2="21.5" y2="12"/><path d="M12 2.5a14 14 0 0 1 0 19 14 14 0 0 1 0-19z"/>',
  coin: '<circle cx="12" cy="12" r="9.5"/><circle cx="12" cy="12" r="5.5"/><path d="M12 6.5v11"/>',
  hand: '<path d="M7 11V6a2 2 0 0 1 4 0v5"/><path d="M11 11V4a2 2 0 0 1 4 0v7"/><path d="M15 11V6a2 2 0 0 1 4 0v9a6 6 0 0 1-6 6h-1a6 6 0 0 1-4.5-2L4 14a2 2 0 0 1 3-3l2 2"/>',
  siren: '<path d="M6 18v-6a6 6 0 0 1 12 0v6"/><path d="M4 18h16"/><path d="M12 2v2"/><path d="M4.5 5.5l1.5 1.5"/><path d="M19.5 5.5L18 7"/>',
  chat: '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
};

function makeIcon(name) {
  const inner = ICONS[name] || ICONS.star;
  return `<svg class="svg-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${inner}</svg>`;
}

const MASCOT_SVG = `
<svg class="velo" viewBox="0 0 240 260" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <ellipse class="velo-shadow" cx="120" cy="246" rx="64" ry="11" fill="#3C3C3C" opacity=".10"/>
  <g class="velo-bob">
    <g class="velo-tilt">
      <ellipse class="velo-wing velo-wing-l" cx="42" cy="152" rx="25" ry="48" fill="#46A302"/>
      <ellipse class="velo-wing velo-wing-r" cx="198" cy="152" rx="25" ry="48" fill="#46A302"/>
      <ellipse cx="120" cy="142" rx="82" ry="92" fill="#58CC02"/>
      <ellipse cx="120" cy="166" rx="53" ry="61" fill="#8FE63D"/>
      <path class="velo-crest" d="M116 38l18 28h-13l9 24-28-33h14z" fill="#FFC800"/>
      <ellipse cx="56" cy="152" rx="17" ry="10" fill="#FF8FA3" opacity=".55"/>
      <ellipse cx="184" cy="152" rx="17" ry="10" fill="#FF8FA3" opacity=".55"/>
      <g class="velo-eye velo-eye-l" transform="translate(86 114)">
        <circle r="25" fill="#FFFFFF"/>
        <circle class="velo-pupil" cx="3" cy="4" r="11.5" fill="#2B2B2B"/>
        <circle cx="-3" cy="-2" r="4" fill="#FFFFFF"/>
      </g>
      <g class="velo-eye velo-eye-r" transform="translate(154 114)">
        <circle r="25" fill="#FFFFFF"/>
        <circle class="velo-pupil" cx="3" cy="4" r="11.5" fill="#2B2B2B"/>
        <circle cx="-3" cy="-2" r="4" fill="#FFFFFF"/>
      </g>
      <path d="M120 138l23 13-23 12-23-12 23-13z" fill="#FF9600"/>
      <path d="M120 163l15-8 8 4-23 12-23-12 8-4 15 8z" fill="#E07E00"/>
      <ellipse cx="76" cy="234" rx="20" ry="11" fill="#FF9600"/>
      <ellipse cx="164" cy="234" rx="20" ry="11" fill="#FF9600"/>
      <ellipse cx="64" cy="240" rx="7" ry="5" fill="#E07E00"/>
      <ellipse cx="76" cy="242" rx="7" ry="5" fill="#E07E00"/>
      <ellipse cx="152" cy="242" rx="7" ry="5" fill="#E07E00"/>
      <ellipse cx="164" cy="240" rx="7" ry="5" fill="#E07E00"/>
    </g>
  </g>
</svg>`;
