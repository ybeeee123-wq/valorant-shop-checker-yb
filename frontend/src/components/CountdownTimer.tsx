import { useEffect, useState } from 'react';
import { ClockIcon } from './Icons';

interface CountdownTimerProps {
  secondsRemaining: number;
  onExpire?: () => void;
  label?: string;
}

export default function CountdownTimer({ secondsRemaining, onExpire, label = 'Next rotation' }: CountdownTimerProps) {
  const [remaining, setRemaining] = useState(secondsRemaining);

  useEffect(() => {
    if (remaining <= 0) {
      onExpire?.();
      return;
    }
    const timeout = window.setTimeout(() => setRemaining((value) => Math.max(0, value - 1)), 1000);
    return () => window.clearTimeout(timeout);
  }, [remaining, onExpire]);

  const hours = Math.floor(remaining / 3600);
  const minutes = Math.floor((remaining % 3600) / 60);
  const seconds = remaining % 60;

  return (
    <div className="reset-timer" aria-label={`${label}: ${hours} hours, ${minutes} minutes, and ${seconds} seconds`}>
      <ClockIcon className="h-[17px] w-[17px]" />
      <span>{label}</span>
      <strong>{hours.toString().padStart(2, '0')}:{minutes.toString().padStart(2, '0')}:{seconds.toString().padStart(2, '0')}</strong>
    </div>
  );
}
