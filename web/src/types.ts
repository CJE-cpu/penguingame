export interface User {
  id: string;
  email: string;
  nickname: string;
}
export interface Score {
  id: string;
  score: number;
  fish: number;
  rescued: number;
  seconds: number;
  cleared: boolean;
  date: string;
  source: string;
}
export interface Rank {
  rank: number;
  nickname: string;
  score: number;
  fish: number;
  rescued: number;
  cleared: boolean;
  date: string;
  isMe?: boolean;
}
export interface DashboardData {
  demo: boolean;
  summary: {
    best: number;
    average: number;
    games: number;
    clears: number;
    rank: number | null;
  };
  records: Score[];
  trend: Score[];
  leaderboard: Rank[];
}
export interface DesktopRecord {
  run: string;
  name: string;
  score: number;
  fish: number;
  rescued: number;
  seconds: number;
  cleared: boolean;
  date: string;
}
