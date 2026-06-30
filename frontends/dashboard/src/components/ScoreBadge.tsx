interface ScoreBadgeProps {
  score: number;
}

export function ScoreBadge({ score }: ScoreBadgeProps) {
  const color =
    score >= 70
      ? 'bg-green-100 text-green-700'
      : score >= 40
        ? 'bg-yellow-100 text-yellow-700'
        : 'bg-gray-100 text-gray-700';

  return (
    <span className={`inline-flex min-w-12 justify-center rounded-full px-2 py-1 text-xs font-semibold ${color}`}>
      {Math.round(score)}
    </span>
  );
}
