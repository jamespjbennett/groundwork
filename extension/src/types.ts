export interface AnalyseResult {
  skipped: boolean;
  reason?: string;
  concepts: string[];
  novel_concept: string;
  explanation: string;
  challenge_question: string;
  confidence_before: number;
}
