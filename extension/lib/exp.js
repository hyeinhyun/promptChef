// EXP / 인사고과 로직. 결재 완료 클릭 = +20 EXP.

export const EXP_PER_APPROVAL = 20;

export const LEVELS = [
  { level: 1, title: "수습", min: 0, max: 99 },
  { level: 2, title: "대리", min: 100, max: 299 },
  { level: 3, title: "팀장", min: 300, max: Infinity }
];

export function levelFromExp(exp) {
  for (const L of LEVELS) if (exp >= L.min && exp <= L.max) return L;
  return LEVELS[LEVELS.length - 1];
}

export function progressInLevel(exp) {
  const L = levelFromExp(exp);
  if (L.max === Infinity) return { ratio: 1, current: exp - L.min, span: 0, isMax: true };
  const span = L.max - L.min + 1;
  const current = exp - L.min;
  return { ratio: Math.min(1, current / span), current, span, isMax: false };
}

export function awardApproval(currentExp) {
  const before = levelFromExp(currentExp);
  const nextExp = currentExp + EXP_PER_APPROVAL;
  const after = levelFromExp(nextExp);
  return {
    nextExp,
    leveledUp: after.level > before.level,
    before,
    after
  };
}
