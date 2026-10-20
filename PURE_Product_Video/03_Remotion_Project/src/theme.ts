import {loadFont} from '@remotion/fonts';
import {staticFile} from 'remotion';

export const COLORS = {
  midnightNavy: '#0B1726',
  deepSlate: '#142638',
  clinicalTeal: '#147D78',
  signalMint: '#35C4B5',
  coolIvory: '#F6F8F7',
  pureWhite: '#FFFFFF',
} as const;

export const FONT_FAMILY = 'Montserrat';
export const FONT_WEIGHTS = [400, 500, 600, 700, 800] as const;

for (const weight of FONT_WEIGHTS) {
  loadFont({
    family: FONT_FAMILY,
    url: staticFile(`fonts/montserrat-latin-${weight}-normal.woff2`),
    format: 'woff2',
    weight: String(weight),
    display: 'block',
  });
}

export const TYPE = {
  display: {fontSize: 96, fontWeight: 800, lineHeight: 1.02},
  h1: {fontSize: 62, fontWeight: 700, lineHeight: 1.08},
  h2: {fontSize: 40, fontWeight: 600, lineHeight: 1.2},
  body: {fontSize: 29, fontWeight: 400, lineHeight: 1.45},
  label: {fontSize: 18, fontWeight: 700, lineHeight: 1.2},
} as const;

export const LAYOUT = {
  marginX: 110,
  marginTop: 86,
  marginBottom: 82,
  radius: 28,
} as const;
