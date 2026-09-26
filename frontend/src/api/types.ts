export const TOPICS = ["python", "react", "javascript"] as const;
export const DIFFICULTIES = ["junior", "mid", "senior"] as const;

export type Topic = (typeof TOPICS)[number];
export type Difficulty = (typeof DIFFICULTIES)[number];

export type Session = {
  session_id: string;
  topic: Topic;
  difficulty: Difficulty;
};

export type Question = {
  question_id: string;
  prompt: string;
  topic: Topic;
  difficulty: Difficulty;
};

export type Grade = {
  score: number;
  verdict: string;
  covered: string[];
  missed: string[];
};

export type ExplanationPoint = {
  point: string;
  detail: string;
};

export type Explanation = {
  answer: string;
  points: ExplanationPoint[];
  pitfalls: string[];
};

export type SessionState = {
  session_id: string;
  topic: Topic;
  difficulty: Difficulty;
  current_question: Question | null;
  current_grade: Grade | null;
  current_explanation: Explanation | null;
};

export const MAX_SCORE = 5;
