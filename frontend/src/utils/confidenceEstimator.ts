export type EstimatedAnswer = {
  parsed_intent: string;
  confidence: number;
  defaulted: boolean;
};

const KEYWORD_RULES: [RegExp, string, number][] = [
  [/\b(?:profit|margin|profitability)\b/i, "PROFIT", 0.9],
  [/\b(?:revenue|sales|growth)\b/i, "GROWTH", 0.85],
  [/\b(?:cost|spending|efficiency)\b/i, "COST", 0.9],
  [/\b(?:market|share|position)\b/i, "MARKET", 0.8],
  [/\b(?:board|directors|governance)\b/i, "BOARD", 0.9],
  [/\b(?:investors|shareholders)\b/i, "INVESTORS", 0.85],
  [/\b(?:executive|leadership|c-suite)\b/i, "EXECUTIVE", 0.85],
  [/\b(?:operations|ops|team)\b/i, "OPERATIONS", 0.8],
];

export function estimateConfidence(text: string): EstimatedAnswer {
  const trimmed = text.trim();

  if (trimmed === "" || trimmed.toLowerCase() === "skip") {
    return { parsed_intent: "DEFAULT", confidence: 0.0, defaulted: true };
  }

  for (const [pattern, intent, confidence] of KEYWORD_RULES) {
    if (pattern.test(trimmed)) {
      return { parsed_intent: intent, confidence, defaulted: false };
    }
  }

  return { parsed_intent: "UNKNOWN", confidence: 0.5, defaulted: false };
}
